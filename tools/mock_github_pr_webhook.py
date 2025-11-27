#!/usr/bin/env python3
"""
mock_github_pr_webhook.py

ローカルの NexusCore サーバに対して、GitHub pull_request Webhook を
モック送信するためのツール。

使い方の例:
    # サーバ起動中に:
    python tools/mock_github_pr_webhook.py \
        --repo-full-name yourname/yourrepo \
        --pr-number 123 \
        --head-sha abcdef1234567890

実際には GitHub から来る payload を 100% 再現しているわけではないが、
Self-Healing のパイプラインと Webhook 処理を E2E で確認するには十分。
"""

from __future__ import annotations

import argparse
import json
import os
from typing import Any, Dict

try:
    import requests
except ImportError:
    print("Error: requests library is required. Install with: pip install requests")
    exit(1)


def build_sample_payload(
    repo_full_name: str,
    pr_number: int,
    head_sha: str,
    label: str,
    base_branch: str,
) -> Dict[str, Any]:
    """
    GitHub pull_request イベントのサンプルペイロードを生成する。
    """
    owner, repo = repo_full_name.split("/", 1)
    return {
        "action": "opened",
        "number": pr_number,
        "repository": {
            "id": 123456789,
            "name": repo,
            "full_name": repo_full_name,
            "owner": {
                "login": owner,
                "id": 1111,
            },
        },
        "pull_request": {
            "number": pr_number,
            "state": "open",
            "draft": False,
            "head": {
                "sha": head_sha,
                "ref": f"refs/pull/{pr_number}/head",
            },
            "base": {
                "ref": base_branch,
            },
            "labels": [
                {
                    "id": 999999,
                    "name": label,
                }
            ],
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Mock GitHub PR Webhook sender",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
例:
  python tools/mock_github_pr_webhook.py \\
      --repo-full-name yourname/yourrepo \\
      --pr-number 123 \\
      --head-sha abcdef1234567890

  # カスタムURLを指定する場合
  python tools/mock_github_pr_webhook.py \\
      --url http://localhost:8000/api/github/webhook \\
      --repo-full-name yourname/yourrepo \\
      --pr-number 123 \\
      --head-sha abcdef1234567890
        """,
    )
    parser.add_argument(
        "--url",
        default="http://127.0.0.1:8000/api/github/webhook",
        help="Webhook エンドポイント URL (デフォルト: http://127.0.0.1:8000/api/github/webhook)",
    )
    parser.add_argument(
        "--repo-full-name",
        required=True,
        help="リポジトリ名 (例: yourname/yourrepo)",
    )
    parser.add_argument(
        "--pr-number",
        type=int,
        required=True,
        help="PR 番号",
    )
    parser.add_argument(
        "--head-sha",
        required=True,
        help="PR の head SHA (テスト対象コミット)",
    )
    parser.add_argument(
        "--label",
        default="self-healing",
        help="Self-Healing 対象ラベル名 (config.label と合わせる)",
    )
    parser.add_argument(
        "--base-branch",
        default="main",
        help="PR の base ブランチ名 (config.allowed_target_branches と合わせる)",
    )
    args = parser.parse_args()

    payload = build_sample_payload(
        repo_full_name=args.repo_full_name,
        pr_number=args.pr_number,
        head_sha=args.head_sha,
        label=args.label,
        base_branch=args.base_branch,
    )

    # 署名は開発用なので省略（本番では X-Hub-Signature-256 が必要）
    headers = {
        "X-GitHub-Event": "pull_request",
        "Content-Type": "application/json",
    }

    print(f"POST {args.url}")
    print("Payload:")
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    print()

    try:
        resp = requests.post(
            args.url,
            headers=headers,
            json=payload,
            timeout=30,
        )

        print(f"Status: {resp.status_code}")
        try:
            print("Response JSON:")
            print(json.dumps(resp.json(), indent=2, ensure_ascii=False))
        except Exception:
            print("Response text:")
            print(resp.text)
    except requests.exceptions.ConnectionError:
        print(f"エラー: {args.url} に接続できません。")
        print("サーバが起動しているか確認してください。")
        exit(1)
    except Exception as e:
        print(f"エラー: {e}")
        exit(1)


if __name__ == "__main__":
    main()

