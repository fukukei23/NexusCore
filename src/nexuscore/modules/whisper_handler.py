from __future__ import annotations

try:
    import whisper
except ImportError:  # pragma: no cover - optional dependency path
    whisper = None


WHISPER_AVAILABLE: bool = whisper is not None


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
        _model = whisper.load_model("small")
    return _model


def transcribe_audio(audio_path: str) -> str:
    try:
        model = _get_model()
        result = model.transcribe(audio_path)
        return result["text"]
    except Exception as e:  # noqa: BLE001 — Whisper SDK呼び出し全体のフォールバック
        import logging
        logging.getLogger(__name__).error(f"Whisper transcription failed: {e}", exc_info=True)
        return ""
