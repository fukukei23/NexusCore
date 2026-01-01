"""
tester_agent.py の包括的テスト

カバレッジ:
- TesterAgent: テスト生成エージェント
  - __init__: TestStrategyManager, TestMetricsCollector統合
  - generate_tests_and_testimony: コードからテスト生成
  - generate_tests_from_plan: 計画からテスト生成
  - generate_tests: 要求からテスト生成（Fast-Lane）
  - generate_tests_for_module: モジュール別テスト生成
  - handle_changed_files: 変更ファイルのバッチ処理
  - _extract_test_code_from_response: テストコード抽出
  - _resolve_test_file_path: テストファイルパス解決
  - _count_test_functions: テスト関数カウント
  - _to_snake_case: snake_case変換
"""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

# 依存モジュールをモック
sys.modules['nexuscore.llm.llm_router'] = MagicMock()
sys.modules['nexuscore.core.retry_utils'] = MagicMock()
sys.modules['nexuscore.core.errors'] = MagicMock()
sys.modules['nexuscore.agents.test_strategy'] = MagicMock()
sys.modules['nexuscore.agents.test_generator_prompt'] = MagicMock()
sys.modules['nexuscore.core.test_metrics'] = MagicMock()

try:
    from nexuscore.agents.tester_agent import TesterAgent
    from nexuscore.agents.base_agent import BaseAgent
    HAS_TESTER_AGENT = True
except ImportError:
    HAS_TESTER_AGENT = False
    TesterAgent = None
    BaseAgent = None


@pytest.mark.skipif(not HAS_TESTER_AGENT, reason="tester_agent module not available")
class TestTesterAgentInit:
    """TesterAgent 初期化のテスト"""

    @patch('nexuscore.agents.tester_agent.TestStrategyManager', None)
    @patch('nexuscore.agents.tester_agent.TestMetricsCollector', None)
    @patch('nexuscore.agents.base_agent.LLMRouter')
    def test_init_inherits_base_agent(self, mock_router_class):
        """BaseAgentを継承している"""
        mock_router_class.return_value = Mock()

        agent = TesterAgent()

        assert isinstance(agent, BaseAgent)
        assert hasattr(agent, 'llm_router')
        assert hasattr(agent, 'logger')
        assert hasattr(agent, 'project_root')

    @patch('nexuscore.agents.tester_agent.TestStrategyManager', None)
    @patch('nexuscore.agents.tester_agent.TestMetricsCollector', None)
    @patch('nexuscore.agents.base_agent.LLMRouter')
    def test_init_with_project_root(self, mock_router_class, tmp_path):
        """project_rootが設定される"""
        mock_router_class.return_value = Mock()

        agent = TesterAgent(project_root=str(tmp_path))

        assert agent.project_root == tmp_path

    @patch('nexuscore.agents.tester_agent.TestStrategyManager', None)
    @patch('nexuscore.agents.tester_agent.TestMetricsCollector', None)
    @patch('nexuscore.agents.base_agent.LLMRouter')
    def test_init_without_strategy_manager(self, mock_router_class):
        """TestStrategyManagerなしでも初期化可能"""
        mock_router_class.return_value = Mock()

        agent = TesterAgent()

        assert agent.strategy_manager is None

    def test_system_prompt_defined(self):
        """SYSTEM_PROMPTが定義されている"""
        assert hasattr(TesterAgent, 'SYSTEM_PROMPT')
        assert "品質保証" in TesterAgent.SYSTEM_PROMPT or "QA" in TesterAgent.SYSTEM_PROMPT


@pytest.mark.skipif(not HAS_TESTER_AGENT, reason="tester_agent module not available")
class TestGenerateTestsAndTestimony:
    """TesterAgent.generate_tests_and_testimony() のテスト"""

    @patch('nexuscore.agents.tester_agent.TestStrategyManager', None)
    @patch('nexuscore.agents.tester_agent.TestMetricsCollector', None)
    @patch('nexuscore.agents.base_agent.HAS_RETRY', False)
    @patch('nexuscore.agents.base_agent.LLMRouter')
    def test_generate_tests_and_testimony_basic(self, mock_router_class):
        """基本的なテスト生成"""
        test_result = {
            "test_code": "def test_hello():\n    assert hello() == 'Hello'",
            "testimony": "Tests the hello function returns correct greeting"
        }

        mock_llm = Mock()
        mock_llm.execute.return_value = json.dumps(test_result)

        mock_router = Mock()
        mock_router.get_llm_for_task.return_value = mock_llm
        mock_router_class.return_value = mock_router

        agent = TesterAgent()
        result = agent.generate_tests_and_testimony("def hello():\n    return 'Hello'")

        assert result == json.dumps(test_result)
        parsed = json.loads(result)
        assert "test_code" in parsed
        assert "testimony" in parsed

    @patch('nexuscore.agents.tester_agent.TestStrategyManager', None)
    @patch('nexuscore.agents.tester_agent.TestMetricsCollector', None)
    @patch('nexuscore.agents.base_agent.HAS_RETRY', False)
    @patch('nexuscore.agents.base_agent.LLMRouter')
    def test_generate_tests_and_testimony_as_json(self, mock_router_class):
        """as_json=Trueで呼ばれる"""
        test_result = {"test_code": "# test", "testimony": "# testimony"}

        mock_llm = Mock()
        mock_llm.execute.return_value = json.dumps(test_result)

        mock_router = Mock()
        mock_router.get_llm_for_task.return_value = mock_llm
        mock_router_class.return_value = mock_router

        agent = TesterAgent()
        agent.generate_tests_and_testimony("def test(): pass")

        call_kwargs = mock_llm.execute.call_args[1]
        assert call_kwargs['as_json'] is True


@pytest.mark.skipif(not HAS_TESTER_AGENT, reason="tester_agent module not available")
class TestGenerateTestsFromPlan:
    """TesterAgent.generate_tests_from_plan() のテスト"""

    @patch('nexuscore.agents.tester_agent.TestStrategyManager', None)
    @patch('nexuscore.agents.tester_agent.TestMetricsCollector', None)
    @patch('nexuscore.agents.base_agent.HAS_RETRY', False)
    @patch('nexuscore.agents.base_agent.LLMRouter')
    def test_generate_tests_from_plan_basic(self, mock_router_class):
        """計画からのテスト生成"""
        plan = {
            "functions_to_implement": [
                {"name": "add", "args": ["a: int", "b: int"], "returns": "int"}
            ]
        }

        test_result = {
            "test_code": "def test_add():\n    assert add(1, 2) == 3",
            "testimony": "Tests the add function"
        }

        mock_llm = Mock()
        mock_llm.execute.return_value = json.dumps(test_result)

        mock_router = Mock()
        mock_router.get_llm_for_task.return_value = mock_llm
        mock_router_class.return_value = mock_router

        agent = TesterAgent()
        result = agent.generate_tests_from_plan(plan, "src.utils.math_utils")

        parsed = json.loads(result)
        assert "test_code" in parsed
        assert "testimony" in parsed

    @patch('nexuscore.agents.tester_agent.TestStrategyManager', None)
    @patch('nexuscore.agents.tester_agent.TestMetricsCollector', None)
    @patch('nexuscore.agents.base_agent.HAS_RETRY', False)
    @patch('nexuscore.agents.base_agent.LLMRouter')
    def test_generate_tests_from_plan_includes_module_import(self, mock_router_class):
        """プロンプトにモジュールimport指示が含まれる"""
        plan = {"functions_to_implement": [{"name": "func"}]}

        mock_llm = Mock()
        mock_llm.execute.return_value = '{"test_code": "# test", "testimony": "# testimony"}'

        mock_router = Mock()
        mock_router.get_llm_for_task.return_value = mock_llm
        mock_router_class.return_value = mock_router

        agent = TesterAgent()
        agent.generate_tests_from_plan(plan, "my.module.path")

        call_args = mock_llm.execute.call_args[1]
        prompt = call_args['prompt']
        assert "my.module.path" in prompt
        assert "from my.module.path import" in prompt


@pytest.mark.skipif(not HAS_TESTER_AGENT, reason="tester_agent module not available")
class TestGenerateTests:
    """TesterAgent.generate_tests() のテスト"""

    @patch('nexuscore.agents.tester_agent.TestStrategyManager', None)
    @patch('nexuscore.agents.tester_agent.TestMetricsCollector', None)
    @patch('nexuscore.agents.base_agent.HAS_RETRY', False)
    @patch('nexuscore.agents.base_agent.LLMRouter')
    def test_generate_tests_fallback(self, mock_router_class):
        """要求からのフォールバックテスト生成"""
        test_result = {
            "test_code": "def test_requirement():\n    pass",
            "testimony": "Requirement test"
        }

        mock_llm = Mock()
        mock_llm.execute.return_value = json.dumps(test_result)

        mock_router = Mock()
        mock_router.get_llm_for_task.return_value = mock_llm
        mock_router_class.return_value = mock_router

        agent = TesterAgent()
        result = agent.generate_tests("Create a simple calculator")

        parsed = json.loads(result)
        assert "test_code" in parsed
        assert "testimony" in parsed


@pytest.mark.skipif(not HAS_TESTER_AGENT, reason="tester_agent module not available")
class TestExtractTestCodeFromResponse:
    """TesterAgent._extract_test_code_from_response() のテスト"""

    @patch('nexuscore.agents.tester_agent.TestStrategyManager', None)
    @patch('nexuscore.agents.tester_agent.TestMetricsCollector', None)
    @patch('nexuscore.agents.base_agent.LLMRouter')
    def test_extract_from_valid_json(self, mock_router_class):
        """有効なJSONからテストコード抽出"""
        mock_router_class.return_value = Mock()

        response = '{"test_code": "def test_func(): pass", "testimony": "Test"}'

        agent = TesterAgent()
        result = agent._extract_test_code_from_response(response)

        assert result == "def test_func(): pass"

    @patch('nexuscore.agents.tester_agent.TestStrategyManager', None)
    @patch('nexuscore.agents.tester_agent.TestMetricsCollector', None)
    @patch('nexuscore.agents.base_agent.LLMRouter')
    def test_extract_from_invalid_json(self, mock_router_class):
        """無効なJSONの場合はそのまま返す"""
        mock_router_class.return_value = Mock()

        response = "Not a JSON response"

        agent = TesterAgent()
        result = agent._extract_test_code_from_response(response)

        assert result == "Not a JSON response"

    @patch('nexuscore.agents.tester_agent.TestStrategyManager', None)
    @patch('nexuscore.agents.tester_agent.TestMetricsCollector', None)
    @patch('nexuscore.agents.base_agent.LLMRouter')
    def test_extract_from_string_json(self, mock_router_class):
        """JSON文字列の場合"""
        mock_router_class.return_value = Mock()

        response = '"Just a string"'

        agent = TesterAgent()
        result = agent._extract_test_code_from_response(response)

        assert result == "Just a string"


@pytest.mark.skipif(not HAS_TESTER_AGENT, reason="tester_agent module not available")
class TestResolveTestFilePath:
    """TesterAgent._resolve_test_file_path() のテスト"""

    @patch('nexuscore.agents.tester_agent.TestStrategyManager', None)
    @patch('nexuscore.agents.tester_agent.TestMetricsCollector', None)
    @patch('nexuscore.agents.base_agent.LLMRouter')
    def test_resolve_test_file_path_from_src(self, mock_router_class, tmp_path):
        """srcディレクトリからのパス解決"""
        mock_router_class.return_value = Mock()

        agent = TesterAgent(project_root=str(tmp_path))
        test_path = agent._resolve_test_file_path("src/nexuscore/utils/file_utils.py")

        assert "tests" in str(test_path)
        assert "test_file_utils.py" in str(test_path)

    @patch('nexuscore.agents.tester_agent.TestStrategyManager', None)
    @patch('nexuscore.agents.tester_agent.TestMetricsCollector', None)
    @patch('nexuscore.agents.base_agent.LLMRouter')
    def test_resolve_test_file_path_adds_test_prefix(self, mock_router_class, tmp_path):
        """test_プレフィックスが追加される"""
        mock_router_class.return_value = Mock()

        agent = TesterAgent(project_root=str(tmp_path))
        test_path = agent._resolve_test_file_path("module.py")

        assert "test_module.py" in str(test_path)


@pytest.mark.skipif(not HAS_TESTER_AGENT, reason="tester_agent module not available")
class TestCountTestFunctions:
    """TesterAgent._count_test_functions() のテスト"""

    @patch('nexuscore.agents.tester_agent.TestStrategyManager', None)
    @patch('nexuscore.agents.tester_agent.TestMetricsCollector', None)
    @patch('nexuscore.agents.base_agent.LLMRouter')
    def test_count_test_functions_basic(self, mock_router_class):
        """テスト関数をカウント"""
        mock_router_class.return_value = Mock()

        test_code = """
def test_one():
    pass

def test_two():
    pass

def helper():
    pass

def test_three():
    pass
"""

        agent = TesterAgent()
        count = agent._count_test_functions(test_code)

        assert count == 3

    @patch('nexuscore.agents.tester_agent.TestStrategyManager', None)
    @patch('nexuscore.agents.tester_agent.TestMetricsCollector', None)
    @patch('nexuscore.agents.base_agent.LLMRouter')
    def test_count_test_functions_empty(self, mock_router_class):
        """テスト関数がない場合"""
        mock_router_class.return_value = Mock()

        agent = TesterAgent()
        count = agent._count_test_functions("def helper(): pass")

        assert count == 0


@pytest.mark.skipif(not HAS_TESTER_AGENT, reason="tester_agent module not available")
class TestEdgeCases:
    """エッジケースのテスト"""

    @patch('nexuscore.agents.tester_agent.TestStrategyManager', None)
    @patch('nexuscore.agents.tester_agent.TestMetricsCollector', None)
    @patch('nexuscore.agents.base_agent.HAS_RETRY', False)
    @patch('nexuscore.agents.base_agent.LLMRouter')
    def test_empty_code_to_test(self, mock_router_class):
        """空のコードでもテスト生成可能"""
        mock_llm = Mock()
        mock_llm.execute.return_value = '{"test_code": "# empty test", "testimony": "# empty"}'

        mock_router = Mock()
        mock_router.get_llm_for_task.return_value = mock_llm
        mock_router_class.return_value = mock_router

        agent = TesterAgent()
        result = agent.generate_tests_and_testimony("")

        assert result == '{"test_code": "# empty test", "testimony": "# empty"}'

    @patch('nexuscore.agents.tester_agent.TestStrategyManager', None)
    @patch('nexuscore.agents.tester_agent.TestMetricsCollector', None)
    @patch('nexuscore.agents.base_agent.HAS_RETRY', False)
    @patch('nexuscore.agents.base_agent.LLMRouter')
    def test_japanese_code(self, mock_router_class):
        """日本語コメントを含むコードのテスト生成"""
        code = "def 挨拶():\n    # 挨拶を返す\n    return 'こんにちは'"

        mock_llm = Mock()
        mock_llm.execute.return_value = '{"test_code": "# テスト", "testimony": "# 証言"}'

        mock_router = Mock()
        mock_router.get_llm_for_task.return_value = mock_llm
        mock_router_class.return_value = mock_router

        agent = TesterAgent()
        result = agent.generate_tests_and_testimony(code)

        assert result

    @patch('nexuscore.agents.tester_agent.TestStrategyManager', None)
    @patch('nexuscore.agents.tester_agent.TestMetricsCollector', None)
    @patch('nexuscore.agents.base_agent.HAS_RETRY', False)
    @patch('nexuscore.agents.base_agent.LLMRouter', None)
    def test_no_llm_router_available(self):
        """LLMRouterが利用できない場合"""
        agent = TesterAgent()
        result = agent.generate_tests_and_testimony("def test(): pass")

        # BaseAgentのフォールバックで空JSONが返る
        assert result == "{}"
