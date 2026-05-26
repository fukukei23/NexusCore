from __future__ import annotations

import logging
import os
from typing import Any

try:
    import requests

    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False


logger = logging.getLogger(__name__)


class SlackNotifier:
    """
    Slack Incoming Webhook を使用して通知を送信するクラス。

    AndroidスマホでもSlackアプリをインストールしていれば通知を受信できます。
    """

    def __init__(self, webhook_url: str | None = None) -> None:
        """
        :param webhook_url: Slack Incoming Webhook URL
                           省略時は環境変数 NEXUS_SLACK_WEBHOOK_URL から取得
        """
        self.webhook_url = webhook_url or os.getenv("NEXUS_SLACK_WEBHOOK_URL")
        self.enabled = bool(self.webhook_url) and HAS_REQUESTS

        if not HAS_REQUESTS:
            logger.warning(
                "requestsライブラリがインストールされていません。Slack通知は無効になります。"
                "インストール: pip install requests"
            )
        elif not self.webhook_url:
            logger.info("NEXUS_SLACK_WEBHOOK_URLが設定されていません。Slack通知は無効になります。")

    def send(
        self,
        *,
        title: str,
        message: str,
        status: str = "info",
        details: dict[str, Any] | None = None,
        color: str | None = None,
    ) -> bool:
        """
        Slackに通知を送信する。

        :param title: 通知のタイトル
        :param message: 通知の本文
        :param status: ステータス（"success", "error", "warning", "info"）
        :param details: 追加の詳細情報（辞書形式）
        :param color: カラーコード（例: "#36a64f" は緑、"#ff0000" は赤）
        :return: 送信成功時True、失敗時False
        """
        if not self.enabled:
            return False

        # ステータスに応じたデフォルトカラー
        if color is None:
            color_map = {
                "success": "#36a64f",  # 緑
                "error": "#ff0000",  # 赤
                "warning": "#ffaa00",  # オレンジ
                "info": "#36a64f",  # 青（Slackのデフォルト）
            }
            color = color_map.get(status, "#36a64f")

        # ステータスの日本語マッピング
        status_jp = {
            "success": "成功",
            "error": "エラー",
            "warning": "警告",
            "info": "情報",
        }
        status_text = status_jp.get(status, status.upper())

        # Slackのメッセージ形式（Attachments形式）
        payload: dict[str, Any] = {
            "text": title,
            "attachments": [
                {
                    "color": color,
                    "fields": [
                        {
                            "title": "ステータス",
                            "value": status_text,
                            "short": True,
                        },
                        {
                            "title": "メッセージ",
                            "value": message,
                            "short": False,
                        },
                    ],
                }
            ],
        }

        # 詳細情報があれば追加
        if details:
            details_text = "\n".join(f"• {k}: {v}" for k, v in details.items() if v is not None)
            if details_text:
                payload["attachments"][0]["fields"].append(
                    {
                        "title": "詳細",
                        "value": details_text[:1000],  # Slackの制限に合わせて切り詰め
                        "short": False,
                    }
                )

        try:
            response = requests.post(
                self.webhook_url,  # type: ignore[arg-type]
                json=payload,
                timeout=10,
            )
            response.raise_for_status()
            logger.info(f"Slack通知を送信しました: {title}")
            return True
        except Exception as e:  # noqa: BLE001 — HTTP/network errors from requests library (optional dep)
            logger.error(f"Slack通知の送信に失敗しました: {e}", exc_info=True)
            return False

    def notify_self_healing_complete(
        self,
        *,
        repo_full_name: str,
        pr_number: int,
        status: str,
        summary: str,
        run_id: str,
        details: dict[str, Any] | None = None,
        metrics: dict[str, Any] | None = None,
        pr_url: str | None = None,
        run_logs_url: str | None = None,
    ) -> bool:
        """
        Self-Healing実行完了通知を送信する。

        :param repo_full_name: リポジトリ名（例: "owner/repo"）
        :param pr_number: PR番号
        :param status: ステータス（"fixed", "not_fixed", "no_issues", "error"）
        :param summary: サマリー
        :param run_id: 実行ID
        :param details: 追加の詳細情報
        :param metrics: メトリクス情報（duration, patches, models, cost, success_rate など）
        :param pr_url: PR URL（例: https://github.com/owner/repo/pull/123）
        :param run_logs_url: Run ログ URL（例: https://your-nexuscore-host/logs/runs/abcd1234）
        :return: 送信成功時True
        """
        # ステータスに応じたタイトルとメッセージ
        status_emoji = {
            "fixed": "✅",
            "not_fixed": "⚠️",
            "no_issues": "ℹ️",
            "error": "❌",
        }
        emoji = status_emoji.get(status, "ℹ️")

        # ステータスの日本語マッピング
        status_jp = {
            "fixed": "修復成功",
            "not_fixed": "修復失敗",
            "no_issues": "問題なし",
            "error": "エラー",
        }
        status_text = status_jp.get(status, status)

        title = f"{emoji} Self-Healing 完了: {repo_full_name} PR #{pr_number}"

        # メッセージ本文を構築（メトリクスを含む）
        message_parts = [
            f"実行ID: `{run_id}`",
            f"ステータス: {status_text}",
        ]

        if metrics:
            if metrics.get("duration_str"):
                message_parts.append(f"実行時間: {metrics['duration_str']}")
            if metrics.get("patch_files_count", 0) > 0:
                message_parts.append(
                    f"パッチ: {metrics.get('patch_lines', 0)} lines / {metrics.get('patch_files_count', 0)} files"
                )
            if metrics.get("model_call_counts"):
                models_list = []
                for model, count in metrics["model_call_counts"].items():
                    models_list.append(f"{model} ({count} calls)")
                message_parts.append(f"使用モデル: {', '.join(models_list[:3])}")
            if metrics.get("estimated_cost_jpy", 0) > 0:
                message_parts.append(f"推定コスト: ~{metrics['estimated_cost_jpy']:.2f} JPY")
            if metrics.get("success_rate") is not None:
                success_rate_pct = metrics["success_rate"] * 100
                message_parts.append(f"最近の成功率 (last 30): {success_rate_pct:.1f}%")

        message_parts.append("")
        message_parts.append(summary)

        # PR URL と Run ログ URL を details セクションとして追加
        detail_lines: list[str] = []
        if pr_url:
            detail_lines.append(f"- PR: {pr_url}")
        if run_logs_url:
            detail_lines.append(f"- Run logs: {run_logs_url}")

        if detail_lines:
            message_parts.append("")
            message_parts.append("詳細:")
            message_parts.extend(detail_lines)

        message = "\n".join(message_parts)

        # ステータスに応じた通知ステータス
        notify_status = (
            "success" if status == "fixed" else ("error" if status == "error" else "warning")
        )

        notify_details = {
            "リポジトリ": repo_full_name,
            "PR番号": str(pr_number),
            "実行ID": run_id,
            "ステータス": status_text,
        }
        if details:
            notify_details.update(details)

        return self.send(
            title=title,
            message=message,
            status=notify_status,
            details=notify_details,
        )

    def notify_orchestrator_complete(
        self,
        *,
        project_path: str,
        requirement: str,
        status: str,
        session_id: str,
        details: dict[str, Any] | None = None,
    ) -> bool:
        """
        Orchestrator実行完了通知を送信する。

        :param project_path: プロジェクトパス
        :param requirement: 要件
        :param status: ステータス（"success", "error", "stopped"）
        :param session_id: セッションID
        :param details: 追加の詳細情報
        :return: 送信成功時True
        """
        status_emoji = {
            "success": "✅",
            "error": "❌",
            "stopped": "⏸️",
        }
        emoji = status_emoji.get(status, "ℹ️")

        # ステータスの日本語マッピング
        status_jp = {
            "success": "成功",
            "error": "エラー",
            "stopped": "中断",
        }
        status_text = status_jp.get(status, status)

        title = f"{emoji} Orchestrator 完了: {project_path}"
        message = f"要件: {requirement[:200]}\nステータス: {status_text}"

        notify_status = (
            "success" if status == "success" else ("error" if status == "error" else "warning")
        )

        notify_details = {
            "プロジェクト": project_path,
            "セッションID": session_id,
            "ステータス": status_text,
        }
        if details:
            notify_details.update(details)

        return self.send(
            title=title,
            message=message,
            status=notify_status,
            details=notify_details,
        )

    def notify_project_complete(
        self,
        *,
        project_name: str,
        task_description: str,
        status: str,
        details: dict[str, Any] | None = None,
    ) -> bool:
        """
        汎用的なプロジェクト完了通知を送信する（atelier-kyo-manager等で使用）。

        :param project_name: プロジェクト名（例: "atelier-kyo-manager"）
        :param task_description: タスクの説明
        :param status: ステータス（"success", "error", "warning", "info"）
        :param details: 追加の詳細情報
        :return: 送信成功時True
        """
        status_emoji = {
            "success": "✅",
            "error": "❌",
            "warning": "⚠️",
            "info": "ℹ️",
        }
        emoji = status_emoji.get(status, "ℹ️")

        # ステータスの日本語マッピング
        status_jp = {
            "success": "成功",
            "error": "エラー",
            "warning": "警告",
            "info": "情報",
        }
        status_text = status_jp.get(status, status)

        title = f"{emoji} {project_name} タスク完了"
        message = f"タスク: {task_description}\nステータス: {status_text}"

        notify_details = {
            "プロジェクト": project_name,
            "ステータス": status_text,
        }
        if details:
            notify_details.update(details)

        return self.send(
            title=title,
            message=message,
            status=status,
            details=notify_details,
        )


def get_notifier() -> SlackNotifier | None:
    """
    グローバルなSlackNotifierインスタンスを取得する。
    Webhook URLが設定されていない場合はNoneを返す。
    """
    notifier = SlackNotifier()
    return notifier if notifier.enabled else None
