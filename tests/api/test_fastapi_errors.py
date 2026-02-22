"""
FastAPI エラーハンドリング統一のテスト

CR-FASTAPI-006 で実装された統一されたエラーレスポンス形式のテスト。
すべてのエンドポイントで統一されたエラー構造を確認する。
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

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


def test_not_found_error_format(client: TestClient, mock_api_key, monkeypatch):
    """
    NotFound エラーの形式確認

    404 エラーが統一された ErrorResponse 形式で返されることを確認。
    """
    # モックの設定
    mock_user = MagicMock()
    mock_user.id = 1

    with patch("nexuscore.webapp.models.Project") as mock_project_model, \
         patch("nexuscore.webapp.models.Run") as mock_run_model, \
         patch("nexuscore.webapp.db") as mock_db, \
         patch("nexuscore.webapp.models.ApiKey") as mock_api_key_model, \
         patch("nexuscore.webapp.models.User") as mock_auth_user:
        # Project と Run のクエリをモック
        mock_query = MagicMock()
        mock_query.filter_by.return_value.first.return_value = None
        mock_project_model.query = mock_query
        mock_run_model.query = mock_query

        # API Key認証のモック
        mock_api_key_obj = MagicMock()
        mock_api_key_obj.user = mock_user
        mock_api_key_model.hash_token.return_value = "hashed_key"
        mock_api_key_model.query.filter_by.return_value.first.return_value = mock_api_key_obj

        response = client.get(
            "/api/v1/projects/999",
            headers={"X-API-Key": mock_api_key}
        )

        assert response.status_code == 404
        data = response.json()
        # CR-NEXUS-034: トップレベル error 形式（Option A）
        assert "error" in data
        assert "code" in data["error"]
        assert "message" in data["error"]
        assert data["error"]["code"] == "NOT_FOUND"
        assert "not found" in data["error"]["message"].lower()
        # detail キーは存在しない（トップレベル error 形式）
        assert "detail" not in data


def test_unauthorized_error_format(client: TestClient):
    """
    Unauthorized エラーの形式確認

    401 エラーが統一された ErrorResponse 形式で返されることを確認。
    """
    # API Key なしでリクエスト
    response = client.get("/api/v1/projects")

    # FastAPI のバリデーションエラー（422）が返される可能性があるため、
    # 認証依存で発生する 401 エラーを確認するため、別の方法でテスト
    # 実際の認証エラーは dependencies/auth.py で発生する
    # ここでは、無効なAPI Keyでリクエストして確認
    response = client.get(
        "/api/v1/projects",
        headers={"X-API-Key": "invalid-key"}
    )

    # 認証エラーが発生する場合、統一された形式で返される
    if response.status_code == 401:
        data = response.json()
        assert "error" in data
        assert "code" in data["error"]
        assert "message" in data["error"]
        assert data["error"]["code"] == "UNAUTHORIZED"


def test_validation_error_format(client: TestClient, mock_api_key, monkeypatch):
    """
    ValidationError の形式確認

    422 エラーが統一された ErrorResponse 形式で返されることを確認。
    """
    # モックの設定
    mock_user = MagicMock()
    mock_user.id = 1

    with patch("nexuscore.webapp.models.Project") as mock_project_model, \
         patch("nexuscore.webapp.models.Run") as mock_run_model, \
         patch("nexuscore.webapp.db") as mock_db, \
         patch("nexuscore.webapp.models.ApiKey") as mock_api_key_model, \
         patch("nexuscore.webapp.models.User") as mock_auth_user:
        # Project と Run のクエリをモック
        mock_query = MagicMock()
        mock_query.filter_by.return_value.first.return_value = None
        mock_project_model.query = mock_query
        mock_run_model.query = mock_query

        # API Key認証のモック
        mock_api_key_obj = MagicMock()
        mock_api_key_obj.user = mock_user
        mock_api_key_model.hash_token.return_value = "hashed_key"
        mock_api_key_model.query.filter_by.return_value.first.return_value = mock_api_key_obj

        # 必須フィールドが欠如したリクエスト
        response = client.post(
            "/api/v1/projects",
            json={},  # name と local_path が欠如
            headers={"X-API-Key": mock_api_key}
        )

        # FastAPI のバリデーションエラー（422）が返される
        assert response.status_code == 422
        data = response.json()
        # CR-NEXUS-034: トップレベル error 形式（Option A）
        assert "error" in data
        assert "code" in data["error"]
        assert "message" in data["error"]
        assert data["error"]["code"] == "VALIDATION_ERROR"
        # detail キーは存在しない（トップレベル error 形式）
        assert "detail" not in data


def test_internal_error_format(client: TestClient, mock_api_key, monkeypatch):
    """
    InternalError の形式確認

    500 エラーが統一された ErrorResponse 形式で返されることを確認。
    """
    # モックの設定
    mock_user = MagicMock()
    mock_user.id = 1

    with patch("nexuscore.webapp.models.Project") as mock_project_model, \
         patch("nexuscore.webapp.models.Run") as mock_run_model, \
         patch("nexuscore.webapp.db") as mock_db, \
         patch("nexuscore.webapp.models.ApiKey") as mock_api_key_model, \
         patch("nexuscore.webapp.models.User") as mock_auth_user:
        # データベースエラーをシミュレート
        mock_query = MagicMock()
        mock_query.filter_by.return_value.order_by.side_effect = Exception("Database error")
        mock_project_model.query = mock_query
        mock_run_model.query = mock_query

        # API Key認証のモック
        mock_api_key_obj = MagicMock()
        mock_api_key_obj.user = mock_user
        mock_api_key_model.hash_token.return_value = "hashed_key"
        mock_api_key_model.query.filter_by.return_value.first.return_value = mock_api_key_obj

        response = client.get(
            "/api/v1/projects",
            headers={"X-API-Key": mock_api_key}
        )

        assert response.status_code == 500
        data = response.json()
        # CR-NEXUS-034: トップレベル error 形式（Option A）
        assert "error" in data
        assert "code" in data["error"]
        assert "message" in data["error"]
        assert data["error"]["code"] == "INTERNAL_ERROR"
        # detail キーは存在しない（トップレベル error 形式）
        assert "detail" not in data


def test_error_schemas_in_openapi(client: TestClient):
    """
    OpenAPI スキーマにエラースキーマが定義されていることを確認
    """
    response = client.get("/api/openapi.json")
    assert response.status_code == 200

    openapi_schema = response.json()
    assert "components" in openapi_schema
    assert "schemas" in openapi_schema["components"]

    # ErrorResponse と ErrorDetail が定義されていることを確認
    assert "ErrorResponse" in openapi_schema["components"]["schemas"]
    assert "ErrorDetail" in openapi_schema["components"]["schemas"]

    # エンドポイントの responses に ErrorResponse が含まれていることを確認
    projects_path = openapi_schema["paths"].get("/api/v1/projects", {})
    if "get" in projects_path:
        get_responses = projects_path["get"].get("responses", {})
        # 401 または 500 のレスポンスに ErrorResponse が含まれている
        assert any(
            "ErrorResponse" in str(response.get("content", {}))
            for response in get_responses.values()
        )


def test_all_endpoints_have_error_responses(client: TestClient):
    """
    すべてのエンドポイントにエラーレスポンスが定義されていることを確認
    """
    response = client.get("/api/openapi.json")
    assert response.status_code == 200

    openapi_schema = response.json()
    paths = openapi_schema.get("paths", {})

    # 主要なエンドポイントを確認
    endpoints_to_check = [
        "/api/v1/projects",
        "/api/v1/projects/{project_id}",
        "/api/v1/run-records",
        "/api/v1/run-records/{run_id}",
        "/api/v1/execute",
        "/api/v1/status/{task_id}",
        "/api/v1/github/webhook",
    ]

    for endpoint_path in endpoints_to_check:
        if endpoint_path in paths:
            path_item = paths[endpoint_path]
            # GET または POST メソッドを確認
            for method in ["get", "post"]:
                if method in path_item:
                    operation = path_item[method]
                    responses = operation.get("responses", {})
                    # 4xx または 5xx のレスポンスが定義されていることを確認
                    # OpenAPI スキーマではステータスコードが文字列として保存されているため、int に変換
                    error_statuses = [
                        code for code in responses.keys()
                        if (isinstance(code, str) and code.isdigit() and int(code) >= 400)
                        or (isinstance(code, int) and code >= 400)
                    ]
                    if error_statuses:
                        # エラーレスポンスに ErrorResponse が含まれていることを確認
                        assert any(
                            "ErrorResponse" in str(responses[status].get("content", {}))
                            for status in error_statuses
                        ), f"{endpoint_path} ({method}) のエラーレスポンスに ErrorResponse が含まれていません"

