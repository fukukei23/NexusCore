#!/usr/bin/env python3
"""
API Key ブートストラップ CLI

初回 API Key を発行するための公式 CLI ツール。
ユーザーが存在しない場合は自動的に作成します。

使用方法:
    python -m nexuscore.cli.bootstrap_apikey \
        --user-login dev \
        --user-name "Dev User" \
        --key-name "Local Dev Key"
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# プロジェクトルートをパスに追加
# bootstrap_apikey.py は src/nexuscore/cli/ にあるため、
# プロジェクトルートは 3 階層上
current_file = Path(__file__).resolve()
src_path = current_file.parent.parent.parent  # src/nexuscore/cli -> src/nexuscore -> src
project_root = src_path.parent  # src -> プロジェクトルート

if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from nexuscore.webapp import create_app, db
from nexuscore.webapp.models import User, ApiKey


def bootstrap_apikey_main(argv: list[str] | None = None) -> int:
    """
    API Key ブートストラップ CLI のメイン関数

    Args:
        argv: コマンドライン引数（None の場合は sys.argv を使用）

    Returns:
        int: 終了コード（0: 成功、1: エラー）
    """
    parser = argparse.ArgumentParser(
        description="Bootstrap API key for NexusCore user",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # 初回発行（ユーザーも自動作成）
  python -m nexuscore.cli.bootstrap_apikey \\
      --user-login dev \\
      --user-name "Dev User" \\
      --key-name "Local Dev Key"

  # 既存ユーザーに追加発行
  python -m nexuscore.cli.bootstrap_apikey \\
      --user-login dev \\
      --key-name "CI/CD Key"
        """,
    )
    parser.add_argument(
        "--user-login",
        required=True,
        help="GitHub login (github_login) of the user",
    )
    parser.add_argument(
        "--user-name",
        help="Display name for the user (used when creating new user)",
    )
    parser.add_argument(
        "--key-name",
        default="Bootstrap Dev Key",
        help="Name/description for the API key (default: 'Bootstrap Dev Key')",
    )

    args = parser.parse_args(argv)

    # Flask アプリを作成
    app = create_app()

    try:
        with app.app_context():
            # ユーザーを検索
            user = User.query.filter_by(github_login=args.user_login).first()

            if not user:
                # ユーザーが存在しない場合は新規作成
                # github_id は一意な文字列を生成（CLI ブートストラップ用）
                github_id = f"cli_bootstrap_{args.user_login}"
                
                # 既に同じ github_id が存在する場合はエラー
                existing_user = User.query.filter_by(github_id=github_id).first()
                if existing_user:
                    print(f"Error: User with github_id '{github_id}' already exists.", file=sys.stderr)
                    print(f"  Existing user: {existing_user.github_login} (id: {existing_user.id})", file=sys.stderr)
                    return 1

                user_name = args.user_name or args.user_login
                user = User(
                    github_id=github_id,
                    github_login=args.user_login,
                    name=user_name,
                )
                db.session.add(user)
                db.session.commit()
                db.session.refresh(user)
                print(f"[INFO] Created user: {args.user_login} (id={user.id})", file=sys.stderr)
            else:
                print(f"[INFO] Using existing user: {args.user_login} (id={user.id})", file=sys.stderr)

            # API Key を生成
            raw_token = ApiKey.generate_token()
            token_hash = ApiKey.hash_token(raw_token)

            api_key = ApiKey(
                user_id=user.id,
                token_hash=token_hash,
                name=args.key_name,
            )

            db.session.add(api_key)
            db.session.commit()
            db.session.refresh(api_key)

            print(f"[INFO] Created API key: \"{args.key_name}\" (id={api_key.id})", file=sys.stderr)
            print(f"export NEXUSCORE_API_KEY=\"{raw_token}\"", file=sys.stdout)

            return 0

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(bootstrap_apikey_main())

