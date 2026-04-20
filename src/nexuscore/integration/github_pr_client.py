"""
GitHub PR 自動生成クライアント

Self-Healing パイプラインで修正パッチを適用後、
自動的にブランチ作成→コミット→PR作成を行う。
"""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from typing import Any

logger = logging.getLogger(__name__)

GITHUB_API_URL = "https://api.github.com"


class GitHubPRClient:
    """GitHub REST API 経由でブランチ・コミット・PR を操作するクライアント。"""

    def __init__(self, token: str, repo_full_name: str) -> None:
        self.token = token
        self.repo_full_name = repo_full_name
        self.base_headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "NexusCore/1.0",
        }

    def _request(
        self, method: str, path: str, data: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        url = f"{GITHUB_API_URL}/repos/{self.repo_full_name}{path}"
        req = urllib.request.Request(url, method=method, headers=self.base_headers)
        if data is not None:
            req.data = json.dumps(data).encode("utf-8")
            req.add_header("Content-Type", "application/json")

        try:
            with urllib.request.urlopen(req) as resp:
                return json.loads(resp.read().decode("utf-8"))  # type: ignore[no-any-return]
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8")
            raise RuntimeError(
                f"GitHub API error {e.code} on {method} {path}: {error_body}"
            ) from e

    # ------------------------------------------------------------------
    # 低レベル操作
    # ------------------------------------------------------------------

    def create_branch(self, branch_name: str, base_sha: str) -> dict[str, Any]:
        """指定 SHA を起点にブランチを作成する。"""
        return self._request(
            "POST",
            "/git/refs",
            {"ref": f"refs/heads/{branch_name}", "sha": base_sha},
        )

    def get_branch_sha(self, branch_name: str) -> str:
        """ブランチの最新コミット SHA を取得する。"""
        ref = self._request("GET", f"/git/ref/heads/{branch_name}")
        return ref["object"]["sha"]  # type: ignore[no-any-return]

    def commit_files(
        self,
        branch_name: str,
        message: str,
        files: dict[str, str],
        author_name: str = "NexusCore Bot",
        author_email: str = "bot@nexuscore.dev",
    ) -> dict[str, Any]:
        """複数ファイルを一度にコミットする（blob→tree→commit→ref更新）。"""
        head_sha = self.get_branch_sha(branch_name)
        head_commit = self._request("GET", f"/git/commits/{head_sha}")
        base_tree = head_commit["tree"]["sha"]

        blobs: list[dict[str, Any]] = []
        for path, content in files.items():
            blob = self._request(
                "POST", "/git/blobs", {"content": content, "encoding": "utf-8"}
            )
            blobs.append(
                {"path": path, "mode": "100644", "type": "blob", "sha": blob["sha"]}
            )

        tree = self._request(
            "POST", "/git/trees", {"base_tree": base_tree, "tree": blobs}
        )
        commit = self._request(
            "POST",
            "/git/commits",
            {
                "message": message,
                "tree": tree["sha"],
                "parents": [head_sha],
                "author": {"name": author_name, "email": author_email},
            },
        )
        self._request(
            "PATCH", f"/git/refs/heads/{branch_name}", {"sha": commit["sha"]}
        )
        return commit

    def create_pull_request(
        self, title: str, body: str, head: str, base: str = "main"
    ) -> dict[str, Any]:
        """PR を作成する。"""
        return self._request(
            "POST", "/pulls", {"title": title, "body": body, "head": head, "base": base}
        )

    # ------------------------------------------------------------------
    # 高レベル操作（オーケストレーション）
    # ------------------------------------------------------------------

    def auto_create_fix_pr(
        self,
        *,
        branch_name: str,
        base_branch: str,
        commit_message: str,
        pr_title: str,
        pr_body: str,
        files: dict[str, str],
    ) -> dict[str, Any]:
        """
        ブランチ作成 → コミット → PR作成 を一括実行する。

        Args:
            branch_name: 新規ブランチ名
            base_branch: ベースブランチ（通常 "main"）
            commit_message: コミットメッセージ
            pr_title: PR タイトル
            pr_body: PR 本文
            files: {ファイルパス: ファイル内容}

        Returns:
            {"pr_number": int, "pr_url": str, "branch": str}
        """
        base_sha = self.get_branch_sha(base_branch)
        self.create_branch(branch_name, base_sha)
        self.commit_files(branch_name, commit_message, files)
        pr = self.create_pull_request(pr_title, pr_body, branch_name, base_branch)

        result = {
            "pr_number": pr["number"],
            "pr_url": pr["html_url"],
            "branch": branch_name,
        }
        logger.info(
            f"Auto-created fix PR #{pr['number']}: {pr['html_url']} "
            f"({branch_name} → {base_branch})"
        )
        return result
