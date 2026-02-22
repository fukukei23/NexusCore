"""
FastAPI RunView API エンドポイントのテスト (CR-NEXUS-029).

POST /api/v1/run-view/runs エンドポイントのテスト。
"""

import json
import pytest
from pathlib import Path
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
    """データベースモデルをモック（認証用）"""
    with patch("nexuscore.webapp.models.User") as mock_user, \
         patch("nexuscore.webapp.models.ApiKey") as mock_api_key_model, \
         patch("nexuscore.webapp.db") as mock_db:
        # API Key認証のモック
        mock_user_obj = MagicMock()
        mock_user_obj.id = 1
        mock_user.query.first.return_value = mock_user_obj

        mock_api_key_obj = MagicMock()
        mock_api_key_obj.user = mock_user_obj
        mock_api_key_model.hash_token.return_value = "hashed_key"
        mock_api_key_model.query.filter_by.return_value.first.return_value = mock_api_key_obj

        yield {
            "User": mock_user,
            "ApiKey": mock_api_key_model,
            "db": mock_db,
        }


@pytest.fixture
def isolated_state_dir(monkeypatch, tmp_path):
    """RunState ディレクトリを tmp に隔離"""
    state_dir = tmp_path / "run_state"
    state_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("NEXUSCORE_RUN_STATE_DIR", str(state_dir))
    monkeypatch.setenv("NEXUSCORE_RUN_LOCK_DIR", str(tmp_path / "run_lock"))
    monkeypatch.setenv("NEXUSCORE_RUNSTATE_HMAC_SECRET", "test-secret")
    return state_dir


def test_create_run_view_success(
    client: TestClient, mock_api_key, mock_db_models, isolated_state_dir, monkeypatch
):
    """POST /api/v1/runs で正常にRunを作成できる"""
    # Mock get_orchestrator to return a fake orchestrator
    class FakeOrchestrator:
        def __init__(self):
            self.project_path = "/tmp/test"
            self.calls = []

        def run_full_project(self, *args, **kwargs):
            self.calls.append("run_full_project")

    fake_orch = FakeOrchestrator()

    def mock_get_orchestrator(project_path=None, language="ja"):
        return fake_orch

    # run_with_authority をモックして paused を返す
    def mock_run_with_authority(*args, **kwargs):
        return {
            "status": "paused",
            "run_id": "test-run-created",
            "next_phase": "implementation",
        }

    with patch("nexuscore.api.routes.run_view.get_orchestrator", side_effect=mock_get_orchestrator), \
         patch("nexuscore.orchestrator.authority_runner.run_with_authority", side_effect=mock_run_with_authority):
        response = client.post(
            "/api/v1/runs",
            headers={"X-API-Key": mock_api_key},
            json={
                "requirement": "Create a simple app",
                "authority_level": "partial",
                "language": "ja",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["run_id"] == "test-run-created"
        assert data["status"] == "paused"
        assert data["phase"] == "implementation"
        # RunState raw JSON を返さない
        assert "schema_version" not in data
        assert "integrity" not in data

