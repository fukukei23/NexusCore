"""
github_webhook_handler.py

Flask サーバで GitHub Webhook を受信するエンドポイント。

/api/github/webhook に POST リクエストが来たら、
github_self_healing_webhook.github_webhook() を呼び出す。
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from flask import request

from nexuscore.api.github_self_healing_webhook import github_webhook

logger = logging.getLogger(__name__)


def handle_github_webhook() -> Dict[str, Any]:
    """
    Flask の /api/github/webhook エンドポイントから呼び出される。

    GitHub Webhook のペイロードを受け取り、Self-Healing を実行する。
    """
    event = request.headers.get("X-GitHub-Event", "unknown")
    delivery = request.headers.get("X-GitHub-Delivery", "unknown")

    if event != "pull_request":
        logger.info(f"Ignoring non-pull_request event: {event}")
        return {
            "accepted": False,
            "reason": f"Event type '{event}' is not supported. Only 'pull_request' is handled.",
        }

    try:
        payload = request.get_json()
        if not payload:
            return {
                "accepted": False,
                "reason": "Invalid payload: JSON is required",
            }, 400

        # Self-Healing を実行
        result = github_webhook(
            payload=payload,
            project_root=None,  # 環境変数から取得
            event=event,
            delivery=delivery,
        )

        # PR コメント投稿（オプション）
        _post_pr_comment_if_configured(result, payload)

        return {
            "accepted": True,
            "result": result,
        }

    except Exception as e:
        logger.error(f"GitHub webhook handling failed: {e}", exc_info=True)
        return {
            "accepted": False,
            "error": str(e),
        }, 500


def _post_pr_comment_if_configured(result: Dict[str, Any], payload: Dict[str, Any]) -> None:
    """
    GITHUB_SELF_HEALING_TOKEN が設定されていれば、PR にコメントを投稿する。
    """
    import os

    token = os.getenv("GITHUB_SELF_HEALING_TOKEN")
    if not token:
        logger.debug("GITHUB_SELF_HEALING_TOKEN not set. Skipping PR comment.")
        return

        try:
            import os
            from nexuscore.api.github_self_healing_webhook import format_pr_comment

            repo_full_name = payload.get("repository", {}).get("full_name")
            pr_number = payload.get("pull_request", {}).get("number")

            if not repo_full_name or not pr_number:
                logger.warning("Cannot post PR comment: missing repo_full_name or pr_number")
                return

            # プロジェクトルートを取得（環境変数から）
            project_root = os.getenv("NEXUS_PROJECT_ROOT", os.getcwd())
            comment_body = format_pr_comment(result, project_root=project_root)

        # GitHub API で PR コメントを投稿
        import requests

        url = f"https://api.github.com/repos/{repo_full_name}/issues/{pr_number}/comments"
        headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
        }
        data = {"body": comment_body}

        resp = requests.post(url, headers=headers, json=data, timeout=30)
        resp.raise_for_status()

        logger.info(f"Posted PR comment to {repo_full_name}#{pr_number}")

    except Exception as e:
        # PR コメント投稿失敗は致命的ではないのでログだけ
        logger.error(f"Failed to post PR comment: {e}", exc_info=True)

