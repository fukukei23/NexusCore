#!/usr/bin/env python3
"""
quick_e2e_test.py

Self-Healing E2E テストを簡易実行するスクリプト。
サーバを起動せずに、直接関数を呼び出してテストします。
"""

import json
import os
import sys
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(project_root / "src"))

os.environ["NEXUS_PROJECT_ROOT"] = str(project_root)

from nexuscore.api.github_self_healing_webhook import github_webhook


def main():
    """E2E テストを実行"""
    print("=== Self-Healing E2E テスト ===")
    print(f"Project root: {project_root}")

    # モックペイロードを作成
    payload = {
        "action": "opened",
        "number": 1,
        "repository": {
            "id": 123456789,
            "name": "test-repo",
            "full_name": "test/repo",
            "owner": {
                "login": "test",
                "id": 1111,
            },
        },
        "pull_request": {
            "number": 1,
            "state": "open",
            "draft": False,
            "head": {
                "sha": "abc123def4567890",
                "ref": "refs/pull/1/head",
            },
            "base": {
                "ref": "main",
            },
            "labels": [
                {
                    "id": 999999,
                    "name": "self-healing",
                }
            ],
        },
    }

    print("\n=== モックペイロード ===")
    print(json.dumps(payload, indent=2, ensure_ascii=False))

    print("\n=== Self-Healing 実行 ===")
    try:
        result = github_webhook(
            payload=payload,
            project_root=str(project_root),
            event="pull_request",
            delivery="test-delivery-123",
        )

        print("\n=== 実行結果 ===")
        print(json.dumps(result, indent=2, ensure_ascii=False))

        # 実行履歴を確認
        history_file = project_root / ".nexus" / "history" / "self_healing.log.jsonl"
        if history_file.exists():
            print("\n=== 実行履歴（最新1件） ===")
            with open(history_file, "r", encoding="utf-8") as f:
                lines = f.readlines()
                if lines:
                    last_line = lines[-1].strip()
                    try:
                        record = json.loads(last_line)
                        print(json.dumps(record, indent=2, ensure_ascii=False))
                    except json.JSONDecodeError:
                        print(last_line)

        print("\n✅ E2E テスト完了")

    except Exception as e:
        print(f"\n❌ エラー: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

