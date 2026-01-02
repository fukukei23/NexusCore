"""
debugger_agent.py の包括的テスト

カバレッジ:
- DebuggerAgent: デバッグ・パッチ生成エージェント
  - __init__: knowledge_base初期化
  - debug_and_patch: エラーログ→修正コード→パッチ生成
  - _find_solution_from_kb: ナレッジベース検索
  - _generate_fixed_code: LLMによるコード修正
  - _create_diff: unified diff生成
"""

import difflib
import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

try:
    from nexuscore.agents.debugger_agent import DebuggerAgent
    HAS_DEBUGGER_AGENT = True
except ImportError:
    HAS_DEBUGGER_AGENT = False
    DebuggerAgent = None


@pytest.mark.skipif(not HAS_DEBUGGER_AGENT, reason="debugger_agent module not available")
class TestDebuggerAgentInit:
    """DebuggerAgent 初期化のテスト"""

    def test_init_without_knowledge_base(self):
        """ナレッジベースなしで初期化"""
        with patch('nexuscore.agents.debugger_agent.BaseAgent.__init__', return_value=None):
            agent = DebuggerAgent()
            agent.logger = Mock()  # Mock logger

            assert agent.local_knowledge_base is None

    def test_init_with_knowledge_base_file(self, tmp_path):
        """ナレッジベースファイルを指定して初期化"""
        kb_file = tmp_path / "knowledge_base.json"
        kb_data = [
            {
                "error_signature": "ImportError: cannot import name 'add'",
                "cause": "Wrong import",
                "solution_pattern": {"type": "fix_import"}
            }
        ]
        kb_file.write_text(json.dumps(kb_data))

        with patch('nexuscore.agents.debugger_agent.BaseAgent.__init__', return_value=None):
            agent = DebuggerAgent.__new__(DebuggerAgent)
            agent.logger = Mock()
            DebuggerAgent.__init__(agent, knowledge_base_path=str(kb_file))

            assert agent.local_knowledge_base is not None
            assert len(agent.local_knowledge_base) == 1
            assert agent.local_knowledge_base[0]["cause"] == "Wrong import"

    def test_init_with_invalid_knowledge_base_file(self, tmp_path):
        """無効なナレッジベースファイルの場合"""
        kb_file = tmp_path / "invalid_kb.json"
        kb_file.write_text("not valid json")

        with patch('nexuscore.agents.debugger_agent.BaseAgent.__init__', return_value=None):
            agent = DebuggerAgent.__new__(DebuggerAgent)
            agent.logger = Mock()
            DebuggerAgent.__init__(agent, knowledge_base_path=str(kb_file))

            # エラーが発生してもNoneになる
            assert agent.local_knowledge_base is None


@pytest.mark.skipif(not HAS_DEBUGGER_AGENT, reason="debugger_agent module not available")
class TestDebugAndPatch:
    """DebuggerAgent.debug_and_patch() のテスト"""

    @patch('nexuscore.agents.debugger_agent.BaseAgent.__init__', return_value=None)
    @patch('nexuscore.agents.debugger_agent.BaseAgent.execute_llm_task')
    def test_debug_and_patch_basic(self, mock_execute_llm, mock_base_init):
        """基本的なデバッグとパッチ生成"""
        # LLMが修正コードを返す
        fixed_code = "def add(a, b):\n    return a + b  # Fixed"
        mock_execute_llm.return_value = fixed_code

        agent = DebuggerAgent()
        agent.logger = Mock()  # Mock logger
        error_log = "TypeError: unsupported operand type(s) for +: 'int' and 'str'"
        files_content = {
            "src/calculator.py": "def add(a, b):\n    return a + b"
        }
        project_path = "/home/user/project"

        result = agent.debug_and_patch(error_log, files_content, project_path)

        assert "patch" in result
        assert "fixed_code" in result
        assert result["fixed_code"] == fixed_code

    @patch('nexuscore.agents.debugger_agent.BaseAgent.__init__', return_value=None)
    @patch('nexuscore.agents.debugger_agent.BaseAgent.execute_llm_task')
    def test_debug_and_patch_no_files(self, mock_execute_llm, mock_base_init):
        """ファイルが提供されない場合"""
        agent = DebuggerAgent()
        agent.logger = Mock()  # Mock logger
        error_log = "Some error"
        files_content = {}
        project_path = "/home/user/project"

        result = agent.debug_and_patch(error_log, files_content, project_path)

        assert "error" in result
        assert result["error"] == "No files provided for debugging."

    @patch('nexuscore.agents.debugger_agent.BaseAgent.__init__', return_value=None)
    @patch('nexuscore.agents.debugger_agent.BaseAgent.execute_llm_task')
    def test_debug_and_patch_with_known_solution(self, mock_execute_llm, mock_base_init, tmp_path):
        """ナレッジベースから既知の解決策が見つかる場合"""
        kb_file = tmp_path / "kb.json"
        kb_data = [
            {
                "error_signature": "ImportError",
                "cause": "Wrong import statement",
                "solution_pattern": {"type": "fix_import"}
            }
        ]
        kb_file.write_text(json.dumps(kb_data))

        fixed_code = "from math import sqrt"
        mock_execute_llm.return_value = fixed_code

        agent = DebuggerAgent.__new__(DebuggerAgent)
        agent.logger = Mock()
        DebuggerAgent.__init__(agent, knowledge_base_path=str(kb_file))
        error_log = "ImportError: cannot import name 'sqrt'"
        files_content = {
            "src/calc.py": "import sqrt"
        }
        project_path = "/home/user/project"

        result = agent.debug_and_patch(error_log, files_content, project_path)

        assert result["solution_used"] is not None
        assert result["solution_used"]["cause"] == "Wrong import statement"


@pytest.mark.skipif(not HAS_DEBUGGER_AGENT, reason="debugger_agent module not available")
class TestFindSolutionFromKB:
    """DebuggerAgent._find_solution_from_kb() のテスト"""

    @patch('nexuscore.agents.debugger_agent.BaseAgent.__init__', return_value=None)
    def test_find_solution_from_local_kb(self, mock_base_init, tmp_path):
        """ローカルナレッジベースから解決策を検索"""
        kb_file = tmp_path / "kb.json"
        kb_data = [
            {
                "error_signature": "NameError.*not defined",
                "cause": "Variable not defined",
                "solution_pattern": {"type": "define_variable"}
            }
        ]
        kb_file.write_text(json.dumps(kb_data))

        agent = DebuggerAgent.__new__(DebuggerAgent)
        agent.logger = Mock()
        DebuggerAgent.__init__(agent, knowledge_base_path=str(kb_file))

        error_log = "NameError: name 'x' is not defined"

        solution = agent._find_solution_from_kb(error_log)

        assert solution is not None
        assert solution["cause"] == "Variable not defined"

    @patch('nexuscore.agents.debugger_agent.BaseAgent.__init__', return_value=None)
    def test_find_solution_no_match(self, mock_base_init, tmp_path):
        """ナレッジベースに一致するエントリがない場合"""
        kb_file = tmp_path / "kb.json"
        kb_data = [
            {
                "error_signature": "ImportError",
                "cause": "Wrong import",
                "solution_pattern": {"type": "fix_import"}
            }
        ]
        kb_file.write_text(json.dumps(kb_data))

        agent = DebuggerAgent.__new__(DebuggerAgent)
        agent.logger = Mock()
        DebuggerAgent.__init__(agent, knowledge_base_path=str(kb_file))

        error_log = "TypeError: unsupported operand"

        solution = agent._find_solution_from_kb(error_log)

        assert solution is None

    @patch('nexuscore.agents.debugger_agent.BaseAgent.__init__', return_value=None)
    @patch('nexuscore.agents.debugger_agent.knowledge_base')
    def test_find_solution_from_global_kb(self, mock_kb, mock_base_init):
        """グローバルナレッジベースから解決策を検索"""
        mock_kb.find_solution.return_value = {
            "error_signature": "SyntaxError",
            "cause": "Missing colon",
            "solution_pattern": {"type": "add_colon"}
        }

        agent = DebuggerAgent()
        agent.logger = Mock()  # Mock logger
        error_log = "SyntaxError: invalid syntax"

        solution = agent._find_solution_from_kb(error_log)

        assert solution is not None
        assert solution["cause"] == "Missing colon"


@pytest.mark.skipif(not HAS_DEBUGGER_AGENT, reason="debugger_agent module not available")
class TestGenerateFixedCode:
    """DebuggerAgent._generate_fixed_code() のテスト"""

    @patch('nexuscore.agents.debugger_agent.BaseAgent.__init__', return_value=None)
    @patch('nexuscore.agents.debugger_agent.BaseAgent.execute_llm_task')
    def test_generate_fixed_code_basic(self, mock_execute_llm, mock_base_init):
        """基本的なコード修正生成"""
        fixed_code = "def add(a, b):\n    return a + b"
        mock_execute_llm.return_value = fixed_code

        agent = DebuggerAgent()
        agent.logger = Mock()  # Mock logger
        error_log = "TypeError"
        source_path = "src/calc.py"
        source_code = "def add(a, b):\n    return a + 'b'"
        instruction = "Fix the TypeError"

        result = agent._generate_fixed_code(error_log, source_path, source_code, instruction)

        assert result == fixed_code

    @patch('nexuscore.agents.debugger_agent.BaseAgent.__init__', return_value=None)
    @patch('nexuscore.agents.debugger_agent.BaseAgent.execute_llm_task')
    def test_generate_fixed_code_with_code_fence(self, mock_execute_llm, mock_base_init):
        """コードフェンス付きのレスポンス"""
        fixed_code = "def add(a, b):\n    return a + b"
        mock_execute_llm.return_value = f"```python\n{fixed_code}\n```"

        agent = DebuggerAgent()
        agent.logger = Mock()  # Mock logger
        result = agent._generate_fixed_code("error", "path", "code", "instruction")

        # コードフェンスが除去される
        assert result == fixed_code

    @patch('nexuscore.agents.debugger_agent.BaseAgent.__init__', return_value=None)
    @patch('nexuscore.agents.debugger_agent.BaseAgent.execute_llm_task')
    def test_generate_fixed_code_llm_failure(self, mock_execute_llm, mock_base_init):
        """LLM実行失敗時"""
        mock_execute_llm.side_effect = Exception("LLM error")

        agent = DebuggerAgent()
        agent.logger = Mock()  # Mock logger
        result = agent._generate_fixed_code("error", "path", "code", "instruction")

        assert result is None


@pytest.mark.skipif(not HAS_DEBUGGER_AGENT, reason="debugger_agent module not available")
class TestCreateDiff:
    """DebuggerAgent._create_diff() のテスト"""

    @patch('nexuscore.agents.debugger_agent.BaseAgent.__init__', return_value=None)
    def test_create_diff_basic(self, mock_base_init):
        """基本的なdiff生成"""
        agent = DebuggerAgent()
        agent.logger = Mock()  # Mock logger

        original = "def add(a, b):\n    return a + 'b'\n"
        fixed = "def add(a, b):\n    return a + b\n"
        source_path = "/home/user/project/src/calc.py"
        project_path = "/home/user/project"

        diff = agent._create_diff(original, fixed, source_path, project_path)

        assert "src/calc.py" in diff
        assert "---" in diff
        assert "+++" in diff
        assert "-    return a + 'b'" in diff
        assert "+    return a + b" in diff

    @patch('nexuscore.agents.debugger_agent.BaseAgent.__init__', return_value=None)
    def test_create_diff_no_changes(self, mock_base_init):
        """変更がない場合"""
        agent = DebuggerAgent()
        agent.logger = Mock()  # Mock logger

        code = "def add(a, b):\n    return a + b\n"
        source_path = "/home/user/project/src/calc.py"
        project_path = "/home/user/project"

        diff = agent._create_diff(code, code, source_path, project_path)

        # 変更がない場合は空文字列
        assert diff == ""

    @patch('nexuscore.agents.debugger_agent.BaseAgent.__init__', return_value=None)
    def test_create_diff_relative_path_error(self, mock_base_init):
        """相対パス計算エラー時"""
        agent = DebuggerAgent()
        agent.logger = Mock()  # Mock logger

        original = "line1\n"
        fixed = "line2\n"
        source_path = "src/calc.py"  # 相対パスで指定
        project_path = "/home/user/project"

        # エラーが発生してもdiffは生成される
        diff = agent._create_diff(original, fixed, source_path, project_path)

        assert diff != ""


@pytest.mark.skipif(not HAS_DEBUGGER_AGENT, reason="debugger_agent module not available")
class TestEdgeCases:
    """エッジケースのテスト"""

    @patch('nexuscore.agents.debugger_agent.BaseAgent.__init__', return_value=None)
    @patch('nexuscore.agents.debugger_agent.BaseAgent.execute_llm_task')
    def test_debug_and_patch_empty_error_log(self, mock_execute_llm, mock_base_init):
        """空のエラーログ"""
        mock_execute_llm.return_value = "fixed code"

        agent = DebuggerAgent()
        agent.logger = Mock()  # Mock logger
        error_log = ""
        files_content = {"src/calc.py": "code"}
        project_path = "/home/user/project"

        result = agent.debug_and_patch(error_log, files_content, project_path)

        # エラーログが空でも処理は継続
        assert "patch" in result

    @patch('nexuscore.agents.debugger_agent.BaseAgent.__init__', return_value=None)
    @patch('nexuscore.agents.debugger_agent.BaseAgent.execute_llm_task')
    def test_generate_fixed_code_empty_response(self, mock_execute_llm, mock_base_init):
        """LLMが空のレスポンスを返す場合"""
        mock_execute_llm.return_value = ""

        agent = DebuggerAgent()
        agent.logger = Mock()  # Mock logger
        result = agent._generate_fixed_code("error", "path", "code", "instruction")

        assert result is None

    @patch('nexuscore.agents.debugger_agent.BaseAgent.__init__', return_value=None)
    @patch('nexuscore.agents.debugger_agent.BaseAgent.execute_llm_task')
    def test_generate_fixed_code_diff_format_response(self, mock_execute_llm, mock_base_init):
        """diff形式のレスポンス"""
        diff_response = "```diff\n--- a/file.py\n+++ b/file.py\n@@ -1,1 +1,1 @@\n-old\n+new\n```"
        mock_execute_llm.return_value = diff_response

        agent = DebuggerAgent()
        agent.logger = Mock()  # Mock logger
        result = agent._generate_fixed_code("error", "path", "code", "instruction")

        # diffプレフィックスが除去される
        assert "```" not in result
        assert "diff" not in result.lower() or result.strip().startswith("---")

    @patch('nexuscore.agents.debugger_agent.BaseAgent.__init__', return_value=None)
    def test_find_solution_invalid_regex(self, mock_base_init, tmp_path):
        """マッチしない正規表現のerror_signature"""
        kb_file = tmp_path / "kb.json"
        kb_data = [
            {
                "error_signature": "^NotMatchingAnything$",  # マッチしない正規表現
                "cause": "Test",
                "solution_pattern": {}
            }
        ]
        kb_file.write_text(json.dumps(kb_data))

        agent = DebuggerAgent.__new__(DebuggerAgent)
        agent.logger = Mock()
        DebuggerAgent.__init__(agent, knowledge_base_path=str(kb_file))
        error_log = "Some error"

        # マッチしない場合はNoneが返される
        solution = agent._find_solution_from_kb(error_log)
        assert solution is None
