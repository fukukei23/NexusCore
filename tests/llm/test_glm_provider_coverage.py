"""glm_provider.py のテスト — カバレッジ56%→向上"""
import json
import os
from unittest.mock import patch, MagicMock

import pytest

from nexuscore.llm.providers.glm_provider import GLMLLM


class TestGLMLLMInit:
    @patch.dict(os.environ, {}, clear=False)
    def test_stub_mode_when_no_key(self):
        for key in ["GLM_API_KEY", "GLM_MODEL", "GLM_API_BASE", "GLM_BASE_URL"]:
            os.environ.pop(key, None)
        llm = GLMLLM("glm-4-plus")
        assert llm.model_name == "glm-4-plus"
        assert llm.real_calls is False

    @patch.dict(os.environ, {"GLM_API_KEY": "fake-key"})
    def test_real_mode_with_key(self):
        mock_session = MagicMock()
        mock_factory = MagicMock()
        mock_factory.available = True
        mock_factory.create_session.return_value = mock_session
        with patch("nexuscore.llm.providers.openai_compat.HTTP_CLIENT_FACTORY", mock_factory):
            with patch("nexuscore.llm.providers.openai_compat._real_call_enabled", return_value=True):
                llm = GLMLLM("glm-4-plus")
                assert llm.real_calls is True
                assert llm.session == mock_session

    @patch.dict(os.environ, {"GLM_API_KEY": "fake-key", "GLM_MODEL": "custom-model"})
    def test_env_model_override(self):
        mock_factory = MagicMock()
        mock_factory.available = False
        with patch("nexuscore.llm.providers.openai_compat.HTTP_CLIENT_FACTORY", mock_factory):
            with patch("nexuscore.llm.providers.openai_compat._real_call_enabled", return_value=False):
                llm = GLMLLM("glm-4-plus")
                assert llm.model_name == "custom-model"

    @patch.dict(os.environ, {"GLM_API_KEY": "fake-key"})
    def test_no_http_session_falls_to_stub(self):
        mock_factory = MagicMock()
        mock_factory.available = True
        mock_factory.create_session.return_value = None
        with patch("nexuscore.llm.providers.openai_compat.HTTP_CLIENT_FACTORY", mock_factory):
            with patch("nexuscore.llm.providers.openai_compat._real_call_enabled", return_value=True):
                llm = GLMLLM("glm-4-plus")
                assert llm.real_calls is False

    @patch.dict(os.environ, {"GLM_API_KEY": "fake-key", "GLM_BASE_URL": "https://custom.api/v1"})
    def test_custom_base_url(self):
        mock_factory = MagicMock()
        mock_factory.available = False
        with patch("nexuscore.llm.providers.openai_compat.HTTP_CLIENT_FACTORY", mock_factory):
            with patch("nexuscore.llm.providers.openai_compat._real_call_enabled", return_value=False):
                llm = GLMLLM("glm-4-plus")
                assert llm.base_url == "https://custom.api/v1"

    @patch.dict(os.environ, {"GLM_API_KEY": "fake-key", "GLM_API_BASE": "https://api.base/v2"})
    def test_glm_api_base_takes_priority(self):
        mock_factory = MagicMock()
        mock_factory.available = False
        with patch("nexuscore.llm.providers.openai_compat.HTTP_CLIENT_FACTORY", mock_factory):
            with patch("nexuscore.llm.providers.openai_compat._real_call_enabled", return_value=False):
                llm = GLMLLM("glm-4-plus")
                assert llm.base_url == "https://api.base/v2"


class TestGLMLLMExecute:
    def _make_stub_llm(self):
        llm = GLMLLM.__new__(GLMLLM)
        from nexuscore.llm.providers.base import BaseLLM
        BaseLLM.__init__(llm, "glm-4-plus")
        llm.real_calls = False
        llm.session = None
        llm.base_url = "https://open.bigmodel.cn/api/paas/v4"
        llm.api_key = "fake-key"
        return llm

    def test_stub_mode_returns_json(self):
        llm = self._make_stub_llm()
        result = llm.execute("prompt", "system", as_json=True)
        data = json.loads(result)
        assert data["mode"] == "glm-stub"
        assert data["as_json"] is True

    def test_stub_mode_returns_text(self):
        llm = self._make_stub_llm()
        result = llm.execute("prompt", "system")
        assert isinstance(result, str)
        assert "stub" in result.lower() or "preview" in result.lower()

    def test_real_call_success(self):
        llm = self._make_stub_llm()
        llm.real_calls = True
        mock_session = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": "Hello from GLM"}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5},
        }
        mock_resp.raise_for_status = MagicMock()
        mock_session.post.return_value = mock_resp
        llm.session = mock_session

        result = llm.execute("prompt", "system")
        assert result == "Hello from GLM"
        assert llm.last_call_mode == "real"

    def test_real_call_http_error_fallback(self):
        llm = self._make_stub_llm()
        llm.real_calls = True
        mock_session = MagicMock()
        mock_error = MagicMock()
        mock_error.response.text = "server error"
        from nexuscore.llm.http_client import RequestsHTTPError
        mock_session.post.side_effect = RequestsHTTPError("500", response=mock_error)
        llm.session = mock_session

        result = llm.execute("prompt", "system")
        assert llm.last_call_mode == "stub-fallback"

    def test_real_call_http_error_with_bad_response_attr(self):
        llm = self._make_stub_llm()
        llm.real_calls = True
        mock_session = MagicMock()
        mock_error = MagicMock()
        mock_error.response.text = MagicMock(side_effect=Exception("no text"))
        from nexuscore.llm.http_client import RequestsHTTPError
        mock_session.post.side_effect = RequestsHTTPError("500", response=mock_error)
        llm.session = mock_session

        result = llm.execute("prompt", "system", as_json=True)
        data = json.loads(result)
        assert data["mode"] == "glm-stub-fallback"

    def test_real_call_generic_exception_fallback(self):
        llm = self._make_stub_llm()
        llm.real_calls = True
        mock_session = MagicMock()
        mock_session.post.side_effect = RuntimeError("connection failed")
        llm.session = mock_session

        result = llm.execute("prompt", "system")
        assert llm.last_call_mode == "stub-fallback"

    def test_real_call_as_json_strips_json(self):
        llm = self._make_stub_llm()
        llm.real_calls = True
        mock_session = MagicMock()
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": "```json\n{\"key\": \"value\"}\n```"}}],
            "usage": {},
        }
        mock_resp.raise_for_status = MagicMock()
        mock_session.post.return_value = mock_resp
        llm.session = mock_session

        result = llm.execute("prompt", "system", as_json=True)
        assert "key" in result

    def test_real_call_no_text_raises_fallback(self):
        llm = self._make_stub_llm()
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

        # Empty text triggers RuntimeError → caught by generic except → stub-fallback
        result = llm.execute("prompt", "system")
        assert llm.last_call_mode == "stub-fallback"

    @patch.dict(os.environ, {"NEXUS_DEFAULT_MAX_OUT_TOKENS": "1024"})
    def test_real_call_with_max_tokens(self):
        llm = self._make_stub_llm()
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

        llm.execute("prompt", "system")
        call_kwargs = mock_session.post.call_args[1]
        assert call_kwargs["json"]["max_tokens"] == 1024

    @patch.dict(os.environ, {"NEXUS_DEFAULT_MAX_OUT_TOKENS": "not-a-number"})
    def test_real_call_with_invalid_max_tokens(self):
        llm = self._make_stub_llm()
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

        llm.execute("prompt", "system")
        call_kwargs = mock_session.post.call_args[1]
        assert "max_tokens" not in call_kwargs["json"]
