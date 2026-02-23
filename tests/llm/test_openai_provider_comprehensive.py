"""
Comprehensive tests for OpenAI LLM Provider

Tests cover:
- Initialization (real/stub mode)
- Azure configuration
- API calls and responses
- Error handling
- Timeout and retry
- JSON mode
- Environment variable handling
"""

import os
from unittest.mock import Mock, patch

import pytest

from nexuscore.llm.providers.openai_provider import OpenAILLM


class TestOpenAIProviderInit:
    """Test OpenAI provider initialization"""

    @patch.dict(os.environ, {}, clear=True)
    def test_init_without_api_key_uses_stub_mode(self):
        """Should use stub mode when API key is missing"""
        provider = OpenAILLM("gpt-5.1")
        assert provider.real_calls is False
        assert provider.api_key is None

    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}, clear=True)
    @patch("nexuscore.llm.providers.openai_provider._real_call_enabled", return_value=True)
    @patch("nexuscore.llm.providers.openai_provider.HTTP_CLIENT_FACTORY")
    def test_init_with_api_key_uses_real_mode(self, mock_factory, mock_real_enabled):
        """Should use real mode when API key is set"""
        mock_session = Mock()
        mock_factory.available = True
        mock_factory.create_session.return_value = mock_session

        provider = OpenAILLM("gpt-5.1")
        assert provider.real_calls is True
        assert provider.api_key == "test-key"

    @patch.dict(
        os.environ,
        {"OPENAI_API_KEY": "test-key", "OPENAI_BASE_URL": "https://custom.api.com"},
        clear=True,
    )
    @patch("nexuscore.llm.providers.openai_provider._real_call_enabled", return_value=True)
    @patch("nexuscore.llm.providers.openai_provider.HTTP_CLIENT_FACTORY")
    def test_init_with_custom_base_url(self, mock_factory, mock_real_enabled):
        """Should support custom base URL"""
        mock_session = Mock()
        mock_factory.available = True
        mock_factory.create_session.return_value = mock_session

        provider = OpenAILLM("gpt-5.1")
        assert provider.base_url == "https://custom.api.com"

    @patch.dict(
        os.environ,
        {
            "OPENAI_API_KEY": "test-key",
            "OPENAI_AZURE": "1",
            "OPENAI_AZURE_DEPLOYMENT": "gpt-5-deploy",
        },
        clear=True,
    )
    @patch("nexuscore.llm.providers.openai_provider._real_call_enabled", return_value=True)
    @patch("nexuscore.llm.providers.openai_provider.HTTP_CLIENT_FACTORY")
    def test_init_azure_mode(self, mock_factory, mock_real_enabled):
        """Should support Azure OpenAI configuration"""
        mock_session = Mock()
        mock_factory.available = True
        mock_factory.create_session.return_value = mock_session

        provider = OpenAILLM("gpt-5.1")
        assert provider.azure is True
        assert provider.azure_deployment == "gpt-5-deploy"

    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key", "OPENAI_AZURE": "1"}, clear=True)
    @patch("nexuscore.llm.providers.openai_provider._real_call_enabled", return_value=True)
    @patch("nexuscore.llm.providers.openai_provider.HTTP_CLIENT_FACTORY")
    def test_init_azure_without_deployment_raises_error(self, mock_factory, mock_real_enabled):
        """Should raise error when Azure mode without deployment name"""
        mock_session = Mock()
        mock_factory.available = True
        mock_factory.create_session.return_value = mock_session

        with pytest.raises(ValueError, match="OPENAI_AZURE_DEPLOYMENT"):
            OpenAILLM("gpt-5.1")


class TestOpenAIProviderExecute:
    """Test OpenAI provider execute method"""

    @patch.dict(os.environ, {}, clear=True)
    def test_execute_stub_mode_returns_default_content(self):
        """Should return default stub content in stub mode"""
        provider = OpenAILLM("gpt-5.1")
        result = provider.execute("test prompt", "test system")

        assert isinstance(result, str)
        assert len(result) > 0

    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}, clear=True)
    @patch("nexuscore.llm.providers.openai_provider._real_call_enabled", return_value=True)
    @patch("nexuscore.llm.providers.openai_provider.HTTP_CLIENT_FACTORY")
    def test_execute_real_mode_calls_api(self, mock_factory, mock_real_enabled):
        """Should call OpenAI API in real mode"""
        mock_session = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "AI response"}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 20},
        }
        mock_session.post.return_value = mock_response
        mock_factory.available = True
        mock_factory.create_session.return_value = mock_session

        provider = OpenAILLM("gpt-5.1")
        result = provider.execute("test prompt", "test system")

        assert result == "AI response"
        mock_session.post.assert_called_once()

    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}, clear=True)
    @patch("nexuscore.llm.providers.openai_provider._real_call_enabled", return_value=True)
    @patch("nexuscore.llm.providers.openai_provider.HTTP_CLIENT_FACTORY")
    def test_execute_with_json_mode(self, mock_factory, mock_real_enabled):
        """Should use JSON mode when as_json=True"""
        mock_session = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": '{"result": "success"}'}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 20},
        }
        mock_session.post.return_value = mock_response
        mock_factory.available = True
        mock_factory.create_session.return_value = mock_session

        provider = OpenAILLM("gpt-5.1")
        result = provider.execute("test prompt", "test system", as_json=True)

        # Check that payload includes response_format
        call_args = mock_session.post.call_args
        payload = call_args[1]["json"]
        assert "response_format" in payload
        assert payload["response_format"]["type"] == "json_object"

    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}, clear=True)
    @patch("nexuscore.llm.providers.openai_provider._real_call_enabled", return_value=True)
    @patch("nexuscore.llm.providers.openai_provider.HTTP_CLIENT_FACTORY")
    def test_execute_with_custom_temperature(self, mock_factory, mock_real_enabled):
        """Should use custom temperature parameter"""
        mock_session = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "AI response"}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 20},
        }
        mock_session.post.return_value = mock_response
        mock_factory.available = True
        mock_factory.create_session.return_value = mock_session

        provider = OpenAILLM("gpt-4")  # Non-GPT-5 model
        result = provider.execute("test prompt", "test system", temperature=0.8)

        call_args = mock_session.post.call_args
        payload = call_args[1]["json"]
        assert payload["temperature"] == 0.8


class TestOpenAIProviderErrorHandling:
    """Test OpenAI provider error handling"""

    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}, clear=True)
    @patch("nexuscore.llm.providers.openai_provider._real_call_enabled", return_value=True)
    @patch("nexuscore.llm.providers.openai_provider.HTTP_CLIENT_FACTORY")
    def test_execute_handles_http_error(self, mock_factory, mock_real_enabled):
        """Should handle HTTP errors gracefully"""
        mock_session = Mock()
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_session.post.return_value = mock_response
        mock_factory.available = True
        mock_factory.create_session.return_value = mock_session

        provider = OpenAILLM("gpt-5.1")

        # Should fall back to stub on error
        result = provider.execute("test prompt", "test system")
        assert isinstance(result, str)

    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}, clear=True)
    @patch("nexuscore.llm.providers.openai_provider._real_call_enabled", return_value=True)
    @patch("nexuscore.llm.providers.openai_provider.HTTP_CLIENT_FACTORY")
    def test_execute_handles_rate_limit(self, mock_factory, mock_real_enabled):
        """Should handle rate limit errors"""
        mock_session = Mock()
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.text = "Rate limit exceeded"
        mock_session.post.return_value = mock_response
        mock_factory.available = True
        mock_factory.create_session.return_value = mock_session

        provider = OpenAILLM("gpt-5.1")
        result = provider.execute("test prompt", "test system")

        # Should fall back to stub on rate limit
        assert isinstance(result, str)

    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}, clear=True)
    @patch("nexuscore.llm.providers.openai_provider._real_call_enabled", return_value=True)
    @patch("nexuscore.llm.providers.openai_provider.HTTP_CLIENT_FACTORY")
    def test_execute_handles_malformed_response(self, mock_factory, mock_real_enabled):
        """Should handle malformed API responses"""
        mock_session = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"invalid": "structure"}
        mock_session.post.return_value = mock_response
        mock_factory.available = True
        mock_factory.create_session.return_value = mock_session

        provider = OpenAILLM("gpt-5.1")
        result = provider.execute("test prompt", "test system")

        # Should fall back to stub on invalid response
        assert isinstance(result, str)


class TestOpenAIProviderAzure:
    """Test Azure OpenAI specific features"""

    @patch.dict(
        os.environ,
        {
            "OPENAI_API_KEY": "azure-key",
            "OPENAI_AZURE": "1",
            "OPENAI_AZURE_DEPLOYMENT": "gpt-5-deploy",
            "OPENAI_BASE_URL": "https://my-resource.openai.azure.com",
        },
        clear=True,
    )
    @patch("nexuscore.llm.providers.openai_provider._real_call_enabled", return_value=True)
    @patch("nexuscore.llm.providers.openai_provider.HTTP_CLIENT_FACTORY")
    def test_azure_url_format(self, mock_factory, mock_real_enabled):
        """Should format Azure URL correctly"""
        mock_session = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Azure response"}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 20},
        }
        mock_session.post.return_value = mock_response
        mock_factory.available = True
        mock_factory.create_session.return_value = mock_session

        provider = OpenAILLM("gpt-5.1")
        provider.execute("test", "system")

        call_args = mock_session.post.call_args
        url = call_args[0][0]
        assert "openai/deployments/gpt-5-deploy/chat/completions" in url
        assert "api-version" in url

    @patch.dict(
        os.environ,
        {
            "OPENAI_API_KEY": "azure-key",
            "OPENAI_AZURE": "1",
            "OPENAI_AZURE_DEPLOYMENT": "gpt-5-deploy",
            "OPENAI_AZURE_API_VERSION": "2024-10-01-preview",
        },
        clear=True,
    )
    @patch("nexuscore.llm.providers.openai_provider._real_call_enabled", return_value=True)
    @patch("nexuscore.llm.providers.openai_provider.HTTP_CLIENT_FACTORY")
    def test_azure_custom_api_version(self, mock_factory, mock_real_enabled):
        """Should support custom Azure API version"""
        mock_session = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Azure response"}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 20},
        }
        mock_session.post.return_value = mock_response
        mock_factory.available = True
        mock_factory.create_session.return_value = mock_session

        provider = OpenAILLM("gpt-5.1")
        assert provider.azure_api_version == "2024-10-01-preview"


class TestOpenAIProviderModelVariants:
    """Test different OpenAI model variants"""

    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}, clear=True)
    @patch("nexuscore.llm.providers.openai_provider._real_call_enabled", return_value=True)
    @patch("nexuscore.llm.providers.openai_provider.HTTP_CLIENT_FACTORY")
    def test_gpt5_model_no_temperature(self, mock_factory, mock_real_enabled):
        """GPT-5 models should not include temperature parameter"""
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

        provider = OpenAILLM("gpt-5.1-codex")
        provider.execute("test", "system", temperature=0.8)

        call_args = mock_session.post.call_args
        payload = call_args[1]["json"]
        # GPT-5 models should not have temperature in payload
        assert "temperature" not in payload or payload.get("temperature") is None

    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}, clear=True)
    @patch("nexuscore.llm.providers.openai_provider._real_call_enabled", return_value=True)
    @patch("nexuscore.llm.providers.openai_provider.HTTP_CLIENT_FACTORY")
    def test_o_series_model_no_temperature(self, mock_factory, mock_real_enabled):
        """O-series models should not include temperature parameter"""
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

        provider = OpenAILLM("o1-preview")
        provider.execute("test", "system", temperature=0.8)

        call_args = mock_session.post.call_args
        payload = call_args[1]["json"]
        assert "temperature" not in payload or payload.get("temperature") is None
