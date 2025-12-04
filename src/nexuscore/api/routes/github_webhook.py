"""
GitHub Webhook エンドポイント

GitHub pull_request Webhook を受信して Self-Healing Service を実行するエンドポイント。
既存の Flask 実装 (`src/nexuscore/api/github_webhook_handler.py`) と互換性を保つ。

注意: このエンドポイントは GitHub Webhook の署名認証（X-Hub-Signature-256）のみを使用し、
API Key 認証（X-API-Key）は使用しません。これは GitHub Webhook の標準的な実装パターンです。
"""
import hashlib
import hmac
import logging
import os
from typing import Optional

from fastapi import APIRouter, Header, HTTPException, Request, status

from ..schemas.error import ErrorResponse
from ..schemas.github_webhook import GitHubWebhookPayload, GitHubWebhookResponse
from ..utils.errors import make_bad_request_error, make_unauthorized_error

router = APIRouter(
    prefix="/api/v1/github",
    tags=["github", "webhook"],
)

logger = logging.getLogger(__name__)


def verify_github_signature(
    payload_body: bytes,
    signature_header: Optional[str],
    secret: Optional[str],
) -> bool:
    """
    GitHub Webhook の署名を検証する

    GitHub Webhook は `X-Hub-Signature-256` ヘッダーを使用して署名検証を行う。
    形式: `sha256=<hex_digest>`

    Args:
        payload_body: リクエストボディ（bytes）
        signature_header: X-Hub-Signature-256 ヘッダーの値
        secret: GitHub Webhook Secret（環境変数から取得）

    Returns:
        bool: 署名が有効な場合 True
    """
    if not secret:
        # シークレットが設定されていない場合は検証をスキップ（開発環境など）
        logger.warning("GITHUB_WEBHOOK_SECRET is not set. Skipping signature verification.")
        return True

    if not signature_header:
        logger.warning("X-Hub-Signature-256 header is missing.")
        return False

    # ヘッダーの形式: "sha256=<hex_digest>"
    if not signature_header.startswith("sha256="):
        logger.warning(f"Invalid signature format: {signature_header}")
        return False

    # 署名を抽出
    received_signature = signature_header[7:]  # "sha256=" を除去

    # 期待される署名を計算
    expected_signature = hmac.new(
        secret.encode("utf-8"),
        payload_body,
        hashlib.sha256,
    ).hexdigest()

    # タイミング攻撃を防ぐために hmac.compare_digest を使用
    return hmac.compare_digest(received_signature, expected_signature)


@router.post(
    "/webhook",
    response_model=GitHubWebhookResponse,
    summary="GitHub Webhook endpoint",
    status_code=status.HTTP_200_OK,
    responses={
        400: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
async def github_webhook_endpoint(
    request: Request,
    x_github_event: Optional[str] = Header(None, alias="X-GitHub-Event"),
    x_github_delivery: Optional[str] = Header(None, alias="X-GitHub-Delivery"),
    x_hub_signature_256: Optional[str] = Header(None, alias="X-Hub-Signature-256"),
) -> GitHubWebhookResponse:
    """
    GitHub Webhook エンドポイント

    GitHub pull_request イベントを受信して Self-Healing Service を実行する。
    既存の Flask 実装 (`handle_github_webhook`) と互換性を保つ。

    Args:
        request: FastAPI Request オブジェクト（ボディ取得用）
        x_github_event: X-GitHub-Event ヘッダー
        x_github_delivery: X-GitHub-Delivery ヘッダー
        x_hub_signature_256: X-Hub-Signature-256 ヘッダー（署名検証用）

    Returns:
        GitHubWebhookResponse: Webhook処理結果

    Raises:
        HTTPException: 署名検証失敗時（401）または内部エラー時（500）
    """
    event = x_github_event or "unknown"
    delivery = x_github_delivery or "unknown"

    logger.info(f"GitHub webhook received: event={event} delivery={delivery}")

    # イベントタイプの確認（pull_request のみ処理）
    if event != "pull_request":
        logger.info(f"Ignoring non-pull_request event: {event}")
        return GitHubWebhookResponse(
            accepted=False,
            reason=f"Event type '{event}' is not supported. Only 'pull_request' is handled.",
        )

    # リクエストボディを取得
    try:
        payload_body = await request.body()
        if not payload_body:
            return GitHubWebhookResponse(
                accepted=False,
                reason="Invalid payload: JSON is required",
            )
    except Exception as e:
        logger.error(f"Failed to read request body: {e}", exc_info=True)
        raise make_bad_request_error("Failed to read request body")

    # 署名検証（オプション）
    webhook_secret = os.getenv("GITHUB_WEBHOOK_SECRET")
    if webhook_secret:
        if not verify_github_signature(payload_body, x_hub_signature_256, webhook_secret):
            logger.warning(f"Invalid signature for delivery {delivery}")
            raise make_unauthorized_error("Invalid signature")

    # JSON ペイロードをパース
    try:
        import json
        payload_dict = json.loads(payload_body.decode("utf-8"))
        payload = GitHubWebhookPayload(**payload_dict)
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON payload: {e}", exc_info=True)
        return GitHubWebhookResponse(
            accepted=False,
            reason="Invalid payload: JSON is required",
        )
    except Exception as e:
        logger.error(f"Failed to parse payload: {e}", exc_info=True)
        return GitHubWebhookResponse(
            accepted=False,
            reason=f"Failed to parse payload: {str(e)}",
        )

    # Self-Healing を実行
    try:
        from nexuscore.api.github_self_healing_webhook import github_webhook

        result = github_webhook(
            payload=payload_dict,  # Pydanticモデルではなく、元のdictを渡す（既存実装との互換性）
            project_root=None,  # 環境変数から取得
            event=event,
            delivery=delivery,
        )

        # PR コメント投稿（オプション）
        _post_pr_comment_if_configured(result, payload_dict)

        # Slack 通知送信（オプション）
        _send_slack_notification_if_configured(result, payload_dict)

        # レスポンスを構築
        return GitHubWebhookResponse(
            accepted=True,
            result=result,
            status=result.get("status"),
            summary=result.get("summary"),
        )

    except ImportError as e:
        logger.error(f"GitHub webhook handler is not available: {e}", exc_info=True)
        raise make_internal_error("GitHub webhook handler not available")
    except Exception as e:
        logger.error(f"GitHub webhook handling failed: {e}", exc_info=True)
        return GitHubWebhookResponse(
            accepted=False,
            error=str(e),
        )


def _post_pr_comment_if_configured(result: dict, payload: dict) -> None:
    """
    GITHUB_SELF_HEALING_TOKEN が設定されていれば、PR にコメントを投稿する。

    既存の Flask 実装 (`_post_pr_comment_if_configured`) と同じロジック。
    """
    token = os.getenv("GITHUB_SELF_HEALING_TOKEN")
    if not token:
        logger.debug("GITHUB_SELF_HEALING_TOKEN not set. Skipping PR comment.")
        return

    try:
        from nexuscore.api.github_self_healing_webhook import format_pr_comment

        repo_full_name = payload.get("repository", {}).get("full_name")
        pr_number = payload.get("pull_request", {}).get("number")

        if not repo_full_name or not pr_number:
            logger.warning("Cannot post PR comment: missing repo_full_name or pr_number")
            return

        # プロジェクトルートを取得（環境変数から）
        project_root = os.getenv("NEXUS_PROJECT_ROOT", os.getcwd())
        comment_body = format_pr_comment(
            result,
            project_root=project_root,
            repo_full_name=repo_full_name,
            pr_number=pr_number,
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

    except Exception as e:
        # PR コメント投稿失敗は致命的ではないのでログだけ
        logger.error(f"Failed to post PR comment: {e}", exc_info=True)


def _send_slack_notification_if_configured(result: dict, payload: dict) -> None:
    """
    NEXUS_SLACK_WEBHOOK_URL が設定されていれば、Slack に通知を送信する。

    既存の Flask 実装 (`_send_slack_notification_if_configured`) と同じロジック。
    """
    webhook_url = os.getenv("NEXUS_SLACK_WEBHOOK_URL")
    if not webhook_url:
        logger.debug("NEXUS_SLACK_WEBHOOK_URL not set. Skipping Slack notification.")
        return

    try:
        from nexuscore.core.notifier import SlackNotifier
        try:
            from nexuscore.integration.github_pr_comment import _collect_run_metrics, _compute_recent_success_rate
        except ImportError:
            # フォールバック: run_report_generator からインポート
            from nexuscore.integration.run_report_generator import _collect_run_metrics, _compute_recent_success_rate

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
            from nexuscore.webapp.models import Run, Project
            from nexuscore.webapp import db

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
        except Exception as e:
            logger.warning(f"Failed to collect metrics for Slack notification: {e}", exc_info=True)

        # PR URL と Run ログ URL を構築
        pr_url = f"https://github.com/{repo_full_name}/pull/{pr_number}" if repo_full_name and pr_number else None

        run_logs_url = None
        if run and run.run_id:
            try:
                from nexuscore.config.config import AppConfig
                base_url = AppConfig.WEBAPP_BASE_URL.rstrip("/")
                run_logs_url = f"{base_url}/logs/runs/{run.run_id}"
            except Exception as e:
                logger.warning(f"Failed to build run_logs_url: {e}", exc_info=True)

        # Slack 通知を送信
        notifier = SlackNotifier(webhook_url=webhook_url)

        status_value = result.get("status", "unknown")
        summary = result.get("summary", "Self-Healing execution completed")
        run_id_str = run_id if run_id else result.get("run_id", "unknown")

        success = notifier.notify_self_healing_complete(
            repo_full_name=repo_full_name,
            pr_number=pr_number,
            status=status_value,
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
            logger.warning(f"Failed to send Slack notification for {repo_full_name} PR #{pr_number}")

    except Exception as e:
        # Slack 通知失敗は致命的ではないのでログだけ
        logger.error(f"Failed to send Slack notification: {e}", exc_info=True)

