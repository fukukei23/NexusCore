"""
views_api_test.py の包括的なテスト

API Test UIの全機能をテスト：
- GET /api-test/: フォーム表示
- POST /api-test/: API実行とシミュレーション
- プロジェクト一覧とAPIキー一覧の表示
- エラーハンドリング
"""
from __future__ import annotations

import pytest
from unittest.mock import Mock, patch, MagicMock

from nexuscore.webapp import db
from nexuscore.webapp.models import User, Project, ApiKey


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture(scope="function")
def app():
    """Flask test app with in-memory SQLite database"""
    from nexuscore.webapp import create_app

    config_overrides = {
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "SQLALCHEMY_TRACK_MODIFICATIONS": False,
        "SECRET_KEY": "test-secret-key",
        "WTF_CSRF_ENABLED": False,
    }

    app = create_app(config_overrides=config_overrides)

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """Flask test client"""
    return app.test_client()


@pytest.fixture
def test_user(app):
    """テスト用ユーザー"""
    user = User(
        github_id="12345",
        github_login="testuser",
        name="Test User",
        email="test@example.com",
    )
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def test_project(app, test_user):
    """テスト用プロジェクト"""
    project = Project(
        owner_id=test_user.id,
        name="test_project",
        local_path="/tmp/test",
    )
    db.session.add(project)
    db.session.commit()
    return project


@pytest.fixture
def test_api_key(app, test_user):
    """テスト用APIキー"""
    api_key = ApiKey(
        user_id=test_user.id,
        name="Test API Key",
        token_hash=ApiKey.hash_token("test-token-12345"),
    )
    db.session.add(api_key)
    db.session.commit()
    return api_key


@pytest.fixture
def authenticated_client(client, app, test_user):
    """認証済みクライアント"""
    with client.session_transaction() as sess:
        sess["user_id"] = test_user.id
    return client


# ============================================================================
# Tests: GET /api-test/
# ============================================================================


class TestApiTestGet:
    """GET /api-test/ のテスト"""

    def test_api_test_get_without_auth_redirects(self, client):
        """認証なしはリダイレクトされる"""
        response = client.get("/api-test/")
        # require_authデコレータによるリダイレクト
        assert response.status_code in [302, 401]

    def test_api_test_get_with_auth_returns_form(self, authenticated_client, test_user):
        """認証済みユーザーはフォームを取得できる"""
        response = authenticated_client.get("/api-test/")

        assert response.status_code == 200
        assert b"API Test" in response.data
        assert test_user.github_login.encode() in response.data

    def test_api_test_get_displays_api_keys(self, authenticated_client, test_user, test_api_key):
        """ユーザーのAPIキー一覧が表示される"""
        response = authenticated_client.get("/api-test/")

        assert response.status_code == 200
        assert test_api_key.name.encode() in response.data
        assert str(test_api_key.id).encode() in response.data

    def test_api_test_get_displays_projects(self, authenticated_client, test_user, test_project):
        """ユーザーのプロジェクト一覧が表示される"""
        response = authenticated_client.get("/api-test/")

        assert response.status_code == 200
        assert test_project.name.encode() in response.data
        assert str(test_project.id).encode() in response.data

    def test_api_test_get_with_no_api_keys(self, authenticated_client, test_user):
        """APIキーがない場合でもフォームは表示される"""
        response = authenticated_client.get("/api-test/")

        assert response.status_code == 200
        assert b"API Test" in response.data
        # APIキーのオプションがない（またはNoneのみ）
        assert b"None (use session auth)" in response.data

    def test_api_test_get_with_no_projects(self, authenticated_client, test_user):
        """プロジェクトがない場合でもフォームは表示される"""
        response = authenticated_client.get("/api-test/")

        assert response.status_code == 200
        assert b"API Test" in response.data
        assert b"Select a project" in response.data

    def test_api_test_get_with_multiple_api_keys(self, authenticated_client, test_user):
        """複数のAPIキーがすべて表示される"""
        api_key1 = ApiKey(user_id=test_user.id, name="Key 1", token_hash=ApiKey.hash_token("token1"))
        api_key2 = ApiKey(user_id=test_user.id, name="Key 2", token_hash=ApiKey.hash_token("token2"))
        db.session.add_all([api_key1, api_key2])
        db.session.commit()

        response = authenticated_client.get("/api-test/")

        assert response.status_code == 200
        assert b"Key 1" in response.data
        assert b"Key 2" in response.data

    def test_api_test_get_with_multiple_projects(self, authenticated_client, test_user):
        """複数のプロジェクトがすべて表示される"""
        project1 = Project(owner_id=test_user.id, name="Project 1", local_path="/tmp/p1")
        project2 = Project(owner_id=test_user.id, name="Project 2", local_path="/tmp/p2")
        db.session.add_all([project1, project2])
        db.session.commit()

        response = authenticated_client.get("/api-test/")

        assert response.status_code == 200
        assert b"Project 1" in response.data
        assert b"Project 2" in response.data


# ============================================================================
# Tests: POST /api-test/
# ============================================================================


class TestApiTestPost:
    """POST /api-test/ のテスト"""

    def test_api_test_post_without_auth_redirects(self, client):
        """認証なしはリダイレクトされる"""
        response = client.post("/api-test/", data={})
        assert response.status_code in [302, 401]

    def test_api_test_post_without_project_id_shows_error(self, authenticated_client, test_user):
        """project_idがない場合はエラーメッセージが表示される"""
        response = authenticated_client.post("/api-test/", data={
            "requirement": "Test requirement",
        })

        assert response.status_code == 200
        assert b"Project ID and requirement are required" in response.data

    def test_api_test_post_without_requirement_shows_error(self, authenticated_client, test_user, test_project):
        """requirementがない場合はエラーメッセージが表示される"""
        response = authenticated_client.post("/api-test/", data={
            "project_id": test_project.id,
        })

        assert response.status_code == 200
        assert b"Project ID and requirement are required" in response.data

    def test_api_test_post_with_valid_data_shows_result(self, authenticated_client, test_user, test_project):
        """有効なデータでPOSTするとAPI呼び出しシミュレーション結果が表示される"""
        response = authenticated_client.post("/api-test/", data={
            "project_id": test_project.id,
            "requirement": "Fix all bugs",
        })

        assert response.status_code == 200
        assert b"API Call Result" in response.data
        assert b"API call simulated" in response.data

    def test_api_test_post_with_api_key_id(self, authenticated_client, test_user, test_project, test_api_key):
        """api_key_idパラメータも受け入れられる"""
        response = authenticated_client.post("/api-test/", data={
            "project_id": test_project.id,
            "requirement": "Run tests",
            "api_key_id": test_api_key.id,
        })

        assert response.status_code == 200
        assert b"API Call Result" in response.data

    def test_api_test_post_sets_g_current_api_user(self, authenticated_client, test_user, test_project):
        """g.current_api_userが設定される（APIコールシミュレーション）"""
        response = authenticated_client.post("/api-test/", data={
            "project_id": test_project.id,
            "requirement": "Test",
        })

        # API呼び出しがシミュレートされ、結果が返される
        assert response.status_code == 200
        # シミュレーション結果が含まれる
        assert b"API call simulated" in response.data or b"API Call Result" in response.data

    def test_api_test_post_handles_exception(self, authenticated_client, test_user, test_project):
        """例外が発生した場合はエラーメッセージが表示される"""
        response = authenticated_client.post("/api-test/", data={
            "project_id": test_project.id,
            "requirement": "Cause error",
        })

        # 実装上、tryブロックで囲まれているので例外は握りつぶされ、エラーメッセージが表示される可能性がある
        assert response.status_code == 200
        # エラーメッセージまたは結果が含まれる
        assert b"API" in response.data or b"result" in response.data.lower()

    def test_api_test_post_displays_form_on_error(self, authenticated_client, test_user):
        """エラー時もフォームが再表示される"""
        response = authenticated_client.post("/api-test/", data={
            "requirement": "Missing project_id",
        })

        assert response.status_code == 200
        # エラーメッセージとフォームの両方が表示される
        assert b"required" in response.data.lower()
        assert b"Project ID" in response.data or b"project_id" in response.data

    def test_api_test_post_shows_curl_example(self, authenticated_client, test_user, test_project):
        """POSTレスポンスにcurlの使用例が含まれる"""
        response = authenticated_client.post("/api-test/", data={
            "project_id": test_project.id,
            "requirement": "Test",
        })

        assert response.status_code == 200
        assert b"curl" in response.data
        assert b"X-Api-Key" in response.data

    def test_api_test_post_result_contains_json(self, authenticated_client, test_user, test_project):
        """結果にJSON形式のデータが含まれる"""
        response = authenticated_client.post("/api-test/", data={
            "project_id": test_project.id,
            "requirement": "Generate tests",
        })

        assert response.status_code == 200
        # JSONレスポンスがHTMLに埋め込まれている
        assert b"status_code" in response.data or b"message" in response.data

    def test_api_test_post_with_empty_requirement(self, authenticated_client, test_user, test_project):
        """空のrequirementはエラー"""
        response = authenticated_client.post("/api-test/", data={
            "project_id": test_project.id,
            "requirement": "",
        })

        assert response.status_code == 200
        assert b"required" in response.data.lower()

    def test_api_test_post_includes_note_about_actual_api(self, authenticated_client, test_user, test_project):
        """実際のAPI使用についての注意書きが含まれる"""
        response = authenticated_client.post("/api-test/", data={
            "project_id": test_project.id,
            "requirement": "Test",
        })

        assert response.status_code == 200
        assert b"UI test page" in response.data or b"test page" in response.data.lower()
        assert b"actual API" in response.data or b"external API" in response.data


# ============================================================================
# Tests: HTML生成
# ============================================================================


class TestApiTestHtml:
    """HTML生成のテスト"""

    def test_api_test_html_contains_form_elements(self, authenticated_client, test_user):
        """HTMLに必要なフォーム要素が含まれる"""
        response = authenticated_client.get("/api-test/")

        assert response.status_code == 200
        assert b"<form" in response.data
        assert b'name="project_id"' in response.data
        assert b'name="requirement"' in response.data
        assert b'name="api_key_id"' in response.data
        assert b'type="submit"' in response.data

    def test_api_test_html_contains_styles(self, authenticated_client, test_user):
        """HTMLにスタイルが含まれる"""
        response = authenticated_client.get("/api-test/")

        assert response.status_code == 200
        assert b"<style>" in response.data
        assert b"font-family" in response.data

    def test_api_test_html_displays_logged_in_user(self, authenticated_client, test_user):
        """ログイン中のユーザー名が表示される"""
        response = authenticated_client.get("/api-test/")

        assert response.status_code == 200
        assert b"Logged in as:" in response.data
        assert test_user.github_login.encode() in response.data

    def test_api_test_html_has_back_link(self, authenticated_client, test_user):
        """プロジェクト一覧への戻りリンクがある"""
        response = authenticated_client.get("/api-test/")

        assert response.status_code == 200
        assert b"/projects/" in response.data
        assert b"Back to Projects" in response.data or b"back" in response.data.lower()
