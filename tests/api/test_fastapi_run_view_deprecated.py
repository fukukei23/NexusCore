"""
FastAPI RunView deprecated endpoints smoke test (CR-NEXUS-032).

Minimal test to verify deprecated /api/v1/run-view/runs endpoints still work.
"""

import json
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
    """データベースモデルをモック（認証用）"""
    with (
        patch("nexuscore.webapp.models.User") as mock_user,
        patch("nexuscore.webapp.models.ApiKey") as mock_api_key_model,
        patch("nexuscore.webapp.db") as mock_db,
    ):
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


def test_deprecated_get_run_view_still_works(
    client: TestClient, mock_api_key, mock_db_models, isolated_state_dir
):
    """Deprecated GET /api/v1/run-view/runs/{run_id} がまだ動作することを確認"""
    run_id = "test-run-deprecated"

    # Create a minimal RunState
    state_file = isolated_state_dir / f"{run_id}.json"
    state = {
        "schema_version": "1.0",
        "run_id": run_id,
        "status": "PAUSED",
        "authority_level": "partial",
        "next_phase": "implementation",
        "updated_at": "2025-01-01T00:00:00+00:00",
    }
    state_file.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")

    response = client.get(
        f"/api/v1/run-view/runs/{run_id}",
        headers={"X-API-Key": mock_api_key},
    )

    # Should work same as canonical endpoint
    assert response.status_code == 200
    data = response.json()
    assert data["run_id"] == run_id
    assert data["status"] == "PAUSED"
    # RunState raw JSON を返さない
    assert "schema_version" not in data
    assert "integrity" not in data
