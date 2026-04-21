"""
Comprehensive tests for MiniMax LLM Provider
"""

from __future__ import annotations

import json
import os
from unittest.mock import Mock, patch

from nexuscore.llm.http_client import RequestsHTTPError
from nexuscore.llm.providers.minimax_provider import MiniMaxLLM


class TestMiniMaxProviderInit:
    @patch.dict(os.environ, {}, clear=True)
    def test_init_without_api_key_uses_stub_mode(self):
        provider = MiniMaxLLM("minimax-m2.7")
        assert provider.real_calls is False
        assert provider.api_key is None

    @patch.dict(os.environ, {"MINIMAX_MODEL": "minimax-override"}, clear=True)
    def test_init_minimax_model_env_overrides_model_name(self):
        provider = MiniMaxLLM("minimax-m2.7")
        assert provider.model_name == "minimax-override"

    @patch.dict(os.environ, {}, clear=True)
    def test_init_default_base_url(self):
        provider = MiniMaxLLM("minimax-m2.7")
        assert provider.base_url == "https://api.minimax.chat/v1"

    @patch.dict(os.environ, {"MINIMAX_API_KEY": "test-key"}, clear=True)
    @patch("nexuscore.llm.providers.minimax_provider._real_call_enabled", return_value=True)
    @patch("nexuscore.llm.providers.minimax_provider.HTTP_CLIENT_FACTORY")
    def test_init_with_api_key_uses_real_mode(self, mock_factory, mock_real_enabled):
        mock_session = Mock()
        mock_factory.available = True
        mock_factory.create_session.return_value = mock_session
        provider = MiniMaxLLM("minimax-m2.7")
        assert provider.real_calls is True
        assert provider.api_key == "test-key"

    @patch.dict(os.environ, {"MINIMAX_API_KEY": "test-key", "MINIMAX_API_BASE": "https://custom.minimax.com/v1"}, clear=True)
    @patch("nexuscore.llm.providers.minimax_provider._real_call_enabled", return_value=True)
    @patch("nexuscore.llm.providers.minimax_provider.HTTP_CLIENT_FACTORY")
    def test_init_minimax_api_base_uses_custom_url(self, mock_factory, mock_real_enabled):
        mock_factory.available = True
        mock_factory.create_session.return_value = Mock()
        provider = MiniMaxLLM("minimax-m2.7")
        assert provider.base_url == "https://custom.minimax.com/v1"

    @patch.dict(os.environ, {"MINIMAX_API_KEY": "test-key", "MINIMAX_BASE_URL": "https://alt.minimax.io/v1"}, clear=True)
    @patch("nexuscore.llm.providers.minimax_provider._real_call_enabled", return_value=True)
    @patch("nexuscore.llm.providers.minimax_provider.HTTP_CLIENT_FACTORY")
    def test_init_minimax_base_url_uses_custom_url(self, mock_factory, mock_real_enabled):
        mock_factory.available = True
        mock_factory.create_session.return_value = Mock()
        provider = MiniMaxLLM("minimax-m2.7")
        assert provider.base_url == "https://alt.minimax.io/v1"

    @patch.dict(os.environ, {"MINIMAX_API_KEY": "test-key", "MINIMAX_API_BASE": "https://custom.minimax.com/v1/"}, clear=True)
    @patch("nexuscore.llm.providers.minimax_provider._real_call_enabled", return_value=True)
    @patch("nexuscore.llm.providers.minimax_provider.HTTP_CLIENT_FACTORY")
    def test_init_base_url_strips_trailing_slash(self, mock_factory, mock_real_enabled):
        mock_factory.available = True
        mock_factory.create_session.return_value = Mock()
        provider = MiniMaxLLM("minimax-m2.7")
        assert provider.base_url == "https://custom.minimax.com/v1"

    @patch.dict(os.environ, {"MINIMAX_API_KEY": "test-key"}, clear=True)
    @patch("nexuscore.llm.providers.minimax_provider._real_call_enabled", return_value=True)
    @patch("nexuscore.llm.providers.minimax_provider.HTTP_CLIENT_FACTORY")
    def test_init_session_none_falls_back_to_stub(self, mock_factory, mock_real_enabled):
        mock_factory.available = True
        mock_factory.create_session.return_value = None
        provider = MiniMaxLLM("minimax-m2.7")
        assert provider.real_calls is False

    @patch.dict(os.environ, {"MINIMAX_API_KEY": "test-key"}, clear=True)
    @patch("nexuscore.llm.providers.minimax_provider._real_call_enabled", return_value=True)
    @patch("nexuscore.llm.providers.minimax_provider.HTTP_CLIENT_FACTORY")
    def test_init_http_factory_unavailable_falls_back_to_stub(self, mock_factory, mock_real_enabled):
        mock_factory.available = False
        provider = MiniMaxLLM("minimax-m2.7")
        assert provider.real_calls is False


class TestMiniMaxProviderExecute:
    @patch.dict(os.environ, {}, clear=True)
    def test_execute_stub_mode_returns_string(self):
        provider = MiniMaxLLM("minimax-m2.7")
        result = provider.execute("test prompt", "test system")
        assert isinstance(result, str)
        assert len(result) > 0

    @patch.dict(os.environ, {}, clear=True)
    def test_execute_stub_mode_sets_last_call_mode(self):
        provider = MiniMaxLLM("minimax-m2.7")
        provider.execute("prompt", "system")
        assert provider.last_call_mode == "stub"

    @patch.dict(os.environ, {"MINIMAX_API_KEY": "test-key"}, clear=True)
    @patch("nexuscore.llm.providers.minimax_provider._real_call_enabled", return_value=True)
    @patch("nexuscore.llm.providers.minimax_provider.HTTP_CLIENT_FACTORY")
    def test_execute_real_mode_returns_api_text(self, mock_factory, mock_real_enabled):
        mock_session = Mock()
        mock_response = Mock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "MiniMax response"}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 20},
        }
        mock_session.post.return_value = mock_response
        mock_factory.available = True
        mock_factory.create_session.return_value = mock_session
        provider = MiniMaxLLM("minimax-m2.7")
        result = provider.execute("test prompt", "test system")
        assert result == "MiniMax response"
        mock_session.post.assert_called_once()

    @patch.dict(os.environ, {"MINIMAX_API_KEY": "test-key"}, clear=True)
    @patch("nexuscore.llm.providers.minimax_provider._real_call_enabled", return_value=True)
    @patch("nexuscore.llm.providers.minimax_provider.HTTP_CLIENT_FACTORY")
    def test_execute_sends_correct_messages(self, mock_factory, mock_real_enabled):
        mock_session = Mock()
        mock_response = Mock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "ok"}}],
            "usage": {},
        }
        mock_session.post.return_value = mock_response
        mock_factory.available = True
        mock_factory.create_session.return_value = mock_session
        provider = MiniMaxLLM("minimax-m2.7")
        provider.execute("my prompt", "my system")
        payload = mock_session.post.call_args[1]["json"]
        assert payload["model"] == "minimax-m2.7"
        assert payload["messages"][0] == {"role": "system", "content": "my system"}
        assert payload["messages"][1] == {"role": "user", "content": "my prompt"}

    @patch.dict(os.environ, {"MINIMAX_API_KEY": "test-key"}, clear=True)
    @patch("nexuscore.llm.providers.minimax_provider._real_call_enabled", return_value=True)
    @patch("nexuscore.llm.providers.minimax_provider.HTTP_CLIENT_FACTORY")
    def test_execute_sends_auth_header(self, mock_factory, mock_real_enabled):
        mock_session = Mock()
        mock_response = Mock()
        mock_response.json.return_value = {"choices": [{"message": {"content": "ok"}}], "usage": {}}
        mock_session.post.return_value = mock_response
        mock_factory.available = True
        mock_factory.create_session.return_value = mock_session
        provider = MiniMaxLLM("minimax-m2.7")
        provider.execute("prompt", "system")
        headers = mock_session.post.call_args[1]["headers"]
        assert headers["Authorization"] == "Bearer test-key"
        assert headers["Content-Type"] == "application/json"

    @patch.dict(os.environ, {"MINIMAX_API_KEY": "test-key"}, clear=True)
    @patch("nexuscore.llm.providers.minimax_provider._real_call_enabled", return_value=True)
    @patch("nexuscore.llm.providers.minimax_provider.HTTP_CLIENT_FACTORY")
    def test_execute_with_custom_temperature(self, mock_factory, mock_real_enabled):
        mock_session = Mock()
        mock_response = Mock()
        mock_response.json.return_value = {"choices": [{"message": {"content": "ok"}}], "usage": {}}
        mock_session.post.return_value = mock_response
        mock_factory.available = True
        mock_factory.create_session.return_value = mock_session
        provider = MiniMaxLLM("minimax-m2.7")
        provider.execute("prompt", "system", temperature=0.9)
        assert mock_session.post.call_args[1]["json"]["temperature"] == 0.9

    @patch.dict(os.environ, {"MINIMAX_API_KEY": "test-key", "NEXUS_DEFAULT_MAX_OUT_TOKENS": "4096"}, clear=True)
    @patch("nexuscore.llm.providers.minimax_provider._real_call_enabled", return_value=True)
    @patch("nexuscore.llm.providers.minimax_provider.HTTP_CLIENT_FACTORY")
    def test_execute_with_max_tokens_env(self, mock_factory, mock_real_enabled):
        mock_session = Mock()
        mock_response = Mock()
        mock_response.json.return_value = {"choices": [{"message": {"content": "ok"}}], "usage": {}}
        mock_session.post.return_value = mock_response
        mock_factory.available = True
        mock_factory.create_session.return_value = mock_session
        provider = MiniMaxLLM("minimax-m2.7")
        provider.execute("prompt", "system")
        assert mock_session.post.call_args[1]["json"]["max_tokens"] == 4096

    @patch.dict(os.environ, {"MINIMAX_API_KEY": "test-key"}, clear=True)
    @patch("nexuscore.llm.providers.minimax_provider._real_call_enabled", return_value=True)
    @patch("nexuscore.llm.providers.minimax_provider.HTTP_CLIENT_FACTORY")
    def test_execute_json_mode_sets_response_format(self, mock_factory, mock_real_enabled):
        mock_session = Mock()
        mock_response = Mock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": '{"k":"v"}'}}],
            "usage": {},
        }
        mock_session.post.return_value = mock_response
        mock_factory.available = True
        mock_factory.create_session.return_value = mock_session
        provider = MiniMaxLLM("minimax-m2.7")
        provider.execute("prompt", "system", as_json=True)
        assert mock_session.post.call_args[1]["json"]["response_format"] == {"type": "json_object"}

    @patch.dict(os.environ, {"MINIMAX_API_KEY": "test-key"}, clear=True)
    @patch("nexuscore.llm.providers.minimax_provider._real_call_enabled", return_value=True)
    @patch("nexuscore.llm.providers.minimax_provider.HTTP_CLIENT_FACTORY")
    def test_execute_multiple_choices_concatenated(self, mock_factory, mock_real_enabled):
        mock_session = Mock()
        mock_response = Mock()
        mock_response.json.return_value = {
            "choices": [
                {"message": {"content": "Part1 "}},
                {"message": {"content": "Part2"}},
            ],
            "usage": {},
        }
        mock_session.post.return_value = mock_response
        mock_factory.available = True
        mock_factory.create_session.return_value = mock_session
        provider = MiniMaxLLM("minimax-m2.7")
        result = provider.execute("prompt", "system")
        assert result == "Part1 Part2"

    @patch.dict(os.environ, {"MINIMAX_API_KEY": "test-key"}, clear=True)
    @patch("nexuscore.llm.providers.minimax_provider._real_call_enabled", return_value=True)
    @patch("nexuscore.llm.providers.minimax_provider.HTTP_CLIENT_FACTORY")
    def test_execute_real_mode_sets_last_call_mode(self, mock_factory, mock_real_enabled):
        mock_session = Mock()
        mock_response = Mock()
        mock_response.json.return_value = {"choices": [{"message": {"content": "ok"}}], "usage": {}}
        mock_session.post.return_value = mock_response
        mock_factory.available = True
        mock_factory.create_session.return_value = mock_session
        provider = MiniMaxLLM("minimax-m2.7")
        provider.execute("prompt", "system")
        assert provider.last_call_mode == "real"

    @patch.dict(os.environ, {"MINIMAX_API_KEY": "test-key"}, clear=True)
    @patch("nexuscore.llm.providers.minimax_provider._real_call_enabled", return_value=True)
    @patch("nexuscore.llm.providers.minimax_provider.HTTP_CLIENT_FACTORY")
    def test_execute_records_token_usage(self, mock_factory, mock_real_enabled):
        mock_session = Mock()
        mock_response = Mock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "ok"}}],
            "usage": {"prompt_tokens": 15, "completion_tokens": 30},
        }
        mock_session.post.return_value = mock_response
        mock_factory.available = True
        mock_factory.create_session.return_value = mock_session
        provider = MiniMaxLLM("minimax-m2.7")
        provider.execute("prompt", "system")
        assert provider._last_usage is not None
        assert provider._last_usage["prompt_tokens"] == 15
        assert provider._last_usage["completion_tokens"] == 30


class TestMiniMaxProviderErrorHandling:
    @patch.dict(os.environ, {"MINIMAX_API_KEY": "test-key"}, clear=True)
    @patch("nexuscore.llm.providers.minimax_provider._real_call_enabled", return_value=True)
    @patch("nexuscore.llm.providers.minimax_provider.HTTP_CLIENT_FACTORY")
    def test_execute_http_error_falls_back_to_stub(self, mock_factory, mock_real_enabled):
        mock_session = Mock()
        err = RequestsHTTPError()
        err.response = Mock()
        err.response.text = "Bad Request"
        mock_session.post.side_effect = err
        mock_factory.available = True
        mock_factory.create_session.return_value = mock_session
        provider = MiniMaxLLM("minimax-m2.7")
        result = provider.execute("prompt", "system")
        assert isinstance(result, str) and len(result) > 0
        assert provider.last_call_mode == "stub-fallback"

    @patch.dict(os.environ, {"MINIMAX_API_KEY": "test-key"}, clear=True)
    @patch("nexuscore.llm.providers.minimax_provider._real_call_enabled", return_value=True)
    @patch("nexuscore.llm.providers.minimax_provider.HTTP_CLIENT_FACTORY")
    def test_execute_http_error_as_json_returns_json_string(self, mock_factory, mock_real_enabled):
        mock_session = Mock()
        err = RequestsHTTPError()
        err.response = Mock()
        err.response.text = "Error"
        mock_session.post.side_effect = err
        mock_factory.available = True
        mock_factory.create_session.return_value = mock_session
        provider = MiniMaxLLM("minimax-m2.7")
        result = provider.execute("prompt", "system", as_json=True)
        parsed = json.loads(result)
        assert parsed["mode"] == "minimax-stub-fallback"

    @patch.dict(os.environ, {"MINIMAX_API_KEY": "test-key"}, clear=True)
    @patch("nexuscore.llm.providers.minimax_provider._real_call_enabled", return_value=True)
    @patch("nexuscore.llm.providers.minimax_provider.HTTP_CLIENT_FACTORY")
    def test_execute_general_exception_falls_back_to_stub(self, mock_factory, mock_real_enabled):
        mock_session = Mock()
        mock_session.post.side_effect = ConnectionError("fail")
        mock_factory.available = True
        mock_factory.create_session.return_value = mock_session
        provider = MiniMaxLLM("minimax-m2.7")
        result = provider.execute("prompt", "system")
        assert isinstance(result, str)
        assert provider.last_call_mode == "stub-fallback"

    @patch.dict(os.environ, {"MINIMAX_API_KEY": "test-key"}, clear=True)
    @patch("nexuscore.llm.providers.minimax_provider._real_call_enabled", return_value=True)
    @patch("nexuscore.llm.providers.minimax_provider.HTTP_CLIENT_FACTORY")
    def test_execute_empty_choices_falls_back_to_stub(self, mock_factory, mock_real_enabled):
        mock_session = Mock()
        mock_response = Mock()
        mock_response.json.return_value = {"choices": [], "usage": {}}
        mock_session.post.return_value = mock_response
        mock_factory.available = True
        mock_factory.create_session.return_value = mock_session
        provider = MiniMaxLLM("minimax-m2.7")
        result = provider.execute("prompt", "system")
        assert isinstance(result, str)
        assert provider.last_call_mode == "stub-fallback"

    @patch.dict(os.environ, {"MINIMAX_API_KEY": "test-key"}, clear=True)
    @patch("nexuscore.llm.providers.minimax_provider._real_call_enabled", return_value=True)
    @patch("nexuscore.llm.providers.minimax_provider.HTTP_CLIENT_FACTORY")
    def test_execute_no_choices_key_falls_back_to_stub(self, mock_factory, mock_real_enabled):
        mock_session = Mock()
        mock_response = Mock()
        mock_response.json.return_value = {"unexpected": "structure"}
        mock_session.post.return_value = mock_response
        mock_factory.available = True
        mock_factory.create_session.return_value = mock_session
        provider = MiniMaxLLM("minimax-m2.7")
        result = provider.execute("prompt", "system")
        assert isinstance(result, str)
        assert provider.last_call_mode == "stub-fallback"

    @patch.dict(os.environ, {"MINIMAX_API_KEY": "test-key"}, clear=True)
    @patch("nexuscore.llm.providers.minimax_provider._real_call_enabled", return_value=True)
    @patch("nexuscore.llm.providers.minimax_provider.HTTP_CLIENT_FACTORY")
    def test_execute_http_error_response_text_raises_is_handled(self, mock_factory, mock_real_enabled):
        mock_session = Mock()
        err = RequestsHTTPError()
        err.response = None  # response.text access raises AttributeError (caught by inner try/except)
        mock_session.post.side_effect = err
        mock_factory.available = True
        mock_factory.create_session.return_value = mock_session
        provider = MiniMaxLLM("minimax-m2.7")
        result = provider.execute("prompt", "system")
        assert isinstance(result, str)
        assert provider.last_call_mode == "stub-fallback"


class TestMiniMaxProviderStubDetails:
    @patch.dict(os.environ, {}, clear=True)
    def test_stub_as_json_returns_valid_json(self):
        provider = MiniMaxLLM("minimax-m2.7")
        result = provider.execute("prompt", "system", as_json=True)
        parsed = json.loads(result)
        assert isinstance(parsed, dict)
        assert parsed["mode"] == "minimax-stub"
        assert parsed["as_json"] is True

    @patch.dict(os.environ, {}, clear=True)
    def test_stub_as_json_contains_model_name(self):
        provider = MiniMaxLLM("minimax-test-model")
        result = provider.execute("prompt", "system", as_json=True)
        parsed = json.loads(result)
        assert parsed["model"] == "minimax-test-model"

    @patch.dict(os.environ, {}, clear=True)
    def test_stub_not_as_json_returns_plain_string(self):
        provider = MiniMaxLLM("minimax-m2.7")
        result = provider.execute("prompt", "system", as_json=False)
        assert not result.startswith("{")

    @patch.dict(os.environ, {"MINIMAX_API_KEY": "test-key"}, clear=True)
    @patch("nexuscore.llm.providers.minimax_provider._real_call_enabled", return_value=True)
    @patch("nexuscore.llm.providers.minimax_provider.HTTP_CLIENT_FACTORY")
    def test_fallback_json_contains_model_and_mode(self, mock_factory, mock_real_enabled):
        mock_session = Mock()
        mock_session.post.side_effect = ConnectionError("fail")
        mock_factory.available = True
        mock_factory.create_session.return_value = mock_session
        provider = MiniMaxLLM("minimax-m2.7")
        result = provider.execute("prompt", "system", as_json=True)
        parsed = json.loads(result)
        assert parsed["model"] == "minimax-m2.7"
        assert parsed["mode"] == "minimax-stub-fallback"


# --- Coverage gap tests for lines 26-27, 68-69, 75-76, branch 90->88 ---


class TestCoverageGapLines26to27:
    """Cover lines 26-27: api_key is None but real_calls would be True."""

    @patch.dict(os.environ, {}, clear=True)
    @patch("nexuscore.llm.providers.minimax_provider._real_call_enabled", return_value=True)
    @patch("nexuscore.llm.providers.minimax_provider.HTTP_CLIENT_FACTORY")
    def test_no_api_key_but_real_enabled_falls_back(self, mock_factory, mock_real_enabled):
        mock_factory.available = True
        mock_factory.create_session.return_value = Mock()
        provider = MiniMaxLLM("minimax-m2.7")
        assert provider.real_calls is False


class TestCoverageGapMaxTokens:
    """Cover lines 68-69: NEXUS_DEFAULT_MAX_OUT_TOKENS env var."""

    @patch.dict(os.environ, {"MINIMAX_API_KEY": "test-key", "NEXUS_DEFAULT_MAX_OUT_TOKENS": "512"}, clear=True)
    @patch("nexuscore.llm.providers.minimax_provider._real_call_enabled", return_value=True)
    @patch("nexuscore.llm.providers.minimax_provider.HTTP_CLIENT_FACTORY")
    def test_max_tokens_from_env_in_real_call_payload(self, mock_factory, mock_real_enabled):
        mock_resp = Mock()
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": "hello"}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5},
        }
        mock_resp.raise_for_status = Mock()
        mock_session = Mock()
        mock_session.post.return_value = mock_resp
        mock_factory.available = True
        mock_factory.create_session.return_value = mock_session
        provider = MiniMaxLLM("minimax-m2.7")
        result = provider.execute("prompt", "system")
        assert result == "hello"
        call_kwargs = mock_session.post.call_args
        payload = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")
        assert payload["max_tokens"] == 512

    @patch.dict(os.environ, {"MINIMAX_API_KEY": "test-key", "NEXUS_DEFAULT_MAX_OUT_TOKENS": "abc"}, clear=True)
    @patch("nexuscore.llm.providers.minimax_provider._real_call_enabled", return_value=True)
    @patch("nexuscore.llm.providers.minimax_provider.HTTP_CLIENT_FACTORY")
    def test_invalid_max_tokens_env_ignored(self, mock_factory, mock_real_enabled):
        mock_resp = Mock()
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": "ok"}}],
            "usage": {},
        }
        mock_resp.raise_for_status = Mock()
        mock_session = Mock()
        mock_session.post.return_value = mock_resp
        mock_factory.available = True
        mock_factory.create_session.return_value = mock_session
        provider = MiniMaxLLM("minimax-m2.7")
        provider.execute("prompt", "system")
        call_kwargs = mock_session.post.call_args
        payload = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")
        assert "max_tokens" not in payload


class TestCoverageGapAsJsonResponseFormat:
    """Cover line 75-76: as_json=True adds response_format."""

    @patch.dict(os.environ, {"MINIMAX_API_KEY": "test-key"}, clear=True)
    @patch("nexuscore.llm.providers.minimax_provider._real_call_enabled", return_value=True)
    @patch("nexuscore.llm.providers.minimax_provider.HTTP_CLIENT_FACTORY")
    def test_as_json_adds_response_format_to_payload(self, mock_factory, mock_real_enabled):
        mock_resp = Mock()
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": '{"key": "value"}'}}],
            "usage": {},
        }
        mock_resp.raise_for_status = Mock()
        mock_session = Mock()
        mock_session.post.return_value = mock_resp
        mock_factory.available = True
        mock_factory.create_session.return_value = mock_session
        provider = MiniMaxLLM("minimax-m2.7")
        result = provider.execute("prompt", "system", as_json=True)
        call_kwargs = mock_session.post.call_args
        payload = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")
        assert payload["response_format"] == {"type": "json_object"}
        assert "key" in result


class TestCoverageGapTemperatureErrorBranch:
    """Cover branch 90->88: temperature TypeError/ValueError handling."""

    @patch.dict(os.environ, {"MINIMAX_API_KEY": "test-key"}, clear=True)
    @patch("nexuscore.llm.providers.minimax_provider._real_call_enabled", return_value=True)
    @patch("nexuscore.llm.providers.minimax_provider.HTTP_CLIENT_FACTORY")
    def test_invalid_temperature_type_error_handled(self, mock_factory, mock_real_enabled):
        mock_resp = Mock()
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": "ok"}}],
            "usage": {},
        }
        mock_resp.raise_for_status = Mock()
        mock_session = Mock()
        mock_session.post.return_value = mock_resp
        mock_factory.available = True
        mock_factory.create_session.return_value = mock_session
        provider = MiniMaxLLM("minimax-m2.7")
        result = provider.execute("prompt", "system", temperature="not-a-number")
        assert result == "ok"
        call_kwargs = mock_session.post.call_args
        payload = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")
        assert "temperature" not in payload

    @patch.dict(os.environ, {"MINIMAX_API_KEY": "test-key"}, clear=True)
    @patch("nexuscore.llm.providers.minimax_provider._real_call_enabled", return_value=True)
    @patch("nexuscore.llm.providers.minimax_provider.HTTP_CLIENT_FACTORY")
    def test_none_temperature_handled(self, mock_factory, mock_real_enabled):
        mock_resp = Mock()
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": "ok"}}],
            "usage": {},
        }
        mock_resp.raise_for_status = Mock()
        mock_session = Mock()
        mock_session.post.return_value = mock_resp
        mock_factory.available = True
        mock_factory.create_session.return_value = mock_session
        provider = MiniMaxLLM("minimax-m2.7")
        result = provider.execute("prompt", "system", temperature=None)
        assert result == "ok"
        call_kwargs = mock_session.post.call_args
        payload = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")
        assert "temperature" not in payload
