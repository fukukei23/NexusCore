#!/usr/bin/env python3
"""
API キー発行スクリプト

NexusCore Webapp のデータベースに API キーを登録するためのスクリプト。

使用方法:
    python tools/generate_api_key.py --user <github_login> --name "VSCode Extension Key"
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from nexuscore.webapp import create_app, db
from nexuscore.webapp.models import User, ApiKey


def main():
    parser = argparse.ArgumentParser(description="Generate API key for NexusCore user")
    parser.add_argument(
        "--user",
        required=True,
        help="GitHub login (github_login) of the user",
    )
    parser.add_argument(
        "--name",
        required=True,
        help="Name/description for the API key (e.g., 'VSCode Extension Key')",
    )
    parser.add_argument(
        "--show-existing",
        action="store_true",
        help="Show existing API keys for the user",
    )

    args = parser.parse_args()

    # Flask アプリを作成
    app = create_app()

    with app.app_context():
        # ユーザーを取得
        user = User.query.filter_by(github_login=args.user).first()

        if not user:
            print(f"Error: User '{args.user}' not found.")
            print("Available users:")
            for u in User.query.all():
                print(f"  - {u.github_login} (id: {u.id})")
            sys.exit(1)

        # 既存の API キーを表示
        if args.show_existing:
            existing_keys = ApiKey.query.filter_by(user_id=user.id).all()
            if existing_keys:
                print(f"\nExisting API keys for user '{args.user}':")
                for key in existing_keys:
                    print(f"  - ID: {key.id}, Name: {key.name}, Created: {key.created_at}")
            else:
                print(f"\nNo existing API keys for user '{args.user}'.")
            print()

        # 新しい API キーを生成
        raw_token = ApiKey.generate_token()
        token_hash = ApiKey.hash_token(raw_token)

        api_key = ApiKey(
            user_id=user.id,
            token_hash=token_hash,
            name=args.name,
        )

        db.session.add(api_key)
        db.session.commit()

        print(f"\n✅ API key generated successfully!")
        print(f"\nUser: {user.github_login} (id: {user.id})")
        print(f"Key Name: {args.name}")
        print(f"Key ID: {api_key.id}")
        print(f"\n⚠️  IMPORTANT: Save this API key now. It will not be shown again!")
        print(f"\nAPI Key: {raw_token}\n")
        print("Usage example:")
        print(f'  curl -H "X-Api-Key: {raw_token}" https://your-nexuscore-host/api/v1/projects')


if __name__ == "__main__":
    main()

