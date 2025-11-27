#!/usr/bin/env python3
"""
notify_slack.py

atelier-kyo-manager など、任意のプロジェクトからSlack通知を送信するための
スタンドアロンスクリプト。

使用方法:
    python tools/notify_slack.py --project "atelier-kyo-manager" --task "実装完了" --status "success"
"""

import argparse
import os
import sys
from pathlib import Path

# NexusCoreのsrcディレクトリをパスに追加
project_root = Path(__file__).resolve().parent.parent
src_dir = project_root / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from nexuscore.core.notifier import get_notifier


def main():
    parser = argparse.ArgumentParser(
        description="Slack通知を送信する",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
例:
  # 成功通知
  python tools/notify_slack.py --project "atelier-kyo-manager" --task "実装完了" --status "success"

  # エラー通知
  python tools/notify_slack.py --project "atelier-kyo-manager" --task "テスト失敗" --status "error" --detail "エラー詳細"
        """,
    )
    parser.add_argument(
        "--project",
        type=str,
        required=True,
        help="プロジェクト名（例: atelier-kyo-manager）",
    )
    parser.add_argument(
        "--task",
        type=str,
        required=True,
        help="タスクの説明",
    )
    parser.add_argument(
        "--status",
        type=str,
        choices=["success", "error", "warning", "info"],
        default="info",
        help="ステータス（デフォルト: info）",
    )
    parser.add_argument(
        "--detail",
        type=str,
        help="追加の詳細情報（キー:値の形式、複数指定可）",
        action="append",
    )
    parser.add_argument(
        "--webhook-url",
        type=str,
        help="Slack Webhook URL（省略時は環境変数 NEXUS_SLACK_WEBHOOK_URL を使用）",
    )

    args = parser.parse_args()

    # Notifierを初期化
    notifier = get_notifier()
    if args.webhook_url:
        from nexuscore.core.notifier import SlackNotifier
        notifier = SlackNotifier(webhook_url=args.webhook_url)

    if not notifier or not notifier.enabled:
        print("エラー: Slack通知が有効になっていません。")
        print("環境変数 NEXUS_SLACK_WEBHOOK_URL を設定するか、--webhook-url を指定してください。")
        sys.exit(1)

    # 詳細情報をパース
    details = {}
    if args.detail:
        for d in args.detail:
            if ":" in d:
                key, value = d.split(":", 1)
                details[key.strip()] = value.strip()
            else:
                details["詳細"] = d

    # 通知を送信
    success = notifier.notify_project_complete(
        project_name=args.project,
        task_description=args.task,
        status=args.status,
        details=details if details else None,
    )

    if success:
        print(f"✅ Slack通知を送信しました: {args.project} - {args.task}")
        sys.exit(0)
    else:
        print(f"❌ Slack通知の送信に失敗しました")
        sys.exit(1)


if __name__ == "__main__":
    main()

