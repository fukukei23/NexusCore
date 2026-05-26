from __future__ import annotations

import base64
import difflib
import logging
import time
from typing import Any

import requests

logger = logging.getLogger(__name__)

MAX_DIFF_LINES = 1000
MAX_RETRIES = 3
AUTO_LABELS = ["autofix", "debugger-agent"]


class GitHubPRCreator:
    """GitHub REST API でパッチ含む PR を自動生成する。"""

    GITHUB_API_BASE = "https://api.github.com"

    def __init__(self, token: str, max_diff_lines: int = MAX_DIFF_LINES) -> None:
        self.token = token
        self.max_diff_lines = max_diff_lines
        self.headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
            "Content-Type": "application/json",
        }

    def _request_with_retry(self, method: str, url: str, **kwargs: Any) -> requests.Response:
        """exponential backoff 付きリクエスト（最大 MAX_RETRIES 回）。"""
        kwargs.setdefault("timeout", 30)
        last_exc: Exception | None = None
        for attempt in range(MAX_RETRIES):
            try:
                resp = requests.request(method, url, headers=self.headers, **kwargs)
                resp.raise_for_status()
                return resp
            except requests.RequestException as exc:
                last_exc = exc
                if attempt < MAX_RETRIES - 1:
                    wait = 2 ** attempt
                    logger.warning("API %s %s failed (attempt %d/%d), retrying in %ds: %s",
                                   method, url, attempt + 1, MAX_RETRIES, wait, exc)
                    time.sleep(wait)
        raise RuntimeError(f"API call failed after {MAX_RETRIES} retries: {last_exc}") from last_exc

    @staticmethod
    def validate_diff_size(diff_text: str, max_lines: int = MAX_DIFF_LINES) -> bool:
        """差分行数が制限内か検証する。"""
        return len(diff_text.splitlines()) <= max_lines

    def add_labels(self, repo_full_name: str, issue_number: int, labels: list[str] | None = None) -> bool:
        """Issue/PR にラベルを付与する。"""
        labels = labels or AUTO_LABELS
        url = f"{self.GITHUB_API_BASE}/repos/{repo_full_name}/issues/{issue_number}/labels"
        self._request_with_retry("POST", url, json={"labels": labels})
        logger.info("Added labels %s to #%d", labels, issue_number)
        return True

    def get_default_branch(self, repo_full_name: str) -> str:
        """リポジトリのデフォルトブランチ名を取得する。"""
        url = f"{self.GITHUB_API_BASE}/repos/{repo_full_name}"
        resp = self._request_with_retry("GET", url)
        return str(resp.json().get("default_branch", "main"))

    def get_branch_sha(self, repo_full_name: str, branch: str) -> str:
        """指定ブランチの最新コミット SHA を取得する。"""
        url = f"{self.GITHUB_API_BASE}/repos/{repo_full_name}/git/ref/heads/{branch}"
        resp = self._request_with_retry("GET", url)
        return str(resp.json()["object"]["sha"])

    def create_branch(self, repo_full_name: str, new_branch: str, base_sha: str) -> bool:
        """新しいブランチを作成する。既存ブランチ（422）はスキップして True を返す。"""
        url = f"{self.GITHUB_API_BASE}/repos/{repo_full_name}/git/refs"
        data = {"ref": f"refs/heads/{new_branch}", "sha": base_sha}
        try:
            self._request_with_retry("POST", url, json=data)
            logger.info("Created branch '%s' from SHA %s", new_branch, base_sha[:7])
        except RuntimeError:
            logger.warning("Branch '%s' may already exist, continuing.", new_branch)
        return True

    def get_file_sha(self, repo_full_name: str, file_path: str, branch: str) -> str | None:
        """ファイルの blob SHA を取得する。ファイルが存在しない場合は None を返す。"""
        url = f"{self.GITHUB_API_BASE}/repos/{repo_full_name}/contents/{file_path}"
        try:
            resp = self._request_with_retry("GET", url, params={"ref": branch})
            return resp.json().get("sha")
        except RuntimeError:
            return None

    def update_file(
        self,
        repo_full_name: str,
        file_path: str,
        content: str,
        branch: str,
        commit_message: str,
    ) -> bool:
        """ファイルを base64 エンコードして GitHub Contents API で更新する。"""
        url = f"{self.GITHUB_API_BASE}/repos/{repo_full_name}/contents/{file_path}"
        encoded = base64.b64encode(content.encode("utf-8")).decode("utf-8")
        file_sha = self.get_file_sha(repo_full_name, file_path, branch)

        data: dict[str, Any] = {
            "message": commit_message,
            "content": encoded,
            "branch": branch,
        }
        if file_sha:
            data["sha"] = file_sha

        self._request_with_retry("PUT", url, json=data)
        logger.info("Updated '%s' on branch '%s'", file_path, branch)
        return True

    def create_pull_request(
        self,
        repo_full_name: str,
        head_branch: str,
        base_branch: str,
        title: str,
        body: str,
    ) -> dict[str, Any]:
        """PR を作成して GitHub API のレスポンスを返す。"""
        url = f"{self.GITHUB_API_BASE}/repos/{repo_full_name}/pulls"
        data = {
            "title": title,
            "body": body,
            "head": head_branch,
            "base": base_branch,
        }
        resp = self._request_with_retry("POST", url, json=data)
        return resp.json()

    def create_fix_pr(
        self,
        repo_full_name: str,
        file_path: str,
        fixed_content: str,
        base_branch: str,
        fix_branch: str,
        error_summary: str,
        original_content: str | None = None,
    ) -> dict[str, Any]:
        """
        DebuggerAgent が生成した修正コードを GitHub PR として自動作成する。

        フロー: 差分バリデーション -> ブランチ作成 -> ファイル更新コミット -> PR 作成 -> ラベル付与

        Returns:
            {"pr_number": int, "pr_url": str, "pr_title": str, "branch": str, "status": "created"}
        """
        if original_content is not None:
            diff_lines = list(difflib.unified_diff(
                original_content.splitlines(keepends=True),
                fixed_content.splitlines(keepends=True),
                fromfile=f"a/{file_path}",
                tofile=f"b/{file_path}",
            ))
            if not diff_lines:
                return {"status": "skipped", "reason": "no_changes"}
            if not self.validate_diff_size("".join(diff_lines), self.max_diff_lines):
                return {"status": "skipped", "reason": "diff_too_large"}

        base_sha = self.get_branch_sha(repo_full_name, base_branch)
        self.create_branch(repo_full_name, fix_branch, base_sha)

        commit_message = f"fix: DebuggerAgent自動修正 - {error_summary[:72]}"
        self.update_file(
            repo_full_name=repo_full_name,
            file_path=file_path,
            content=fixed_content,
            branch=fix_branch,
            commit_message=commit_message,
        )

        pr_title = f"[AutoFix] {error_summary[:60]}"
        pr_body = (
            "## 自動修正PR\n\n"
            "NexusCore **DebuggerAgent** が生成した修正パッチです。\n\n"
            f"### エラーサマリー\n```\n{error_summary[:500]}\n```\n\n"
            "### 変更ファイル\n"
            f"- `{file_path}`\n\n"
            "---\n"
            "_このPRはNexusCore DebuggerAgentによって自動生成されました。"
            "マージ前に内容を確認してください。_"
        )

        pr = self.create_pull_request(
            repo_full_name=repo_full_name,
            head_branch=fix_branch,
            base_branch=base_branch,
            title=pr_title,
            body=pr_body,
        )

        pr_number = pr.get("number")
        if pr_number:
            try:
                self.add_labels(repo_full_name, pr_number)
            except Exception:  # noqa: BLE001 — ラベル追加失敗はPR作成を止めない
                logger.warning("Label addition failed for PR #%d, continuing.", pr_number)

        return {
            "pr_number": pr_number,
            "pr_url": pr.get("html_url"),
            "pr_title": pr_title,
            "branch": fix_branch,
            "status": "created",
        }
