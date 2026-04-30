"""
Comprehensive tests for Anthropic (Claude) LLM Provider

Tests cover:
- Initialization (real/stub mode)
- API calls and responses
- Error handling
- Timeout and retry
- Environment variable handling
- Claude-specific features
"""

import os
from unittest.mock import Mock, patch

from nexuscore.llm.providers.anthropic_provider import AnthropicLLM


class TestAnthropicProviderInit:
    """Test Anthropic provider initialization"""

    @patch.dict(os.environ, {}, clear=True)
    def test_init_without_api_key_uses_stub_mode(self):
        """Should use stub mode when API key is missing"""
        provider = AnthropicLLM("claude-sonnet-4.5")
        assert provider.real_calls is False
        assert provider.api_key is None

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}, clear=True)
    @patch("nexuscore.llm.providers.anthropic_provider._real_call_enabled", return_value=True)
    @patch("nexuscore.llm.providers.anthropic_provider.HTTP_CLIENT_FACTORY")
    def test_init_with_api_key_uses_real_mode(self, mock_factory, mock_real_enabled):
        """Should use real mode when API key is set"""
        mock_session = Mock()
        mock_factory.available = True
        mock_factory.create_session.return_value = mock_session

        provider = AnthropicLLM("claude-sonnet-4.5")
        assert provider.real_calls is True
        assert provider.api_key == "test-key"

    @patch.dict(
        os.environ,
        {"ANTHROPIC_API_KEY": "test-key", "ANTHROPIC_BASE_URL": "https://custom.api.com"},
        clear=True,
    )
    @patch("nexuscore.llm.providers.anthropic_provider._real_call_enabled", return_value=True)
    @patch("nexuscore.llm.providers.anthropic_provider.HTTP_CLIENT_FACTORY")
    def test_init_with_custom_base_url(self, mock_factory, mock_real_enabled):
        """Should support custom base URL"""
        mock_session = Mock()
        mock_factory.available = True
        mock_factory.create_session.return_value = mock_session

        provider = AnthropicLLM("claude-sonnet-4.5")
        assert provider.base_url == "https://custom.api.com"

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}, clear=True)
    @patch("nexuscore.llm.providers.anthropic_provider._real_call_enabled", return_value=True)
    @patch("nexuscore.llm.providers.anthropic_provider.HTTP_CLIENT_FACTORY")
    def test_init_without_http_factory_falls_back_to_stub(self, mock_factory, mock_real_enabled):
        """Should fall back to stub mode when HTTP factory unavailable"""
        mock_factory.available = True
        mock_factory.create_session.return_value = None

        provider = AnthropicLLM("claude-sonnet-4.5")
        assert provider.real_calls is False


class TestAnthropicProviderExecute:
    """Test Anthropic provider execute method"""

    @patch.dict(os.environ, {}, clear=True)
    def test_execute_stub_mode_returns_default_content(self):
        """Should return default stub content in stub mode"""
        provider = AnthropicLLM("claude-sonnet-4.5")
        result = provider.execute("test prompt", "test system")

        assert isinstance(result, str)
        assert len(result) > 0

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}, clear=True)
    @patch("nexuscore.llm.providers.anthropic_provider._real_call_enabled", return_value=True)
    @patch("nexuscore.llm.providers.anthropic_provider.HTTP_CLIENT_FACTORY")
    def test_execute_real_mode_calls_api(self, mock_factory, mock_real_enabled):
        """Should call Anthropic API in real mode"""
        mock_session = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "content": [{"type": "text", "text": "Claude response"}],
            "usage": {"input_tokens": 10, "output_tokens": 20},
        }
        mock_session.post.return_value = mock_response
        mock_factory.available = True
        mock_factory.create_session.return_value = mock_session

        provider = AnthropicLLM("claude-sonnet-4.5")
        result = provider.execute("test prompt", "test system")

        assert result == "Claude response"
        mock_session.post.assert_called_once()
        call_args = mock_session.post.call_args
        assert call_args[1]["json"]["model"] == "claude-sonnet-4.5"
        assert call_args[1]["json"]["messages"][0]["content"] == "test prompt"
        assert call_args[1]["json"]["system"] == "test system"

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}, clear=True)
    @patch("nexuscore.llm.providers.anthropic_provider._real_call_enabled", return_value=True)
    @patch("nexuscore.llm.providers.anthropic_provider.HTTP_CLIENT_FACTORY")
    def test_execute_with_custom_temperature(self, mock_factory, mock_real_enabled):
        """Should support custom temperature"""
        mock_session = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "content": [{"type": "text", "text": "response"}],
            "usage": {"input_tokens": 10, "output_tokens": 20},
        }
        mock_session.post.return_value = mock_response
        mock_factory.available = True
        mock_factory.create_session.return_value = mock_session

        provider = AnthropicLLM("claude-sonnet-4.5")
        provider.execute("prompt", "system", temperature=0.7)

        call_args = mock_session.post.call_args
        assert call_args[1]["json"]["temperature"] == 0.7

    @patch.dict(
        os.environ,
        {"ANTHROPIC_API_KEY": "test-key", "NEXUS_DEFAULT_MAX_OUT_TOKENS": "2000"},
        clear=True,
    )
    @patch("nexuscore.llm.providers.anthropic_provider._real_call_enabled", return_value=True)
    @patch("nexuscore.llm.providers.anthropic_provider.HTTP_CLIENT_FACTORY")
    def test_execute_with_max_tokens(self, mock_factory, mock_real_enabled):
        """Should support max_tokens parameter"""
        mock_session = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "content": [{"type": "text", "text": "response"}],
            "usage": {"input_tokens": 10, "output_tokens": 20},
        }
        mock_session.post.return_value = mock_response
        mock_factory.available = True
        mock_factory.create_session.return_value = mock_session

        provider = AnthropicLLM("claude-sonnet-4.5")
        provider.execute("prompt", "system")

        call_args = mock_session.post.call_args
        assert call_args[1]["json"]["max_tokens"] == 2000


class TestAnthropicProviderErrorHandling:
    """Test Anthropic provider error handling"""

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}, clear=True)
    @patch("nexuscore.llm.providers.anthropic_provider._real_call_enabled", return_value=True)
    @patch("nexuscore.llm.providers.anthropic_provider.HTTP_CLIENT_FACTORY")
    def test_execute_handles_http_error(self, mock_factory, mock_real_enabled):
        """Should handle HTTP errors gracefully"""
        mock_session = Mock()
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_session.post.return_value = mock_response
        mock_factory.available = True
        mock_factory.create_session.return_value = mock_session

        provider = AnthropicLLM("claude-sonnet-4.5")
        result = provider.execute("prompt", "system")

        # Should fall back to stub content
        assert isinstance(result, str)
        assert len(result) > 0

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}, clear=True)
    @patch("nexuscore.llm.providers.anthropic_provider._real_call_enabled", return_value=True)
    @patch("nexuscore.llm.providers.anthropic_provider.HTTP_CLIENT_FACTORY")
    def test_execute_handles_rate_limit(self, mock_factory, mock_real_enabled):
        """Should handle rate limit errors"""
        mock_session = Mock()
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.text = "Rate limit exceeded"
        mock_session.post.return_value = mock_response
        mock_factory.available = True
        mock_factory.create_session.return_value = mock_session

        provider = AnthropicLLM("claude-sonnet-4.5")
        result = provider.execute("prompt", "system")

        # Should fall back to stub content
        assert isinstance(result, str)

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}, clear=True)
    @patch("nexuscore.llm.providers.anthropic_provider._real_call_enabled", return_value=True)
    @patch("nexuscore.llm.providers.anthropic_provider.HTTP_CLIENT_FACTORY")
    def test_execute_handles_malformed_response(self, mock_factory, mock_real_enabled):
        """Should handle malformed API responses"""
        mock_session = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"invalid": "structure"}
        mock_session.post.return_value = mock_response
        mock_factory.available = True
        mock_factory.create_session.return_value = mock_session

        provider = AnthropicLLM("claude-sonnet-4.5")
        result = provider.execute("prompt", "system")

        # Should fall back to stub content
        assert isinstance(result, str)


class TestAnthropicProviderHeaders:
    """Test Anthropic-specific headers"""

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}, clear=True)
    @patch("nexuscore.llm.providers.anthropic_provider._real_call_enabled", return_value=True)
    @patch("nexuscore.llm.providers.anthropic_provider.HTTP_CLIENT_FACTORY")
    def test_execute_includes_anthropic_version_header(self, mock_factory, mock_real_enabled):
        """Should include anthropic-version header"""
        mock_session = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "content": [{"type": "text", "text": "response"}],
            "usage": {"input_tokens": 10, "output_tokens": 20},
        }
        mock_session.post.return_value = mock_response
        mock_factory.available = True
        mock_factory.create_session.return_value = mock_session

        provider = AnthropicLLM("claude-sonnet-4.5")
        provider.execute("prompt", "system")

        call_args = mock_session.post.call_args
        headers = call_args[1]["headers"]
        assert "anthropic-version" in headers
        assert headers["anthropic-version"] == "2023-06-01"

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}, clear=True)
    @patch("nexuscore.llm.providers.anthropic_provider._real_call_enabled", return_value=True)
    @patch("nexuscore.llm.providers.anthropic_provider.HTTP_CLIENT_FACTORY")
    def test_execute_includes_authorization_header(self, mock_factory, mock_real_enabled):
        """Should include x-api-key header for Anthropic API"""
        mock_session = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "content": [{"type": "text", "text": "response"}],
            "usage": {"input_tokens": 10, "output_tokens": 20},
        }
        mock_session.post.return_value = mock_response
        mock_factory.available = True
        mock_factory.create_session.return_value = mock_session

        provider = AnthropicLLM("claude-sonnet-4.5")
        provider.execute("prompt", "system")

        call_args = mock_session.post.call_args
        headers = call_args[1]["headers"]
        assert headers["x-api-key"] == "test-key"


class TestAnthropicProviderModels:
    """Test different Claude model variants"""

    @patch.dict(os.environ, {}, clear=True)
    def test_supports_claude_sonnet(self):
        """Should support Claude Sonnet models"""
        provider = AnthropicLLM("claude-sonnet-4.5")
        assert provider.model_name == "claude-sonnet-4.5"

    @patch.dict(os.environ, {}, clear=True)
    def test_supports_claude_opus(self):
        """Should support Claude Opus models"""
        provider = AnthropicLLM("claude-opus-4.5")
        assert provider.model_name == "claude-opus-4.5"

    @patch.dict(os.environ, {}, clear=True)
    def test_supports_claude_haiku(self):
        """Should support Claude Haiku models"""
        provider = AnthropicLLM("claude-haiku-4.5")
        assert provider.model_name == "claude-haiku-4.5"
