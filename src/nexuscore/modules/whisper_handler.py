"""
Whisper 依存のラッパーモジュール。

- whisper パッケージが無い環境でも import だけは通るようにする
- 実際に機能を使う場合は WHISPER_AVAILABLE を確認するか、
  _require_whisper() を経由してエラーを出す
"""

from __future__ import annotations

try:
    import whisper  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover - optional dependency path
    whisper = None  # type: ignore[assignment]


WHISPER_AVAILABLE: bool = whisper is not None  # type: ignore[truthy-function]


def _require_whisper() -> None:
    if whisper is None:
        raise RuntimeError(
            "whisper is not installed. Install `openai-whisper` to use audio features."
        )


# model は遅延読み込みにする（import 時にエラーを避けるため）
_model = None


def _get_model():
    """モデルを遅延読み込みする"""
    _require_whisper()
    global _model
    if _model is None:
        _model = whisper.load_model("small")  # type: ignore[union-attr]
    return _model


def transcribe_audio(audio_path: str) -> str:
    try:
        model = _get_model()
        result = model.transcribe(audio_path)
        return result["text"]
    except Exception as e:
        return f"文字起こし中にエラーが発生しました: {e}"
