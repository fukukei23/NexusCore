"""
planner_agent.py の包括的テスト

カバレッジ:
- PlannerAgent: 実装計画生成エージェント
  - __init__: BaseAgentの継承
  - generate_plan: 実装計画生成
    - JSON形式での計画生成
    - フォールバック計画
    - 最小3タスクの保証
  - _get_file_context: プロジェクトファイルコンテキスト取得
  - _is_plan_valid: 計画の妥当性検証
  - _fallback_plan: フォールバック計画生成
  - _to_snake_case: snake_case変換
"""

import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest


@pytest.fixture(autouse=True)
def mock_dependencies():
    """各テストの前後で依存モジュールをモック化/復元（テスト分離のため）"""
    # テスト前：元の状態を保存してモック化
    original_modules = {
        'nexuscore.llm.llm_router': sys.modules.get('nexuscore.llm.llm_router'),
        'nexuscore.core.retry_utils': sys.modules.get('nexuscore.core.retry_utils'),
        'nexuscore.core.errors': sys.modules.get('nexuscore.core.errors'),
        'nexuscore.utils.json_sanitizer': sys.modules.get('nexuscore.utils.json_sanitizer'),
    }

    sys.modules['nexuscore.llm.llm_router'] = MagicMock()
    sys.modules['nexuscore.core.retry_utils'] = MagicMock()
    sys.modules['nexuscore.core.errors'] = MagicMock()
    sys.modules['nexuscore.utils.json_sanitizer'] = MagicMock()

    yield  # ← ここでテストが実行される

    # テスト後：元の状態に復元
    for module_name, original_module in original_modules.items():
        if original_module is None:
            sys.modules.pop(module_name, None)
        else:
            sys.modules[module_name] = original_module


try:
    from nexuscore.agents.planner_agent import PlannerAgent
    from nexuscore.agents.base_agent import BaseAgent
    HAS_PLANNER_AGENT = True
except ImportError:
    HAS_PLANNER_AGENT = False
    PlannerAgent = None
    BaseAgent = None


@pytest.mark.skipif(not HAS_PLANNER_AGENT, reason="planner_agent module not available")
class TestPlannerAgentInit:
    """PlannerAgent 初期化のテスト"""

    @patch('nexuscore.agents.base_agent.LLMRouter')
    def test_init_inherits_base_agent(self, mock_router_class):
        """BaseAgentを継承している"""
        mock_router_class.return_value = Mock()

        agent = PlannerAgent()

        assert isinstance(agent, BaseAgent)
        assert hasattr(agent, 'llm_router')
        assert hasattr(agent, 'logger')

    def test_system_prompt_defined(self):
        """SYSTEM_PROMPTが定義されている"""
        assert hasattr(PlannerAgent, 'SYSTEM_PROMPT')
        assert "アーキテクト" in PlannerAgent.SYSTEM_PROMPT
        assert "タスク" in PlannerAgent.SYSTEM_PROMPT


@pytest.mark.skipif(not HAS_PLANNER_AGENT, reason="planner_agent module not available")
class TestGeneratePlan:
    """PlannerAgent.generate_plan() のテスト"""

    @patch('nexuscore.agents.planner_agent.sanitize_json_like', side_effect=lambda x: x)
    @patch('nexuscore.agents.base_agent.HAS_RETRY', False)
    @patch('nexuscore.agents.base_agent.LLMRouter')
    def test_generate_plan_basic(self, mock_router_class, mock_sanitize):
        """基本的な計画生成"""
        plan_json = {
            "functions_to_implement": [
                {
                    "name": "create_todo",
                    "description": "Create a new todo item",
                    "args": ["title: str", "description: str"],
                    "returns": "TodoItem",
                    "dependencies": [],
                    "tests": ["Test creating a todo"],
                    "acceptance_criteria": ["Todo is persisted"],
                    "priority": "P0"
                },
                {
                    "name": "list_todos",
                    "description": "List all todos",
                    "args": [],
                    "returns": "List[TodoItem]",
                    "dependencies": ["create_todo"],
                    "tests": ["Test listing todos"],
                    "acceptance_criteria": ["All todos are returned"],
                    "priority": "P1"
                },
                {
                    "name": "delete_todo",
                    "description": "Delete a todo item",
                    "args": ["id: int"],
                    "returns": "bool",
                    "dependencies": ["list_todos"],
                    "tests": ["Test deleting a todo"],
                    "acceptance_criteria": ["Todo is removed"],
                    "priority": "P2"
                }
            ]
        }

        mock_llm = Mock()
        mock_llm.execute.return_value = json.dumps(plan_json)

        mock_router = Mock()
        mock_router.get_llm_for_task.return_value = mock_llm
        mock_router.last_mode = "real"
        mock_router_class.return_value = mock_router

        agent = PlannerAgent()
        result = agent.generate_plan("Create a CLI todo app", context={})

        assert "functions_to_implement" in result
        assert len(result["functions_to_implement"]) >= 3

    @patch('nexuscore.agents.planner_agent.sanitize_json_like', side_effect=lambda x: x)
    @patch('nexuscore.agents.base_agent.HAS_RETRY', False)
    @patch('nexuscore.agents.base_agent.LLMRouter')
    def test_generate_plan_with_context(self, mock_router_class, mock_sanitize, tmp_path):
        """コンテキスト付き計画生成"""
        # プロジェクトファイルを作成
        (tmp_path / "main.py").write_text("def main(): pass")
        (tmp_path / "utils.py").write_text("def helper(): pass")

        plan_json = {
            "functions_to_implement": [
                {"name": "task1", "description": "Task 1", "args": [], "returns": "None",
                 "dependencies": [], "tests": ["test1"], "acceptance_criteria": ["AC1"], "priority": "P0"},
                {"name": "task2", "description": "Task 2", "args": [], "returns": "None",
                 "dependencies": [], "tests": ["test2"], "acceptance_criteria": ["AC2"], "priority": "P1"},
                {"name": "task3", "description": "Task 3", "args": [], "returns": "None",
                 "dependencies": [], "tests": ["test3"], "acceptance_criteria": ["AC3"], "priority": "P2"}
            ]
        }

        mock_llm = Mock()
        mock_llm.execute.return_value = json.dumps(plan_json)

        mock_router = Mock()
        mock_router.get_llm_for_task.return_value = mock_llm
        mock_router.last_mode = "real"
        mock_router_class.return_value = mock_router

        agent = PlannerAgent()
        result = agent.generate_plan("Add features", context={"project_path": str(tmp_path)})

        assert "functions_to_implement" in result
        assert len(result["functions_to_implement"]) >= 3

    @patch('nexuscore.agents.planner_agent.sanitize_json_like', side_effect=lambda x: x)
    @patch('nexuscore.agents.base_agent.HAS_RETRY', False)
    @patch('nexuscore.agents.base_agent.LLMRouter')
    def test_generate_plan_fallback_on_invalid_json(self, mock_router_class, mock_sanitize):
        """無効なJSONの場合はフォールバック計画を生成"""
        mock_llm = Mock()
        mock_llm.execute.return_value = "Not a valid JSON"

        mock_router = Mock()
        mock_router.get_llm_for_task.return_value = mock_llm
        mock_router.last_mode = "real"
        mock_router_class.return_value = mock_router

        agent = PlannerAgent()
        result = agent.generate_plan("Test requirement", context={})

        # フォールバック計画が生成される
        assert "functions_to_implement" in result
        assert len(result["functions_to_implement"]) >= 3

    @patch('nexuscore.agents.planner_agent.sanitize_json_like', side_effect=lambda x: x)
    @patch('nexuscore.agents.base_agent.HAS_RETRY', False)
    @patch('nexuscore.agents.base_agent.LLMRouter')
    def test_generate_plan_stub_mode_fallback(self, mock_router_class, mock_sanitize):
        """スタブモードの場合はフォールバック計画を生成"""
        plan_json = {"mode": "stub", "functions_to_implement": []}

        mock_llm = Mock()
        mock_llm.execute.return_value = json.dumps(plan_json)

        mock_router = Mock()
        mock_router.get_llm_for_task.return_value = mock_llm
        mock_router.last_mode = "stub"
        mock_router_class.return_value = mock_router

        agent = PlannerAgent()
        result = agent.generate_plan("Test requirement", context={})

        # フォールバック計画が生成される
        assert "functions_to_implement" in result
        assert len(result["functions_to_implement"]) >= 3

    @patch('nexuscore.agents.planner_agent.sanitize_json_like', side_effect=lambda x: x)
    @patch('nexuscore.agents.base_agent.HAS_RETRY', False)
    @patch('nexuscore.agents.base_agent.LLMRouter')
    def test_generate_plan_fewer_than_3_tasks_merges_fallback(self, mock_router_class, mock_sanitize):
        """3タスク未満の場合はフォールバックタスクとマージ"""
        plan_json = {
            "functions_to_implement": [
                {"name": "task1", "description": "Only one task", "args": [], "returns": "None",
                 "dependencies": [], "tests": ["test"], "acceptance_criteria": ["AC"], "priority": "P0"}
            ]
        }

        mock_llm = Mock()
        mock_llm.execute.return_value = json.dumps(plan_json)

        mock_router = Mock()
        mock_router.get_llm_for_task.return_value = mock_llm
        mock_router.last_mode = "real"
        mock_router_class.return_value = mock_router

        agent = PlannerAgent()
        result = agent.generate_plan("Test requirement", context={})

        # 最低3タスクが保証される
        assert len(result["functions_to_implement"]) >= 3


@pytest.mark.skipif(not HAS_PLANNER_AGENT, reason="planner_agent module not available")
class TestGetFileContext:
    """PlannerAgent._get_file_context() のテスト"""

    @patch('nexuscore.agents.base_agent.LLMRouter')
    def test_get_file_context_with_files(self, mock_router_class, tmp_path):
        """ファイルがある場合のコンテキスト取得"""
        mock_router_class.return_value = Mock()

        # テストファイルを作成
        (tmp_path / "main.py").write_text("# main")
        (tmp_path / "utils.py").write_text("# utils")

        agent = PlannerAgent()
        context = agent._get_file_context(str(tmp_path))

        assert "main.py" in context
        assert "utils.py" in context

    @patch('nexuscore.agents.base_agent.LLMRouter')
    def test_get_file_context_empty_project(self, mock_router_class, tmp_path):
        """ファイルがない場合"""
        mock_router_class.return_value = Mock()

        agent = PlannerAgent()
        context = agent._get_file_context(str(tmp_path))

        assert "ファイルが見つかりません" in context

    @patch('nexuscore.agents.base_agent.LLMRouter')
    def test_get_file_context_max_files_limit(self, mock_router_class, tmp_path):
        """ファイル数が多い場合は制限される"""
        mock_router_class.return_value = Mock()

        # 20個のファイルを作成
        for i in range(20):
            (tmp_path / f"file{i}.py").write_text(f"# file {i}")

        agent = PlannerAgent()
        context = agent._get_file_context(str(tmp_path), max_files=15)

        assert "一部抜粋" in context

    @patch('nexuscore.agents.base_agent.LLMRouter')
    def test_get_file_context_ignores_excluded_dirs(self, mock_router_class, tmp_path):
        """除外ディレクトリ（.git, __pycache__等）を無視"""
        mock_router_class.return_value = Mock()

        (tmp_path / "main.py").write_text("# main")
        (tmp_path / ".git").mkdir()
        (tmp_path / ".git" / "config").write_text("# git config")
        (tmp_path / "__pycache__").mkdir()
        (tmp_path / "__pycache__" / "cache.pyc").write_text("# cache")

        agent = PlannerAgent()
        context = agent._get_file_context(str(tmp_path))

        assert "main.py" in context
        assert ".git" not in context
        assert "__pycache__" not in context


@pytest.mark.skipif(not HAS_PLANNER_AGENT, reason="planner_agent module not available")
class TestIsPlanValid:
    """PlannerAgent._is_plan_valid() のテスト"""

    @patch('nexuscore.agents.base_agent.LLMRouter')
    def test_valid_plan(self, mock_router_class):
        """有効な計画"""
        mock_router_class.return_value = Mock()

        agent = PlannerAgent()
        plan = {"functions_to_implement": [{"name": "task1"}]}

        assert agent._is_plan_valid(plan) is True

    @patch('nexuscore.agents.base_agent.LLMRouter')
    def test_invalid_plan_not_dict(self, mock_router_class):
        """辞書でない場合は無効"""
        mock_router_class.return_value = Mock()

        agent = PlannerAgent()

        assert agent._is_plan_valid([]) is False
        assert agent._is_plan_valid("string") is False

    @patch('nexuscore.agents.base_agent.LLMRouter')
    def test_invalid_plan_missing_functions_key(self, mock_router_class):
        """functions_to_implementキーがない場合は無効"""
        mock_router_class.return_value = Mock()

        agent = PlannerAgent()
        plan = {"other_key": []}

        assert agent._is_plan_valid(plan) is False

    @patch('nexuscore.agents.base_agent.LLMRouter')
    def test_invalid_plan_empty_functions(self, mock_router_class):
        """functions_to_implementが空の場合は無効"""
        mock_router_class.return_value = Mock()

        agent = PlannerAgent()
        plan = {"functions_to_implement": []}

        assert agent._is_plan_valid(plan) is False


@pytest.mark.skipif(not HAS_PLANNER_AGENT, reason="planner_agent module not available")
class TestFallbackPlan:
    """PlannerAgent._fallback_plan() のテスト"""

    @patch('nexuscore.agents.base_agent.LLMRouter')
    def test_fallback_plan_generates_3_tasks(self, mock_router_class):
        """フォールバック計画は最低3タスク生成"""
        mock_router_class.return_value = Mock()

        agent = PlannerAgent()
        plan = agent._fallback_plan("Test requirement", context={})

        assert "functions_to_implement" in plan
        assert len(plan["functions_to_implement"]) == 3

    @patch('nexuscore.agents.base_agent.LLMRouter')
    def test_fallback_plan_task_structure(self, mock_router_class):
        """フォールバックタスクの構造が正しい"""
        mock_router_class.return_value = Mock()

        agent = PlannerAgent()
        plan = agent._fallback_plan("Create todo app", context={})

        task = plan["functions_to_implement"][0]
        assert "name" in task
        assert "description" in task
        assert "args" in task
        assert "returns" in task
        assert "dependencies" in task
        assert "tests" in task
        assert "acceptance_criteria" in task
        assert "priority" in task


@pytest.mark.skipif(not HAS_PLANNER_AGENT, reason="planner_agent module not available")
class TestToSnakeCase:
    """PlannerAgent._to_snake_case() のテスト"""

    def test_to_snake_case_basic(self):
        """基本的な変換"""
        assert PlannerAgent._to_snake_case("HelloWorld") == "hello_world"
        assert PlannerAgent._to_snake_case("hello world") == "hello_world"
        assert PlannerAgent._to_snake_case("Hello-World") == "hello_world"

    def test_to_snake_case_already_snake_case(self):
        """既にsnake_caseの場合"""
        assert PlannerAgent._to_snake_case("hello_world") == "hello_world"

    def test_to_snake_case_with_numbers(self):
        """数字を含む場合"""
        assert PlannerAgent._to_snake_case("Test123Function") == "test123_function"

    def test_to_snake_case_special_chars(self):
        """特殊文字を含む場合"""
        assert PlannerAgent._to_snake_case("Hello@World!") == "hello_world"

    def test_to_snake_case_empty_string(self):
        """空文字列の場合"""
        assert PlannerAgent._to_snake_case("") == ""


@pytest.mark.skipif(not HAS_PLANNER_AGENT, reason="planner_agent module not available")
class TestEdgeCases:
    """エッジケースのテスト"""

    @patch('nexuscore.agents.planner_agent.sanitize_json_like', side_effect=lambda x: x)
    @patch('nexuscore.agents.base_agent.HAS_RETRY', False)
    @patch('nexuscore.agents.base_agent.LLMRouter')
    def test_japanese_requirement(self, mock_router_class, mock_sanitize):
        """日本語の要求"""
        plan_json = {
            "functions_to_implement": [
                {"name": "タスク1", "description": "日本語説明", "args": [], "returns": "None",
                 "dependencies": [], "tests": ["テスト"], "acceptance_criteria": ["条件"], "priority": "P0"},
                {"name": "タスク2", "description": "日本語説明2", "args": [], "returns": "None",
                 "dependencies": [], "tests": ["テスト2"], "acceptance_criteria": ["条件2"], "priority": "P1"},
                {"name": "タスク3", "description": "日本語説明3", "args": [], "returns": "None",
                 "dependencies": [], "tests": ["テスト3"], "acceptance_criteria": ["条件3"], "priority": "P2"}
            ]
        }

        mock_llm = Mock()
        mock_llm.execute.return_value = json.dumps(plan_json, ensure_ascii=False)

        mock_router = Mock()
        mock_router.get_llm_for_task.return_value = mock_llm
        mock_router.last_mode = "real"
        mock_router_class.return_value = mock_router

        agent = PlannerAgent()
        result = agent.generate_plan("TODOアプリを作成", context={})

        assert "functions_to_implement" in result

    @patch('nexuscore.agents.base_agent.LLMRouter', None)
    def test_no_llm_router_available(self):
        """LLMRouterが利用できない場合はフォールバック"""
        agent = PlannerAgent()
        result = agent.generate_plan("Test requirement", context={})

        # フォールバック計画が生成される
        assert "functions_to_implement" in result
        assert len(result["functions_to_implement"]) >= 3
