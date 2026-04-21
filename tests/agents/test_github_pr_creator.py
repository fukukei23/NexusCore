"""tests/agents/test_github_pr_creator.py
GitHubPRCreator の単体テスト（requests を全てモック）
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from nexuscore.agents.github_pr_creator import GitHubPRCreator


@pytest.fixture
def creator():
    return GitHubPRCreator(token="test_token")


def _mock_response(status_code: int, json_data: dict) -> MagicMock:
    m = MagicMock()
    m.status_code = status_code
    m.json.return_value = json_data
    m.raise_for_status.return_value = None
    return m


def test_get_default_branch_ok(creator):
    resp = _mock_response(200, {"default_branch": "main"})
    with patch.object(creator, "_request_with_retry", return_value=resp):
        assert creator.get_default_branch("owner/repo") == "main"


def test_get_default_branch_fallback(creator):
    resp = _mock_response(200, {})
    with patch.object(creator, "_request_with_retry", return_value=resp):
        assert creator.get_default_branch("owner/repo") == "main"


def test_get_branch_sha_ok(creator):
    resp = _mock_response(200, {"object": {"sha": "abc123"}})
    with patch.object(creator, "_request_with_retry", return_value=resp):
        sha = creator.get_branch_sha("owner/repo", "main")
    assert sha == "abc123"


def test_create_branch_ok(creator):
    with patch.object(creator, "_request_with_retry") as mock_req:
        mock_req.return_value = _mock_response(201, {"ref": "refs/heads/fix/test"})
        assert creator.create_branch("owner/repo", "fix/test", "abc123") is True


def test_create_branch_already_exists(creator):
    with patch.object(creator, "_request_with_retry") as mock_req:
        mock_req.side_effect = RuntimeError("422 already exists")
        assert creator.create_branch("owner/repo", "fix/test", "abc123") is True


def test_get_file_sha_ok(creator):
    resp = _mock_response(200, {"sha": "fileSHA456"})
    with patch.object(creator, "_request_with_retry", return_value=resp):
        sha = creator.get_file_sha("owner/repo", "src/foo.py", "fix/test")
    assert sha == "fileSHA456"


def test_get_file_sha_not_found(creator):
    with patch.object(creator, "_request_with_retry", side_effect=RuntimeError("404")):
        sha = creator.get_file_sha("owner/repo", "src/foo.py", "fix/test")
    assert sha is None


def test_update_file_ok(creator):
    with patch.object(creator, "_request_with_retry") as mock_req:
        mock_req.side_effect = [
            _mock_response(200, {"sha": "existingSHA"}),
            _mock_response(200, {"content": {}}),
        ]
        result = creator.update_file("owner/repo", "src/foo.py", "new content", "fix/test", "fix: auto")
    assert result is True


def test_update_file_new_file(creator):
    with patch.object(creator, "_request_with_retry") as mock_req:
        mock_req.side_effect = [
            RuntimeError("404"),
            _mock_response(201, {"content": {}}),
        ]
        result = creator.update_file("owner/repo", "src/new.py", "content", "fix/test", "add: file")
    assert result is True


def test_create_pull_request_ok(creator):
    resp = _mock_response(201, {"number": 42, "html_url": "https://github.com/owner/repo/pull/42"})
    with patch.object(creator, "_request_with_retry", return_value=resp):
        pr = creator.create_pull_request("owner/repo", "fix/test", "main", "[AutoFix] err", "body")
    assert pr["number"] == 42
    assert "pull/42" in pr["html_url"]


def test_create_fix_pr_full_flow(creator):
    with patch.object(creator, "get_branch_sha", return_value="baseSHA"), \
         patch.object(creator, "create_branch", return_value=True), \
         patch.object(creator, "update_file", return_value=True), \
         patch.object(creator, "create_pull_request", return_value={"number": 99, "html_url": "https://example.com/pr/99"}), \
         patch.object(creator, "add_labels") as mock_labels:

        result = creator.create_fix_pr(
            repo_full_name="owner/repo",
            file_path="src/bug.py",
            fixed_content="print('fixed')",
            base_branch="main",
            fix_branch="fix/auto-99",
            error_summary="ValueError in foo()",
        )

    mock_labels.assert_called_once_with("owner/repo", 99)
    assert result["pr_number"] == 99
    assert result["branch"] == "fix/auto-99"
    assert result["status"] == "created"


def test_create_fix_pr_returns_expected_keys(creator):
    with patch.object(creator, "get_branch_sha", return_value="sha"), \
         patch.object(creator, "create_branch", return_value=True), \
         patch.object(creator, "update_file", return_value=True), \
         patch.object(creator, "create_pull_request", return_value={"number": 1, "html_url": "https://url"}), \
         patch.object(creator, "add_labels"):

        result = creator.create_fix_pr("o/r", "f.py", "code", "main", "fix/1", "err")

    assert set(result.keys()) >= {"pr_number", "pr_url", "pr_title", "branch", "status"}
    assert result["status"] == "created"
