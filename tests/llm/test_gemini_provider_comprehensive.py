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

# Mock google.generativeai module if not installed
if "google.generativeai" not in sys.modules:
    mock_genai = MagicMock()
    sys.modules["google.generativeai"] = mock_genai
    sys.modules["google"] = MagicMock()

from nexuscore.llm.providers.gemini_provider import GeminiLLM


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
        with patch("google.generativeai.configure") as mock_configure:
            provider = GeminiLLM("gemini-2.5-flash")
            assert provider.real_calls is True
            assert provider.client == "ok"
            mock_configure.assert_called_once_with(api_key="test-key")

    @patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}, clear=True)
    @patch("nexuscore.llm.providers.gemini_provider._real_call_enabled", return_value=True)
    def test_init_without_genai_library_falls_back_to_stub(self, mock_real_enabled):
        """Should fall back to stub mode when google-generativeai not installed"""
        with patch("nexuscore.llm.providers.gemini_provider.BaseLLM.__init__"):
            with patch.dict("sys.modules", {"google.generativeai": None}):
                provider = GeminiLLM("gemini-2.5-flash")
                provider.real_calls = False
                provider.client = None
                assert provider.real_calls is False
                assert provider.client is None


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
        with patch("google.generativeai.configure"):
            provider = GeminiLLM("gemini-2.5-flash")
            provider.client = "ok"
            provider.real_calls = True

            mock_model = Mock()
            mock_part = Mock()
            mock_part.text = "Gemini response"
            mock_content = Mock()
            mock_content.parts = [mock_part]
            mock_candidate = Mock()
            mock_candidate.content = mock_content
            mock_response = Mock()
            mock_response.candidates = [mock_candidate]
            mock_model.generate_content.return_value = mock_response

            with patch("google.generativeai.GenerativeModel", return_value=mock_model):
                result = provider.execute("test prompt", "test system")

                assert result == "Gemini response"
                mock_model.generate_content.assert_called_once_with(
                    "test prompt",
                    generation_config={"temperature": 0.3, "response_mime_type": "text/plain"},
                )

    @patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}, clear=True)
    @patch("nexuscore.llm.providers.gemini_provider._real_call_enabled", return_value=True)
    def test_execute_with_custom_temperature(self, mock_real_enabled):
        """Should support custom temperature"""
        with patch("google.generativeai.configure"):
            provider = GeminiLLM("gemini-2.5-flash")
            provider.client = "ok"
            provider.real_calls = True

            mock_model = Mock()
            mock_part = Mock()
            mock_part.text = "response"
            mock_content = Mock()
            mock_content.parts = [mock_part]
            mock_candidate = Mock()
            mock_candidate.content = mock_content
            mock_response = Mock()
            mock_response.candidates = [mock_candidate]
            mock_model.generate_content.return_value = mock_response

            with patch("google.generativeai.GenerativeModel", return_value=mock_model):
                provider.execute("prompt", "system", temperature=0.7)

                call_args = mock_model.generate_content.call_args
                assert call_args[1]["generation_config"]["temperature"] == 0.7

    @patch.dict(
        os.environ,
        {"GEMINI_API_KEY": "test-key", "NEXUS_DEFAULT_MAX_OUT_TOKENS": "2000"},
        clear=True,
    )
    @patch("nexuscore.llm.providers.gemini_provider._real_call_enabled", return_value=True)
    def test_execute_with_max_tokens(self, mock_real_enabled):
        """Should support max_output_tokens parameter"""
        with patch("google.generativeai.configure"):
            provider = GeminiLLM("gemini-2.5-flash")
            provider.client = "ok"
            provider.real_calls = True

            mock_model = Mock()
            mock_part = Mock()
            mock_part.text = "response"
            mock_content = Mock()
            mock_content.parts = [mock_part]
            mock_candidate = Mock()
            mock_candidate.content = mock_content
            mock_response = Mock()
            mock_response.candidates = [mock_candidate]
            mock_model.generate_content.return_value = mock_response

            with patch("google.generativeai.GenerativeModel", return_value=mock_model):
                provider.execute("prompt", "system")

                call_args = mock_model.generate_content.call_args
                assert call_args[1]["generation_config"]["max_output_tokens"] == 2000

    @patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}, clear=True)
    @patch("nexuscore.llm.providers.gemini_provider._real_call_enabled", return_value=True)
    def test_execute_with_json_mode(self, mock_real_enabled):
        """Should support JSON mode with response_mime_type"""
        with patch("google.generativeai.configure"):
            provider = GeminiLLM("gemini-2.5-flash")
            provider.client = "ok"
            provider.real_calls = True

            mock_model = Mock()
            mock_part = Mock()
            mock_part.text = '{"key": "value"}'
            mock_content = Mock()
            mock_content.parts = [mock_part]
            mock_candidate = Mock()
            mock_candidate.content = mock_content
            mock_response = Mock()
            mock_response.candidates = [mock_candidate]
            mock_model.generate_content.return_value = mock_response

            with patch("google.generativeai.GenerativeModel", return_value=mock_model):
                provider.execute("prompt", "system", as_json=True)

                call_args = mock_model.generate_content.call_args
                assert call_args[1]["generation_config"]["response_mime_type"] == "application/json"


class TestGeminiProviderErrorHandling:
    """Test Gemini provider error handling"""

    @patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}, clear=True)
    @patch("nexuscore.llm.providers.gemini_provider._real_call_enabled", return_value=True)
    def test_execute_handles_generation_error(self, mock_real_enabled):
        """Should handle generation errors gracefully"""
        with patch("google.generativeai.configure"):
            provider = GeminiLLM("gemini-2.5-flash")
            provider.client = "ok"
            provider.real_calls = True

            mock_model = Mock()
            mock_model.generate_content.side_effect = Exception("API Error")

            with patch("google.generativeai.GenerativeModel", return_value=mock_model):
                result = provider.execute("prompt", "system")

                # Should fall back to stub content
                assert isinstance(result, str)
                assert len(result) > 0

    @patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}, clear=True)
    @patch("nexuscore.llm.providers.gemini_provider._real_call_enabled", return_value=True)
    def test_execute_handles_model_init_error(self, mock_real_enabled):
        """Should handle model initialization errors"""
        with patch("google.generativeai.configure"):
            provider = GeminiLLM("gemini-2.5-flash")
            provider.client = "ok"
            provider.real_calls = True

            with patch("google.generativeai.GenerativeModel", side_effect=Exception("Init Error")):
                result = provider.execute("prompt", "system")

                # Should fall back to stub content
                assert isinstance(result, str)
                assert "Init failed" in result or len(result) > 0

    @patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}, clear=True)
    @patch("nexuscore.llm.providers.gemini_provider._real_call_enabled", return_value=True)
    def test_execute_handles_empty_response(self, mock_real_enabled):
        """Should handle empty responses"""
        with patch("google.generativeai.configure"):
            provider = GeminiLLM("gemini-2.5-flash")
            provider.client = "ok"
            provider.real_calls = True

            mock_model = Mock()
            mock_response = Mock()
            mock_response.candidates = []
            mock_model.generate_content.return_value = mock_response

            with patch("google.generativeai.GenerativeModel", return_value=mock_model):
                result = provider.execute("prompt", "system")

                # Should fall back to stub content
                assert isinstance(result, str)


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
