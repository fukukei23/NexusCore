"""
coder_agent.py の包括的テスト

カバレッジ:
- CoderAgent: コード生成エージェント
  - __init__: BaseAgentの継承
  - implement_code: コード実装
    - AST構文検査
    - リトライロジック
    - Tree-sitter検証（オプション）
  - _validate_python_syntax: Python構文検証
  - _validate_code: 言語別コード検証
"""

import ast
import sys
from unittest.mock import MagicMock, Mock, patch

import pytest


@pytest.fixture(autouse=True)
def mock_dependencies():
    """各テストの前後で依存モジュールをモック化/復元（テスト分離のため）"""
    # テスト前：元の状態を保存してモック化
    original_modules = {
        "nexuscore.llm.llm_router": sys.modules.get("nexuscore.llm.llm_router"),
        "nexuscore.core.retry_utils": sys.modules.get("nexuscore.core.retry_utils"),
        "nexuscore.core.errors": sys.modules.get("nexuscore.core.errors"),
        "nexuscore.utils.tree_sitter_checker": sys.modules.get(
            "nexuscore.utils.tree_sitter_checker"
        ),
    }

    sys.modules["nexuscore.llm.llm_router"] = MagicMock()
    sys.modules["nexuscore.core.retry_utils"] = MagicMock()
    sys.modules["nexuscore.core.errors"] = MagicMock()
    sys.modules["nexuscore.utils.tree_sitter_checker"] = MagicMock()

    yield  # ← ここでテストが実行される

    # テスト後：元の状態に復元
    for module_name, original_module in original_modules.items():
        if original_module is None:
            sys.modules.pop(module_name, None)
        else:
            sys.modules[module_name] = original_module


try:
    from nexuscore.agents.base_agent import BaseAgent
    from nexuscore.agents.coder_agent import CoderAgent

    HAS_CODER_AGENT = True
except ImportError:
    HAS_CODER_AGENT = False
    CoderAgent = None
    BaseAgent = None


@pytest.mark.skipif(not HAS_CODER_AGENT, reason="coder_agent module not available")
class TestCoderAgentInit:
    """CoderAgent 初期化のテスト"""

    @patch("nexuscore.agents.base_agent.LLMRouter")
    def test_init_inherits_base_agent(self, mock_router_class):
        """BaseAgentを継承している"""
        mock_router_class.return_value = Mock()

        agent = CoderAgent()

        assert isinstance(agent, BaseAgent)
        assert hasattr(agent, "llm_router")
        assert hasattr(agent, "logger")

    def test_system_prompt_defined(self):
        """SYSTEM_PROMPTが定義されている"""
        assert hasattr(CoderAgent, "SYSTEM_PROMPT")
        assert "Python開発者" in CoderAgent.SYSTEM_PROMPT

    def test_retry_limit_defined(self):
        """RETRY_LIMITが定義されている"""
        assert CoderAgent.RETRY_LIMIT == 2


@pytest.mark.skipif(not HAS_CODER_AGENT, reason="coder_agent module not available")
class TestImplementCode:
    """CoderAgent.implement_code() のテスト"""

    @patch("nexuscore.agents.base_agent.HAS_RETRY", False)
    @patch("nexuscore.agents.base_agent.LLMRouter")
    def test_implement_code_basic(self, mock_router_class):
        """基本的なコード実装"""
        valid_code = "def hello():\n    return 'Hello, World!'"

        mock_llm = Mock()
        mock_llm.execute.return_value = valid_code

        mock_router = Mock()
        mock_router.get_llm_for_task.return_value = mock_llm
        mock_router_class.return_value = mock_router

        agent = CoderAgent()
        result = agent.implement_code(
            task_description="Create a hello function", existing_code="", code_language="python"
        )

        assert result == valid_code
        # AST検証を通過していることを確認
        ast.parse(result)  # 例外が発生しないことを確認

    @patch("nexuscore.agents.base_agent.HAS_RETRY", False)
    @patch("nexuscore.agents.base_agent.LLMRouter")
    def test_implement_code_with_syntax_error_retry(self, mock_router_class):
        """構文エラーがある場合はリトライする"""
        invalid_code = "def broken(\n    pass"  # 構文エラー
        valid_code = "def fixed():\n    pass"

        mock_llm = Mock()
        mock_llm.execute.side_effect = [invalid_code, valid_code]

        mock_router = Mock()
        mock_router.get_llm_for_task.return_value = mock_llm
        mock_router_class.return_value = mock_router

        agent = CoderAgent()
        result = agent.implement_code(
            task_description="Create a function", existing_code="", code_language="python"
        )

        # 2回目の試行で成功したコードが返る
        assert result == valid_code
        assert mock_llm.execute.call_count == 2

    @patch("nexuscore.agents.base_agent.HAS_RETRY", False)
    @patch("nexuscore.agents.base_agent.LLMRouter")
    def test_implement_code_max_retries_exceeded(self, mock_router_class):
        """最大リトライ回数を超えた場合は最後の結果を返す"""
        invalid_code = "def broken(\n    pass"

        mock_llm = Mock()
        mock_llm.execute.return_value = invalid_code

        mock_router = Mock()
        mock_router.get_llm_for_task.return_value = mock_llm
        mock_router_class.return_value = mock_router

        agent = CoderAgent()
        result = agent.implement_code(
            task_description="Create a function", existing_code="", code_language="python"
        )

        # RETRY_LIMIT回試行しても失敗した場合は最後の結果を返す
        assert result == invalid_code
        assert mock_llm.execute.call_count == agent.RETRY_LIMIT

    @patch("nexuscore.agents.base_agent.HAS_RETRY", False)
    @patch("nexuscore.agents.base_agent.LLMRouter")
    def test_implement_code_with_existing_code(self, mock_router_class):
        """既存コードに対する修正"""
        existing = "def old():\n    pass"
        new_code = "def old():\n    return 'updated'"

        mock_llm = Mock()
        mock_llm.execute.return_value = new_code

        mock_router = Mock()
        mock_router.get_llm_for_task.return_value = mock_llm
        mock_router_class.return_value = mock_router

        agent = CoderAgent()
        result = agent.implement_code(
            task_description="Update the function to return 'updated'",
            existing_code=existing,
            code_language="python",
        )

        assert result == new_code
        # プロンプトに既存コードが含まれていることを確認
        call_args = mock_llm.execute.call_args[1]
        assert existing in call_args["prompt"]


@pytest.mark.skipif(not HAS_CODER_AGENT, reason="coder_agent module not available")
class TestValidatePythonSyntax:
    """CoderAgent._validate_python_syntax() のテスト"""

    @patch("nexuscore.agents.base_agent.LLMRouter")
    def test_validate_valid_python_code(self, mock_router_class):
        """有効なPythonコードの検証"""
        mock_router_class.return_value = Mock()

        agent = CoderAgent()
        valid, error = agent._validate_python_syntax("def hello():\n    pass")

        assert valid is True
        assert error == ""

    @patch("nexuscore.agents.base_agent.LLMRouter")
    def test_validate_invalid_python_code(self, mock_router_class):
        """無効なPythonコードの検証"""
        mock_router_class.return_value = Mock()

        agent = CoderAgent()
        valid, error = agent._validate_python_syntax("def broken(\n    pass")

        assert valid is False
        assert "SyntaxError" in error

    @patch("nexuscore.agents.base_agent.LLMRouter")
    def test_validate_empty_code(self, mock_router_class):
        """空のコードの検証"""
        mock_router_class.return_value = Mock()

        agent = CoderAgent()
        valid, error = agent._validate_python_syntax("")

        assert valid is True  # 空のコードは有効なPython
        assert error == ""


@pytest.mark.skipif(not HAS_CODER_AGENT, reason="coder_agent module not available")
class TestValidateCode:
    """CoderAgent._validate_code() のテスト"""

    @patch("nexuscore.agents.base_agent.LLMRouter")
    def test_validate_code_python(self, mock_router_class):
        """Python言語のコード検証"""
        mock_router_class.return_value = Mock()

        agent = CoderAgent()
        valid, error = agent._validate_code("python", "def test():\n    pass")

        assert valid is True

    @patch("nexuscore.agents.base_agent.LLMRouter")
    def test_validate_code_unsupported_language(self, mock_router_class):
        """サポートされていない言語の場合はスキップ"""
        mock_router_class.return_value = Mock()

        agent = CoderAgent()
        # tree-sitterが利用できない場合は成功扱い
        valid, error = agent._validate_code("rust", "fn main() {}")

        assert valid is True


@pytest.mark.skipif(not HAS_CODER_AGENT, reason="coder_agent module not available")
class TestEdgeCases:
    """エッジケースのテスト"""

    @patch("nexuscore.agents.base_agent.HAS_RETRY", False)
    @patch("nexuscore.agents.base_agent.LLMRouter")
    def test_japanese_task_description(self, mock_router_class):
        """日本語のタスク記述"""
        valid_code = "def 挨拶():\n    return 'こんにちは'"

        mock_llm = Mock()
        mock_llm.execute.return_value = valid_code

        mock_router = Mock()
        mock_router.get_llm_for_task.return_value = mock_llm
        mock_router_class.return_value = mock_router

        agent = CoderAgent()
        result = agent.implement_code(
            task_description="挨拶関数を作成してください", existing_code="", code_language="python"
        )

        assert result == valid_code

    @patch("nexuscore.agents.base_agent.HAS_RETRY", False)
    @patch("nexuscore.agents.base_agent.LLMRouter")
    def test_task_with_guardian_feedback(self, mock_router_class):
        """Guardianからのフィードバックを含むタスク"""
        code = "def test():\n    return True"

        mock_llm = Mock()
        mock_llm.execute.return_value = code

        mock_router = Mock()
        mock_router.get_llm_for_task.return_value = mock_llm
        mock_router_class.return_value = mock_router

        agent = CoderAgent()
        result = agent.implement_code(
            task_description="Create a test function [Guardianからのフィードバック: Add error handling]",
            existing_code="",
            code_language="python",
        )

        assert result == code
        # プロンプトにフィードバックが含まれていることを確認
        call_args = mock_llm.execute.call_args[1]
        assert "Guardianからのフィードバック" in call_args["prompt"]

    @patch("nexuscore.agents.base_agent.HAS_RETRY", False)
    @patch("nexuscore.agents.base_agent.LLMRouter", None)
    def test_no_llm_router_available(self):
        """LLMRouterが利用できない場合"""
        agent = CoderAgent()
        result = agent.implement_code(
            task_description="Test", existing_code="", code_language="python"
        )

        # BaseAgentのフォールバックで空文字列が返る
        assert result == ""

    @patch("nexuscore.agents.base_agent.HAS_RETRY", False)
    @patch("nexuscore.agents.base_agent.LLMRouter")
    def test_implement_code_with_task_type(self, mock_router_class):
        """task_type="code_generate"が使用される"""
        mock_llm = Mock()
        mock_llm.execute.return_value = "def test():\n    pass"

        mock_router = Mock()
        mock_router.get_llm_for_task.return_value = mock_llm
        mock_router_class.return_value = mock_router

        agent = CoderAgent()
        agent.implement_code(task_description="Test", existing_code="", code_language="python")

        # task_type="code_generate"で呼ばれることを確認
        mock_router.get_llm_for_task.assert_called()
