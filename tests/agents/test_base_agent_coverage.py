"""
base_agent.py のカバレッジ向上テスト

未カバー行: 19-20, 25-26, 40-48, 120-125, 141, 147, 172-175
"""

from __future__ import annotations

from unittest.mock import MagicMock, Mock, patch

import pytest


class TestBaseAgentInitFallback:
    """BaseAgent の初期化フォールバックテスト"""

    def test_init_without_llm_router(self):
        """LLMRouter が None の場合でも初期化が成功することを確認"""
        with patch("nexuscore.agents.base_agent.LLMRouter", None):
            from nexuscore.agents.base_agent import BaseAgent

            agent = BaseAgent()
            assert agent.llm_router is None

    def test_init_llm_router_raises_exception(self):
        """LLMRouter の初期化で例外が発生しても agent が作成されることを確認"""
        with patch("nexuscore.agents.base_agent.LLMRouter", side_effect=RuntimeError("init fail")):
            from nexuscore.agents.base_agent import BaseAgent

            agent = BaseAgent()
            assert agent.llm_router is None

    def test_init_with_valid_llm_router(self):
        """正常な LLMRouter で初期化されることを確認"""
        mock_router = Mock()
        with patch("nexuscore.agents.base_agent.LLMRouter", return_value=mock_router):
            from nexuscore.agents.base_agent import BaseAgent

            agent = BaseAgent()
            assert agent.llm_router is mock_router


class TestExecuteLlmTaskFallback:
    """execute_llm_task のフォールバックテスト"""

    def test_no_llm_router_returns_empty_string(self):
        """llm_router が None の場合、空文字列を返すことを確認"""
        from nexuscore.agents.base_agent import BaseAgent

        agent = BaseAgent()
        agent.llm_router = None
        result = agent.execute_llm_task("test prompt")
        assert result == ""

    def test_no_llm_router_as_json_returns_empty_json(self):
        """llm_router が None で as_json=True の場合、{} を返すことを確認"""
        from nexuscore.agents.base_agent import BaseAgent

        agent = BaseAgent()
        agent.llm_router = None
        result = agent.execute_llm_task("test prompt", as_json=True)
        assert result == "{}"

    def test_llm_router_has_no_get_llm_for_task(self):
        """llm_router に get_llm_for_task がない場合の動作確認"""
        from nexuscore.agents.base_agent import BaseAgent

        agent = BaseAgent()
        agent.llm_router = Mock(spec=[])  # 空のspec → 属性なし
        result = agent.execute_llm_task("test prompt")
        assert result == ""

    def test_llm_router_get_default_llm_returns_none(self):
        """get_default_llm が None を返す場合の動作確認"""
        from nexuscore.agents.base_agent import BaseAgent

        agent = BaseAgent()
        mock_router = Mock()
        mock_router.get_llm_for_task.side_effect = AttributeError("not found")
        agent.llm_router = mock_router
        result = agent.execute_llm_task("test prompt")
        assert result == ""


class TestExecuteLlmTaskWithMockLlm:
    """execute_llm_task の LLM モックテスト"""

    def test_execute_with_mock_llm_returns_response(self):
        """モック LLM が正常に応答を返すことを確認"""
        from nexuscore.agents.base_agent import BaseAgent

        agent = BaseAgent()
        mock_llm = Mock()
        mock_llm.execute.return_value = "Hello from LLM"
        mock_router = Mock()
        mock_router.get_llm_for_task.return_value = mock_llm
        agent.llm_router = mock_router

        result = agent.execute_llm_task("test prompt")
        assert result == "Hello from LLM"

    def test_execute_as_json_with_valid_json(self):
        """as_json=True で有効な JSON が返されることを確認"""
        from nexuscore.agents.base_agent import BaseAgent

        agent = BaseAgent()
        mock_llm = Mock()
        mock_llm.execute.return_value = '{"key": "value"}'
        mock_router = Mock()
        mock_router.get_llm_for_task.return_value = mock_llm
        agent.llm_router = mock_router

        result = agent.execute_llm_task("test prompt", as_json=True)
        assert result == '{"key": "value"}'

    def test_execute_as_json_with_invalid_json_falls_back(self):
        """as_json=True で無効な JSON の場合フォールバックすることを確認"""
        from nexuscore.agents.base_agent import BaseAgent

        agent = BaseAgent()
        mock_llm = Mock()
        mock_llm.execute.return_value = "not json"
        mock_router = Mock()
        mock_router.get_llm_for_task.return_value = mock_llm
        agent.llm_router = mock_router

        # HAS_RETRY=False の場合、例外が起きてもフォールバックする
        with patch("nexuscore.agents.base_agent.HAS_RETRY", False):
            result = agent.execute_llm_task("test prompt", as_json=True)
            assert result == "{}"

    def test_execute_llm_raises_exception_falls_back(self):
        """LLM 実行で例外が発生した場合フォールバックすることを確認"""
        from nexuscore.agents.base_agent import BaseAgent

        agent = BaseAgent()
        mock_llm = Mock()
        mock_llm.execute.side_effect = RuntimeError("LLM error")
        mock_router = Mock()
        mock_router.get_llm_for_task.return_value = mock_llm
        agent.llm_router = mock_router

        with patch("nexuscore.agents.base_agent.HAS_RETRY", False):
            result = agent.execute_llm_task("test prompt")
            assert result == ""

    def test_llm_client_get_raises_exception(self):
        """LLM クライアント取得で例外が発生した場合のフォールバック確認"""
        from nexuscore.agents.base_agent import BaseAgent

        agent = BaseAgent()
        mock_router = Mock()
        mock_router.get_llm_for_task.side_effect = RuntimeError("connection fail")
        agent.llm_router = mock_router

        with patch("nexuscore.agents.base_agent.HAS_RETRY", False):
            result = agent.execute_llm_task("test prompt")
            assert result == ""


class TestBaseAgentSystemPrompt:
    """system_prompt と JSON ガードのテスト"""

    def test_custom_system_prompt(self):
        """カスタム SYSTEM_PROMPT が使われることを確認"""
        from nexuscore.agents.base_agent import BaseAgent

        class CustomAgent(BaseAgent):
            SYSTEM_PROMPT = "You are a code reviewer."

        agent = CustomAgent()
        assert agent.SYSTEM_PROMPT == "You are a code reviewer."

    def test_default_system_prompt(self):
        """デフォルト SYSTEM_PROMPT が設定されていることを確認"""
        from nexuscore.agents.base_agent import BaseAgent

        agent = BaseAgent()
        assert "helpful assistant" in agent.SYSTEM_PROMPT.lower()

    def test_retry_context_stored(self):
        """retry_context が正しく保存されることを確認"""
        from nexuscore.agents.base_agent import BaseAgent

        agent = BaseAgent()
        assert agent.retry_context is None

        mock_ctx = Mock()
        agent.retry_context = mock_ctx
        assert agent.retry_context is mock_ctx
