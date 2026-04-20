"""
GitHubPRClient および SelfHealingService._auto_create_fix_pr のテスト
"""

import json
import os
import urllib.error
from unittest.mock import MagicMock, patch

import pytest

from nexuscore.integration.github_pr_client import GitHubPRClient


# ---------------------------------------------------------------------------
# ヘルパー
# ---------------------------------------------------------------------------
def _mock_response(data_dict):
    """urlopen が返すモックレスポンスを生成する。"""
    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps(data_dict).encode("utf-8")
    mock_resp.__enter__ = MagicMock(return_value=mock_resp)
    mock_resp.__exit__ = MagicMock(return_value=False)
    return mock_resp


# ===========================================================================
# TestGitHubPRClient
# ===========================================================================
class TestGitHubPRClient:
    """GitHubPRClient のユニットテスト（HTTP通信をモック）。"""

    def test_init(self):
        client = GitHubPRClient(token="tok123", repo_full_name="own/repo")
        assert client.token == "tok123"
        assert client.repo_full_name == "own/repo"

    @patch("nexuscore.integration.github_pr_client.urllib.request.urlopen")
    def test_create_branch(self, mock_urlopen):
        mock_urlopen.return_value = _mock_response({"ref": "refs/heads/fix"})
        client = GitHubPRClient(token="tok", repo_full_name="own/repo")
        result = client.create_branch("fix", "abc123")

        req = mock_urlopen.call_args[0][0]
        assert req.method == "POST"
        assert "/repos/own/repo/git/refs" in req.full_url
        payload = json.loads(req.data)
        assert payload == {"ref": "refs/heads/fix", "sha": "abc123"}

    @patch("nexuscore.integration.github_pr_client.urllib.request.urlopen")
    def test_get_branch_sha(self, mock_urlopen):
        mock_urlopen.return_value = _mock_response({"object": {"sha": "deadbeef"}})
        client = GitHubPRClient(token="tok", repo_full_name="own/repo")
        sha = client.get_branch_sha("main")
        assert sha == "deadbeef"

    @patch("nexuscore.integration.github_pr_client.urllib.request.urlopen")
    def test_commit_files(self, mock_urlopen):
        mock_urlopen.side_effect = [
            _mock_response({"object": {"sha": "ref_sha"}}),       # GET ref
            _mock_response({"tree": {"sha": "tree_base"}}),       # GET commit
            _mock_response({"sha": "blob1"}),                     # POST blob
            _mock_response({"sha": "new_tree"}),                  # POST tree
            _mock_response({"sha": "new_commit_sha"}),            # POST commit
            _mock_response({}),                                    # PATCH ref
        ]
        client = GitHubPRClient(token="tok", repo_full_name="own/repo")
        result = client.commit_files("fix-br", "msg", {"src/app.py": "print(1)"})

        assert mock_urlopen.call_count == 6
        methods = [c[0][0].method for c in mock_urlopen.call_args_list]
        assert methods == ["GET", "GET", "POST", "POST", "POST", "PATCH"]

    @patch("nexuscore.integration.github_pr_client.urllib.request.urlopen")
    def test_create_pull_request(self, mock_urlopen):
        mock_urlopen.return_value = _mock_response(
            {"number": 42, "html_url": "https://github.com/own/repo/pull/42"}
        )
        client = GitHubPRClient(token="tok", repo_full_name="own/repo")
        pr = client.create_pull_request("Title", "Body", "fix-br", "main")

        assert pr["number"] == 42
        req = mock_urlopen.call_args[0][0]
        assert req.method == "POST"
        assert "/repos/own/repo/pulls" in req.full_url

    @patch("nexuscore.integration.github_pr_client.urllib.request.urlopen")
    def test_auto_create_fix_pr(self, mock_urlopen):
        mock_urlopen.side_effect = [
            _mock_response({"object": {"sha": "base_sha"}}),          # get_branch_sha
            _mock_response({}),                                        # create_branch
            _mock_response({"object": {"sha": "ref_sha"}}),           # commit_files: GET ref
            _mock_response({"tree": {"sha": "tree_base"}}),           # commit_files: GET commit
            _mock_response({"sha": "blob_sha"}),                      # commit_files: POST blob
            _mock_response({"sha": "new_tree_sha"}),                  # commit_files: POST tree
            _mock_response({"sha": "new_commit_sha"}),                # commit_files: POST commit
            _mock_response({}),                                        # commit_files: PATCH ref
            _mock_response(                                            # create_pull_request
                {"number": 7, "html_url": "https://github.com/own/repo/pull/7"}
            ),
        ]
        client = GitHubPRClient(token="tok", repo_full_name="own/repo")
        result = client.auto_create_fix_pr(
            branch_name="fix/auto-123",
            base_branch="main",
            commit_message="auto-fix",
            pr_title="Auto-fix PR",
            pr_body="fix applied",
            files={"src/app.py": "print(1)"},
        )

        assert result["pr_number"] == 7
        assert result["branch"] == "fix/auto-123"
        assert mock_urlopen.call_count == 9

    @patch("nexuscore.integration.github_pr_client.urllib.request.urlopen")
    def test_request_http_error(self, mock_urlopen):
        error_body = b'{"message": "Not Found"}'
        mock_urlopen.side_effect = urllib.error.HTTPError(
            url="http://url", code=404, msg="Not Found", hdrs=None, fp=None
        )
        # HTTPError の fp.read() が error_body を返すようにする
        mock_urlopen.side_effect.read = lambda: error_body

        client = GitHubPRClient(token="tok", repo_full_name="own/repo")
        with pytest.raises(RuntimeError, match="GitHub API error 404"):
            client.get_branch_sha("missing")


# ===========================================================================
# TestAutoCreateFixPR（SelfHealingService._auto_create_fix_pr のテスト）
# ===========================================================================
class TestAutoCreateFixPR:
    """SelfHealingService._auto_create_fix_pr のテスト。"""

    @patch(
        "nexuscore.services.self_healing_service.SelfHealingService.__init__",
        return_value=None,
    )
    def _make_service(self, mock_init):
        from nexuscore.services.self_healing_service import SelfHealingService

        svc = SelfHealingService.__new__(SelfHealingService)
        import logging

        svc.logger = logging.getLogger("test")
        return svc

    @patch.dict(os.environ, {"NEXUS_GITHUB_TOKEN": "mock_token"})
    @patch("nexuscore.integration.github_pr_client.GitHubPRClient.auto_create_fix_pr")
    def test_auto_pr_created_when_fixed(self, mock_auto_pr):
        mock_auto_pr.return_value = {
            "pr_number": 99,
            "pr_url": "https://github.com/o/r/pull/99",
            "branch": "fix/auto-123",
        }
        svc = self._make_service()
        result = svc._auto_create_fix_pr(
            repo_full_name="owner/repo",
            head_sha="abc1234567",
            pr_number=10,
            run_id="sh-12345-10-abc1234",
            patch_text="--- a/f.py\n+++ b/f.py\n",
            changed_files=["f.py"],
        )

        assert result is not None
        assert result["pr_number"] == 99

    @patch.dict(os.environ, {}, clear=True)
    def test_auto_pr_skipped_no_token(self):
        svc = self._make_service()
        result = svc._auto_create_fix_pr(
            repo_full_name="owner/repo",
            head_sha="abc1234567",
            pr_number=10,
            run_id="sh-12345-10-abc1234",
            patch_text="patch",
            changed_files=["f.py"],
        )
        assert result is None

    @patch.dict(os.environ, {"NEXUS_GITHUB_TOKEN": "mock_token"})
    def test_auto_pr_skipped_no_files(self):
        svc = self._make_service()
        result = svc._auto_create_fix_pr(
            repo_full_name="owner/repo",
            head_sha="abc1234567",
            pr_number=10,
            run_id="sh-12345-10-abc1234",
            patch_text="patch",
            changed_files=[],
        )
        assert result is None

    @patch.dict(os.environ, {"NEXUS_GITHUB_TOKEN": "mock_token"})
    @patch(
        "nexuscore.integration.github_pr_client.GitHubPRClient.auto_create_fix_pr",
        side_effect=RuntimeError("API failure"),
    )
    def test_auto_pr_failure_non_fatal(self, mock_auto_pr):
        svc = self._make_service()
        result = svc._auto_create_fix_pr(
            repo_full_name="owner/repo",
            head_sha="abc1234567",
            pr_number=10,
            run_id="sh-12345-10-abc1234",
            patch_text="patch",
            changed_files=["f.py"],
        )
        assert result is None  # 例外でもNoneを返す（クラッシュしない）
