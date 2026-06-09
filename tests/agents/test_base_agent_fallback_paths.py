import json
import pytest
from unittest.mock import MagicMock, patch

MODULE_PATH = "nexuscore.agents.base_agent"


@pytest.fixture
def base_agent():
    from nexuscore.agents.base_agent import BaseAgent
    return BaseAgent()


class TestImportFallbacks:
    """モジュールレベルのインポート失敗時のフォールバックパス (L19-20, 25-26, 40-48)"""

    def test_dotenv_load_fallback_does_not_crash(self):
        """dotenv.load_dotenv 例外でも BaseAgent は初期化できる (L19-20)"""
        with patch.dict("sys.modules", {"dotenv": None}):
            from nexuscore.agents.base_agent import BaseAgent
            agent = BaseAgent()
            assert agent is not None

    def test_llm_router_none_fallback(self):
        """LLMRouter が None の時、BaseAgent は警告を出して None を保持 (L25-26)"""
        with patch(f"{MODULE_PATH}.LLMRouter", None):
            from nexuscore.agents.base_agent import BaseAgent
            agent = BaseAgent()
            assert agent.llm_router is None

    def test_has_retry_false_fallback(self):
        """HAS_RETRY=False の時、リトライなしで直接実行される (L40-48)"""
        with patch(f"{MODULE_PATH}.HAS_RETRY", False):
            from nexuscore.agents.base_agent import BaseAgent
            agent = BaseAgent()
            mock_llm = MagicMock()
            mock_llm.execute.return_value = "ok"
            agent.llm_router = MagicMock()
            agent.llm_router.get_llm_for_task.return_value = mock_llm
            result = agent.execute_llm_task("test")
            assert result == "ok"


class TestExecuteLlmFallbackPaths:
    """execute_llm_task のエラーフォールバックパス (L141, 147)"""

    def test_invalid_json_fallback_with_retry(self, base_agent):
        """as_json=True + retry_with_context=None → フォールバックで '{}' を返す (L141→147→175)"""
        mock_llm = MagicMock()
        mock_llm.execute.return_value = "not json"
        base_agent.llm_router = MagicMock()
        base_agent.llm_router.get_llm_for_task.return_value = mock_llm

        with patch(f"{MODULE_PATH}.HAS_RETRY", True), \
             patch(f"{MODULE_PATH}.retry_with_context", None):
            result = base_agent.execute_llm_task("prompt", as_json=True)
            assert result == "{}"

    def test_convert_http_error_on_execute(self, base_agent):
        """LLM実行エラー時にNexusエラー変換が呼ばれる (L147)"""
        mock_llm = MagicMock()
        mock_llm.execute.side_effect = Exception("HTTP 500")
        base_agent.llm_router = MagicMock()
        base_agent.llm_router.get_llm_for_task.return_value = mock_llm

        mock_converter = MagicMock(side_effect=ConnectionError("nexus error"))
        with patch(f"{MODULE_PATH}.HAS_RETRY", True), \
             patch(f"{MODULE_PATH}.convert_http_error_to_nexus_error", mock_converter), \
             patch(f"{MODULE_PATH}.retry_with_context", None):
            # convert_http_error_to_nexus_error raises → caught by HAS_RETRY=False fallback path
            result = base_agent.execute_llm_task("prompt", as_json=True)
            assert result == "{}"

    def test_no_llm_client_returns_empty_json(self, base_agent):
        """LLMクライアントなし → as_json=True で '{}' を返す"""
        base_agent.llm_router = MagicMock()
        base_agent.llm_router.get_llm_for_task.return_value = None
        result = base_agent.execute_llm_task("prompt", as_json=True)
        assert result == "{}"

    def test_no_llm_client_returns_empty_string(self, base_agent):
        """LLMクライアントなし → as_json=False で '' を返す"""
        base_agent.llm_router = MagicMock()
        base_agent.llm_router.get_llm_for_task.return_value = None
        result = base_agent.execute_llm_task("prompt", as_json=False)
        assert result == ""

    def test_execute_error_no_retry_fallback(self, base_agent):
        """HAS_RETRY=False で実行エラー → フォールバック値を返す (L180-183)"""
        base_agent.llm_router = MagicMock()
        base_agent.llm_router.get_llm_for_task.side_effect = Exception("fail")

        with patch(f"{MODULE_PATH}.HAS_RETRY", False):
            result = base_agent.execute_llm_task("prompt", as_json=True)
            assert result == "{}"
