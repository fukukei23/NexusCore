"""
API スモークテスト

外部統合 API（/api/v1/*）の HTTP ステータスと最低限の JSON キーを検証する軽量テスト。

UI スモークテストと同様、「壊れていないこと」を保証する用途に留める。

CR-NEXUS-037: FastAPI public API を対象とするよう修正（Flask webapp から切り替え）。
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from nexuscore.api.fastapi_app import app
from tests.api.helpers_api import assert_json_keys


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
    with (
        patch("nexuscore.webapp.models.Project") as mock_project_model,
        patch("nexuscore.webapp.models.Run") as mock_run_model,
        patch("nexuscore.webapp.models.User") as mock_user_model,
        patch("nexuscore.webapp.models.ApiKey") as mock_api_key_model,
        patch("nexuscore.webapp.db") as mock_db,
    ):

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


def test_get_projects_requires_api_key(client: TestClient):
    """API キーなしでプロジェクト一覧を取得すると 401/403/422 が返る"""
    # FastAPI では必須ヘッダーが欠如している場合、バリデーションエラー（422）が返される
    resp = client.get("/api/v1/projects")
    assert resp.status_code in (401, 403, 422)


def test_get_projects_with_api_key(client: TestClient, mock_api_key, mock_db_models):
    """有効な API キーでプロジェクト一覧を取得できる"""
    from sqlalchemy import desc as sa_desc

    # モックの設定
    def mock_desc(column):
        if isinstance(column, MagicMock):
            return column
        return sa_desc(column)

    with patch("nexuscore.api.routes._projects_crud.desc", side_effect=mock_desc):
        mock_query = MagicMock()
        mock_query.filter_by.return_value.order_by.return_value.all.return_value = [
            mock_db_models["project"]
        ]
        mock_db_models["Project"].query = mock_query

        headers = {"X-API-Key": mock_api_key}
        resp = client.get("/api/v1/projects", headers=headers)

        assert resp.status_code == 200

        data = resp.json()
        assert "projects" in data
        assert isinstance(data["projects"], list)

        if data["projects"]:
            project = data["projects"][0]
            assert_json_keys(project, ["id", "name"])


def test_post_run_requires_api_key(client: TestClient, mock_db_models):
    """API キーなしで Run を実行すると 401/403/422 が返る"""
    # FastAPI では必須ヘッダーが欠如している場合、バリデーションエラー（422）が返される
    url = f"/api/v1/projects/{mock_db_models['project'].id}/run"
    resp = client.post(url, json={"requirement": "Test run"})
    assert resp.status_code in (401, 403, 422)


def test_post_run_with_api_key(client: TestClient, mock_api_key, mock_db_models):
    """有効な API キーで Run を実行できる"""
    import uuid

    # モックの設定
    mock_db_models["Project"].query.filter_by.return_value.first.return_value = mock_db_models[
        "project"
    ]

    mock_run = MagicMock()
    mock_run.id = 1
    mock_run.run_id = uuid.uuid4().hex
    mock_run.project_id = mock_db_models["project"].id
    mock_run.status = "PENDING"
    mock_db_models["Run"].return_value = mock_run

    url = f"/api/v1/projects/{mock_db_models['project'].id}/run"
    headers = {"X-API-Key": mock_api_key}
    payload = {
        "requirement": "Smoke test self-healing run",
        "autonomy_level": 1,
        "fast_lane": True,
    }

    with (
        patch("nexuscore.webapp.orchestrator_inline.run_orchestrator_inline"),
        patch("nexuscore.webapp.celery_app.run_orchestrator_task"),
        patch("os.getenv", return_value="1"),
    ):  # Celery 使用を強制（202 を返す）
        resp = client.post(url, headers=headers, json=payload)

        # 非同期 = 202 / 同期 = 200 を許容
        assert resp.status_code in (200, 202)

        data = resp.json()
        assert_json_keys(data, ["run_id", "project_id", "status"])


def test_get_latest_run_requires_api_key(client: TestClient, mock_db_models):
    """API キーなしで最新 Run を取得すると 401/403/422 が返る"""
    # FastAPI では必須ヘッダーが欠如している場合、バリデーションエラー（422）が返される
    url = f"/api/v1/projects/{mock_db_models['project'].id}/runs/latest"
    resp = client.get(url)
    assert resp.status_code in (401, 403, 422)


def test_get_latest_run_with_api_key(client: TestClient, mock_api_key, mock_db_models):
    """有効な API キーで最新 Run を取得できる"""
    from datetime import datetime

    # モックの設定
    mock_db_models["Project"].query.filter_by.return_value.first.return_value = mock_db_models[
        "project"
    ]

    mock_run = MagicMock()
    mock_run.id = 1
    mock_run.run_id = "test-run-123"
    mock_run.project_id = 1
    mock_run.status = "SUCCESS"
    mock_run.started_at = datetime(2025, 1, 1, 0, 0, 0)
    mock_run.finished_at = datetime(2025, 1, 1, 0, 5, 0)

    # desc() をモック（test_fastapi_project_runs.py と同じパターン）
    with patch("nexuscore.api.routes._projects_runs.desc") as mock_desc:
        mock_desc.return_value = MagicMock()

        # Run のクエリチェーンをモック
        mock_query_chain = MagicMock()
        mock_query_chain.order_by.return_value.first.return_value = mock_run
        mock_db_models["Run"].query.filter_by.return_value = mock_query_chain

        url = f"/api/v1/projects/{mock_db_models['project'].id}/runs/latest"
        headers = {"X-API-Key": mock_api_key}

        resp = client.get(url, headers=headers)

        assert resp.status_code == 200

        data = resp.json()
        # {"run": {...}} 形式を想定
        assert "run" in data

        if data["run"] is not None:
            run_obj = data["run"]
            assert_json_keys(run_obj, ["id", "run_id", "status"])


def test_get_latest_run_without_runs(client: TestClient, mock_api_key, mock_db_models):
    """Run がない場合でも最新 Run 取得が 200 を返す"""
    # モックの設定
    mock_db_models["Project"].query.filter_by.return_value.first.return_value = mock_db_models[
        "project"
    ]

    # desc() をモック（test_fastapi_project_runs.py と同じパターン）
    with patch("nexuscore.api.routes._projects_runs.desc") as mock_desc:
        mock_desc.return_value = MagicMock()

        # Run が見つからない場合
        mock_query_chain = MagicMock()
        mock_query_chain.order_by.return_value.first.return_value = None
        mock_db_models["Run"].query.filter_by.return_value = mock_query_chain

        url = f"/api/v1/projects/{mock_db_models['project'].id}/runs/latest"
        headers = {"X-API-Key": mock_api_key}

        resp = client.get(url, headers=headers)

        assert resp.status_code == 200

        data = resp.json()
        assert "run" in data
        # Run がない場合は null を許容
        assert data["run"] is None or isinstance(data["run"], dict)
