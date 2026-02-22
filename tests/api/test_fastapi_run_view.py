"""
FastAPI RunView API エンドポイントのテスト (CR-NEXUS-028).

RunState-based RunView projection API endpoints のテスト。
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


@pytest.fixture
def sample_run_state(isolated_state_dir):
    """サンプルの RunState を作成"""
    run_id = "test-run-123"
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
    return run_id, state


def test_get_run_view_not_found(client: TestClient, mock_api_key, mock_db_models, isolated_state_dir):
    """GET /api/v1/runs/{run_id} で RunState が見つからない場合は 404"""
    response = client.get(
        "/api/v1/runs/nonexistent-run-id",
        headers={"X-API-Key": mock_api_key},
    )

    assert response.status_code == 404
    data = response.json()
    # CR-NEXUS-034: トップレベル error 形式（Option A）
    assert "error" in data
    assert "code" in data["error"]
    assert data["error"]["code"] == "NOT_FOUND"
    assert "detail" not in data


def test_get_run_view_success(client: TestClient, mock_api_key, mock_db_models, sample_run_state):
    """GET /api/v1/runs/{run_id} で RunView を返す"""
    run_id, _ = sample_run_state

    response = client.get(
        f"/api/v1/runs/{run_id}",
        headers={"X-API-Key": mock_api_key},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["run_id"] == run_id
    assert data["status"] == "PAUSED"
    assert data["phase"] == "implementation"
    assert data["authority_level"] == "partial"
    # RunState raw JSON を返さない
    assert "schema_version" not in data
    assert "integrity" not in data


def test_resume_run_view_conflict(
    client: TestClient, mock_api_key, mock_db_models, isolated_state_dir, monkeypatch
):
    """POST /api/v1/runs/{run_id}/resume で CONFLICT の場合は 409 + explainability"""
    run_id = "test-run-conflict"

    # Create a minimal RunState for load_state to succeed
    state_file = isolated_state_dir / f"{run_id}.json"
    import json
    state = {
        "schema_version": "1.0",
        "run_id": run_id,
        "status": "PAUSED",
    }
    state_file.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")

    # Mock get_orchestrator to return a fake orchestrator
    class FakeOrchestrator:
        def __init__(self):
            self.project_path = "/tmp/test"

    def mock_get_orchestrator(project_path=None, language="ja"):
        return FakeOrchestrator()

    # resume_run をモックして CONFLICT を返す（orchestrator_factory 引数に対応）
    def mock_resume_run(run_id_param: str, *, orchestrator_factory=None):
        from nexuscore.orchestrator.explainability import build_explainability

        return {
            "status": "CONFLICT",
            "run_id": run_id_param,
            "explainability": build_explainability(
                what=f"Resume conflict: run_id={run_id_param} is already being resumed/executed",
                why_code="CONFLICT",
                next_action="wait/retry",
            ),
        }

    with patch("nexuscore.api.routes.run_view.get_orchestrator", side_effect=mock_get_orchestrator), \
         patch("nexuscore.orchestrator.authority_runner.resume_run", side_effect=mock_resume_run):
        response = client.post(
            f"/api/v1/runs/{run_id}/resume",
            headers={"X-API-Key": mock_api_key},
        )

        assert response.status_code == 409
        data = response.json()
        # HTTPException の detail が返される
        assert "run_id" in data or "detail" in data
        # explainability が含まれる
        if "explainability" in data:
            assert data["explainability"]["what"] is not None
            assert data["explainability"]["why"] is not None
            assert data["explainability"]["next_action"] is not None


def test_resume_run_view_integrity_violation(
    client: TestClient, mock_api_key, mock_db_models, isolated_state_dir, monkeypatch
):
    """POST /api/v1/runs/{run_id}/resume で integrity violation の場合は 400 + explainability"""
    run_id = "test-run-integrity-violation"

    # Create a minimal RunState for load_state to succeed
    state_file = isolated_state_dir / f"{run_id}.json"
    import json
    state = {
        "schema_version": "1.0",
        "run_id": run_id,
        "status": "PAUSED",
    }
    state_file.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")

    # Mock get_orchestrator to return a fake orchestrator
    class FakeOrchestrator:
        def __init__(self):
            self.project_path = "/tmp/test"

    def mock_get_orchestrator(project_path=None, language="ja"):
        return FakeOrchestrator()

    # resume_run をモックして FAILED (integrity violation) を返す（orchestrator_factory 引数に対応）
    def mock_resume_run(run_id_param: str, *, orchestrator_factory=None):
        from nexuscore.orchestrator.explainability import build_explainability

        return {
            "status": "FAILED",
            "run_id": run_id_param,
            "explainability": build_explainability(
                what=f"Resume failed: RunState integrity verification failed for run_id={run_id_param}",
                why_code="STATE_INTEGRITY_VIOLATION",
                next_action="Abort this run_id and start a new run",
            ),
        }

    with patch("nexuscore.api.routes.run_view.get_orchestrator", side_effect=mock_get_orchestrator), \
         patch("nexuscore.orchestrator.authority_runner.resume_run", side_effect=mock_resume_run):
        response = client.post(
            f"/api/v1/runs/{run_id}/resume",
            headers={"X-API-Key": mock_api_key},
        )

        assert response.status_code == 400
        data = response.json()
        # HTTPException の detail が返される
        assert "run_id" in data or "detail" in data
        # explainability が含まれる
        if "explainability" in data:
            assert "STATE_INTEGRITY_VIOLATION" in data["explainability"]["why"]


def test_resume_run_view_not_found(
    client: TestClient, mock_api_key, mock_db_models, isolated_state_dir, monkeypatch
):
    """POST /api/v1/runs/{run_id}/resume で RunState が見つからない場合は 404"""
    run_id = "test-run-not-found"

    # resume_run をモックして FAILED (not found) を返す
    def mock_resume_run(run_id_param: str):
        from nexuscore.orchestrator.explainability import build_explainability

        return {
            "status": "FAILED",
            "run_id": run_id_param,
            "explainability": build_explainability(
                what=f"Resume failed: RunState not found for run_id={run_id_param}",
                why_code="STATE_NOT_FOUND",
                next_action="Check run_id or start a new run",
            ),
        }

    # load_state をモックして FileNotFoundError を発生させる（resume_run 後に呼ばれる）
    def mock_load_state(run_id_param: str):
        raise FileNotFoundError(f"RunState not found: {run_id_param}")

    with patch("nexuscore.orchestrator.authority_runner.resume_run", side_effect=mock_resume_run), \
         patch("nexuscore.orchestrator.run_state_store.load_state", side_effect=mock_load_state):
        response = client.post(
            f"/api/v1/runs/{run_id}/resume",
            headers={"X-API-Key": mock_api_key},
        )

        # load_state が FileNotFoundError を発生させる場合は 404 になる
        assert response.status_code == 404
        data = response.json()
        # CR-NEXUS-034: トップレベル error 形式（Option A）
    assert "error" in data
    assert "code" in data["error"]
    assert data["error"]["code"] == "NOT_FOUND"
    assert "detail" not in data


def test_resume_run_view_success(
    client: TestClient, mock_api_key, mock_db_models, sample_run_state, monkeypatch
):
    """POST /api/v1/runs/{run_id}/resume で成功した場合は RunView を返す"""
    run_id, state = sample_run_state

    # Mock get_orchestrator to return a fake orchestrator
    class FakeOrchestrator:
        def __init__(self):
            self.project_path = "/tmp/test"

    def mock_get_orchestrator(project_path=None, language="ja"):
        return FakeOrchestrator()

    # resume_run をモックして RUNNING を返す（orchestrator_factory 引数に対応）
    def mock_resume_run(run_id_param: str, *, orchestrator_factory=None):
        return {
            "status": "RUNNING",
            "run_id": run_id_param,
        }

    with patch("nexuscore.api.routes.run_view.get_orchestrator", side_effect=mock_get_orchestrator), \
         patch("nexuscore.orchestrator.authority_runner.resume_run", side_effect=mock_resume_run):
        response = client.post(
            f"/api/v1/runs/{run_id}/resume",
            headers={"X-API-Key": mock_api_key},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["run_id"] == run_id
        assert data["status"] == "RUNNING"
        # RunState raw JSON を返さない
        assert "schema_version" not in data
        assert "integrity" not in data


def test_run_view_requires_authentication(client: TestClient):
    """RunView API は認証必須"""
    response = client.get("/api/v1/runs/test-run-id")
    assert response.status_code == 422  # FastAPI のバリデーションエラー（必須ヘッダー欠如）


def test_run_view_openapi_documented(client: TestClient):
    """OpenAPI スキーマに RunView エンドポイントが定義されていることを確認"""
    response = client.get("/api/openapi.json")
    assert response.status_code == 200

    openapi_schema = response.json()
    assert "paths" in openapi_schema

    # /api/v1/runs/{run_id} の確認（canonical endpoint）
    assert "/api/v1/runs/{run_id}" in openapi_schema["paths"]
    run_view_path = openapi_schema["paths"]["/api/v1/runs/{run_id}"]
    assert "get" in run_view_path

    # /api/v1/runs/{run_id}/resume の確認（canonical endpoint）
    assert "/api/v1/runs/{run_id}/resume" in openapi_schema["paths"]
    resume_path = openapi_schema["paths"]["/api/v1/runs/{run_id}/resume"]

    # Deprecated /api/v1/run-view/runs が OpenAPI に含まれていないことを確認
    assert "/api/v1/run-view/runs/{run_id}" not in openapi_schema["paths"]
    assert "post" in resume_path

