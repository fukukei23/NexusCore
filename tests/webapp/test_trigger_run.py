"""
NexusCore Webapp - trigger_run エンドポイントのテスト

注意: このテストファイルは Flask レガシー前提です。
CR-FASTAPI-010 で Flask API が削除されたため、このテストファイルは skip されます。
FastAPI 側のテストは tests/api/test_fastapi_*.py を参照してください。
"""

import pytest

# CR-FASTAPI-010: Flask レガシー前提のテストは削除済み
# FastAPI 側のテストは tests/api/test_fastapi_*.py を参照してください
pytest.skip(
    "Flask legacy trigger_run tests have been removed in CR-FASTAPI-010. "
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


def test_trigger_run_authenticated(client, app, test_user, test_project):
    """
    認証済みで /projects/<id>/run に POST → Run が1件増える & 状態が PENDING
    """
    with app.app_context():
        # セッションにユーザーIDを設定（認証済み状態をシミュレート）
        with client.session_transaction() as sess:
            sess["user_id"] = test_user.id
            sess["github_login"] = test_user.github_login

        # 実行前の Run 数を確認
        initial_count = Run.query.count()

        # POST リクエスト
        response = client.post(
            f"/projects/{test_project.id}/run",
            json={
                "requirement": "Test requirement",
                "autonomy_level": 1,
                "fast_lane": False,
            },
            content_type="application/json",
        )

        # ステータスコードを確認（非同期の場合は 202、同期の場合は 200）
        assert response.status_code in [200, 202]

        # Run が1件増えていることを確認
        final_count = Run.query.count()
        assert final_count == initial_count + 1

        # 最新の Run を取得
        latest_run = Run.query.order_by(Run.created_at.desc()).first()
        assert latest_run is not None
        assert latest_run.project_id == test_project.id
        assert latest_run.triggered_by == test_user.id
        assert latest_run.status == "PENDING"
        assert latest_run.requirement == "Test requirement"


def test_trigger_run_missing_requirement(client, app, test_user, test_project):
    """
    requirement 未指定なら 400
    """
    with app.app_context():
        # セッションにユーザーIDを設定
        with client.session_transaction() as sess:
            sess["user_id"] = test_user.id
            sess["github_login"] = test_user.github_login

        # POST リクエスト（requirement なし）
        response = client.post(
            f"/projects/{test_project.id}/run",
            json={
                "autonomy_level": 1,
            },
            content_type="application/json",
        )

        # 400 エラーを確認
        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data
        assert "requirement" in data["error"].lower()


def test_trigger_run_unauthenticated(client, app, test_project):
    """
    未認証で /projects/<id>/run に POST → リダイレクト（ログインページ）
    """
    # セッションにユーザーIDを設定しない（未認証状態）

    # POST リクエスト
    response = client.post(
        f"/projects/{test_project.id}/run",
        json={
            "requirement": "Test requirement",
        },
        content_type="application/json",
        follow_redirects=False,
    )

    # リダイレクト（302）または 401 を確認
    assert response.status_code in [302, 401]


def test_trigger_run_wrong_owner(client, app, test_user, test_project):
    """
    別ユーザーのプロジェクトにアクセス → 404
    """
    with app.app_context():
        # 別ユーザーを作成
        other_user = User(
            github_id="456",
            github_login="other_user",
        )
        db.session.add(other_user)
        db.session.commit()

        # 別ユーザーでログイン
        with client.session_transaction() as sess:
            sess["user_id"] = other_user.id
            sess["github_login"] = other_user.github_login

        # POST リクエスト
        response = client.post(
            f"/projects/{test_project.id}/run",
            json={
                "requirement": "Test requirement",
            },
            content_type="application/json",
        )

        # 404 エラーを確認
        assert response.status_code == 404
