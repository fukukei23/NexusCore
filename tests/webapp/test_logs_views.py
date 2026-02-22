"""
NexusCore Webapp - logs ビューのテスト

注意: このテストファイルは Flask レガシー前提です。
CR-FASTAPI-010 で Flask API が削除されたため、このテストファイルは skip されます。
FastAPI 側のテストは tests/api/test_fastapi_*.py を参照してください。
"""

import pytest

# CR-FASTAPI-010: Flask レガシー前提のテストは削除済み
# FastAPI 側のテストは tests/api/test_fastapi_*.py を参照してください
pytest.skip(
    "Flask legacy logs_views tests have been removed in CR-FASTAPI-010. "
    "Use FastAPI tests in tests/api/test_fastapi_*.py instead.",
    allow_module_level=True,
)


@pytest.fixture
def app():
    """テスト用 Flask アプリ"""
    app = create_app(
        config_overrides={
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "TESTING": True,
            "SECRET_KEY": "test-secret-key",
        }
    )
    return app


@pytest.fixture
def client(app):
    """テスト用クライアント"""
    with app.app_context():
        db.create_all()
        yield app.test_client()
        db.drop_all()


@pytest.fixture
def test_user(app):
    """テスト用ユーザー"""
    with app.app_context():
        user = User(
            github_id="123",
            github_login="test_user",
        )
        db.session.add(user)
        db.session.commit()
        return user


@pytest.fixture
def other_user(app):
    """別ユーザー"""
    with app.app_context():
        user = User(
            github_id="456",
            github_login="other_user",
        )
        db.session.add(user)
        db.session.commit()
        return user


@pytest.fixture
def test_project(app, test_user):
    """テスト用プロジェクト"""
    with app.app_context():
        project = Project(
            owner_id=test_user.id,
            name="Test Project",
            local_path="/tmp/test",
        )
        db.session.add(project)
        db.session.commit()
        return project


@pytest.fixture
def test_run(app, test_project, test_user):
    """テスト用 Run"""
    with app.app_context():
        run = Run(
            project_id=test_project.id,
            run_id="test-run-123",
            triggered_by=test_user.id,
            status="RUNNING",
        )
        db.session.add(run)
        db.session.commit()
        return run


@pytest.fixture
def test_log(app, test_run):
    """テスト用 ExecutionLog"""
    with app.app_context():
        log = ExecutionLog(
            run_id=test_run.id,
            source="ORCHESTRATOR",
            level="INFO",
            message="Test log message",
            payload_json='{"key": "value"}',
        )
        db.session.add(log)
        db.session.commit()
        return log


def test_project_logs_authenticated(client, app, test_user, test_project, test_run, test_log):
    """
    /logs/projects/<id> が 200 & 自分のプロジェクト
    """
    with app.app_context():
        # セッションにユーザーIDを設定
        with client.session_transaction() as sess:
            sess["user_id"] = test_user.id
            sess["github_login"] = test_user.github_login

        # GET リクエスト
        response = client.get(f"/logs/projects/{test_project.id}")

        # 200 を確認
        assert response.status_code == 200

        # JSON レスポンスの場合
        if response.content_type == "application/json":
            data = response.get_json()
            assert "logs" in data
            assert len(data["logs"]) >= 1


def test_project_logs_wrong_owner(client, app, other_user, test_project):
    """
    /logs/projects/<id> が 404 & 自分のプロジェクト以外
    """
    with app.app_context():
        # 別ユーザーでログイン
        with client.session_transaction() as sess:
            sess["user_id"] = other_user.id
            sess["github_login"] = other_user.github_login

        # GET リクエスト
        response = client.get(f"/logs/projects/{test_project.id}")

        # 404 を確認
        assert response.status_code == 404


def test_run_logs_authenticated(client, app, test_user, test_project, test_run, test_log):
    """
    /logs/runs/<run_id> が 200 & ownership チェック
    """
    with app.app_context():
        # セッションにユーザーIDを設定
        with client.session_transaction() as sess:
            sess["user_id"] = test_user.id
            sess["github_login"] = test_user.github_login

        # GET リクエスト
        response = client.get(f"/logs/runs/{test_run.run_id}")

        # 200 を確認
        assert response.status_code == 200

        # JSON レスポンスの場合
        if response.content_type == "application/json":
            data = response.get_json()
            assert "logs" in data
            assert "run" in data
            assert data["run"]["run_id"] == test_run.run_id


def test_run_logs_wrong_owner(client, app, other_user, test_project, test_run):
    """
    /logs/runs/<run_id> が 404 & ownership チェック失敗
    """
    with app.app_context():
        # 別ユーザーでログイン
        with client.session_transaction() as sess:
            sess["user_id"] = other_user.id
            sess["github_login"] = other_user.github_login

        # GET リクエスト
        response = client.get(f"/logs/runs/{test_run.run_id}")

        # 404 を確認
        assert response.status_code == 404


def test_run_logs_unauthenticated(client, app, test_run):
    """
    /logs/runs/<run_id> が リダイレクト（未認証）
    """
    # セッションにユーザーIDを設定しない

    # GET リクエスト
    response = client.get(
        f"/logs/runs/{test_run.run_id}",
        follow_redirects=False,
    )

    # リダイレクト（302）または 401 を確認
    assert response.status_code in [302, 401]
