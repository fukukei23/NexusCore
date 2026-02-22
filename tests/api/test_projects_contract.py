"""
Projects API Contract Tests

CR-NEXUS-040: Projects API のレスポンス shape を契約として固定するテスト。
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
    mock_key = "test-api-key-123"
    monkeypatch.setenv("NEXUSCORE_API_KEY", mock_key)
    return mock_key


@pytest.fixture
def mock_db_models():
    """データベースモデルをモック"""
    with patch("nexuscore.webapp.models.Project") as mock_project_model, \
         patch("nexuscore.webapp.models.Run") as mock_run_model, \
         patch("nexuscore.webapp.models.User") as mock_user_model, \
         patch("nexuscore.webapp.models.ApiKey") as mock_api_key_model, \
         patch("nexuscore.webapp.db") as mock_db:

        mock_user = MagicMock()
        mock_user.id = 1

        mock_project = MagicMock()
        mock_project.id = 1
        mock_project.name = "Test Project"
        mock_project.owner_id = 1
        mock_project.repo_url = "https://github.com/example/repo"
        mock_project.local_path = "/tmp/test"
        mock_project.created_at = "2025-01-01T00:00:00"
        mock_project.updated_at = "2025-01-01T00:00:00"

        mock_api_key_obj = MagicMock()
        mock_api_key_obj.user = mock_user
        mock_api_key_obj.user_id = 1
        mock_api_key_model.hash_token.return_value = "hashed_key"
        mock_api_key_model.query.filter_by.return_value.first.return_value = mock_api_key_obj

        yield {
            "Project": mock_project_model,
            "Run": mock_run_model,
            "User": mock_user_model,
            "ApiKey": mock_api_key_model,
            "db": mock_db,
            "user": mock_user,
            "project": mock_project,
        }


def test_get_projects_response_shape(client: TestClient, mock_api_key, mock_db_models):
    """
    GET /api/v1/projects の成功レスポンス shape を検証
    Contract: トップレベルに "projects" キーを持つこと
    """
    from sqlalchemy import desc as sa_desc

    def mock_desc(column):
        if isinstance(column, MagicMock):
            return column
        return sa_desc(column)

    with patch("nexuscore.api.routes.projects.desc", side_effect=mock_desc):
        mock_query = MagicMock()
        mock_query.filter_by.return_value.order_by.return_value.all.return_value = [mock_db_models["project"]]
        mock_db_models["Project"].query = mock_query

        headers = {"X-API-Key": mock_api_key}
        resp = client.get("/api/v1/projects", headers=headers)

        assert resp.status_code == 200
        data = resp.json()

        # Contract: トップレベルに "projects" キーを持つこと
        assert "projects" in data
        assert isinstance(data["projects"], list)

        # Contract: projects が空でない場合の shape
        if data["projects"]:
            project = data["projects"][0]
            # smoke テストが期待する最小限のキー
            assert "id" in project
            assert "name" in project


def test_get_latest_run_response_shape_with_run(client: TestClient, mock_api_key, mock_db_models):
    """
    GET /api/v1/projects/{project_id}/runs/latest の成功レスポンス shape を検証（run あり）
    Contract: トップレベルに "run" キーを持ち、run が dict であること
    """
    from datetime import datetime

    mock_db_models["Project"].query.filter_by.return_value.first.return_value = mock_db_models["project"]

    mock_run = MagicMock()
    mock_run.id = 1
    mock_run.run_id = "test-run-123"
    mock_run.project_id = 1
    mock_run.status = "SUCCESS"
    mock_run.started_at = datetime(2025, 1, 1, 0, 0, 0)
    mock_run.finished_at = datetime(2025, 1, 1, 0, 5, 0)

    with patch("nexuscore.api.routes.projects.desc") as mock_desc:
        mock_desc.return_value = MagicMock()

        mock_query_chain = MagicMock()
        mock_query_chain.order_by.return_value.first.return_value = mock_run
        mock_db_models["Run"].query.filter_by.return_value = mock_query_chain

        url = f"/api/v1/projects/{mock_db_models['project'].id}/runs/latest"
        headers = {"X-API-Key": mock_api_key}

        resp = client.get(url, headers=headers)

        assert resp.status_code == 200
        data = resp.json()

        # Contract: トップレベルに "run" キーを持つこと
        assert "run" in data
        # Contract: run が dict であること（null ではない）
        assert isinstance(data["run"], dict)
        # Contract: smoke テストが期待する最小限のキー
        assert "id" in data["run"]
        assert "run_id" in data["run"]
        assert "status" in data["run"]


def test_get_latest_run_response_shape_without_run(client: TestClient, mock_api_key, mock_db_models):
    """
    GET /api/v1/projects/{project_id}/runs/latest の成功レスポンス shape を検証（run なし）
    Contract: トップレベルに "run" キーを持ち、run が null であること
    """
    mock_db_models["Project"].query.filter_by.return_value.first.return_value = mock_db_models["project"]

    with patch("nexuscore.api.routes.projects.desc") as mock_desc:
        mock_desc.return_value = MagicMock()

        mock_query_chain = MagicMock()
        mock_query_chain.order_by.return_value.first.return_value = None
        mock_db_models["Run"].query.filter_by.return_value = mock_query_chain

        url = f"/api/v1/projects/{mock_db_models['project'].id}/runs/latest"
        headers = {"X-API-Key": mock_api_key}

        resp = client.get(url, headers=headers)

        assert resp.status_code == 200
        data = resp.json()

        # Contract: トップレベルに "run" キーを持つこと
        assert "run" in data
        # Contract: run が null であること
        assert data["run"] is None


def test_projects_error_response_envelope_401(client: TestClient):
    """
    Projects API のエラーレスポンス shape を検証（401）
    Contract: トップレベルに "error" キーを持ち、"detail" がトップレベルにないこと
    """
    resp = client.get("/api/v1/projects")

    # 401/403/422 のいずれかが返る（認証エラー）
    assert resp.status_code in (401, 403, 422)

    data = resp.json()

    # Contract: トップレベルに "error" キーを持つこと（CR-NEXUS-034 Option A）
    assert "error" in data
    assert isinstance(data["error"], dict)

    # Contract: "error" に "code" と "message" が含まれること
    assert "code" in data["error"]
    assert "message" in data["error"]

    # Contract: "detail" がトップレベルにないこと（FastAPI標準の {"detail": ...} 形式ではない）
    assert "detail" not in data


def test_projects_error_response_envelope_404(client: TestClient, mock_api_key, mock_db_models):
    """
    Projects API のエラーレスポンス shape を検証（404）
    Contract: トップレベルに "error" キーを持ち、"detail" がトップレベルにないこと
    """
    mock_db_models["Project"].query.filter_by.return_value.first.return_value = None

    url = "/api/v1/projects/99999/runs/latest"
    headers = {"X-API-Key": mock_api_key}

    resp = client.get(url, headers=headers)

    assert resp.status_code == 404

    data = resp.json()

    # Contract: トップレベルに "error" キーを持つこと（CR-NEXUS-034 Option A）
    assert "error" in data
    assert isinstance(data["error"], dict)

    # Contract: "error" に "code" と "message" が含まれること
    assert "code" in data["error"]
    assert "message" in data["error"]

    # Contract: "detail" がトップレベルにないこと
    assert "detail" not in data


def test_projects_openapi_schema_includes_response_model(client: TestClient):
    """
    OpenAPI schema に projects エンドポイントの response_model が含まれることを検証
    """
    resp = client.get("/api/openapi.json")
    assert resp.status_code == 200

    schema = resp.json()

    # GET /api/v1/projects の 200 レスポンスが schema を参照していることを確認
    projects_path = schema["paths"].get("/api/v1/projects", {})
    assert "get" in projects_path

    get_op = projects_path["get"]
    responses = get_op.get("responses", {})
    response_200 = responses.get("200", {})

    # Contract: 200 レスポンスに content と schema が含まれること
    assert "content" in response_200
    content = response_200["content"]
    assert "application/json" in content

    json_content = content["application/json"]
    assert "schema" in json_content

    # Contract: schema が $ref または components.schemas に定義されていること
    schema_ref = json_content["schema"]
    if "$ref" in schema_ref:
        # $ref の場合、components.schemas に定義されている
        ref_path = schema_ref["$ref"]
        assert ref_path.startswith("#/components/schemas/")
        schema_name = ref_path.split("/")[-1]
        assert schema_name in schema.get("components", {}).get("schemas", {})

    # GET /api/v1/projects/{project_id}/runs/latest の 200 レスポンスも確認
    latest_run_path = schema["paths"].get("/api/v1/projects/{project_id}/runs/latest", {})
    assert "get" in latest_run_path

    get_op_latest = latest_run_path["get"]
    responses_latest = get_op_latest.get("responses", {})
    response_200_latest = responses_latest.get("200", {})

    assert "content" in response_200_latest
    content_latest = response_200_latest["content"]
    assert "application/json" in content_latest

    json_content_latest = content_latest["application/json"]
    assert "schema" in json_content_latest

