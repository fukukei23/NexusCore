"""
E2E テスト用 SQLite DB セットアップ

FastAPI アプリの E2E テストで使用する SQLite DB を作成・初期化する。
"""

from __future__ import annotations

import os
import tempfile

import pytest
from flask import Flask

from nexuscore.webapp import db
from nexuscore.webapp.models import ApiKey, Project, User

# E2E テスト用の SQLite DB パス
E2E_DB_PATH: str | None = None


def create_e2e_db() -> tuple[str, Flask]:
    """
    E2E テスト用の SQLite DB を作成し、Flask アプリを初期化する。

    Returns:
        tuple[str, Flask]: (DB パス, Flask アプリインスタンス)
    """
    # 一時ファイルとして SQLite DB を作成
    temp_dir = tempfile.mkdtemp(prefix="nexuscore_e2e_")
    db_path = os.path.join(temp_dir, "test_e2e.db")
    db_uri = f"sqlite:///{db_path}"

    # Flask アプリを作成して DB を初期化
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = db_uri
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["TESTING"] = True

    # DB を初期化
    db.init_app(app)

    # アプリコンテキスト内でテーブルを作成
    with app.app_context():
        db.create_all()

    return db_path, app


def setup_test_data(app: Flask) -> tuple[User, ApiKey]:
    """
    テスト用の初期データを挿入する。

    Args:
        app: Flask アプリインスタンス

    Returns:
        tuple[User, ApiKey]: (テストユーザー, テスト API Key)
    """
    with app.app_context():
        # テストユーザーを作成
        test_user = User(
            github_id="test_user_123",
            github_login="test_user",
            name="Test User",
            email="test@example.com",
        )
        db.session.add(test_user)
        db.session.commit()

        # テスト API Key を作成
        test_api_key_plain = "test_api_key_e2e_12345"
        test_api_key = ApiKey(
            user_id=test_user.id,
            token_hash=ApiKey.hash_token(test_api_key_plain),
            name="E2E Test API Key",
        )
        db.session.add(test_api_key)
        db.session.commit()

        # テストプロジェクトを作成（最低 1 件）
        test_project = Project(
            owner_id=test_user.id,
            name="Test Project",
            repo_url="https://github.com/test/test-project",
            local_path="/tmp/test_project",
        )
        db.session.add(test_project)
        db.session.commit()

        return test_user, test_api_key


@pytest.fixture(scope="session")
def e2e_db_path():
    """
    E2E テスト用の SQLite DB パスを提供する fixture。

    Returns:
        str: DB パス
    """
    global E2E_DB_PATH
    if E2E_DB_PATH is None:
        db_path, app = create_e2e_db()
        E2E_DB_PATH = db_path
        # 初期データを挿入
        setup_test_data(app)
    return E2E_DB_PATH


@pytest.fixture(scope="session")
def e2e_flask_app():
    """
    E2E テスト用の Flask アプリインスタンスを提供する fixture。

    Returns:
        Flask: Flask アプリインスタンス
    """
    db_path, app = create_e2e_db()
    setup_test_data(app)
    return app


@pytest.fixture(scope="session")
def e2e_test_api_key():
    """
    E2E テスト用の API Key（平文）を提供する fixture。

    Returns:
        str: API Key（平文）
    """
    return "test_api_key_e2e_12345"


@pytest.fixture(scope="session")
def e2e_test_user_id():
    """
    E2E テスト用のユーザー ID を提供する fixture。

    Returns:
        int: ユーザー ID
    """
    # setup_test_data で作成されたユーザーの ID を返す
    # 実際の実装では、e2e_flask_app から取得する
    return 1
