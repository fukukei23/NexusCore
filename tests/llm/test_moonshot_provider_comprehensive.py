"""
Comprehensive tests for Moonshot (Kimi) LLM Provider

Tests cover:
- Initialization (real/stub mode)
- API calls and responses
- Error handling
- JSON mode
- Environment variable handling
- Kimi-specific features
"""

import os
from unittest.mock import Mock, patch

from nexuscore.llm.providers.moonshot_provider import MoonshotLLM


class TestMoonshotProviderInit:
    """Test Moonshot provider initialization"""

    @patch.dict(os.environ, {}, clear=True)
    def test_init_without_api_key_uses_stub_mode(self):
        """Should use stub mode when API key is missing"""
        provider = MoonshotLLM("kimi-1")
        assert provider.real_calls is False
        assert provider.api_key is None

    @patch.dict(os.environ, {"KIMI_API_KEY": "test-key"}, clear=True)
    @patch("nexuscore.llm.providers.moonshot_provider._real_call_enabled", return_value=True)
    @patch("nexuscore.llm.providers.moonshot_provider.HTTP_CLIENT_FACTORY")
    def test_init_with_api_key_uses_real_mode(self, mock_factory, mock_real_enabled):
        """Should use real mode when API key is set"""
        mock_session = Mock()
        mock_factory.available = True
        mock_factory.create_session.return_value = mock_session

        provider = MoonshotLLM("kimi-1")
        assert provider.real_calls is True
        assert provider.api_key == "test-key"

    @patch.dict(
        os.environ,
        {"KIMI_API_KEY": "test-key", "KIMI_BASE_URL": "https://custom.moonshot.com"},
        clear=True,
    )
    @patch("nexuscore.llm.providers.moonshot_provider._real_call_enabled", return_value=True)
    @patch("nexuscore.llm.providers.moonshot_provider.HTTP_CLIENT_FACTORY")
    def test_init_with_custom_base_url(self, mock_factory, mock_real_enabled):
        """Should support custom base URL"""
        mock_session = Mock()
        mock_factory.available = True
        mock_factory.create_session.return_value = mock_session

        provider = MoonshotLLM("kimi-1")
        assert provider.base_url == "https://custom.moonshot.com"

    @patch.dict(os.environ, {"KIMI_API_KEY": "test-key"}, clear=True)
    @patch("nexuscore.llm.providers.moonshot_provider._real_call_enabled", return_value=True)
    @patch("nexuscore.llm.providers.moonshot_provider.HTTP_CLIENT_FACTORY")
    def test_init_without_http_factory_falls_back_to_stub(self, mock_factory, mock_real_enabled):
        """Should fall back to stub mode when HTTP factory unavailable"""
        mock_factory.available = True
        mock_factory.create_session.return_value = None

        provider = MoonshotLLM("kimi-1")
        assert provider.real_calls is False


class TestMoonshotProviderExecute:
    """Test Moonshot provider execute method"""

    @patch.dict(os.environ, {}, clear=True)
    def test_execute_stub_mode_returns_default_content(self):
        """Should return default stub content in stub mode"""
        provider = MoonshotLLM("kimi-1")
        result = provider.execute("test prompt", "test system")

        assert isinstance(result, str)
        assert len(result) > 0

    @patch.dict(os.environ, {"KIMI_API_KEY": "test-key"}, clear=True)
    @patch("nexuscore.llm.providers.moonshot_provider._real_call_enabled", return_value=True)
    @patch("nexuscore.llm.providers.moonshot_provider.HTTP_CLIENT_FACTORY")
    def test_execute_real_mode_calls_api(self, mock_factory, mock_real_enabled):
        """Should call Moonshot API in real mode"""
        mock_session = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Kimi response"}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 20},
        }
        mock_session.post.return_value = mock_response
        mock_factory.available = True
        mock_factory.create_session.return_value = mock_session

        provider = MoonshotLLM("kimi-1")
        result = provider.execute("test prompt", "test system")

        assert result == "Kimi response"
        mock_session.post.assert_called_once()
        call_args = mock_session.post.call_args
        assert call_args[1]["json"]["model"] == "kimi-1"
        assert call_args[1]["json"]["messages"][0]["role"] == "system"
        assert call_args[1]["json"]["messages"][0]["content"] == "test system"
        assert call_args[1]["json"]["messages"][1]["role"] == "user"
        assert call_args[1]["json"]["messages"][1]["content"] == "test prompt"

    @patch.dict(os.environ, {"KIMI_API_KEY": "test-key"}, clear=True)
    @patch("nexuscore.llm.providers.moonshot_provider._real_call_enabled", return_value=True)
    @patch("nexuscore.llm.providers.moonshot_provider.HTTP_CLIENT_FACTORY")
    def test_execute_with_custom_temperature(self, mock_factory, mock_real_enabled):
        """Should support custom temperature"""
        mock_session = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "response"}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 20},
        }
        mock_session.post.return_value = mock_response
        mock_factory.available = True
        mock_factory.create_session.return_value = mock_session

        provider = MoonshotLLM("kimi-1")
        provider.execute("prompt", "system", temperature=0.7)

        call_args = mock_session.post.call_args
        assert call_args[1]["json"]["temperature"] == 0.7

    @patch.dict(
        os.environ, {"KIMI_API_KEY": "test-key", "NEXUS_DEFAULT_MAX_OUT_TOKENS": "2000"}, clear=True
    )
    @patch("nexuscore.llm.providers.moonshot_provider._real_call_enabled", return_value=True)
    @patch("nexuscore.llm.providers.moonshot_provider.HTTP_CLIENT_FACTORY")
    def test_execute_with_max_tokens(self, mock_factory, mock_real_enabled):
        """Should support max_tokens parameter"""
        mock_session = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "response"}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 20},
        }
        mock_session.post.return_value = mock_response
        mock_factory.available = True
        mock_factory.create_session.return_value = mock_session

        provider = MoonshotLLM("kimi-1")
        provider.execute("prompt", "system")

        call_args = mock_session.post.call_args
        assert call_args[1]["json"]["max_tokens"] == 2000

    @patch.dict(os.environ, {"KIMI_API_KEY": "test-key"}, clear=True)
    @patch("nexuscore.llm.providers.moonshot_provider._real_call_enabled", return_value=True)
    @patch("nexuscore.llm.providers.moonshot_provider.HTTP_CLIENT_FACTORY")
    def test_execute_with_json_mode(self, mock_factory, mock_real_enabled):
        """Should support JSON mode"""
        mock_session = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": '{"key": "value"}'}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 20},
        }
        mock_session.post.return_value = mock_response
        mock_factory.available = True
        mock_factory.create_session.return_value = mock_session

        provider = MoonshotLLM("kimi-1")
        provider.execute("prompt", "system", as_json=True)

        call_args = mock_session.post.call_args
        assert call_args[1]["json"]["response_format"] == {"type": "json_object"}


class TestMoonshotProviderErrorHandling:
    """Test Moonshot provider error handling"""

    @patch.dict(os.environ, {"KIMI_API_KEY": "test-key"}, clear=True)
    @patch("nexuscore.llm.providers.moonshot_provider._real_call_enabled", return_value=True)
    @patch("nexuscore.llm.providers.moonshot_provider.HTTP_CLIENT_FACTORY")
    def test_execute_handles_http_error(self, mock_factory, mock_real_enabled):
        """Should handle HTTP errors gracefully"""
        mock_session = Mock()
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_session.post.return_value = mock_response
        mock_factory.available = True
        mock_factory.create_session.return_value = mock_session

        provider = MoonshotLLM("kimi-1")
        result = provider.execute("prompt", "system")

        # Should fall back to stub content
        assert isinstance(result, str)
        assert len(result) > 0

    @patch.dict(os.environ, {"KIMI_API_KEY": "test-key"}, clear=True)
    @patch("nexuscore.llm.providers.moonshot_provider._real_call_enabled", return_value=True)
    @patch("nexuscore.llm.providers.moonshot_provider.HTTP_CLIENT_FACTORY")
    def test_execute_handles_rate_limit(self, mock_factory, mock_real_enabled):
        """Should handle rate limit errors"""
        mock_session = Mock()
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.text = "Rate limit exceeded"
        mock_session.post.return_value = mock_response
        mock_factory.available = True
        mock_factory.create_session.return_value = mock_session

        provider = MoonshotLLM("kimi-1")
        result = provider.execute("prompt", "system")

        # Should fall back to stub content
        assert isinstance(result, str)

    @patch.dict(os.environ, {"KIMI_API_KEY": "test-key"}, clear=True)
    @patch("nexuscore.llm.providers.moonshot_provider._real_call_enabled", return_value=True)
    @patch("nexuscore.llm.providers.moonshot_provider.HTTP_CLIENT_FACTORY")
    def test_execute_handles_malformed_response(self, mock_factory, mock_real_enabled):
        """Should handle malformed API responses"""
        mock_session = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"invalid": "structure"}
        mock_session.post.return_value = mock_response
        mock_factory.available = True
        mock_factory.create_session.return_value = mock_session

        provider = MoonshotLLM("kimi-1")
        result = provider.execute("prompt", "system")

        # Should fall back to stub content
        assert isinstance(result, str)


class TestMoonshotProviderModels:
    """Test different Moonshot/Kimi model variants"""

    @patch.dict(os.environ, {}, clear=True)
    def test_supports_kimi_1(self):
        """Should support kimi-1 model"""
        provider = MoonshotLLM("kimi-1")
        assert provider.model_name == "kimi-1"

    @patch.dict(os.environ, {}, clear=True)
    def test_supports_moonshot_v1(self):
        """Should support moonshot-v1 model"""
        provider = MoonshotLLM("moonshot-v1-8k")
        assert provider.model_name == "moonshot-v1-8k"

    @patch.dict(os.environ, {}, clear=True)
    def test_supports_moonshot_v1_32k(self):
        """Should support moonshot-v1-32k model"""
        provider = MoonshotLLM("moonshot-v1-32k")
        assert provider.model_name == "moonshot-v1-32k"
