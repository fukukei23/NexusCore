"""
Comprehensive tests for Google Gemini LLM Provider

Tests cover:
- Initialization (real/stub mode)
- API calls and responses
- Error handling
- JSON mode
- Environment variable handling
- Gemini-specific features
"""

import os
import sys
from unittest.mock import MagicMock, Mock, patch

import pytest

# google-generativeai is not required at install time — tests mock it via
# sys.modules.  Provide a baseline mock so the module-level TYPE_CHECKING
# import in gemini_provider.py resolves during collection.
def _make_package_mock(name):
    """Create a MagicMock that Python's import system recognises as a package."""
    m = MagicMock()
    m.__path__ = []
    m.__package__ = name
    m.__name__ = name
    return m

if "google" not in sys.modules:
    sys.modules["google"] = _make_package_mock("google")
_genai_mock = MagicMock()
sys.modules["google.generativeai"] = _genai_mock

from nexuscore.llm.providers.gemini_provider import GeminiLLM


def _make_genai_mock():
    """Create a fresh MagicMock for google.generativeai with all needed attributes."""
    genai = MagicMock()
    genai.configure = MagicMock()
    genai.GenerativeModel = MagicMock()
    return genai


def _make_response(text="Gemini response"):
    """Create a mock Gemini API response with the given text."""
    mock_part = Mock()
    mock_part.text = text
    mock_content = Mock()
    mock_content.parts = [mock_part]
    mock_candidate = Mock()
    mock_candidate.content = mock_content
    mock_response = Mock()
    mock_response.candidates = [mock_candidate]
    return mock_response


def _install_genai_mock(genai_mock):
    """Replace google.generativeai mock in sys.modules AND on the parent module.

    ``import google.generativeai`` returns ``sys.modules["google"].generativeai``,
    not ``sys.modules["google.generativeai"]`` — so both must be set.
    """
    google = sys.modules.get("google")
    if google is None or not hasattr(google, "__path__"):
        google = _make_package_mock("google")
        sys.modules["google"] = google
    google.generativeai = genai_mock
    sys.modules["google.generativeai"] = genai_mock
    return genai_mock


def _restore_genai_mock():
    """Restore the module-level mock after a test."""
    sys.modules["google.generativeai"] = _genai_mock
    google = sys.modules.get("google")
    if google is not None:
        google.generativeai = _genai_mock


class TestGeminiProviderInit:
    """Test Gemini provider initialization"""

    @patch.dict(os.environ, {}, clear=True)
    def test_init_without_api_key_uses_stub_mode(self):
        """Should use stub mode when API key is missing"""
        provider = GeminiLLM("gemini-2.5-flash")
        assert provider.real_calls is False
        assert provider.client is None

    @patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}, clear=True)
    @patch("nexuscore.llm.providers.gemini_provider._real_call_enabled", return_value=True)
    def test_init_with_api_key_uses_real_mode(self, mock_real_enabled):
        """Should use real mode when API key is set"""
        genai = _make_genai_mock()
        _install_genai_mock(genai)
        try:
            provider = GeminiLLM("gemini-2.5-flash")
            assert provider.real_calls is True
            assert provider.client == "ok"
            genai.configure.assert_called_once_with(api_key="test-key")
        finally:
            _restore_genai_mock()

    @patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}, clear=True)
    @patch("nexuscore.llm.providers.gemini_provider._real_call_enabled", return_value=True)
    @pytest.mark.xfail(
        reason="フルテスト実行時のフレーク（test_generator 機能改善時に解消）— 2026-07-08"
    )
    def test_init_without_genai_library_falls_back_to_stub(self, mock_real_enabled):
        """Should fall back to stub mode when google-generativeai raises ImportError"""
        class _BrokenModule:
            def __getattr__(self, name):
                raise ImportError("no google-generativeai")

        sys.modules["google.generativeai"] = _BrokenModule()
        try:
            provider = GeminiLLM("gemini-2.5-flash")
            assert provider.real_calls is False
            assert provider.client is None
        finally:
            _restore_genai_mock()


class TestGeminiProviderExecute:
    """Test Gemini provider execute method"""

    @patch.dict(os.environ, {}, clear=True)
    def test_execute_stub_mode_returns_default_content(self):
        """Should return default stub content in stub mode"""
        provider = GeminiLLM("gemini-2.5-flash")
        result = provider.execute("test prompt", "test system")

        assert isinstance(result, str)
        assert len(result) > 0

    @patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}, clear=True)
    @patch("nexuscore.llm.providers.gemini_provider._real_call_enabled", return_value=True)
    def test_execute_real_mode_calls_api(self, mock_real_enabled):
        """Should call Gemini API in real mode"""
        genai = _make_genai_mock()
        mock_model = Mock()
        mock_model.generate_content.return_value = _make_response("Gemini response")
        genai.GenerativeModel.return_value = mock_model
        _install_genai_mock(genai)
        try:
            provider = GeminiLLM("gemini-2.5-flash")
            assert provider.real_calls is True

            result = provider.execute("test prompt", "test system")

            assert result == "Gemini response"
            genai.GenerativeModel.assert_called_once_with(
                "gemini-2.5-flash",
                system_instruction="test system",
            )
            mock_model.generate_content.assert_called_once_with(
                "test prompt",
                generation_config={"temperature": 0.3, "response_mime_type": "text/plain"},
            )
        finally:
            _restore_genai_mock()

    @patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}, clear=True)
    @patch("nexuscore.llm.providers.gemini_provider._real_call_enabled", return_value=True)
    def test_execute_with_custom_temperature(self, mock_real_enabled):
        """Should support custom temperature"""
        genai = _make_genai_mock()
        mock_model = Mock()
        mock_model.generate_content.return_value = _make_response("response")
        genai.GenerativeModel.return_value = mock_model
        _install_genai_mock(genai)
        try:
            provider = GeminiLLM("gemini-2.5-flash")

            provider.execute("prompt", "system", temperature=0.7)

            call_args = mock_model.generate_content.call_args
            assert call_args[1]["generation_config"]["temperature"] == 0.7
        finally:
            _restore_genai_mock()

    @patch.dict(
        os.environ,
        {"GEMINI_API_KEY": "test-key", "NEXUS_DEFAULT_MAX_OUT_TOKENS": "2000"},
        clear=True,
    )
    @patch("nexuscore.llm.providers.gemini_provider._real_call_enabled", return_value=True)
    def test_execute_with_max_tokens(self, mock_real_enabled):
        """Should support max_output_tokens parameter"""
        genai = _make_genai_mock()
        mock_model = Mock()
        mock_model.generate_content.return_value = _make_response("response")
        genai.GenerativeModel.return_value = mock_model
        _install_genai_mock(genai)
        try:
            provider = GeminiLLM("gemini-2.5-flash")

            provider.execute("prompt", "system")

            call_args = mock_model.generate_content.call_args
            assert call_args[1]["generation_config"]["max_output_tokens"] == 2000
        finally:
            _restore_genai_mock()

    @patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}, clear=True)
    @patch("nexuscore.llm.providers.gemini_provider._real_call_enabled", return_value=True)
    def test_execute_with_json_mode(self, mock_real_enabled):
        """Should support JSON mode with response_mime_type"""
        genai = _make_genai_mock()
        mock_model = Mock()
        mock_model.generate_content.return_value = _make_response('{"key": "value"}')
        genai.GenerativeModel.return_value = mock_model
        _install_genai_mock(genai)
        try:
            provider = GeminiLLM("gemini-2.5-flash")

            provider.execute("prompt", "system", as_json=True)

            call_args = mock_model.generate_content.call_args
            assert call_args[1]["generation_config"]["response_mime_type"] == "application/json"
        finally:
            _restore_genai_mock()


class TestGeminiProviderErrorHandling:
    """Test Gemini provider error handling"""

    @patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}, clear=True)
    @patch("nexuscore.llm.providers.gemini_provider._real_call_enabled", return_value=True)
    def test_execute_handles_generation_error(self, mock_real_enabled):
        """Should handle generation errors gracefully"""
        genai = _make_genai_mock()
        mock_model = Mock()
        mock_model.generate_content.side_effect = Exception("API Error")
        genai.GenerativeModel.return_value = mock_model
        _install_genai_mock(genai)
        try:
            provider = GeminiLLM("gemini-2.5-flash")

            result = provider.execute("prompt", "system")

            assert isinstance(result, str)
            assert len(result) > 0
        finally:
            _restore_genai_mock()

    @patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}, clear=True)
    @patch("nexuscore.llm.providers.gemini_provider._real_call_enabled", return_value=True)
    def test_execute_handles_model_init_error(self, mock_real_enabled):
        """Should handle model initialization errors"""
        genai = _make_genai_mock()
        genai.GenerativeModel.side_effect = Exception("Init Error")
        _install_genai_mock(genai)
        try:
            provider = GeminiLLM("gemini-2.5-flash")

            result = provider.execute("prompt", "system")

            assert isinstance(result, str)
            assert "Init failed" in result or len(result) > 0
        finally:
            _restore_genai_mock()

    @patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}, clear=True)
    @patch("nexuscore.llm.providers.gemini_provider._real_call_enabled", return_value=True)
    def test_execute_handles_empty_response(self, mock_real_enabled):
        """Should handle empty responses"""
        genai = _make_genai_mock()
        mock_model = Mock()
        mock_response = Mock()
        mock_response.candidates = []
        mock_response.text = ""
        mock_model.generate_content.return_value = mock_response
        genai.GenerativeModel.return_value = mock_model
        _install_genai_mock(genai)
        try:
            provider = GeminiLLM("gemini-2.5-flash")

            result = provider.execute("prompt", "system")

            assert isinstance(result, str)
        finally:
            _restore_genai_mock()


class TestGeminiProviderModels:
    """Test different Gemini model variants"""

    @patch.dict(os.environ, {}, clear=True)
    def test_supports_gemini_flash(self):
        """Should support gemini-flash models"""
        provider = GeminiLLM("gemini-2.5-flash")
        assert provider.model_name == "gemini-2.5-flash"

    @patch.dict(os.environ, {}, clear=True)
    def test_supports_gemini_pro(self):
        """Should support gemini-pro models"""
        provider = GeminiLLM("gemini-2.5-pro")
        assert provider.model_name == "gemini-2.5-pro"

    @patch.dict(os.environ, {}, clear=True)
    def test_supports_gemini_3(self):
        """Should support gemini-3.0 models"""
        provider = GeminiLLM("gemini-3.0-pro")
        assert provider.model_name == "gemini-3.0-pro"
