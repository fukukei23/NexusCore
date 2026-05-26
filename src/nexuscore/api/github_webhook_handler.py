from __future__ import annotations

import logging
from typing import Any

from nexuscore.api.github_self_healing_webhook import github_webhook

logger = logging.getLogger(__name__)


def handle_github_webhook() -> dict[str, Any]:
    """
    Flask の /api/github/webhook エンドポイントから呼び出される。

    GitHub Webhook のペイロードを受け取り、Self-Healing を実行する。
    """
    from flask import request

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
            return {  # type: ignore[return-value]
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

        # Slack 通知送信（オプション）
        _send_slack_notification_if_configured(result, payload)

        return {
            "accepted": True,
            "result": result,
        }

    except Exception as e:  # noqa: BLE001
        logger.error(f"GitHub webhook handling failed: {e}", exc_info=True)
        return {  # type: ignore[return-value]
            "accepted": False,
            "error": str(e),
        }, 500


def _post_pr_comment_if_configured(result: dict[str, Any], payload: dict[str, Any]) -> None:
    """
    GITHUB_SELF_HEALING_TOKEN が設定されていれば、PR にコメントを投稿する。
    """
    import os

    token = os.getenv("GITHUB_SELF_HEALING_TOKEN")
    if not token:
        logger.debug("GITHUB_SELF_HEALING_TOKEN not set. Skipping PR comment.")
        return

    try:
        from nexuscore.api.github_self_healing_webhook import format_pr_comment

        repo_full_name = payload.get("repository", {}).get("full_name")
        pr_number = payload.get("pull_request", {}).get("number")
        # CR-E3: commit_sha を取得
        commit_sha = payload.get("pull_request", {}).get("head", {}).get("sha")

        if not repo_full_name or not pr_number:
            logger.warning("Cannot post PR comment: missing repo_full_name or pr_number")
            return

        # repo_full_name の形式を検証（"owner/repo" のみ許可）
        if "/" not in repo_full_name or repo_full_name.startswith("/") or repo_full_name.endswith("/"):
            logger.warning(f"Invalid repo_full_name format: {repo_full_name}")
            return

        # プロジェクトルートを取得（環境変数から）
        project_root = os.getenv("NEXUS_PROJECT_ROOT", os.getcwd())
        comment_body = format_pr_comment(
            result,
            project_root=project_root,
            repo_full_name=repo_full_name,
            pr_number=pr_number,
            commit_sha=commit_sha,  # CR-E3
        )

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

    except Exception as e:  # noqa: BLE001
        # PR コメント投稿失敗は致命的ではないのでログだけ
        logger.error(f"Failed to post PR comment: {e}", exc_info=True)


def _send_slack_notification_if_configured(result: dict[str, Any], payload: dict[str, Any]) -> None:
    """
    NEXUS_SLACK_WEBHOOK_URL が設定されていれば、Slack に通知を送信する。
    """
    import os

    webhook_url = os.getenv("NEXUS_SLACK_WEBHOOK_URL")
    if not webhook_url:
        logger.debug("NEXUS_SLACK_WEBHOOK_URL not set. Skipping Slack notification.")
        return

    try:
        from nexuscore.core.notifier import SlackNotifier

        try:
            from nexuscore.integration.github_pr_comment import (
                _collect_run_metrics,
                _compute_recent_success_rate,
            )
        except ImportError:
            # フォールバック: run_report_generator からインポート
            from nexuscore.integration.run_report_generator import (
                _collect_run_metrics,
                _compute_recent_success_rate,
            )

        repo_full_name = payload.get("repository", {}).get("full_name")
        pr_number = payload.get("pull_request", {}).get("number")

        if not repo_full_name or not pr_number:
            logger.warning("Cannot send Slack notification: missing repo_full_name or pr_number")
            return

        # Run と Project を取得（メトリクス収集用）
        run = None
        project = None
        metrics = None

        try:
            from nexuscore.webapp.models import Run

            # result から run_id を取得（run_id が含まれている場合）
            run_id = result.get("run_id") or result.get("details", {}).get("run_id")
            if run_id:
                # run_id で検索（run_id は文字列、id は整数）
                run = Run.query.filter_by(run_id=run_id).first()
                if run:
                    project = run.project
                    metrics = _collect_run_metrics(run)
                    if project:
                        metrics["success_rate"] = _compute_recent_success_rate(project.id, limit=30)
        except Exception as e:  # noqa: BLE001
            logger.warning(f"Failed to collect metrics for Slack notification: {e}", exc_info=True)

        # PR URL と Run ログ URL を構築
        pr_url = (
            f"https://github.com/{repo_full_name}/pull/{pr_number}"
            if repo_full_name and pr_number
            else None
        )

        run_logs_url = None
        if run and run.run_id:
            try:
                from nexuscore.config.unified_config import get_config as _get_config

                base_url = _get_config().webapp_base_url.rstrip("/")
                run_logs_url = f"{base_url}/logs/runs/{run.run_id}"
            except Exception as e:  # noqa: BLE001
                logger.warning(f"Failed to build run_logs_url: {e}", exc_info=True)

        # Slack 通知を送信
        notifier = SlackNotifier(webhook_url=webhook_url)

        status = result.get("status", "unknown")
        summary = result.get("summary", "Self-Healing execution completed")
        run_id_str = run_id if run_id else result.get("run_id", "unknown")

        success = notifier.notify_self_healing_complete(
            repo_full_name=repo_full_name,
            pr_number=pr_number,
            status=status,
            summary=summary,
            run_id=run_id_str,
            details={
                "リポジトリ": repo_full_name,
                "PR番号": str(pr_number),
            },
            metrics=metrics,
            pr_url=pr_url,
            run_logs_url=run_logs_url,
        )

        if success:
            logger.info(f"Sent Slack notification for {repo_full_name} PR #{pr_number}")
        else:
            logger.warning(
                f"Failed to send Slack notification for {repo_full_name} PR #{pr_number}"
            )

    except Exception as e:  # noqa: BLE001
        # Slack 通知失敗は致命的ではないのでログだけ
        logger.error(f"Failed to send Slack notification: {e}", exc_info=True)
