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


# ============================================================================
# Additional Tests: Uncovered Code Paths
# ============================================================================


@pytest.mark.skipif(not HAS_TESTER_AGENT, reason="tester_agent module not available")
class TestAdditionalCoverage:
    """未カバーのコードパスをテスト"""

    @patch('nexuscore.agents.tester_agent.TestStrategyManager', None)
    @patch('nexuscore.agents.tester_agent.TestMetricsCollector', None)
    @patch('nexuscore.agents.base_agent.HAS_RETRY', False)
    @patch('nexuscore.agents.base_agent.LLMRouter')
    def test_write_or_merge_test_file_creates_directory(self, mock_router_class, tmp_path):
        """テストファイル書き込み時にディレクトリを作成"""
        mock_router = Mock()
        mock_router_class.return_value = mock_router

        agent = TesterAgent(project_root=str(tmp_path))

        test_file_path = tmp_path / "tests" / "new_dir" / "test_new.py"
        test_code = "def test_example():\n    assert True"

        agent._write_or_merge_test_file(test_file_path, test_code)

        # ディレクトリが作成される
        assert test_file_path.parent.exists()
        # ファイルが書き込まれる
        assert test_file_path.exists()
        assert "def test_example" in test_file_path.read_text()

    @patch('nexuscore.agents.tester_agent.TestStrategyManager', None)
    @patch('nexuscore.agents.tester_agent.TestMetricsCollector', None)
    @patch('nexuscore.agents.base_agent.HAS_RETRY', False)
    @patch('nexuscore.agents.base_agent.LLMRouter')
    def test_write_or_merge_test_file_overwrites_existing(self, mock_router_class, tmp_path):
        """既存のテストファイルを上書き"""
        mock_router = Mock()
        mock_router_class.return_value = mock_router

        agent = TesterAgent(project_root=str(tmp_path))

        test_file_path = tmp_path / "test_existing.py"
        test_file_path.write_text("old content")

        new_test_code = "def test_new():\n    assert True"
        agent._write_or_merge_test_file(test_file_path, new_test_code)

        # 新しい内容で上書きされる
        content = test_file_path.read_text()
        assert "def test_new" in content
        assert "old content" not in content

    @patch('nexuscore.agents.tester_agent.TestStrategyManager', None)
    @patch('nexuscore.agents.tester_agent.TestMetricsCollector', None)
    @patch('nexuscore.agents.base_agent.HAS_RETRY', False)
    @patch('nexuscore.agents.base_agent.LLMRouter')
    def test_count_test_functions_with_various_formats(self, mock_router_class):
        """様々な形式のテスト関数をカウント"""
        mock_router = Mock()
        mock_router_class.return_value = mock_router

        agent = TesterAgent()

        test_code = """
def test_basic():
    pass

def test_with_params(param1, param2):
    pass

    def test_indented():
        pass

def helper_function():
    pass

def test_async():
    pass
"""
        count = agent._count_test_functions(test_code)
        # test_ で始まる関数: test_basic, test_with_params, test_indented, test_async
        assert count == 4

    @patch('nexuscore.agents.tester_agent.TestStrategyManager', None)
    @patch('nexuscore.agents.tester_agent.TestMetricsCollector', None)
    @patch('nexuscore.agents.base_agent.HAS_RETRY', False)
    @patch('nexuscore.agents.base_agent.LLMRouter')
    def test_get_coverage_for_module_returns_zero(self, mock_router_class):
        """カバレッジ取得（現在はダミー実装）"""
        mock_router = Mock()
        mock_router_class.return_value = mock_router

        agent = TesterAgent()

        coverage = agent._get_coverage_for_module("nexuscore.utils.example")
        # 現在の実装は常に 0.0 を返す
        assert coverage == 0.0

    @patch('nexuscore.agents.tester_agent.TestStrategyManager', None)
    @patch('nexuscore.agents.tester_agent.TestMetricsCollector', None)
    @patch('nexuscore.agents.base_agent.HAS_RETRY', False)
    @patch('nexuscore.agents.base_agent.LLMRouter')
    @patch('subprocess.run')
    def test_run_tests_and_get_coverage_success(self, mock_subprocess, mock_router_class, tmp_path):
        """テスト実行成功時のカバレッジ取得"""
        mock_router = Mock()
        mock_router_class.return_value = mock_router

        # subprocess.run のモック（成功）
        mock_subprocess.return_value = Mock(returncode=0, stderr="")

        agent = TesterAgent(project_root=str(tmp_path))
        test_file_path = tmp_path / "test_example.py"

        coverage = agent._run_tests_and_get_coverage("example", test_file_path)

        # テストが実行される
        mock_subprocess.assert_called_once()
        # カバレッジは現在 0.0（将来実装予定）
        assert coverage == 0.0

    @patch('nexuscore.agents.tester_agent.TestStrategyManager', None)
    @patch('nexuscore.agents.tester_agent.TestMetricsCollector', None)
    @patch('nexuscore.agents.base_agent.HAS_RETRY', False)
    @patch('nexuscore.agents.base_agent.LLMRouter')
    @patch('subprocess.run')
    def test_run_tests_and_get_coverage_failure(self, mock_subprocess, mock_router_class, tmp_path):
        """テスト実行失敗時の処理"""
        mock_router = Mock()
        mock_router_class.return_value = mock_router

        # subprocess.run のモック（失敗）
        mock_subprocess.return_value = Mock(returncode=1, stderr="Test failed")

        agent = TesterAgent(project_root=str(tmp_path))
        test_file_path = tmp_path / "test_example.py"

        coverage = agent._run_tests_and_get_coverage("example", test_file_path)

        # テストが実行される（失敗しても処理は継続）
        mock_subprocess.assert_called_once()
        assert coverage == 0.0

    @patch('nexuscore.agents.tester_agent.TestStrategyManager', None)
    @patch('nexuscore.agents.tester_agent.TestMetricsCollector', None)
    @patch('nexuscore.agents.base_agent.HAS_RETRY', False)
    @patch('nexuscore.agents.base_agent.LLMRouter')
    @patch('subprocess.run')
    def test_run_tests_timeout_handling(self, mock_subprocess, mock_router_class, tmp_path):
        """テスト実行タイムアウトの処理"""
        from subprocess import TimeoutExpired

        mock_router = Mock()
        mock_router_class.return_value = mock_router

        # タイムアウトエラーを発生させる
        mock_subprocess.side_effect = TimeoutExpired("pytest", 60)

        agent = TesterAgent(project_root=str(tmp_path))
        test_file_path = tmp_path / "test_slow.py"

        coverage = agent._run_tests_and_get_coverage("slow_module", test_file_path)

        # タイムアウトしてもエラーにならず、0.0 を返す
        assert coverage == 0.0

    @patch('nexuscore.agents.tester_agent.TestStrategyManager', None)
    @patch('nexuscore.agents.tester_agent.TestMetricsCollector', None)
    @patch('nexuscore.agents.base_agent.HAS_RETRY', False)
    @patch('nexuscore.agents.base_agent.LLMRouter')
    def test_infer_module_name_from_path_standard(self, mock_router_class):
        """ファイルパスからモジュール名を推定（標準ケース）"""
        mock_router = Mock()
        mock_router_class.return_value = mock_router

        agent = TesterAgent()

        # src/nexuscore/utils/file_utils.py -> file_utils（簡易実装）
        module_name = agent._infer_module_name_from_path("src/nexuscore/utils/file_utils.py")
        assert module_name == "file_utils"

    @patch('nexuscore.agents.tester_agent.TestStrategyManager', None)
    @patch('nexuscore.agents.tester_agent.TestMetricsCollector', None)
    @patch('nexuscore.agents.base_agent.HAS_RETRY', False)
    @patch('nexuscore.agents.base_agent.LLMRouter')
    def test_infer_module_name_from_path_edge_cases(self, mock_router_class):
        """ファイルパスからモジュール名を推定（エッジケース）"""
        mock_router = Mock()
        mock_router_class.return_value = mock_router

        agent = TesterAgent()

        # nexuscore/agents/base.py -> base（拡張子なしのファイル名）
        module_name = agent._infer_module_name_from_path("nexuscore/agents/base.py")
        assert module_name == "base"

    @patch('nexuscore.agents.tester_agent.TestStrategyManager', None)
    @patch('nexuscore.agents.tester_agent.TestMetricsCollector', None)
    @patch('nexuscore.agents.base_agent.HAS_RETRY', False)
    @patch('nexuscore.agents.base_agent.LLMRouter')
    def test_apply_generated_test_code_full_workflow(self, mock_router_class, tmp_path):
        """テストコード適用の完全なワークフロー"""
        mock_router = Mock()
        mock_router_class.return_value = mock_router

        agent = TesterAgent(project_root=str(tmp_path))

        # subprocess.run をモック（テスト実行をスキップ）
        with patch('subprocess.run') as mock_subprocess:
            mock_subprocess.return_value = Mock(returncode=0, stderr="")

            test_code = "def test_workflow():\n    assert True\n\ndef test_workflow2():\n    pass"
            target_file = "src/nexuscore/example.py"

            test_file_path, test_count, cov_before, cov_after = agent._apply_generated_test_code(
                "nexuscore.example",
                test_code,
                target_file
            )

            # テストファイルが作成される
            assert "test_example.py" in test_file_path
            # テスト関数が2つカウントされる
            assert test_count == 2
            # カバレッジが取得される（現在は0.0）
            assert cov_before == 0.0
            assert cov_after == 0.0


class TestTesterAgentAdvancedScenarios:
    """より深い統合シナリオとエッジケース"""

    @patch('nexuscore.agents.tester_agent.TestStrategyManager', None)
    @patch('nexuscore.agents.tester_agent.TestMetricsCollector', None)
    @patch('nexuscore.agents.base_agent.HAS_RETRY', False)
    @patch('nexuscore.agents.base_agent.LLMRouter')
    def test_write_or_merge_test_file_with_existing_content_merge(
        self, mock_router_class, tmp_path
    ):
        """既存のテストファイルとの内容マージ"""
        agent = TesterAgent(project_root=str(tmp_path))

        # 既存のテストファイルを作成
        test_file_path = tmp_path / "tests" / "test_merge.py"
        test_file_path.parent.mkdir(parents=True, exist_ok=True)
        existing_content = "def test_existing():\n    assert True\n"
        test_file_path.write_text(existing_content)

        # 新しいテストコードを追加
        new_test_code = "def test_new():\n    assert False\n"
        agent._write_or_merge_test_file(test_file_path, new_test_code)

        # ファイルが更新されている
        final_content = test_file_path.read_text()
        assert "test_new" in final_content

    @patch('nexuscore.agents.tester_agent.TestStrategyManager', None)
    @patch('nexuscore.agents.tester_agent.TestMetricsCollector', None)
    @patch('nexuscore.agents.base_agent.HAS_RETRY', False)
    @patch('nexuscore.agents.base_agent.LLMRouter')
    def test_count_test_functions_with_class_based_tests(
        self, mock_router_class, tmp_path
    ):
        """クラスベースのテスト関数カウント"""
        agent = TesterAgent(project_root=str(tmp_path))

        test_code = """
class TestExample:
    def test_method1(self):
        pass

    def test_method2(self):
        pass

def test_function():
    pass
"""
        count = agent._count_test_functions(test_code)
        # クラスメソッド2つ + 関数1つ = 3
        assert count == 3

    @patch('nexuscore.agents.tester_agent.TestStrategyManager', None)
    @patch('nexuscore.agents.tester_agent.TestMetricsCollector', None)
    @patch('nexuscore.agents.base_agent.HAS_RETRY', False)
    @patch('nexuscore.agents.base_agent.LLMRouter')
    @patch('subprocess.run')
    def test_run_tests_with_coverage_success(
        self, mock_subprocess, mock_router_class, tmp_path
    ):
        """カバレッジ成功時のテスト実行"""
        # pytest成功とカバレッジ出力をシミュレート
        mock_subprocess.return_value = Mock(
            returncode=0,
            stderr="test_module.py::test_example PASSED\nCoverage: 85%"
        )

        agent = TesterAgent(project_root=str(tmp_path))
        test_file_path = tmp_path / "tests" / "test_module.py"
        coverage = agent._run_tests_and_get_coverage("test_module", test_file_path)

        # カバレッジが0.0（実際の解析なし）
        assert coverage == 0.0

    @patch('nexuscore.agents.tester_agent.TestStrategyManager', None)
    @patch('nexuscore.agents.tester_agent.TestMetricsCollector', None)
    @patch('nexuscore.agents.base_agent.HAS_RETRY', False)
    @patch('nexuscore.agents.base_agent.LLMRouter')
    def test_infer_module_name_with_complex_path(
        self, mock_router_class, tmp_path
    ):
        """複雑なパスからのモジュール名推論"""
        agent = TesterAgent(project_root=str(tmp_path))

        # 深いネストパス
        complex_path = "src/nexuscore/agents/helpers/utils/file_handler.py"
        module_name = agent._infer_module_name_from_path(complex_path)

        # 実装は path.stem を返すので "file_handler"
        assert module_name == "file_handler"

    @patch('nexuscore.agents.tester_agent.TestStrategyManager', None)
    @patch('nexuscore.agents.tester_agent.TestMetricsCollector', None)
    @patch('nexuscore.agents.base_agent.HAS_RETRY', False)
    @patch('nexuscore.agents.base_agent.LLMRouter')
    @patch('subprocess.run')
    def test_apply_generated_test_code_with_multiple_tests(
        self, mock_subprocess, mock_router_class, tmp_path
    ):
        """複数のテスト関数を含むコードの適用"""
        agent = TesterAgent(project_root=str(tmp_path))

        mock_subprocess.return_value = Mock(returncode=0, stderr="")

        test_code = """
def test_one():
    assert True

def test_two():
    assert True

def test_three():
    assert True
"""
        target_file = "src/nexuscore/multi.py"

        test_file_path, test_count, cov_before, cov_after = agent._apply_generated_test_code(
            "nexuscore.multi",
            test_code,
            target_file
        )

        # 3つのテスト関数がカウントされる
        assert test_count == 3
        assert "test_multi.py" in test_file_path

