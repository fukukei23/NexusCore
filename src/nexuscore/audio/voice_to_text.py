"""Utilities for recording audio, invoking Whisper, and light-weight helpers.

This module deliberately keeps the runtime dependencies optional so that
importing it never fails even when audio/translation libraries are missing.
"""

from __future__ import annotations

import logging
import os
import tempfile
import threading
import time
from collections.abc import Callable
from contextlib import AbstractContextManager
from pathlib import Path
from typing import TypeAlias

import numpy as np
import openai
import sounddevice as sd
from dotenv import load_dotenv
from scipy.io.wavfile import write

try:  # Optional dependencies for feature toggles
    from google.cloud import translate_v2 as google_translate
except Exception:  # pragma: no cover - optional dependency
    google_translate = None

try:
    import langdetect
except Exception:  # pragma: no cover - optional dependency
    langdetect = None

logger = logging.getLogger(__name__)
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

AudioInput: TypeAlias = str | bytes | np.ndarray
StreamFactory: TypeAlias = Callable[[Callable[[np.ndarray, int, float, object], None]], AbstractContextManager[object]]

_DEFAULT_CONFIG: dict[str, str | int] = {
    "language": os.getenv("VOICE_TO_TEXT_TARGET_LANG", "en"),
    "model_size": os.getenv("VOICE_TO_TEXT_MODEL_SIZE", "base"),
    "sample_rate": int(os.getenv("VOICE_TO_TEXT_SAMPLE_RATE", 16000)),
    "channels": int(os.getenv("VOICE_TO_TEXT_CHANNELS", 1)),
}
_AUDIO_CONFIG: dict[str, str | int] = dict(_DEFAULT_CONFIG)
_MODEL_STATE = {"initialized": False, "loaded": False}


def _update_audio_config(config: dict[str, str | int]) -> dict[str, str | int]:
    """内部設定を書き換えてコピーを返す（直接の外部参照を避ける）。"""
    _AUDIO_CONFIG.update(config)
    return dict(_AUDIO_CONFIG)


def _reset_audio_config() -> dict[str, str | int]:
    """内部設定をデフォルトに戻す。"""
    _AUDIO_CONFIG.update(_DEFAULT_CONFIG)
    return dict(_AUDIO_CONFIG)


def _set_model_state_flag(key: str, value: bool) -> None:
    """モデル状態フラグの更新を一箇所にまとめる。"""
    _MODEL_STATE[key] = value


def _reset_model_state() -> None:
    """モデル状態を初期状態に戻す。"""
    _MODEL_STATE.update({"initialized": False, "loaded": False})


_translate_client: google_translate.Client | None = None
_whisper_client: WhisperClient | None = None

# NOTE: 下記には内部ユーティリティも含まれるが、後方互換のため __all__ からは削除しない。
__all__ = [
    "record_until_keypress",
    "transcribe",
    "process_audio",
    "load_audio_file",
    "save_transcription",
    "convert_audio",
    "extract_features",
    "recognize_speech",
    "whisper_transcribe",
    "load_whisper_model",
    "whisper_process",
    "transcribe_with_whisper",
    "initialize_whisper",
    "process_audio_stream",
    "stream_transcribe",
    "real_time_transcribe",
    "continuous_recognition",
    "streaming_decode",
    "cleanup",
    "release_resources",
    "close_model",
    "clear_cache",
    "free_memory",
    "reset_session",
    "initialize_model",
    "load_model",
    "unload_model",
    "get_model_info",
    "set_model_config",
    "reset_model",
    "supported_formats",
    "can_process_format",
    "set_language",
    "set_model_size",
    "configure_audio",
    "configure_settings",
    "get_config",
    "update_settings",
    "reset_config",
    "detect_language",
    "translate_text",
    "multi_language_support",
]


class WhisperClient:
    """Thin wrapper around the OpenAI Whisper API with graceful degradation."""

    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model or os.getenv("WHISPER_MODEL", "whisper-1")
        self.default_language = os.getenv("WHISPER_LANGUAGE", "ja")
        if self.api_key:
            openai.api_key = self.api_key

    @property
    def ready(self) -> bool:
        """APIキーが設定されているかどうかを返す。"""
        return bool(self.api_key)

    def transcribe_file(self, audio_path: str, *, language: str | None = None) -> str | None:
        if not self.ready:
            logger.warning("OpenAI API キーが設定されていないため、Whisper を利用できません。")
            return None
        lang = language or self.default_language
        try:
            with open(audio_path, "rb") as audio_file:
                response = openai.audio.transcriptions.create(
                    model=self.model,
                    file=audio_file,
                    language=lang,
                    response_format="text",
                )
        except Exception as exc:  # pragma: no cover - runtime failure path
            logger.error("Whisper transcription に失敗しました: %s (%r)", exc, exc)
            return None
        return response


def _get_whisper_client() -> WhisperClient:
    """Whisper クライアントを遅延初期化し、設定が無ければデフォルトで返す。"""
    global _whisper_client
    if _whisper_client is None:
        _whisper_client = WhisperClient()
    return _whisper_client


def _get_translate_client() -> google_translate.Client | None:
    """翻訳クライアントを遅延初期化し、失敗時はログを残して None を返す。"""
    global _translate_client
    if _translate_client is not None:
        return _translate_client
    if google_translate is None:  # pragma: no cover
        logger.debug("google-cloud-translate がインポートできないため翻訳を無効化します。")
        return None
    try:
        _translate_client = google_translate.Client()
    except Exception as exc:  # pragma: no cover - credentials missing
        logger.warning("google-cloud-translate の初期化に失敗しました: %s", exc)
        _translate_client = None
    return _translate_client


def _as_audio_file(audio_input: AudioInput, sample_rate: int) -> tuple[str, Callable[[], None]]:
    """Return a file path for the input and a cleanup callback."""
    if isinstance(audio_input, str):
        path = Path(audio_input)
        if not path.exists():
            raise FileNotFoundError(audio_input)
        return str(path), lambda: None
    if isinstance(audio_input, bytes):
        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        tmp.write(audio_input)
        tmp.close()
        return tmp.name, lambda: os.unlink(tmp.name)
    if isinstance(audio_input, np.ndarray):
        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        write(tmp.name, sample_rate, audio_input)
        return tmp.name, lambda: os.unlink(tmp.name)
    raise TypeError(f"サポートされていない入力形式です: {type(audio_input)!r}")


def record_until_keypress(
    max_duration: int = 60,
    sample_rate: int | None = None,
    *,
    input_func: Callable[[], str] = input,
    stream_factory: StreamFactory | None = None,
) -> tuple[np.ndarray | None, int]:
    """Record audio until Enter is pressed or the timeout hits.

    Parameters
    ----------
    max_duration: 秒数上限。
    sample_rate: 録音レート。None の場合は設定から取得。
    input_func: テスト時に置き換え可能な入力関数。
    stream_factory: sounddevice.InputStream を差し替えるためのファクトリ。
    """

    sr = int(sample_rate or _AUDIO_CONFIG["sample_rate"])
    recording: list[np.ndarray] = []
    event = threading.Event()
    start_time = time.time()

    def callback(indata, frames, _time, _status):
        if time.time() - start_time > max_duration:
            event.set()
            raise sd.CallbackAbort
        recording.append(indata.copy())

    def default_stream_factory(cb) -> AbstractContextManager[object]:
        return sd.InputStream(samplerate=sr, channels=int(_AUDIO_CONFIG["channels"]), callback=cb)

    stream_ctx = stream_factory(callback) if stream_factory else default_stream_factory(callback)

    def key_thread():
        try:
            input_func()
        finally:
            event.set()

    capture = threading.Thread(target=lambda: _wait_for_stream(stream_ctx, event))
    capture.start()
    trigger = threading.Thread(target=key_thread)
    trigger.start()
    trigger.join(timeout=max_duration)
    capture.join(timeout=1)

    if recording:
        return np.concatenate(recording, axis=0), sr
    return None, sr


def _wait_for_stream(stream_ctx: AbstractContextManager[object], event: threading.Event) -> None:
    with stream_ctx:
        event.wait()


def transcribe_with_whisper(
    audio_input: AudioInput, *, language: str | None = None
) -> str | None:
    """Transcribe the provided audio input via Whisper."""
    client = _get_whisper_client()
    sample_rate = int(_AUDIO_CONFIG["sample_rate"])
    try:
        audio_path, cleanup = _as_audio_file(audio_input, sample_rate)
    except (FileNotFoundError, TypeError) as exc:
        logger.warning("音声ファイルを用意できませんでした: %s", exc)
        return None
    try:
        return client.transcribe_file(audio_path, language=language)
    finally:
        cleanup()


def transcribe(audio_input: AudioInput, *, language: str | None = None) -> str | None:
    return transcribe_with_whisper(audio_input, language=language)


def process_audio(audio_input: AudioInput) -> dict[str, int | float]:
    """Return simple statistics for the provided audio payload."""
    if isinstance(audio_input, bytes):
        length = len(audio_input)
    elif isinstance(audio_input, np.ndarray):
        length = audio_input.size
    elif isinstance(audio_input, str) and Path(audio_input).exists():
        length = Path(audio_input).stat().st_size
    else:
        length = 0
    return {"length": length, "sample_rate": _AUDIO_CONFIG["sample_rate"]}  # type: ignore[dict-item]


def load_audio_file(path: str) -> bytes | None:
    try:
        with open(path, "rb") as stream:
            return stream.read()
    except FileNotFoundError:
        logger.warning("音声ファイルが見つかりません: %s", path)
        return None


def save_transcription(path: str, data: str) -> bool:
    try:
        Path(path).write_text(data, encoding="utf-8")
        return True
    except OSError as exc:
        logger.error("文字起こしの保存に失敗しました: %s", exc)
        return False


def convert_audio(path: str, target_format: str = "wav") -> str:
    logger.info("%s を %s 形式として扱います", path, target_format)
    return str(path)


def extract_features(audio_input: AudioInput) -> dict[str, float]:
    stats = process_audio(audio_input)
    stats.update({"mean": 0.0, "std": 0.0})
    return stats


def recognize_speech(audio_input: AudioInput) -> str | None:
    return transcribe(audio_input)


def whisper_transcribe(audio_input: AudioInput) -> str | None:
    return transcribe(audio_input)


def whisper_process(audio_input: AudioInput) -> dict[str, int | float]:
    return process_audio(audio_input)


def load_whisper_model() -> bool:
    return _get_whisper_client().ready


def initialize_whisper() -> bool:
    return load_whisper_model()


def process_audio_stream(stream) -> str | None:
    chunk = stream.read()
    if not chunk:
        return None
    return transcribe(chunk)


def stream_transcribe(stream) -> str | None:
    return process_audio_stream(stream)


def real_time_transcribe(stream) -> str | None:
    return process_audio_stream(stream)


def continuous_recognition(stream) -> list[str]:
    result = process_audio_stream(stream)
    return [result] if result else []


def streaming_decode(stream) -> str | None:
    result = process_audio_stream(stream)
    return result or None


def cleanup() -> bool:
    return release_resources()


def release_resources() -> bool:
    _reset_model_state()
    return True


def close_model() -> bool:
    return release_resources()


def clear_cache() -> bool:
    return True


def free_memory() -> bool:
    return True


def reset_session() -> bool:
    return True


def initialize_model() -> bool:
    _set_model_state_flag("initialized", True)
    return True


def load_model() -> bool:
    _set_model_state_flag("loaded", True)
    return True


def unload_model() -> bool:
    _set_model_state_flag("loaded", False)
    return True


def get_model_info() -> dict[str, str | int | bool]:
    info = dict(_AUDIO_CONFIG)
    info.update(_MODEL_STATE)
    return info


def set_model_config(config: dict[str, str | int]) -> dict[str, str | int]:
    return _update_audio_config(config)


def reset_model() -> bool:
    _reset_audio_config()
    release_resources()
    return True


def supported_formats() -> list[str]:
    return [".wav", ".mp3", ".flac", ".ogg", ".m4a", ".aac"]


def can_process_format(ext: str) -> bool:
    return ext.lower() in supported_formats()


def set_language(lang: str) -> str:
    if lang:
        _AUDIO_CONFIG["language"] = lang
    return str(_AUDIO_CONFIG["language"])


def set_model_size(size: str) -> str:
    if size:
        _AUDIO_CONFIG["model_size"] = size
    return str(_AUDIO_CONFIG["model_size"])


def configure_audio(config: dict[str, str | int]) -> dict[str, str | int]:
    return set_model_config(config)


def configure_settings(config: dict[str, str | int]) -> dict[str, str | int]:
    return configure_audio(config)


def get_config() -> dict[str, str | int]:
    return dict(_AUDIO_CONFIG)


def update_settings(config: dict[str, str | int]) -> dict[str, str | int]:
    return set_model_config(config)


def reset_config() -> dict[str, str | int]:
    return _reset_audio_config()


def detect_language(text: str | None) -> str | None:
    """Detect language using langdetect or google translate client."""
    if not text:
        return None
    if langdetect:
        try:
            return langdetect.detect(text)
        except Exception:  # pragma: no cover
            logger.debug("langdetect で言語判定に失敗しました。", exc_info=True)
    client = _get_translate_client()
    if client is None:
        return None
    try:
        result = client.detect_language(text)
    except Exception:  # pragma: no cover
        logger.debug("google-cloud-translate で言語判定に失敗しました。", exc_info=True)
        return None
    if isinstance(result, list) and result:
        return result[0].get("language")
    if isinstance(result, dict):
        return result.get("language")
    return None


def translate_text(text: str | None, target_lang: str | None = None) -> str | None:
    """Translate text to target language when client is available."""
    if not text:
        return text
    client = _get_translate_client()
    if client is None:
        return text
    target = target_lang or _AUDIO_CONFIG["language"]
    try:
        response = client.translate(text, target_language=target)
    except Exception:  # pragma: no cover
        logger.warning("翻訳処理に失敗しました。", exc_info=True)
        return text
    if isinstance(response, list):
        return response[0].get("translatedText", text)
    return response.get("translatedText", text)


def multi_language_support(text: str, target_lang: str | None = None) -> str | None:
    """Detect and translate text when必要; 同一言語ならそのまま返す。"""
    detected = detect_language(text)
    target = target_lang or _AUDIO_CONFIG["language"]
    if detected and detected == target:
        return text
    return translate_text(text, target_lang=str(target))
