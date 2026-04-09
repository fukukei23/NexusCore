"""
FastAPI Projects エンドポイントのテスト

CR-FASTAPI-005 で作成された /api/v1/projects エンドポイントのテスト。
既存の Flask テストの期待値に準拠。
"""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from nexuscore.api.fastapi_app import app


@pytest.fixture
def client():
    """FastAPI TestClient のフィクスチャ"""
    return TestClient(app)


@pytest.fixture
def mock_api_key(monkeypatch):
    """API Key をモック"""
    api_key = "test-api-key-123"
    monkeypatch.setenv("NEXUSCORE_API_KEY", api_key)
    yield api_key
    monkeypatch.delenv("NEXUSCORE_API_KEY", raising=False)


@pytest.fixture
def mock_db_models():
    """データベースモデルをモック"""
    with (
        patch("nexuscore.webapp.models.Project") as mock_project,
        patch("nexuscore.webapp.models.User") as mock_user,
        patch("nexuscore.webapp.db") as mock_db,
        patch("nexuscore.webapp.models.ApiKey") as mock_api_key_model,
        patch("nexuscore.webapp.models.User") as mock_auth_user,
    ):
        yield {
            "Project": mock_project,
            "User": mock_user,
            "db": mock_db,
            "ApiKey": mock_api_key_model,
            "AuthUser": mock_auth_user,
        }


def test_list_projects_success(client: TestClient, mock_api_key, mock_db_models):
    """
    プロジェクト一覧取得の正常系テスト
    """
    from sqlalchemy import desc as sa_desc

    # モックの設定
    mock_user = MagicMock()
    mock_user.id = 1
    mock_db_models["User"].query.first.return_value = mock_user

    mock_project1 = MagicMock()
    mock_project1.id = 1
    mock_project1.name = "Project 1"
    mock_project1.repo_url = "https://github.com/owner/repo1"
    mock_project1.local_path = "/path/to/project1"
    mock_project1.created_at = "2025-01-01T00:00:00"
    mock_project1.updated_at = "2025-01-01T00:00:00"

    mock_project2 = MagicMock()
    mock_project2.id = 2
    mock_project2.name = "Project 2"
    mock_project2.repo_url = None
    mock_project2.local_path = "/path/to/project2"
    mock_project2.created_at = "2025-01-02T00:00:00"
    mock_project2.updated_at = "2025-01-02T00:00:00"

    # desc() 関数をパッチして、モックオブジェクトを受け取った場合はそのまま返すようにする
    def mock_desc(column):
        # モックオブジェクトの場合はそのまま返す
        if isinstance(column, MagicMock):
            return column
        return sa_desc(column)

    with patch("nexuscore.api.routes.projects.desc", side_effect=mock_desc):
        mock_query = MagicMock()
        mock_query.filter_by.return_value.order_by.return_value.all.return_value = [
            mock_project1,
            mock_project2,
        ]
        mock_db_models["Project"].query = mock_query

        # API Key認証のモック
        mock_api_key_obj = MagicMock()
        mock_api_key_obj.user = mock_user
        mock_db_models["ApiKey"].hash_token.return_value = "hashed_key"
        mock_db_models["ApiKey"].query.filter_by.return_value.first.return_value = mock_api_key_obj

        response = client.get("/api/v1/projects", headers={"X-API-Key": mock_api_key})

        assert response.status_code == 200
        data = response.json()
        assert "projects" in data
        assert isinstance(data["projects"], list)
        assert len(data["projects"]) == 2


def test_list_projects_requires_authentication(client: TestClient, mock_api_key, mock_db_models):
    """
    認証なしリクエストが 401 を返すことを確認するテスト
    """
    # 認証ヘッダーなしでリクエスト
    response = client.get("/api/v1/projects")

    # FastAPI のバリデーションエラー（422）または認証エラー（401）が返る
    # ヘッダーが必須の場合、422 が返る可能性がある
    assert response.status_code in [401, 422]

    # 不正な API Key でリクエスト
    with (
        patch("nexuscore.webapp.models.ApiKey") as MockApiKey,
        patch("nexuscore.webapp.models.User"),
    ):
        MockApiKey.hash_token.return_value = "hashed_invalid_key"
        MockApiKey.query.filter_by.return_value.first.return_value = (
            None  # 不正なキーは見つからない
        )

        response = client.get("/api/v1/projects", headers={"X-API-Key": "invalid-api-key"})

        # 無効な API Key は 401 を返す（500 ではない）
        assert response.status_code == 401
        data = response.json()
        # CR-NEXUS-034: トップレベル error 形式（Option A）
        assert "error" in data
        assert "code" in data["error"]
        assert data["error"]["code"] == "UNAUTHORIZED"
        error_str = data["error"]["message"].lower()
        assert "api key" in error_str or "unauthorized" in error_str
        assert "detail" not in data


def test_list_projects_requires_header_authentication(client: TestClient):
    """
    プロジェクト一覧取得は認証必須
    """
    response = client.get("/api/v1/projects")
    assert response.status_code == 422  # FastAPI のバリデーションエラー（必須ヘッダー欠如）


def test_create_project_success(client: TestClient, mock_api_key, mock_db_models):
    """
    プロジェクト作成の正常系テスト
    """
    # モックの設定
    mock_user = MagicMock()
    mock_user.id = 1
    mock_db_models["User"].query.first.return_value = mock_user

    mock_project = MagicMock()
    mock_project.id = 1
    mock_project.name = "New Project"
    mock_project.repo_url = "https://github.com/owner/repo"
    mock_project.local_path = "/path/to/project"
    mock_project.context_bundle_path = None
    mock_project.created_at = "2025-01-01T00:00:00"
    mock_project.updated_at = "2025-01-01T00:00:00"

    mock_db_models["Project"].return_value = mock_project

    # API Key認証のモック
    mock_api_key_obj = MagicMock()
    mock_api_key_obj.user = mock_user
    mock_db_models["ApiKey"].hash_token.return_value = "hashed_key"
    mock_db_models["ApiKey"].query.filter_by.return_value.first.return_value = mock_api_key_obj

    response = client.post(
        "/api/v1/projects",
        json={
            "name": "New Project",
            "repo_url": "https://github.com/owner/repo",
            "local_path": "/path/to/project",
        },
        headers={"X-API-Key": mock_api_key},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["id"] == 1
    assert data["name"] == "New Project"
    assert data["repo_url"] == "https://github.com/owner/repo"
    assert data["local_path"] == "/path/to/project"


def test_create_project_validation_error(client: TestClient, mock_api_key, mock_db_models):
    """
    プロジェクト作成のバリデーションエラーテスト
    """
    # モックの設定
    mock_user = MagicMock()
    mock_user.id = 1
    mock_db_models["User"].query.first.return_value = mock_user

    # API Key認証のモック
    mock_api_key_obj = MagicMock()
    mock_api_key_obj.user = mock_user
    mock_db_models["ApiKey"].hash_token.return_value = "hashed_key"
    mock_db_models["ApiKey"].query.filter_by.return_value.first.return_value = mock_api_key_obj

    # name が欠如
    response = client.post(
        "/api/v1/projects",
        json={"repo_url": "https://github.com/owner/repo", "local_path": "/path/to/project"},
        headers={"X-API-Key": mock_api_key},
    )

    assert response.status_code == 422  # FastAPI のバリデーションエラー


def test_get_project_success(client: TestClient, mock_api_key, mock_db_models):
    """
    プロジェクト取得の正常系テスト
    """
    # モックの設定
    mock_user = MagicMock()
    mock_user.id = 1
    mock_db_models["User"].query.first.return_value = mock_user

    mock_project = MagicMock()
    mock_project.id = 1
    mock_project.name = "Project 1"
    mock_project.repo_url = "https://github.com/owner/repo"
    mock_project.local_path = "/path/to/project"
    mock_project.context_bundle_path = "/path/to/context.json"
    mock_project.created_at = "2025-01-01T00:00:00"
    mock_project.updated_at = "2025-01-01T00:00:00"

    mock_query = MagicMock()
    mock_query.filter_by.return_value.first.return_value = mock_project
    mock_db_models["Project"].query = mock_query

    # API Key認証のモック
    mock_api_key_obj = MagicMock()
    mock_api_key_obj.user = mock_user
    mock_db_models["ApiKey"].hash_token.return_value = "hashed_key"
    mock_db_models["ApiKey"].query.filter_by.return_value.first.return_value = mock_api_key_obj

    response = client.get("/api/v1/projects/1", headers={"X-API-Key": mock_api_key})

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == 1
    assert data["name"] == "Project 1"
    assert data["repo_url"] == "https://github.com/owner/repo"
    assert data["local_path"] == "/path/to/project"
    assert data["context_bundle_path"] == "/path/to/context.json"


def test_get_project_not_found(client: TestClient, mock_api_key, mock_db_models):
    """
    プロジェクトが見つからない場合のテスト
    """
    # モックの設定
    mock_user = MagicMock()
    mock_user.id = 1
    mock_db_models["User"].query.first.return_value = mock_user

    mock_query = MagicMock()
    mock_query.filter_by.return_value.first.return_value = None
    mock_db_models["Project"].query = mock_query

    # API Key認証のモック
    mock_api_key_obj = MagicMock()
    mock_api_key_obj.user = mock_user
    mock_db_models["ApiKey"].hash_token.return_value = "hashed_key"
    mock_db_models["ApiKey"].query.filter_by.return_value.first.return_value = mock_api_key_obj

    response = client.get("/api/v1/projects/999", headers={"X-API-Key": mock_api_key})

    assert response.status_code == 404
    data = response.json()
    # FastAPIのHTTPExceptionは detail キーにエラー情報を入れる
    # CR-NEXUS-034: トップレベル error 形式（Option A）
    assert "error" in data
    assert "code" in data["error"]
    assert data["error"]["code"] == "NOT_FOUND"
    assert "not found" in data["error"]["message"].lower()
    assert "detail" not in data


def test_projects_endpoints_are_documented_in_openapi(client: TestClient):
    """
    OpenAPI スキーマに projects エンドポイントが定義されていることを確認
    """
    response = client.get("/api/openapi.json")
    assert response.status_code == 200

    openapi_schema = response.json()
    assert "paths" in openapi_schema

    # /api/v1/projects の確認
    assert "/api/v1/projects" in openapi_schema["paths"]
    projects_path = openapi_schema["paths"]["/api/v1/projects"]
    assert "get" in projects_path
    assert "post" in projects_path

    # /api/v1/projects/{project_id} の確認
    assert "/api/v1/projects/{project_id}" in openapi_schema["paths"]
    project_detail_path = openapi_schema["paths"]["/api/v1/projects/{project_id}"]
    assert "get" in project_detail_path


def test_projects_response_structure(client: TestClient, mock_api_key, mock_db_models):
    """
    プロジェクトレスポンス構造の詳細テスト
    """
    # モックの設定
    mock_user = MagicMock()
    mock_user.id = 1
    mock_db_models["User"].query.first.return_value = mock_user

    mock_project = MagicMock()
    mock_project.id = 1
    mock_project.name = "Test Project"
    mock_project.repo_url = "https://github.com/owner/repo"
    mock_project.local_path = "/path/to/project"
    mock_project.context_bundle_path = None
    mock_project.created_at = "2025-01-01T00:00:00"
    mock_project.updated_at = "2025-01-01T00:00:00"

    mock_query = MagicMock()
    mock_query.filter_by.return_value.first.return_value = mock_project
    mock_db_models["Project"].query = mock_query

    # API Key認証のモック
    mock_api_key_obj = MagicMock()
    mock_api_key_obj.user = mock_user
    mock_db_models["ApiKey"].hash_token.return_value = "hashed_key"
    mock_db_models["ApiKey"].query.filter_by.return_value.first.return_value = mock_api_key_obj

    response = client.get("/api/v1/projects/1", headers={"X-API-Key": mock_api_key})

    assert response.status_code == 200
    data = response.json()

    # レスポンス構造を確認
    assert "id" in data
    assert "name" in data
    assert "repo_url" in data
    assert "local_path" in data
    assert "created_at" in data
    assert "updated_at" in data
    assert isinstance(data["id"], int)
    assert isinstance(data["name"], str)
    assert isinstance(data["local_path"], str)
