#!/usr/bin/env python3
"""API Key ブートストラップ CLI

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
import os
from pathlib import Path
from typing import Tuple

# プロジェクトルートをパスに追加
# bootstrap_apikey.py は src/nexuscore/cli/ にあるため、
# プロジェクトルートは 3 階層上
current_file = Path(__file__).resolve()
src_path = current_file.parent.parent.parent  # src/nexuscore/cli -> src/nexuscore -> src
project_root = src_path.parent  # src -> プロジェクトルート

# PYTHONPATH / sys.path を補正
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

if "PYTHONPATH" not in os.environ:
    os.environ["PYTHONPATH"] = str(src_path)
elif str(src_path) not in os.environ["PYTHONPATH"].split(os.pathsep):
    os.environ["PYTHONPATH"] = f"{src_path}{os.pathsep}{os.environ['PYTHONPATH']}"

from nexuscore.webapp import create_app, db
from nexuscore.webapp.models import User, ApiKey


def bootstrap_apikey_for_app(
    app,
    user_login: str,
    user_name: str | None = None,
    key_name: str = "Bootstrap Dev Key",
) -> Tuple[User, ApiKey, str]:
    """与えられた app コンテキストで User + ApiKey を作成し、生 token を返す純粋ロジック関数。

    テストではこの関数を直接呼び出すことで、テスト用 DB / app を利用できる。
    CLI からは ``bootstrap_apikey_main`` 経由でこの関数を呼び出す。
    """

    with app.app_context():
        # ユーザーを検索
        user = User.query.filter_by(github_login=user_login).first()

        if not user:
            # ユーザーが存在しない場合は新規作成
            github_id = f"cli_bootstrap_{user_login}"

            # 既に同じ github_id が存在する場合はエラー
            existing_user = User.query.filter_by(github_id=github_id).first()
            if existing_user:
                raise RuntimeError(
                    f"User with github_id '{github_id}' already exists "
                    f"(login={existing_user.github_login}, id={existing_user.id})"
                )

            effective_name = user_name or user_login
            user = User(
                github_id=github_id,
                github_login=user_login,
                name=effective_name,
            )
            db.session.add(user)
            db.session.commit()
            db.session.refresh(user)
        # else: 既存ユーザーを再利用

        # API Key を生成
        raw_token = ApiKey.generate_token()
        token_hash = ApiKey.hash_token(raw_token)

        api_key = ApiKey(
            user_id=user.id,
            token_hash=token_hash,
            name=key_name,
        )

        db.session.add(api_key)
        db.session.commit()
        db.session.refresh(api_key)

        # app.app_context() から出る前に、必要な属性を明示的に読み込む
        # これにより、expunge 後でも属性にアクセスできる
        _ = user.id
        _ = user.github_login
        _ = api_key.id
        _ = api_key.name

        # オブジェクトを expunge する（属性は既に読み込まれている）
        db.session.expunge(user)
        db.session.expunge(api_key)

        return user, api_key, raw_token


def bootstrap_apikey_main(argv: list[str] | None = None) -> int:
    """API Key ブートストラップ CLI のメイン関数。

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
        help='Name for the API key (default: "Bootstrap Dev Key")',
    )

    if argv is None:
        argv = sys.argv[1:]
    args = parser.parse_args(argv)

    try:
        # Flask アプリを生成
        app = create_app()

        # CLI から直接実行する場合、DB が未初期化のことがあるため create_all() を呼ぶ。
        # テストでは別の app / DB を用意し、bootstrap_apikey_for_app() を直接呼び出す。
        with app.app_context():
            db.create_all()

        user, api_key, raw_token = bootstrap_apikey_for_app(
            app=app,
            user_login=args.user_login,
            user_name=args.user_name,
            key_name=args.key_name,
        )

        # stderr にはメタ情報、stdout には export コマンドのみを出力
        # bootstrap_apikey_for_app から返されたオブジェクトは expunge されているので、
        # 直接属性にアクセスできる
        print(f"[INFO] Using user: {user.github_login} (id={user.id})", file=sys.stderr)
        print(f'[INFO] Created API key: "{args.key_name}" (id={api_key.id})', file=sys.stderr)
        print(f'export NEXUSCORE_API_KEY="{raw_token}"', file=sys.stdout)

        return 0

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(bootstrap_apikey_main())
