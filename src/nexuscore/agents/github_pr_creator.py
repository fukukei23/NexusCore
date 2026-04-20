"""
github_pr_creator.py

GitHub REST API を使ってDebuggerAgentが生成した修正パッチをPRとして自動作成するモジュール。
PyGithub は使わず requests のみに依存する。
"""

from __future__ import annotations

import base64
import logging
from typing import Any

import requests

logger = logging.getLogger(__name__)


class GitHubPRCreator:
    """GitHub REST API でパッチ含む PR を自動生成する。"""

    GITHUB_API_BASE = "https://api.github.com"

    def __init__(self, token: str) -> None:
        self.token = token
        self.headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
            "Content-Type": "application/json",
        }

    def get_default_branch(self, repo_full_name: str) -> str:
        """リポジトリのデフォルトブランチ名を取得する。"""
        url = f"{self.GITHUB_API_BASE}/repos/{repo_full_name}"
        resp = requests.get(url, headers=self.headers, timeout=30)
        resp.raise_for_status()
        return str(resp.json().get("default_branch", "main"))

    def get_branch_sha(self, repo_full_name: str, branch: str) -> str:
        """指定ブランチの最新コミット SHA を取得する。"""
        url = f"{self.GITHUB_API_BASE}/repos/{repo_full_name}/git/ref/heads/{branch}"
        resp = requests.get(url, headers=self.headers, timeout=30)
        resp.raise_for_status()
        return str(resp.json()["object"]["sha"])

    def create_branch(self, repo_full_name: str, new_branch: str, base_sha: str) -> bool:
        """新しいブランチを作成する。既存ブランチ（422）はスキップして True を返す。"""
        url = f"{self.GITHUB_API_BASE}/repos/{repo_full_name}/git/refs"
        data = {"ref": f"refs/heads/{new_branch}", "sha": base_sha}
        resp = requests.post(url, json=data, headers=self.headers, timeout=30)
        if resp.status_code == 422:
            logger.warning("Branch '%s' already exists, continuing.", new_branch)
            return True
        resp.raise_for_status()
        logger.info("Created branch '%s' from SHA %s", new_branch, base_sha[:7])
        return True

    def get_file_sha(self, repo_full_name: str, file_path: str, branch: str) -> str | None:
        """ファイルの blob SHA を取得する。ファイルが存在しない場合は None を返す。"""
        url = f"{self.GITHUB_API_BASE}/repos/{repo_full_name}/contents/{file_path}"
        resp = requests.get(url, headers=self.headers, params={"ref": branch}, timeout=30)
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return resp.json().get("sha")

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

        resp = requests.put(url, json=data, headers=self.headers, timeout=30)
        resp.raise_for_status()
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
        resp = requests.post(url, json=data, headers=self.headers, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def create_fix_pr(
        self,
        repo_full_name: str,
        file_path: str,
        fixed_content: str,
        base_branch: str,
        fix_branch: str,
        error_summary: str,
    ) -> dict[str, Any]:
        """
        DebuggerAgent が生成した修正コードを GitHub PR として自動作成する。

        フロー: ブランチ作成 -> ファイル更新コミット -> PR 作成

        Returns:
            {"pr_number": int, "pr_url": str, "pr_title": str, "branch": str, "status": "created"}
        """
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

        return {
            "pr_number": pr.get("number"),
            "pr_url": pr.get("html_url"),
            "pr_title": pr_title,
            "branch": fix_branch,
            "status": "created",
        }
