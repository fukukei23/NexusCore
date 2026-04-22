"""openai_provider.py カバレッジブースト — Azure, real-call, error handling"""
import json
import os
from unittest.mock import patch, MagicMock

import pytest

from nexuscore.llm.providers.openai_provider import OpenAILLM


def _make_stub_llm(model_name="gpt-4o"):
    llm = OpenAILLM.__new__(OpenAILLM)
    from nexuscore.llm.providers.base import BaseLLM
    BaseLLM.__init__(llm, model_name)
    llm.real_calls = False
    llm.session = None
    llm.base_url = "https://api.openai.com"
    llm.api_key = "fake-key"
    llm.azure = False
    llm.azure_deployment = None
    llm.azure_api_version = "2024-08-01-preview"
    return llm


class TestOpenAIInit:
    @patch.dict(os.environ, {}, clear=False)
    def test_no_key_stub_mode(self):
        for key in ["OPENAI_API_KEY", "OPENAI_BASE_URL", "OPENAI_AZURE"]:
            os.environ.pop(key, None)
        with patch("nexuscore.llm.providers.openai_provider._real_call_enabled", return_value=False):
            llm = OpenAILLM("gpt-4o")
            assert llm.real_calls is False

    @patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test", "OPENAI_AZURE": "1", "OPENAI_AZURE_DEPLOYMENT": "my-deploy"})
    def test_azure_init(self):
        mock_session = MagicMock()
        mock_factory = MagicMock()
        mock_factory.available = True
        mock_factory.create_session.return_value = mock_session
        with patch("nexuscore.llm.providers.openai_provider.HTTP_CLIENT_FACTORY", mock_factory):
            with patch("nexuscore.llm.providers.openai_provider._real_call_enabled", return_value=True):
                llm = OpenAILLM("gpt-4o")
                assert llm.azure is True
                assert llm.azure_deployment == "my-deploy"

    @patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test", "OPENAI_AZURE": "1"})
    def test_azure_missing_deployment_raises(self):
        with pytest.raises(ValueError, match="OPENAI_AZURE_DEPLOYMENT"):
            with patch("nexuscore.llm.providers.openai_provider._real_call_enabled", return_value=True):
                mock_factory = MagicMock()
                mock_factory.available = True
                mock_factory.create_session.return_value = MagicMock()
                with patch("nexuscore.llm.providers.openai_provider.HTTP_CLIENT_FACTORY", mock_factory):
                    OpenAILLM("gpt-4o")

    @patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"})
    def test_no_http_session_fallback(self):
        mock_factory = MagicMock()
        mock_factory.available = True
        mock_factory.create_session.return_value = None
        with patch("nexuscore.llm.providers.openai_provider.HTTP_CLIENT_FACTORY", mock_factory):
            with patch("nexuscore.llm.providers.openai_provider._real_call_enabled", return_value=True):
                llm = OpenAILLM("gpt-4o")
                assert llm.real_calls is False


class TestOpenAIExecute:
    def test_stub_returns_text(self):
        llm = _make_stub_llm()
        result = llm.execute("prompt", "system")
        assert isinstance(result, str)

    def test_stub_returns_json(self):
        llm = _make_stub_llm()
        result = llm.execute("prompt", "system", as_json=True)
        data = json.loads(result)
        assert "model" in data

    def test_real_call_success(self):
        llm = _make_stub_llm()
        llm.real_calls = True
        mock_session = MagicMock()
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": "Hello"}}],
            "usage": {"prompt_tokens": 5, "completion_tokens": 2},
        }
        mock_resp.raise_for_status = MagicMock()
        mock_session.post.return_value = mock_resp
        llm.session = mock_session

        result = llm.execute("prompt", "system")
        assert result == "Hello"
        assert llm.last_call_mode == "real"

    def test_azure_real_call_url(self):
        llm = _make_stub_llm()
        llm.real_calls = True
        llm.azure = True
        llm.azure_deployment = "test-deploy"
        mock_session = MagicMock()
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": "Azure response"}}],
            "usage": {},
        }
        mock_resp.raise_for_status = MagicMock()
        mock_session.post.return_value = mock_resp
        llm.session = mock_session

        result = llm.execute("prompt", "system")
        call_url = mock_session.post.call_args[1].get("url") or mock_session.post.call_args[0][0]
        assert "deployments" in call_url

    def test_real_call_http_error_fallback(self):
        llm = _make_stub_llm()
        llm.real_calls = True
        mock_session = MagicMock()
        mock_error = MagicMock()
        mock_error.response.text = "server error"
        from nexuscore.llm.http_client import RequestsHTTPError
        mock_session.post.side_effect = RequestsHTTPError("500", response=mock_error)
        llm.session = mock_session

        result = llm.execute("prompt", "system")
        assert llm.last_call_mode == "stub-fallback"

    def test_real_call_http_error_bad_response_attr(self):
        llm = _make_stub_llm()
        llm.real_calls = True
        mock_session = MagicMock()
        mock_error = MagicMock()
        mock_error.response.text = MagicMock(side_effect=AttributeError("no text"))
        from nexuscore.llm.http_client import RequestsHTTPError
        mock_session.post.side_effect = RequestsHTTPError("500", response=mock_error)
        llm.session = mock_session

        result = llm.execute("prompt", "system", as_json=True)
        data = json.loads(result)
        assert data["mode"] == "openai-stub-fallback"

    def test_real_call_generic_error_fallback(self):
        llm = _make_stub_llm()
        llm.real_calls = True
        mock_session = MagicMock()
        mock_session.post.side_effect = RuntimeError("timeout")
        llm.session = mock_session

        result = llm.execute("prompt", "system")
        assert llm.last_call_mode == "stub-fallback"

    def test_real_call_no_text_fallback(self):
        llm = _make_stub_llm()
        llm.real_calls = True
        mock_session = MagicMock()
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": ""}}],
            "usage": {},
        }
        mock_resp.raise_for_status = MagicMock()
        mock_session.post.return_value = mock_resp
        llm.session = mock_session

        result = llm.execute("prompt", "system")
        assert llm.last_call_mode == "stub-fallback"

    def test_gpt5_no_temperature(self):
        llm = _make_stub_llm(model_name="gpt-5-chat-latest")
        llm.real_calls = True
        mock_session = MagicMock()
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": "response"}}],
            "usage": {},
        }
        mock_resp.raise_for_status = MagicMock()
        mock_session.post.return_value = mock_resp
        llm.session = mock_session

        llm.execute("prompt", "system", temperature=0.5)
        payload = mock_session.post.call_args[1]["json"]
        assert "temperature" not in payload

    def test_gpt5_no_max_tokens(self):
        llm = _make_stub_llm(model_name="gpt-5-chat-latest")
        llm.real_calls = True
        mock_session = MagicMock()
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": "response"}}],
            "usage": {},
        }
        mock_resp.raise_for_status = MagicMock()
        mock_session.post.return_value = mock_resp
        llm.session = mock_session

        with patch.dict(os.environ, {"NEXUS_DEFAULT_MAX_OUT_TOKENS": "1024"}):
            llm.execute("prompt", "system")
            payload = mock_session.post.call_args[1]["json"]
            assert "max_tokens" not in payload

    def test_azure_no_deployment_runtime_raises(self):
        llm = _make_stub_llm()
        llm.real_calls = True
        llm.azure = True
        llm.azure_deployment = None
        mock_session = MagicMock()
        llm.session = mock_session

        result = llm.execute("prompt", "system")
        # Should fall through to stub-fallback
        assert llm.last_call_mode == "stub-fallback"
