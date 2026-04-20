# ==============================================================================
# Test: DebuggerAgent.auto_generate_pr フルフロー統合テスト
# Issue #50: MC1-2 DebuggerAgent自動PR生成ロジックの完成
# ==============================================================================

import pytest
from unittest.mock import patch, MagicMock, call

from nexuscore.agents.debugger_agent import DebuggerAgent


@pytest.fixture
def agent():
    """テスト用 DebuggerAgent（KBなし）"""
    return DebuggerAgent()


@pytest.fixture
def mock_llm():
    """execute_llm_task をモック"""
    with patch.object(DebuggerAgent, "execute_llm_task") as m:
        yield m


@pytest.fixture
def mock_pr_creator():
    """GitHubPRCreator のクラスレベルモック（lazy import 対応）"""
    with patch("nexuscore.agents.github_pr_creator.GitHubPRCreator") as cls:
        instance = MagicMock()
        cls.return_value = instance
        yield cls, instance


# ---------------------------------------------------------------------------
# 正常系
# ---------------------------------------------------------------------------


class TestAutoGeneratePRSuccess:
    def test_full_flow_creates_pr(self, agent, mock_llm, mock_pr_creator):
        """debug_and_patch → GitHubPRCreator.create_fix_pr の正常フロー"""
        mock_llm.return_value = "def fixed():\n    pass"
        mock_cls, mock_inst = mock_pr_creator
        mock_inst.create_fix_pr.return_value = {
            "status": "created",
            "pr_number": 42,
            "pr_url": "https://github.com/example/repo/pull/42",
            "pr_title": "[AutoFix] ...",
            "branch": "fix/auto-123",
        }

        result = agent.auto_generate_pr(
            error_log="AssertionError: expected True",
            files_content={"src/module.py": "def broken():\n    pass"},
            project_path="/project",
            repo_full_name="example/repo",
            base_branch="main",
            fix_branch="fix/auto-123",
            github_token="ghp_test123",
        )

        assert result["status"] == "created"
        assert result["pr_number"] == 42
        assert "pr_url" in result

        # GitHubPRCreator(token=...) で初期化
        mock_cls.assert_called_once_with(token="ghp_test123")

        # create_fix_pr が正しい引数で呼ばれた
        mock_inst.create_fix_pr.assert_called_once()
        kwargs = mock_inst.create_fix_pr.call_args.kwargs
        assert kwargs["repo_full_name"] == "example/repo"
        assert kwargs["file_path"] == "src/module.py"
        assert kwargs["base_branch"] == "main"
        assert kwargs["fix_branch"] == "fix/auto-123"

    def test_error_summary_truncated(self, agent, mock_llm, mock_pr_creator):
        """error_summary は120文字で切り詰められる"""
        long_log = "E\n" * 100  # 200文字
        mock_llm.return_value = "fixed code"
        mock_cls, mock_inst = mock_pr_creator
        mock_inst.create_fix_pr.return_value = {"status": "created", "pr_number": 1}

        agent.auto_generate_pr(
            error_log=long_log,
            files_content={"a.py": "old"},
            project_path="/p",
            repo_full_name="r/r",
            base_branch="main",
            fix_branch="fix/1",
            github_token="tok",
        )

        kwargs = mock_inst.create_fix_pr.call_args.kwargs
        assert len(kwargs["error_summary"]) <= 120


# ---------------------------------------------------------------------------
# 異常系: debug_and_patch 失敗
# ---------------------------------------------------------------------------


class TestAutoGeneratePRPatchFailure:
    def test_empty_files_returns_error(self, agent, mock_pr_creator):
        """files_content が空 → 即座にエラー"""
        mock_cls, _ = mock_pr_creator

        result = agent.auto_generate_pr(
            error_log="err",
            files_content={},
            project_path="/p",
            repo_full_name="r/r",
            base_branch="main",
            fix_branch="fix/1",
            github_token="tok",
        )

        assert result["status"] == "error"
        assert "No files" in result["error"]
        mock_cls.assert_not_called()

    def test_llm_returns_none(self, agent, mock_llm, mock_pr_creator):
        """LLM が None を返した場合 → "Failed to generate fixed code." """
        mock_llm.return_value = None
        mock_cls, _ = mock_pr_creator

        result = agent.auto_generate_pr(
            error_log="err",
            files_content={"a.py": "code"},
            project_path="/p",
            repo_full_name="r/r",
            base_branch="main",
            fix_branch="fix/1",
            github_token="tok",
        )

        assert result["status"] == "error"
        assert "Failed to generate fixed code" in result["error"]
        mock_cls.assert_not_called()

    def test_llm_returns_empty_string(self, agent, mock_llm, mock_pr_creator):
        """LLM が空文字を返した場合 → エラー"""
        mock_llm.return_value = "   "
        mock_cls, _ = mock_pr_creator

        result = agent.auto_generate_pr(
            error_log="err",
            files_content={"a.py": "code"},
            project_path="/p",
            repo_full_name="r/r",
            base_branch="main",
            fix_branch="fix/1",
            github_token="tok",
        )

        assert result["status"] == "error"
        mock_cls.assert_not_called()


# ---------------------------------------------------------------------------
# 異常系: GitHub API 失敗
# ---------------------------------------------------------------------------


class TestAutoGeneratePRGitHubFailure:
    def test_create_fix_pr_raises_exception(self, agent, mock_llm, mock_pr_creator):
        """GitHubPRCreator.create_fix_pr が例外を投げた場合"""
        mock_llm.return_value = "fixed"
        mock_cls, mock_inst = mock_pr_creator
        mock_inst.create_fix_pr.side_effect = RuntimeError("API rate limit")

        result = agent.auto_generate_pr(
            error_log="err",
            files_content={"a.py": "old"},
            project_path="/p",
            repo_full_name="r/r",
            base_branch="main",
            fix_branch="fix/1",
            github_token="tok",
        )

        assert result["status"] == "error"
        assert "API rate limit" in result["error"]

    def test_create_fix_pr_returns_error_status(self, agent, mock_llm, mock_pr_creator):
        """create_fix_pr が error ステータスを返した場合"""
        mock_llm.return_value = "fixed"
        _, mock_inst = mock_pr_creator
        mock_inst.create_fix_pr.return_value = {
            "status": "error",
            "error": "Branch already exists",
        }

        result = agent.auto_generate_pr(
            error_log="err",
            files_content={"a.py": "old"},
            project_path="/p",
            repo_full_name="r/r",
            base_branch="main",
            fix_branch="fix/1",
            github_token="tok",
        )

        assert result["status"] == "error"
        assert "Branch already exists" in result["error"]
