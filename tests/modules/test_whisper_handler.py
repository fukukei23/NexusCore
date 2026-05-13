"""Tests for whisper_handler module."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


class TestWhisperAvailability:
    """WHISPER_AVAILABLE flag tests."""

    def test_available_flag_is_bool(self):
        from nexuscore.modules.whisper_handler import WHISPER_AVAILABLE

        assert isinstance(WHISPER_AVAILABLE, bool)


class TestRequireWhisper:
    """_require_whisper() tests."""

    @patch("nexuscore.modules.whisper_handler.whisper", None)
    def test_require_whisper_raises_when_none(self):
        from nexuscore.modules.whisper_handler import _require_whisper

        with pytest.raises(RuntimeError, match="whisper is not installed"):
            _require_whisper()

    @patch("nexuscore.modules.whisper_handler.whisper", MagicMock())
    def test_require_whisper_passes_when_available(self):
        from nexuscore.modules.whisper_handler import _require_whisper

        _require_whisper()  # should not raise


class TestTranscribeAudio:
    """transcribe_audio() tests."""

    @patch("nexuscore.modules.whisper_handler.whisper", None)
    def test_transcribe_without_whisper_returns_error(self):
        from nexuscore.modules.whisper_handler import transcribe_audio

        result = transcribe_audio("/fake/audio.wav")
        assert "エラー" in result

    @patch("nexuscore.modules.whisper_handler._get_model")
    def test_transcribe_returns_text(self, mock_get_model):
        mock_model = MagicMock()
        mock_model.transcribe.return_value = {"text": "hello world"}
        mock_get_model.return_value = mock_model

        from nexuscore.modules.whisper_handler import transcribe_audio

        result = transcribe_audio("/fake/audio.wav")
        assert result == "hello world"

    @patch("nexuscore.modules.whisper_handler._get_model")
    def test_transcribe_handles_exception(self, mock_get_model):
        mock_get_model.side_effect = RuntimeError("whisper is not installed")

        from nexuscore.modules.whisper_handler import transcribe_audio

        result = transcribe_audio("/fake/audio.wav")
        assert "エラー" in result


class TestGetModel:
    """_get_model() lazy loading tests."""

    @patch("nexuscore.modules.whisper_handler.whisper", None)
    def test_get_model_raises_without_whisper(self):
        import nexuscore.modules.whisper_handler as mod

        mod._model = None
        with pytest.raises(RuntimeError):
            mod._get_model()

    @patch("nexuscore.modules.whisper_handler.whisper")
    def test_get_model_loads_once(self, mock_whisper):
        import nexuscore.modules.whisper_handler as mod

        mock_whisper.load_model.return_value = MagicMock(name="loaded_model")
        mod._model = None

        model1 = mod._get_model()
        model2 = mod._get_model()
        assert model1 is model2
        mock_whisper.load_model.assert_called_once_with("small")

        # cleanup
        mod._model = None
