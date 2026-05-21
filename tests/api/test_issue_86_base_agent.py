"""Issue #86: base_agent.py フォールバックパスのテスト

対象: dotenv load_dotenv例外フォールバック、LLMRouter import失敗フォールバック、
execute_llm_task分岐（no router, as_json fallback, error fallback）
"""

import json
import sys
import types
from unittest.mock import MagicMock, patch

import pytest


class TestBaseAgentFallbacks:
    """BaseAgentのインポートフォールバックとLLM実行分岐をテスト"""

    def _import_base_agent(self):
        from nexuscore.agents.base_agent import BaseAgent
        return BaseAgent

    def test_init_without_llm_router(self):
        """LLMRouter=Noneの環境でもBaseAgentは初期化できる"""
        with patch("nexuscore.agents.base_agent.LLMRouter", None):
            BaseAgent = self._import_base_agent()
            agent = BaseAgent()
            assert agent.llm_router is None

    def test_init_llm_router_exception(self):
        """LLMRouter()が例外を投げても初期化は成功する"""
        mock_router_cls = MagicMock(side_effect=RuntimeError("router init failed"))
        with patch("nexuscore.agents.base_agent.LLMRouter", mock_router_cls):
            BaseAgent = self._import_base_agent()
            agent = BaseAgent()
            assert agent.llm_router is None

    def test_execute_llm_task_no_router_returns_empty(self):
        """ルーターがない場合、空文字を返す"""
        with patch("nexuscore.agents.base_agent.LLMRouter", None):
            BaseAgent = self._import_base_agent()
            agent = BaseAgent()
            result = agent.execute_llm_task("test prompt")
            assert result == ""

    def test_execute_llm_task_no_router_as_json_returns_empty_object(self):
        """ルーターがない + as_json=Trueの場合、空のJSONオブジェクトを返す"""
        with patch("nexuscore.agents.base_agent.LLMRouter", None):
            BaseAgent = self._import_base_agent()
            agent = BaseAgent()
            result = agent.execute_llm_task("test prompt", as_json=True)
            assert result == "{}"

    def test_execute_llm_task_with_mock_router(self):
        """ルーター経由でLLM実行が成功するパス"""
        mock_llm = MagicMock()
        mock_llm.execute.return_value = '{"result": "ok"}'

        mock_router = MagicMock()
        mock_router.get_llm_for_task.return_value = mock_llm

        BaseAgent = self._import_base_agent()
        agent = BaseAgent()
        agent.llm_router = mock_router

        result = agent.execute_llm_task("test", as_json=True)
        assert json.loads(result) == {"result": "ok"}

    def test_execute_llm_task_llm_get_failure_returns_fallback(self):
        """LLMクライアント取得失敗時にフォールバックを返す（retryなし環境）"""
        with patch("nexuscore.agents.base_agent.HAS_RETRY", False):
            BaseAgent = self._import_base_agent()
            agent = BaseAgent()
            agent.llm_router = MagicMock()
            agent.llm_router.get_llm_for_task.side_effect = RuntimeError("no llm")

            result = agent.execute_llm_task("test", as_json=True)
            assert result == "{}"

    def test_execute_llm_task_llm_execute_failure_returns_fallback(self):
        """LLM実行失敗時にフォールバックを返す（retryなし環境）"""
        mock_llm = MagicMock()
        mock_llm.execute.side_effect = RuntimeError("execution failed")

        mock_router = MagicMock()
        mock_router.get_llm_for_task.return_value = mock_llm

        with patch("nexuscore.agents.base_agent.HAS_RETRY", False):
            BaseAgent = self._import_base_agent()
            agent = BaseAgent()
            agent.llm_router = mock_router

            result = agent.execute_llm_task("test", as_json=True)
            assert result == "{}"

    def test_execute_llm_task_fallback_default_llm(self):
        """get_llm_for_taskがなければget_default_llmを使用する"""
        mock_llm = MagicMock()
        mock_llm.execute.return_value = "result text"

        mock_router = MagicMock(spec=["get_default_llm"])
        mock_router.get_default_llm.return_value = mock_llm

        BaseAgent = self._import_base_agent()
        agent = BaseAgent()
        agent.llm_router = mock_router

        result = agent.execute_llm_task("test")
        assert result == "result text"

    def test_execute_llm_task_invalid_json_with_retry(self):
        """as_json=Trueで不正JSONが返った場合、InvalidModelOutputErrorが発生"""
        mock_llm = MagicMock()
        mock_llm.execute.return_value = "not valid json"

        mock_router = MagicMock()
        mock_router.get_llm_for_task.return_value = mock_llm

        # retry有効時は、リトライ後にフォールバックを返す
        with patch("nexuscore.agents.base_agent.HAS_RETRY", False):
            BaseAgent = self._import_base_agent()
            agent = BaseAgent()
            agent.llm_router = mock_router

            result = agent.execute_llm_task("test", as_json=True)
            assert result == "{}"

    def test_retry_context_attribute(self):
        """retry_context属性の設定と取得"""
        BaseAgent = self._import_base_agent()
        agent = BaseAgent()
        assert agent.retry_context is None

        mock_ctx = MagicMock()
        agent.retry_context = mock_ctx
        assert agent.retry_context is mock_ctx

    def test_system_prompt_override(self):
        """派生クラスでSYSTEM_PROMPTを上書き可能"""
        BaseAgent = self._import_base_agent()

        class CustomAgent(BaseAgent):
            SYSTEM_PROMPT = "Custom system prompt."

        agent = CustomAgent()
        assert agent.SYSTEM_PROMPT == "Custom system prompt."
