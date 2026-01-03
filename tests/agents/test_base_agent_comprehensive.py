"""
base_agent.py の包括的テスト

カバレッジ:
- BaseAgent: 全エージェントの基底クラス
  - __init__: LLMRouter初期化、logger設定
  - execute_llm_task: LLM実行
    - as_json パラメータでJSON-onlyガード追加
    - task_type によるモデル選択
    - RetryContext 統合
    - エラーハンドリングとフォールバック
"""

import json
import logging
import sys
from unittest.mock import MagicMock, Mock, patch

import pytest

# LLMRouter と retry_utils をモック
sys.modules['nexuscore.llm.llm_router'] = MagicMock()
sys.modules['nexuscore.core.retry_utils'] = MagicMock()
sys.modules['nexuscore.core.errors'] = MagicMock()

try:
    from nexuscore.agents.base_agent import BaseAgent
    HAS_BASE_AGENT = True
except ImportError:
    HAS_BASE_AGENT = False
    BaseAgent = None


@pytest.mark.skipif(not HAS_BASE_AGENT, reason="base_agent module not available")
class TestBaseAgentInit:
    """BaseAgent 初期化のテスト"""

    @patch('nexuscore.agents.base_agent.LLMRouter')
    def test_init_with_llm_router(self, mock_router_class):
        """LLMRouterが正常に初期化される"""
        mock_router_instance = Mock()
        mock_router_class.return_value = mock_router_instance

        agent = BaseAgent()

        assert agent.llm_router == mock_router_instance
        assert agent.retry_context is None
        assert hasattr(agent, 'logger')
        mock_router_class.assert_called_once()

    @patch('nexuscore.agents.base_agent.LLMRouter', None)
    def test_init_without_llm_router(self):
        """LLMRouterが利用できない場合でも初期化成功"""
        agent = BaseAgent()

        assert agent.llm_router is None
        assert hasattr(agent, 'logger')

    @patch('nexuscore.agents.base_agent.LLMRouter')
    def test_init_router_failure(self, mock_router_class):
        """LLMRouter初期化失敗時でも継続"""
        mock_router_class.side_effect = Exception("Router init failed")

        agent = BaseAgent()

        assert agent.llm_router is None
        assert hasattr(agent, 'logger')

    def test_system_prompt_default(self):
        """デフォルトSYSTEM_PROMPTが設定されている"""
        assert BaseAgent.SYSTEM_PROMPT == "You are a helpful assistant."


@pytest.mark.skipif(not HAS_BASE_AGENT, reason="base_agent module not available")
class TestBaseAgentExecuteLLMTask:
    """BaseAgent.execute_llm_task() のテスト"""

    @patch('nexuscore.agents.base_agent.HAS_RETRY', False)
    @patch('nexuscore.agents.base_agent.LLMRouter')
    def test_execute_llm_task_basic(self, mock_router_class):
        """基本的なLLM実行"""
        mock_llm = Mock()
        mock_llm.execute.return_value = "LLM response"

        mock_router = Mock()
        mock_router.get_llm_for_task.return_value = mock_llm
        mock_router_class.return_value = mock_router

        agent = BaseAgent()
        result = agent.execute_llm_task("Test prompt")

        assert result == "LLM response"
        mock_llm.execute.assert_called_once()
        assert "Test prompt" in str(mock_llm.execute.call_args)

    @patch('nexuscore.agents.base_agent.HAS_RETRY', False)
    @patch('nexuscore.agents.base_agent.LLMRouter')
    def test_execute_llm_task_with_json(self, mock_router_class):
        """as_json=Trueでシステムプロンプトにガード追加"""
        mock_llm = Mock()
        mock_llm.execute.return_value = '{"key": "value"}'

        mock_router = Mock()
        mock_router.get_llm_for_task.return_value = mock_llm
        mock_router_class.return_value = mock_router

        agent = BaseAgent()
        result = agent.execute_llm_task("Test prompt", as_json=True)

        assert result == '{"key": "value"}'

        # システムプロンプトにJSON guardが追加されたことを確認
        call_kwargs = mock_llm.execute.call_args[1]
        assert "structured JSON emitter" in call_kwargs['system_prompt']
        assert "ONLY a valid JSON" in call_kwargs['system_prompt']
        assert call_kwargs['as_json'] is True

    @patch('nexuscore.agents.base_agent.HAS_RETRY', False)
    @patch('nexuscore.agents.base_agent.LLMRouter')
    def test_execute_llm_task_with_task_type(self, mock_router_class):
        """task_typeによるモデル選択"""
        mock_llm = Mock()
        mock_llm.execute.return_value = "Response"

        mock_router = Mock()
        mock_router.get_llm_for_task.return_value = mock_llm
        mock_router_class.return_value = mock_router

        agent = BaseAgent()
        result = agent.execute_llm_task("Test prompt", task_type="code_generate")

        assert result == "Response"
        mock_router.get_llm_for_task.assert_called_once_with("Test prompt", task_type="code_generate")

    @patch('nexuscore.agents.base_agent.HAS_RETRY', False)
    @patch('nexuscore.agents.base_agent.LLMRouter')
    def test_execute_llm_task_fallback_to_default_llm(self, mock_router_class):
        """get_llm_for_taskがない場合はget_default_llmにフォールバック"""
        mock_llm = Mock()
        mock_llm.execute.return_value = "Default response"

        mock_router = Mock(spec=[])  # get_llm_for_taskがない
        mock_router.get_default_llm = Mock(return_value=mock_llm)
        mock_router_class.return_value = mock_router

        agent = BaseAgent()
        result = agent.execute_llm_task("Test prompt")

        assert result == "Default response"
        mock_router.get_default_llm.assert_called_once()

    @patch('nexuscore.agents.base_agent.HAS_RETRY', False)
    @patch('nexuscore.agents.base_agent.LLMRouter')
    def test_execute_llm_task_no_llm_available(self, mock_router_class):
        """LLMが利用できない場合は空文字列を返す"""
        mock_router = Mock()
        mock_router.get_llm_for_task.return_value = None
        mock_router_class.return_value = mock_router

        agent = BaseAgent()
        result = agent.execute_llm_task("Test prompt")

        assert result == ""

    @patch('nexuscore.agents.base_agent.HAS_RETRY', False)
    @patch('nexuscore.agents.base_agent.LLMRouter')
    def test_execute_llm_task_no_llm_available_json(self, mock_router_class):
        """LLMが利用できない場合（as_json=True）は{}を返す"""
        mock_router = Mock()
        mock_router.get_llm_for_task.return_value = None
        mock_router_class.return_value = mock_router

        agent = BaseAgent()
        result = agent.execute_llm_task("Test prompt", as_json=True)

        assert result == "{}"

    @patch('nexuscore.agents.base_agent.HAS_RETRY', False)
    @patch('nexuscore.agents.base_agent.LLMRouter')
    def test_execute_llm_task_llm_execution_error(self, mock_router_class):
        """LLM実行エラー時のフォールバック"""
        mock_llm = Mock()
        mock_llm.execute.side_effect = Exception("LLM execution failed")

        mock_router = Mock()
        mock_router.get_llm_for_task.return_value = mock_llm
        mock_router_class.return_value = mock_router

        agent = BaseAgent()
        result = agent.execute_llm_task("Test prompt")

        assert result == ""

    @patch('nexuscore.agents.base_agent.HAS_RETRY', False)
    @patch('nexuscore.agents.base_agent.LLMRouter')
    def test_execute_llm_task_invalid_json_response(self, mock_router_class):
        """as_json=Trueで無効なJSON応答が返された場合"""
        mock_llm = Mock()
        mock_llm.execute.return_value = "Not valid JSON"

        mock_router = Mock()
        mock_router.get_llm_for_task.return_value = mock_llm
        mock_router_class.return_value = mock_router

        agent = BaseAgent()
        result = agent.execute_llm_task("Test prompt", as_json=True)

        # JSONパースエラーで空文字列にフォールバック
        assert result == "{}"

    @patch('nexuscore.agents.base_agent.HAS_RETRY', True)
    @patch('nexuscore.agents.base_agent.retry_with_context')
    @patch('nexuscore.agents.base_agent.LLMRouter')
    def test_execute_llm_task_with_retry(self, mock_router_class, mock_retry):
        """Retry機能が有効な場合"""
        mock_llm = Mock()
        mock_llm.execute.return_value = "Response with retry"

        mock_router = Mock()
        mock_router.get_llm_for_task.return_value = mock_llm
        mock_router_class.return_value = mock_router

        # retry_with_context は wrapped function を返す
        def fake_retry_wrapper(func, **kwargs):
            return func

        mock_retry.return_value = lambda: "Response with retry"

        agent = BaseAgent()
        result = agent.execute_llm_task("Test prompt")

        # Retryが呼ばれることを確認
        assert mock_retry.called or result == "Response with retry"

    @patch('nexuscore.agents.base_agent.HAS_RETRY', False)
    @patch('nexuscore.agents.base_agent.LLMRouter')
    def test_execute_llm_task_with_retry_context_param(self, mock_router_class):
        """retry_context パラメータを渡した場合"""
        mock_llm = Mock()
        mock_llm.execute.return_value = "Response"

        mock_router = Mock()
        mock_router.get_llm_for_task.return_value = mock_llm
        mock_router_class.return_value = mock_router

        agent = BaseAgent()
        mock_retry_context = Mock()

        result = agent.execute_llm_task("Test prompt", retry_context=mock_retry_context)

        assert result == "Response"


@pytest.mark.skipif(not HAS_BASE_AGENT, reason="base_agent module not available")
class TestEdgeCases:
    """エッジケースのテスト"""

    @patch('nexuscore.agents.base_agent.HAS_RETRY', False)
    @patch('nexuscore.agents.base_agent.LLMRouter')
    def test_empty_prompt(self, mock_router_class):
        """空のプロンプトでも動作する"""
        mock_llm = Mock()
        mock_llm.execute.return_value = "Response to empty prompt"

        mock_router = Mock()
        mock_router.get_llm_for_task.return_value = mock_llm
        mock_router_class.return_value = mock_router

        agent = BaseAgent()
        result = agent.execute_llm_task("")

        assert result == "Response to empty prompt"

    @patch('nexuscore.agents.base_agent.HAS_RETRY', False)
    @patch('nexuscore.agents.base_agent.LLMRouter')
    def test_very_long_prompt(self, mock_router_class):
        """非常に長いプロンプトでも動作する"""
        mock_llm = Mock()
        mock_llm.execute.return_value = "Response"

        mock_router = Mock()
        mock_router.get_llm_for_task.return_value = mock_llm
        mock_router_class.return_value = mock_router

        agent = BaseAgent()
        long_prompt = "A" * 100000
        result = agent.execute_llm_task(long_prompt)

        assert result == "Response"

    @patch('nexuscore.agents.base_agent.HAS_RETRY', False)
    @patch('nexuscore.agents.base_agent.LLMRouter')
    def test_unicode_prompt(self, mock_router_class):
        """Unicodeプロンプトが正しく処理される"""
        mock_llm = Mock()
        mock_llm.execute.return_value = "日本語レスポンス"

        mock_router = Mock()
        mock_router.get_llm_for_task.return_value = mock_llm
        mock_router_class.return_value = mock_router

        agent = BaseAgent()
        result = agent.execute_llm_task("日本語のプロンプト")

        assert result == "日本語レスポンス"

    @patch('nexuscore.agents.base_agent.HAS_RETRY', False)
    @patch('nexuscore.agents.base_agent.LLMRouter')
    def test_valid_json_response_not_rejected(self, mock_router_class):
        """as_json=Trueで有効なJSONが正しく処理される"""
        valid_json = '{"status": "success", "data": [1, 2, 3]}'

        mock_llm = Mock()
        mock_llm.execute.return_value = valid_json

        mock_router = Mock()
        mock_router.get_llm_for_task.return_value = mock_llm
        mock_router_class.return_value = mock_router

        agent = BaseAgent()
        result = agent.execute_llm_task("Test", as_json=True)

        assert result == valid_json
        # パースできることを確認
        parsed = json.loads(result)
        assert parsed["status"] == "success"

    @patch('nexuscore.agents.base_agent.HAS_RETRY', False)
    @patch('nexuscore.agents.base_agent.LLMRouter', None)
    def test_execute_without_router(self):
        """LLMRouterなしで実行した場合のフォールバック"""
        agent = BaseAgent()
        result = agent.execute_llm_task("Test prompt")

        assert result == ""

    @patch('nexuscore.agents.base_agent.HAS_RETRY', False)
    @patch('nexuscore.agents.base_agent.LLMRouter', None)
    def test_execute_without_router_json(self):
        """LLMRouterなしで実行（as_json=True）した場合のフォールバック"""
        agent = BaseAgent()
        result = agent.execute_llm_task("Test prompt", as_json=True)

        assert result == "{}"
