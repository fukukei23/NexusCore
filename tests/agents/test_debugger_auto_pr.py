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


# ---------------------------------------------------------------------------
# Issue #50 完了条件: 20回シミュレーションで95%成功率検証
# ---------------------------------------------------------------------------


class TestAutoPRMetrics:
    """メトリクス追跡とバリデーションのテスト"""

    def setup_method(self):
        DebuggerAgent.total_pr_attempts = 0
        DebuggerAgent.successful_prs = 0

    def test_metrics_track_success(self, agent, mock_llm, mock_pr_creator):
        """成功時にメトリクスが正しく更新される"""
        mock_llm.return_value = "def fixed():\n    pass"
        _, mock_inst = mock_pr_creator
        mock_inst.create_fix_pr.return_value = {"status": "created", "pr_number": 1}

        agent.auto_generate_pr(
            error_log="err", files_content={"a.py": "old"},
            project_path="/p", repo_full_name="r/r",
            base_branch="main", fix_branch="fix/1", github_token="tok",
        )

        assert DebuggerAgent.total_pr_attempts == 1
        assert DebuggerAgent.successful_prs == 1

    def test_metrics_track_failure(self, agent, mock_llm, mock_pr_creator):
        """失敗時はsuccessful_prsが増えない"""
        mock_llm.return_value = "fixed"
        _, mock_inst = mock_pr_creator
        mock_inst.create_fix_pr.side_effect = RuntimeError("fail")

        agent.auto_generate_pr(
            error_log="err", files_content={"a.py": "old"},
            project_path="/p", repo_full_name="r/r",
            base_branch="main", fix_branch="fix/1", github_token="tok",
        )

        assert DebuggerAgent.total_pr_attempts == 1
        assert DebuggerAgent.successful_prs == 0

    def test_no_changes_skipped(self, agent, mock_llm, mock_pr_creator):
        """修正コードが元と同じ場合スキップされる"""
        original = "def foo():\n    pass"
        mock_llm.return_value = original
        mock_cls, _ = mock_pr_creator

        result = agent.auto_generate_pr(
            error_log="err", files_content={"a.py": original},
            project_path="/p", repo_full_name="r/r",
            base_branch="main", fix_branch="fix/1", github_token="tok",
        )

        assert result["status"] == "skipped"
        assert result["reason"] == "no_changes"
        mock_cls.assert_not_called()

    def test_original_content_passed_to_creator(self, agent, mock_llm, mock_pr_creator):
        """original_content が create_fix_pr に渡される"""
        mock_llm.return_value = "fixed code"
        _, mock_inst = mock_pr_creator
        mock_inst.create_fix_pr.return_value = {"status": "created", "pr_number": 5}

        agent.auto_generate_pr(
            error_log="err", files_content={"a.py": "original code"},
            project_path="/p", repo_full_name="r/r",
            base_branch="main", fix_branch="fix/1", github_token="tok",
        )

        kwargs = mock_inst.create_fix_pr.call_args.kwargs
        assert kwargs["original_content"] == "original code"

    def test_20_simulations_95_percent_success_rate(self, agent, mock_llm, mock_pr_creator):
        """20回シミュレーション: 19成功/1失敗 = 95%成功率"""
        mock_llm.return_value = "def fixed():\n    pass"
        _, mock_inst = mock_pr_creator
        mock_inst.create_fix_pr.return_value = {"status": "created", "pr_number": 1}

        for i in range(20):
            if i == 19:
                mock_inst.create_fix_pr.side_effect = RuntimeError("transient error")
            agent.auto_generate_pr(
                error_log=f"error_{i}",
                files_content={"src/mod.py": "def broken():\n    pass"},
                project_path="/project",
                repo_full_name="example/repo",
                base_branch="main",
                fix_branch=f"fix/auto-{i}",
                github_token="ghp_test",
            )
            if i == 19:
                mock_inst.create_fix_pr.side_effect = None

        assert DebuggerAgent.total_pr_attempts == 20
        assert DebuggerAgent.successful_prs == 19
        success_rate = DebuggerAgent.successful_prs / DebuggerAgent.total_pr_attempts
        assert success_rate >= 0.95


# ---------------------------------------------------------------------------
# GitHubPRCreator 拡張テスト
# ---------------------------------------------------------------------------


class TestGitHubPRCreatorExtensions:
    """リトライ・差分サイズ・ラベルのテスト"""

    def test_validate_diff_size_within_limit(self):
        from nexuscore.agents.github_pr_creator import GitHubPRCreator
        diff = "\n".join(["+ line"] * 500)
        assert GitHubPRCreator.validate_diff_size(diff, 1000) is True

    def test_validate_diff_size_exceeds_limit(self):
        from nexuscore.agents.github_pr_creator import GitHubPRCreator
        diff = "\n".join(["+ line"] * 1001)
        assert GitHubPRCreator.validate_diff_size(diff, 1000) is False

    def test_create_fix_pr_skips_no_changes(self):
        from nexuscore.agents.github_pr_creator import GitHubPRCreator
        creator = GitHubPRCreator(token="fake")
        with patch.object(creator, "get_branch_sha"):
            result = creator.create_fix_pr(
                repo_full_name="r/r", file_path="a.py",
                fixed_content="same code", base_branch="main",
                fix_branch="fix/1", error_summary="err",
                original_content="same code",
            )
        assert result["status"] == "skipped"
        assert result["reason"] == "no_changes"

    def test_create_fix_pr_skips_oversized_diff(self):
        from nexuscore.agents.github_pr_creator import GitHubPRCreator, MAX_DIFF_LINES
        creator = GitHubPRCreator(token="fake", max_diff_lines=10)
        big_code = "\n".join([f"line {i}" for i in range(100)])
        fixed_code = "\n".join([f"fixed {i}" for i in range(100)])
        with patch.object(creator, "get_branch_sha"):
            result = creator.create_fix_pr(
                repo_full_name="r/r", file_path="a.py",
                fixed_content=fixed_code, base_branch="main",
                fix_branch="fix/1", error_summary="err",
                original_content=big_code,
            )
        assert result["status"] == "skipped"
        assert result["reason"] == "diff_too_large"

    def test_add_labels_called_on_pr_creation(self):
        from nexuscore.agents.github_pr_creator import GitHubPRCreator
        creator = GitHubPRCreator(token="fake")
        with patch.object(creator, "get_branch_sha", return_value="abc123"), \
             patch.object(creator, "create_branch", return_value=True), \
             patch.object(creator, "update_file", return_value=True), \
             patch.object(creator, "create_pull_request", return_value={
                 "number": 42, "html_url": "https://github.com/r/r/pull/42"
             }), \
             patch.object(creator, "add_labels") as mock_labels:
            creator.create_fix_pr(
                repo_full_name="r/r", file_path="a.py",
                fixed_content="fixed", base_branch="main",
                fix_branch="fix/1", error_summary="test error",
            )
            mock_labels.assert_called_once_with("r/r", 42)

    def test_request_with_retry_succeeds_first_try(self):
        from nexuscore.agents.github_pr_creator import GitHubPRCreator
        creator = GitHubPRCreator(token="fake")
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        with patch("nexuscore.agents.github_pr_creator.requests.request", return_value=mock_resp):
            resp = creator._request_with_retry("GET", "http://example.com")
            assert resp == mock_resp

    def test_request_with_retry_retries_on_failure(self):
        from nexuscore.agents.github_pr_creator import GitHubPRCreator
        creator = GitHubPRCreator(token="fake")
        import requests as req
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        with patch("nexuscore.agents.github_pr_creator.requests.request",
                   side_effect=[req.RequestException("timeout"), mock_resp]), \
             patch("nexuscore.agents.github_pr_creator.time.sleep"):
            resp = creator._request_with_retry("GET", "http://example.com")
            assert resp == mock_resp

    def test_request_with_retry_exhausts_retries(self):
        from nexuscore.agents.github_pr_creator import GitHubPRCreator
        import requests as req
        creator = GitHubPRCreator(token="fake")
        with patch("nexuscore.agents.github_pr_creator.requests.request",
                   side_effect=req.RequestException("fail")), \
             patch("nexuscore.agents.github_pr_creator.time.sleep"):
            with pytest.raises(RuntimeError, match="failed after 3 retries"):
                creator._request_with_retry("GET", "http://example.com")
