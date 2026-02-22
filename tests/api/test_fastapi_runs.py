"""
FastAPI Runs エンドポイントのテスト

CR-FASTAPI-005 で作成された /api/v1/runs エンドポイントのテスト。
既存の Flask テストの期待値に準拠。
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


@pytest.fixture
def mock_db_models():
    """データベースモデルをモック"""
    with patch("nexuscore.webapp.models.Run") as mock_run, \
         patch("nexuscore.webapp.models.Project") as mock_project, \
         patch("nexuscore.webapp.models.User") as mock_user, \
         patch("nexuscore.webapp.db") as mock_db, \
         patch("nexuscore.webapp.models.ApiKey") as mock_api_key_model, \
         patch("nexuscore.webapp.models.User") as mock_auth_user:
        yield {
            "Run": mock_run,
            "Project": mock_project,
            "User": mock_user,
            "db": mock_db,
            "ApiKey": mock_api_key_model,
            "AuthUser": mock_auth_user,
        }


def test_list_runs_success(client: TestClient, mock_api_key, mock_db_models):
    """
    Run一覧取得の正常系テスト
    """
    # モックの設定
    mock_user = MagicMock()
    mock_user.id = 1
    mock_db_models["User"].query.first.return_value = mock_user

    mock_run1 = MagicMock()
    mock_run1.id = 1
    mock_run1.run_id = "run-123"
    mock_run1.project_id = 1
    mock_run1.status = "SUCCESS"
    mock_run1.started_at = "2025-01-01T00:00:00"
    mock_run1.finished_at = "2025-01-01T00:05:00"
    mock_run1.created_at = "2025-01-01T00:00:00"

    mock_run2 = MagicMock()
    mock_run2.id = 2
    mock_run2.run_id = "run-456"
    mock_run2.project_id = 1
    mock_run2.status = "FAILED"
    mock_run2.started_at = None
    mock_run2.finished_at = None
    mock_run2.created_at = "2025-01-02T00:00:00"

    from sqlalchemy import desc as sa_desc

    # desc() 関数をパッチして、モックオブジェクトを受け取った場合はそのまま返すようにする
    def mock_desc(column):
        # モックオブジェクトの場合はそのまま返す
        if isinstance(column, MagicMock):
            return column
        return sa_desc(column)

    with patch("nexuscore.api.routes.runs.desc", side_effect=mock_desc):
        mock_query = MagicMock()
        mock_query.join.return_value.filter.return_value.order_by.return_value.all.return_value = [mock_run1, mock_run2]
        mock_db_models["Run"].query = mock_query

        # API Key認証のモック
        mock_api_key_obj = MagicMock()
        mock_api_key_obj.user = mock_user
        mock_db_models["ApiKey"].hash_token.return_value = "hashed_key"
        mock_db_models["ApiKey"].query.filter_by.return_value.first.return_value = mock_api_key_obj

        response = client.get(
            "/api/v1/run-records",
            headers={"X-API-Key": mock_api_key}
        )

        assert response.status_code == 200
    data = response.json()
    assert "runs" in data
    assert isinstance(data["runs"], list)
    assert len(data["runs"]) == 2
    assert data["runs"][0]["run_id"] == "run-123"
    assert data["runs"][0]["status"] == "SUCCESS"


def test_list_runs_with_project_filter(client: TestClient, mock_api_key, mock_db_models):
    """
    Run一覧取得（プロジェクトIDでフィルタ）のテスト
    """
    # モックの設定
    mock_user = MagicMock()
    mock_user.id = 1
    mock_db_models["User"].query.first.return_value = mock_user

    mock_run = MagicMock()
    mock_run.id = 1
    mock_run.run_id = "run-123"
    mock_run.project_id = 1
    mock_run.status = "SUCCESS"
    mock_run.started_at = "2025-01-01T00:00:00"
    mock_run.finished_at = "2025-01-01T00:05:00"
    mock_run.created_at = "2025-01-01T00:00:00"

    from sqlalchemy import desc as sa_desc

    # desc() 関数をパッチして、モックオブジェクトを受け取った場合はそのまま返すようにする
    def mock_desc(column):
        # モックオブジェクトの場合はそのまま返す
        if isinstance(column, MagicMock):
            return column
        return sa_desc(column)

    with patch("nexuscore.api.routes.runs.desc", side_effect=mock_desc):
        # クエリチェーンを正しくモック: Run.query.join(Project).filter(...).filter(...).order_by(...).all()
        mock_query = MagicMock()
        mock_join_result = MagicMock()
        mock_filter1_result = MagicMock()  # Project.owner_id == user_id のフィルタ結果
        mock_filter2_result = MagicMock()  # Run.project_id == project_id のフィルタ結果
        mock_order_by_result = MagicMock()

        mock_query.join.return_value = mock_join_result
        mock_join_result.filter.return_value = mock_filter1_result
        mock_filter1_result.filter.return_value = mock_filter2_result
        mock_filter2_result.order_by.return_value = mock_order_by_result
        mock_order_by_result.all.return_value = [mock_run]

        mock_db_models["Run"].query = mock_query

        # CR-NEXUS-034: 認証のモックを設定（user_id を int 互換にする）
        mock_api_key_obj = MagicMock()
        mock_api_key_obj.user = mock_user
        mock_api_key_obj.user_id = 1  # int として設定
        mock_db_models["ApiKey"].hash_token.return_value = "hashed_key"
        mock_db_models["ApiKey"].query.filter_by.return_value.first.return_value = mock_api_key_obj

        response = client.get(
            "/api/v1/run-records?project_id=1",
            headers={"X-API-Key": mock_api_key}
        )

        assert response.status_code == 200
        data = response.json()
        assert "runs" in data
        assert len(data["runs"]) == 1
        assert data["runs"][0]["project_id"] == 1


def test_list_runs_requires_authentication(client: TestClient):
    """
    Run一覧取得は認証必須
    """
    response = client.get("/api/v1/run-records")
    assert response.status_code == 422  # FastAPI のバリデーションエラー（必須ヘッダー欠如）


def test_get_run_success(client: TestClient, mock_api_key, mock_db_models):
    """
    Run取得の正常系テスト
    """
    # モックの設定
    mock_user = MagicMock()
    mock_user.id = 1
    mock_db_models["User"].query.first.return_value = mock_user

    mock_run = MagicMock()
    mock_run.id = 1
    mock_run.run_id = "run-123"
    mock_run.project_id = 1
    mock_run.triggered_by = 1
    mock_run.status = "SUCCESS"
    mock_run.started_at = "2025-01-01T00:00:00"
    mock_run.finished_at = "2025-01-01T00:05:00"
    mock_run.autonomy_level = 2
    mock_run.llm_model_summary = "gpt-4"
    mock_run.requirement = "Test requirement"
    mock_run.created_at = "2025-01-01T00:00:00"

    mock_query = MagicMock()
    mock_query.join.return_value.filter.return_value.first.return_value = mock_run
    mock_db_models["Run"].query = mock_query

    # API Key認証のモック
    mock_api_key_obj = MagicMock()
    mock_api_key_obj.user = mock_user
    mock_db_models["ApiKey"].hash_token.return_value = "hashed_key"
    mock_db_models["ApiKey"].query.filter_by.return_value.first.return_value = mock_api_key_obj

    response = client.get(
        "/api/v1/run-records/run-123",
        headers={"X-API-Key": mock_api_key}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == 1
    assert data["run_id"] == "run-123"
    assert data["project_id"] == 1
    assert data["status"] == "SUCCESS"
    assert data["triggered_by"] == 1
    assert data["autonomy_level"] == 2
    assert data["llm_model_summary"] == "gpt-4"
    assert data["requirement"] == "Test requirement"


def test_get_run_not_found(client: TestClient, mock_api_key, mock_db_models):
    """
    Runが見つからない場合のテスト
    """
    # モックの設定
    mock_user = MagicMock()
    mock_user.id = 1
    mock_db_models["User"].query.first.return_value = mock_user

    mock_query = MagicMock()
    mock_query.join.return_value.filter.return_value.first.return_value = None
    mock_db_models["Run"].query = mock_query

    # API Key認証のモック
    mock_api_key_obj = MagicMock()
    mock_api_key_obj.user = mock_user
    mock_db_models["ApiKey"].hash_token.return_value = "hashed_key"
    mock_db_models["ApiKey"].query.filter_by.return_value.first.return_value = mock_api_key_obj

    response = client.get(
        "/api/v1/run-records/nonexistent-run-id",
        headers={"X-API-Key": mock_api_key}
    )

    assert response.status_code == 404
    data = response.json()
    # FastAPIのHTTPExceptionは detail キーにエラー情報を入れる
    # CR-NEXUS-034: トップレベル error 形式（Option A）
    assert "error" in data
    assert "code" in data["error"]
    assert "message" in data["error"]
    assert data["error"]["code"] == "NOT_FOUND"
    assert "not found" in data["error"]["message"].lower()
    assert "detail" not in data


def test_runs_endpoints_are_documented_in_openapi(client: TestClient):
    """
    OpenAPI スキーマに runs エンドポイントが定義されていることを確認
    """
    response = client.get("/api/openapi.json")
    assert response.status_code == 200

    openapi_schema = response.json()
    assert "paths" in openapi_schema

    # /api/v1/run-records の確認
    assert "/api/v1/run-records" in openapi_schema["paths"]
    runs_path = openapi_schema["paths"]["/api/v1/run-records"]
    assert "get" in runs_path

    # /api/v1/run-records/{run_id} の確認
    assert "/api/v1/run-records/{run_id}" in openapi_schema["paths"]
    run_detail_path = openapi_schema["paths"]["/api/v1/run-records/{run_id}"]
    assert "get" in run_detail_path


def test_runs_response_structure(client: TestClient, mock_api_key, mock_db_models):
    """
    Runレスポンス構造の詳細テスト
    """
    # モックの設定
    mock_user = MagicMock()
    mock_user.id = 1
    mock_db_models["User"].query.first.return_value = mock_user

    mock_run = MagicMock()
    mock_run.id = 1
    mock_run.run_id = "run-123"
    mock_run.project_id = 1
    mock_run.triggered_by = None
    mock_run.status = "PENDING"
    mock_run.started_at = None
    mock_run.finished_at = None
    mock_run.autonomy_level = None
    mock_run.llm_model_summary = None
    mock_run.requirement = None
    mock_run.created_at = "2025-01-01T00:00:00"

    mock_query = MagicMock()
    mock_query.join.return_value.filter.return_value.first.return_value = mock_run
    mock_db_models["Run"].query = mock_query

    # API Key認証のモック
    mock_api_key_obj = MagicMock()
    mock_api_key_obj.user = mock_user
    mock_db_models["ApiKey"].hash_token.return_value = "hashed_key"
    mock_db_models["ApiKey"].query.filter_by.return_value.first.return_value = mock_api_key_obj

    response = client.get(
        "/api/v1/run-records/run-123",
        headers={"X-API-Key": mock_api_key}
    )

    assert response.status_code == 200
    data = response.json()

    # レスポンス構造を確認
    assert "id" in data
    assert "run_id" in data
    assert "project_id" in data
    assert "status" in data
    assert "created_at" in data
    assert isinstance(data["id"], int)
    assert isinstance(data["run_id"], str)
    assert isinstance(data["project_id"], int)
    assert data["status"] in ["PENDING", "RUNNING", "SUCCESS", "FAILED"]

