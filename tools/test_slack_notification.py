#!/usr/bin/env python3
"""
test_slack_notification.py

Slack 通知機能をテストするスクリプト。

使用方法:
    python tools/test_slack_notification.py
"""

import os
import sys
from pathlib import Path

# NexusCoreのsrcディレクトリをパスに追加
project_root = Path(__file__).resolve().parent.parent
src_dir = project_root / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

# .env ファイルを読み込む
try:
    from dotenv import load_dotenv
    # プロジェクトルートの .env ファイルを読み込む
    env_path = project_root / ".env"
    if env_path.exists():
        load_dotenv(env_path, override=True)
    else:
        # 見つからない場合は自動検索
        load_dotenv(override=True)
except ImportError:
    # python-dotenv がインストールされていない場合
    pass

from nexuscore.core.notifier import get_notifier, SlackNotifier


def main():
    print("=" * 60)
    print("Slack 通知テスト")
    print("=" * 60)
    print()

    # 環境変数の確認
    webhook_url = os.getenv("NEXUS_SLACK_WEBHOOK_URL")
    if not webhook_url:
        print("❌ 環境変数 NEXUS_SLACK_WEBHOOK_URL が設定されていません")
        print()
        print("設定方法:")
        print("  1. .env ファイルに追加:")
        print("     NEXUS_SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL")
        print()
        print("  2. または環境変数として設定:")
        print("     export NEXUS_SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL")
        print()
        print("詳細は docs/slack_notification_setup.md を参照してください")
        sys.exit(1)

    print(f"✅ Webhook URL: {webhook_url[:50]}...")
    print()

    # Notifier を初期化
    notifier = get_notifier()
    if not notifier or not notifier.enabled:
        print("❌ SlackNotifier が無効です")
        sys.exit(1)

    print("✅ SlackNotifier が有効です")
    print()

    # テスト通知を送信
    print("テスト通知を送信しています...")
    print()

    # 1. 基本通知（info）
    print("1. 基本通知（info）を送信...")
    result1 = notifier.send(
        title="🧪 NexusCore テスト通知",
        message="これは基本通知のテストです。",
        status="info",
    )
    print(f"   結果: {'✅ 成功' if result1 else '❌ 失敗'}")
    print()

    # 2. 成功通知
    print("2. 成功通知を送信...")
    result2 = notifier.send(
        title="✅ NexusCore テスト通知（成功）",
        message="これは成功通知のテストです。",
        status="success",
        details={
            "テスト項目": "Slack 通知機能",
            "ステータス": "正常動作",
        },
    )
    print(f"   結果: {'✅ 成功' if result2 else '❌ 失敗'}")
    print()

    # 3. エラー通知
    print("3. エラー通知を送信...")
    result3 = notifier.send(
        title="❌ NexusCore テスト通知（エラー）",
        message="これはエラー通知のテストです。",
        status="error",
        details={
            "エラー種別": "テストエラー",
            "メッセージ": "これはテストです",
        },
    )
    print(f"   結果: {'✅ 成功' if result3 else '❌ 失敗'}")
    print()

    # 4. Orchestrator 完了通知
    print("4. Orchestrator 完了通知を送信...")
    result4 = notifier.notify_orchestrator_complete(
        project_path="/test/project",
        requirement="テスト要件",
        status="success",
        session_id="test-session-123",
        details={
            "Run ID": "test-run-123",
            "プロジェクト名": "テストプロジェクト",
        },
    )
    print(f"   結果: {'✅ 成功' if result4 else '❌ 失敗'}")
    print()

    # 5. プロジェクト完了通知
    print("5. プロジェクト完了通知を送信...")
    result5 = notifier.notify_project_complete(
        project_name="test-project",
        task_description="テストタスク",
        status="success",
        details={
            "変更ファイル数": "5",
            "実行時間": "10秒",
        },
    )
    print(f"   結果: {'✅ 成功' if result5 else '❌ 失敗'}")
    print()

    # 結果サマリー
    print("=" * 60)
    print("テスト結果サマリー")
    print("=" * 60)
    results = [result1, result2, result3, result4, result5]
    success_count = sum(results)
    total_count = len(results)
    print(f"成功: {success_count}/{total_count}")
    print()

    if success_count == total_count:
        print("✅ すべてのテストが成功しました！")
        print("Slack で通知を確認してください。")
        sys.exit(0)
    else:
        print("❌ 一部のテストが失敗しました。")
        print("ログを確認してください。")
        sys.exit(1)


if __name__ == "__main__":
    main()

