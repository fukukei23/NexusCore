"""
============================================================================
Comprehensive Tests for KnowledgeCuratorAgent
============================================================================
高品質テストの原則:
- 外部依存（LLM API、subprocess）のみモック
- 実際のビジネスロジックをテスト
- エッジケースとエラー条件をカバー
============================================================================
"""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from nexuscore.agents.knowledge_curator_agent import KnowledgeCuratorAgent


@pytest.fixture
def api_key():
    """テスト用のAPIキー"""
    return "test-api-key-12345"


@pytest.fixture
def model():
    """テスト用のモデル名"""
    return "gpt-4"


@pytest.fixture
def curator_agent(api_key, model):
    """KnowledgeCuratorAgentのインスタンス"""
    return KnowledgeCuratorAgent(api_key=api_key, model=model)


@pytest.fixture
def temp_project_dir():
    """一時的なプロジェクトディレクトリ"""
    with tempfile.TemporaryDirectory(prefix="test_project_") as tmpdir:
        # プロジェクト構造を作成
        src_dir = Path(tmpdir) / "src"
        tests_dir = Path(tmpdir) / "tests"
        src_dir.mkdir()
        tests_dir.mkdir()

        # ソースファイル
        source_file = src_dir / "calculator.py"
        source_file.write_text(
            """
def add(a, b):
    return a + b

def subtract(a, b):
    return a - b  # Bug: should be a - b but returns a + b
"""
        )

        # テストファイル
        test_file = tests_dir / "test_calculator.py"
        test_file.write_text(
            """
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from calculator import add, subtract

def test_add():
    assert add(2, 3) == 5

def test_subtract():
    assert subtract(5, 3) == 2  # This will fail with the bug
"""
        )

        yield {
            "project_path": tmpdir,
            "source_file": str(source_file),
            "test_file": str(test_file),
        }


@pytest.fixture
def fkb_suggestion():
    """テスト用のFKB提案"""
    return {
        "id": "test-suggestion-001",
        "error_pattern": "AssertionError.*subtract",
        "solution_hint": "Check the subtract function implementation",
        "related_files": ["src/calculator.py"],
    }


@pytest.fixture
def test_output():
    """テストの失敗出力"""
    return """
FAILED tests/test_calculator.py::test_subtract - AssertionError: assert 8 == 2
E       AssertionError: assert 8 == 2
E        +  where 8 = subtract(5, 3)
"""


# ============================================================================
# Tests: __init__
# ============================================================================


class TestInit:
    def test_init_sets_api_key(self, curator_agent, api_key):
        """APIキーが正しく設定される"""
        assert curator_agent.api_key == api_key

    def test_init_sets_model(self, curator_agent, model):
        """モデル名が正しく設定される"""
        assert curator_agent.model == model

    def test_init_creates_logger(self, curator_agent):
        """ロガーが作成される"""
        assert curator_agent.logger is not None
        assert curator_agent.logger.name == "KnowledgeCuratorAgent"


# ============================================================================
# Tests: validate_fkb_suggestion
# ============================================================================


class TestValidateFkbSuggestion:
    @patch("nexuscore.agents.knowledge_curator_agent.DebuggerAgent")
    @patch("nexuscore.agents.knowledge_curator_agent.PatchApplier")
    def test_validate_with_successful_fix(
        self,
        mock_patch_applier_class,
        mock_debugger_class,
        curator_agent,
        temp_project_dir,
        fkb_suggestion,
        test_output,
    ):
        """成功するFKB提案の検証"""
        # DebuggerAgentのモック
        mock_debugger = Mock()
        mock_debugger.debug_and_patch.return_value = {
            "patch": "--- a/src/calculator.py\n+++ b/src/calculator.py\n@@ -4,4 +4,4 @@\n-    return a + b\n+    return a - b"
        }
        mock_debugger_class.return_value = mock_debugger

        # PatchApplierのモック
        mock_patcher = Mock()
        mock_patcher.apply.return_value = True
        mock_patch_applier_class.return_value = mock_patcher

        # _run_tests_in_sandboxをモック
        with patch.object(curator_agent, "_run_tests_in_sandbox", return_value=(True, "")):
            result = curator_agent.validate_fkb_suggestion(
                suggestion=fkb_suggestion,
                original_project_path=temp_project_dir["project_path"],
                failed_test_path=temp_project_dir["test_file"],
                related_source_path=temp_project_dir["source_file"],
                original_test_output=test_output,
            )

        assert result is True
        mock_debugger.debug_and_patch.assert_called_once()
        mock_patcher.apply.assert_called_once()

    @patch("nexuscore.agents.knowledge_curator_agent.DebuggerAgent")
    @patch("nexuscore.agents.knowledge_curator_agent.PatchApplier")
    def test_validate_with_debugger_no_patch(
        self,
        mock_patch_applier_class,
        mock_debugger_class,
        curator_agent,
        temp_project_dir,
        fkb_suggestion,
        test_output,
    ):
        """DebuggerAgentがパッチを生成しない場合"""
        mock_debugger = Mock()
        mock_debugger.debug_and_patch.return_value = None
        mock_debugger_class.return_value = mock_debugger

        result = curator_agent.validate_fkb_suggestion(
            suggestion=fkb_suggestion,
            original_project_path=temp_project_dir["project_path"],
            failed_test_path=temp_project_dir["test_file"],
            related_source_path=temp_project_dir["source_file"],
            original_test_output=test_output,
        )

        assert result is False

    @patch("nexuscore.agents.knowledge_curator_agent.DebuggerAgent")
    @patch("nexuscore.agents.knowledge_curator_agent.PatchApplier")
    def test_validate_with_patch_application_failure(
        self,
        mock_patch_applier_class,
        mock_debugger_class,
        curator_agent,
        temp_project_dir,
        fkb_suggestion,
        test_output,
    ):
        """パッチ適用に失敗した場合"""
        mock_debugger = Mock()
        mock_debugger.debug_and_patch.return_value = {"patch": "dummy patch"}
        mock_debugger_class.return_value = mock_debugger

        mock_patcher = Mock()
        mock_patcher.apply.return_value = False
        mock_patch_applier_class.return_value = mock_patcher

        result = curator_agent.validate_fkb_suggestion(
            suggestion=fkb_suggestion,
            original_project_path=temp_project_dir["project_path"],
            failed_test_path=temp_project_dir["test_file"],
            related_source_path=temp_project_dir["source_file"],
            original_test_output=test_output,
        )

        assert result is False

    @patch("nexuscore.agents.knowledge_curator_agent.DebuggerAgent")
    @patch("nexuscore.agents.knowledge_curator_agent.PatchApplier")
    def test_validate_with_tests_still_failing(
        self,
        mock_patch_applier_class,
        mock_debugger_class,
        curator_agent,
        temp_project_dir,
        fkb_suggestion,
        test_output,
    ):
        """パッチ適用後もテストが失敗する場合"""
        mock_debugger = Mock()
        mock_debugger.debug_and_patch.return_value = {"patch": "dummy patch"}
        mock_debugger_class.return_value = mock_debugger

        mock_patcher = Mock()
        mock_patcher.apply.return_value = True
        mock_patch_applier_class.return_value = mock_patcher

        # テストが失敗する
        with patch.object(
            curator_agent, "_run_tests_in_sandbox", return_value=(False, "Tests failed")
        ):
            result = curator_agent.validate_fkb_suggestion(
                suggestion=fkb_suggestion,
                original_project_path=temp_project_dir["project_path"],
                failed_test_path=temp_project_dir["test_file"],
                related_source_path=temp_project_dir["source_file"],
                original_test_output=test_output,
            )

        assert result is False

    @patch("nexuscore.agents.knowledge_curator_agent.DebuggerAgent")
    def test_validate_with_exception(
        self, mock_debugger_class, curator_agent, temp_project_dir, fkb_suggestion, test_output
    ):
        """検証中に例外が発生した場合"""
        mock_debugger_class.side_effect = Exception("Unexpected error")

        result = curator_agent.validate_fkb_suggestion(
            suggestion=fkb_suggestion,
            original_project_path=temp_project_dir["project_path"],
            failed_test_path=temp_project_dir["test_file"],
            related_source_path=temp_project_dir["source_file"],
            original_test_output=test_output,
        )

        assert result is False

    @patch("nexuscore.agents.knowledge_curator_agent.DebuggerAgent")
    @patch("nexuscore.agents.knowledge_curator_agent.PatchApplier")
    def test_validate_creates_temporary_fkb(
        self,
        mock_patch_applier_class,
        mock_debugger_class,
        curator_agent,
        temp_project_dir,
        fkb_suggestion,
        test_output,
    ):
        """一時的なFKBファイルが作成されることを確認"""
        mock_debugger = Mock()
        mock_debugger.debug_and_patch.return_value = {"patch": "dummy"}
        mock_debugger_class.return_value = mock_debugger

        mock_patcher = Mock()
        mock_patcher.apply.return_value = True
        mock_patch_applier_class.return_value = mock_patcher

        with patch.object(curator_agent, "_run_tests_in_sandbox", return_value=(True, "")):
            curator_agent.validate_fkb_suggestion(
                suggestion=fkb_suggestion,
                original_project_path=temp_project_dir["project_path"],
                failed_test_path=temp_project_dir["test_file"],
                related_source_path=temp_project_dir["source_file"],
                original_test_output=test_output,
            )

        # DebuggerAgentが一時的なFKBパスで初期化されることを確認
        mock_debugger_class.assert_called_once()
        call_kwargs = mock_debugger_class.call_args[1]
        assert "knowledge_base_path" in call_kwargs
        assert "temp_fkb.json" in call_kwargs["knowledge_base_path"]

    @patch("nexuscore.agents.knowledge_curator_agent.DebuggerAgent")
    @patch("nexuscore.agents.knowledge_curator_agent.PatchApplier")
    def test_validate_with_missing_source_file(
        self,
        mock_patch_applier_class,
        mock_debugger_class,
        curator_agent,
        temp_project_dir,
        fkb_suggestion,
        test_output,
    ):
        """ソースファイルが見つからない場合（サンドボックス内）"""
        mock_debugger = Mock()
        # files_contentが空になるため、debug_and_patchは呼ばれない想定
        mock_debugger_class.return_value = mock_debugger

        # 存在しないファイルパスを指定
        result = curator_agent.validate_fkb_suggestion(
            suggestion=fkb_suggestion,
            original_project_path=temp_project_dir["project_path"],
            failed_test_path=temp_project_dir["test_file"],
            related_source_path="/nonexistent/file.py",
            original_test_output=test_output,
        )

        # ファイルが見つからないため検証失敗
        assert result is False


# ============================================================================
# Tests: _run_tests_in_sandbox
# ============================================================================


class TestRunTestsInSandbox:
    def test_run_tests_success(self, curator_agent):
        """テストが成功する場合"""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test_simple.py"
            test_file.write_text(
                """
def test_always_pass():
    assert True
"""
            )

            passed, output = curator_agent._run_tests_in_sandbox(tmpdir, "test_simple.py")

            assert passed is True
            assert "test_simple.py" in output or "passed" in output.lower()

    def test_run_tests_failure(self, curator_agent):
        """テストが失敗する場合"""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test_fail.py"
            test_file.write_text(
                """
def test_always_fail():
    assert False, "This test always fails"
"""
            )

            passed, output = curator_agent._run_tests_in_sandbox(tmpdir, "test_fail.py")

            assert passed is False
            assert "FAILED" in output or "AssertionError" in output

    def test_run_tests_with_syntax_error(self, curator_agent):
        """構文エラーがある場合"""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test_syntax_error.py"
            test_file.write_text(
                """
def test_syntax_error(
    # Missing closing parenthesis
    assert True
"""
            )

            passed, output = curator_agent._run_tests_in_sandbox(tmpdir, "test_syntax_error.py")

            assert passed is False
            assert "SyntaxError" in output or "ERROR" in output

    def test_run_tests_with_nonexistent_file(self, curator_agent):
        """存在しないテストファイル"""
        with tempfile.TemporaryDirectory() as tmpdir:
            passed, output = curator_agent._run_tests_in_sandbox(tmpdir, "nonexistent_test.py")

            assert passed is False
            # pytestはファイルが見つからない場合でもエラーを返す


# ============================================================================
# Tests: Integration scenarios
# ============================================================================


class TestIntegrationScenarios:
    @patch("nexuscore.agents.knowledge_curator_agent.DebuggerAgent")
    @patch("nexuscore.agents.knowledge_curator_agent.PatchApplier")
    def test_full_validation_workflow(
        self,
        mock_patch_applier_class,
        mock_debugger_class,
        curator_agent,
        temp_project_dir,
        test_output,
    ):
        """完全な検証ワークフロー"""
        suggestion = {
            "id": "workflow-test",
            "error_pattern": "subtract.*AssertionError",
            "solution": "Fix subtract function to return a - b instead of a + b",
        }

        mock_debugger = Mock()
        mock_debugger.debug_and_patch.return_value = {
            "patch": "--- a/src/calculator.py\n+++ b/src/calculator.py\n..."
        }
        mock_debugger_class.return_value = mock_debugger

        mock_patcher = Mock()
        mock_patcher.apply.return_value = True
        mock_patch_applier_class.return_value = mock_patcher

        with patch.object(
            curator_agent, "_run_tests_in_sandbox", return_value=(True, "All tests passed")
        ):
            result = curator_agent.validate_fkb_suggestion(
                suggestion=suggestion,
                original_project_path=temp_project_dir["project_path"],
                failed_test_path=temp_project_dir["test_file"],
                related_source_path=temp_project_dir["source_file"],
                original_test_output=test_output,
            )

        assert result is True
        # DebuggerAgentに正しいパラメータが渡されることを確認
        debug_call = mock_debugger.debug_and_patch.call_args
        assert debug_call[1]["error_log"] == test_output
        assert "files_content" in debug_call[1]

    @patch("nexuscore.agents.knowledge_curator_agent.DebuggerAgent")
    @patch("nexuscore.agents.knowledge_curator_agent.PatchApplier")
    def test_sandbox_isolation(
        self,
        mock_patch_applier_class,
        mock_debugger_class,
        curator_agent,
        temp_project_dir,
        fkb_suggestion,
        test_output,
    ):
        """サンドボックスの分離が機能することを確認"""
        original_file_content = Path(temp_project_dir["source_file"]).read_text()

        mock_debugger = Mock()
        mock_debugger.debug_and_patch.return_value = {"patch": "dummy"}
        mock_debugger_class.return_value = mock_debugger

        mock_patcher = Mock()
        mock_patcher.apply.return_value = True
        mock_patch_applier_class.return_value = mock_patcher

        with patch.object(curator_agent, "_run_tests_in_sandbox", return_value=(True, "")):
            curator_agent.validate_fkb_suggestion(
                suggestion=fkb_suggestion,
                original_project_path=temp_project_dir["project_path"],
                failed_test_path=temp_project_dir["test_file"],
                related_source_path=temp_project_dir["source_file"],
                original_test_output=test_output,
            )

        # 元のファイルは変更されていないことを確認
        assert Path(temp_project_dir["source_file"]).read_text() == original_file_content
