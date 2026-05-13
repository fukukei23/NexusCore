"""run_view.py の未カバー行テスト（エラーハンドリング, deprecated endpoints, ステータスマッピング）"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from nexuscore.api.routes.run_view import (
    _get_project_path_from_run_state,
    canonical_router,
)
from nexuscore.api.routes._run_view_deprecated import deprecated_router

# 関数内importのモックパス
LOAD_STATE_PATH = "nexuscore.orchestrator.run_state_store.load_state"
AUTHORITY_RUNNER_PATH = "nexuscore.orchestrator.authority_runner"
GET_ORCH_PATH = "nexuscore.api.dependencies.orchestrator.get_orchestrator"


@pytest.fixture
def app():
    """テスト用FastAPIアプリ"""
    _app = FastAPI()
    _app.include_router(canonical_router, prefix="/api/v1")
    _app.include_router(deprecated_router, prefix="/api/v1")

    from nexuscore.api.dependencies.auth import AuthenticatedUser, get_current_user

    async def _override():
        return AuthenticatedUser(user_id="test", username="tester")

    _app.dependency_overrides[get_current_user] = _override
    return _app


@pytest.fixture
def client(app):
    return TestClient(app)


class TestGetProjectPathFromRunState:
    """_get_project_path_from_run_state (lines 52-54)"""

    def test_returns_project_path_from_execution_context(self):
        """execution_context.project_path からパスを取得"""
        run_state = {"execution_context": {"project_path": "/data/projects/myapp"}}
        result = _get_project_path_from_run_state(run_state)
        assert result == "/data/projects/myapp"

    def test_returns_default_when_no_execution_context(self, monkeypatch):
        """execution_context がない場合 env"""
        monkeypatch.setenv("NEXUSCORE_PROJECT_PATH", "/custom/path")
        result = _get_project_path_from_run_state({})
        assert result == "/custom/path"

    def test_returns_default_when_run_state_none(self, monkeypatch):
        """run_state が None の場合"""
        monkeypatch.setenv("NEXUSCORE_PROJECT_PATH", "/custom/path")
        result = _get_project_path_from_run_state(None)
        assert result == "/custom/path"

    def test_returns_cwd_default_when_no_env(self, monkeypatch):
        """環境変数も run_state もない場合のデフォルト"""
        monkeypatch.delenv("NEXUSCORE_PROJECT_PATH", raising=False)
        result = _get_project_path_from_run_state(None)
        assert ".nexus" in result or "api_runs" in result


class TestGetRunViewErrorHandling:
    """get_run_view の汎用例外ハンドリング (lines 116-120)"""

    def test_internal_error_on_unexpected_exception(self, client):
        """load_state が予期しない例外を投げた場合 500"""
        with patch(LOAD_STATE_PATH, side_effect=RuntimeError("DB connection lost")):
            response = client.get("/api/v1/runs/run-001")
            assert response.status_code == 500

    def test_not_found_when_run_state_missing(self, client):
        """FileNotFoundError の場合 404"""
        with patch(LOAD_STATE_PATH, side_effect=FileNotFoundError):
            response = client.get("/api/v1/runs/run-notfound")
            assert response.status_code == 404


class TestResumeRunViewErrorHandling:
    """resume_run_view のエラーハンドリング (lines 190-191, 214-220)"""

    def test_resume_reload_failure_pass(self, client):
        """reload失敗時(pass)も前のrun_stateで応答する"""
        mock_state = {"status": "PAUSED"}
        with patch(LOAD_STATE_PATH, side_effect=[mock_state, FileNotFoundError]), \
             patch(AUTHORITY_RUNNER_PATH) as mock_ar, \
             patch(GET_ORCH_PATH):
            mock_ar.resume_run.return_value = {"status": "RUNNING", "run_id": "r1"}
            response = client.post("/api/v1/runs/r1/resume")
            assert response.status_code in (200, 201)

    def test_resume_not_found(self, client):
        """FileNotFoundError → 404"""
        with patch(LOAD_STATE_PATH, side_effect=FileNotFoundError):
            response = client.post("/api/v1/runs/r1/resume")
            assert response.status_code == 404

    def test_resume_conflict_status(self, client):
        """CONFLICT ステータス → 409"""
        mock_state = {"status": "PAUSED"}
        with patch(LOAD_STATE_PATH, return_value=mock_state), \
             patch(AUTHORITY_RUNNER_PATH) as mock_ar, \
             patch(GET_ORCH_PATH):
            mock_ar.resume_run.return_value = {"status": "CONFLICT", "run_id": "r1"}
            response = client.post("/api/v1/runs/r1/resume")
            assert response.status_code == 409

    def test_resume_failed_status(self, client):
        """FAILED ステータス → 400"""
        mock_state = {"status": "PAUSED"}
        with patch(LOAD_STATE_PATH, return_value=mock_state), \
             patch(AUTHORITY_RUNNER_PATH) as mock_ar, \
             patch(GET_ORCH_PATH):
            mock_ar.resume_run.return_value = {"status": "FAILED", "run_id": "r1"}
            response = client.post("/api/v1/runs/r1/resume")
            assert response.status_code == 400

    def test_resume_internal_error(self, client):
        """汎用例外 → 500"""
        with patch(LOAD_STATE_PATH, return_value={"status": "PAUSED"}), \
             patch(AUTHORITY_RUNNER_PATH) as mock_ar, \
             patch(GET_ORCH_PATH):
            mock_ar.resume_run.side_effect = RuntimeError("unexpected")
            response = client.post("/api/v1/runs/r1/resume")
            assert response.status_code == 500


class TestCreateRunViewErrorHandling:
    """create_run_view のステータスマッピングと例外 (lines 294, 301-305)"""

    def test_create_failed_status_returns_400(self, client):
        """FAILED ステータス → 400"""
        with patch(AUTHORITY_RUNNER_PATH) as mock_ar, \
             patch(GET_ORCH_PATH):
            mock_ar.run_with_authority.return_value = {"status": "FAILED", "run_id": "r1"}
            response = client.post("/api/v1/runs", json={"requirement": "test"})
            assert response.status_code == 400

    def test_create_aborted_status_returns_400(self, client):
        """ABORTED ステータス → 400"""
        with patch(AUTHORITY_RUNNER_PATH) as mock_ar, \
             patch(GET_ORCH_PATH):
            mock_ar.run_with_authority.return_value = {"status": "ABORTED", "run_id": "r1"}
            response = client.post("/api/v1/runs", json={"requirement": "test"})
            assert response.status_code == 400

    def test_create_internal_error(self, client):
        """汎用例外 → 500"""
        with patch(AUTHORITY_RUNNER_PATH) as mock_ar, \
             patch(GET_ORCH_PATH):
            mock_ar.run_with_authority.side_effect = RuntimeError("boom")
            response = client.post("/api/v1/runs", json={"requirement": "test"})
            assert response.status_code == 500


class TestDeprecatedEndpoints:
    """deprecated endpoints (lines 369-377, 404-412)"""

    def test_deprecated_get_delegates_to_canonical(self, client):
        """deprecated GET が canonical に委譲"""
        mock_state = {"status": "COMPLETED", "next_phase": None}
        with patch(LOAD_STATE_PATH, return_value=mock_state):
            response = client.get("/api/v1/run-view/runs/r1")
            assert response.status_code == 200

    def test_deprecated_resume_delegates(self, client):
        """deprecated resume が canonical に委譲"""
        mock_state = {"status": "PAUSED"}
        with patch(LOAD_STATE_PATH, return_value=mock_state), \
             patch(AUTHORITY_RUNNER_PATH) as mock_ar, \
             patch(GET_ORCH_PATH):
            mock_ar.resume_run.return_value = {"status": "RUNNING", "run_id": "r1"}
            response = client.post("/api/v1/run-view/runs/r1/resume")
            assert response.status_code in (200, 201)

    def test_deprecated_create_delegates(self, client):
        """deprecated create が canonical に委譲"""
        with patch(AUTHORITY_RUNNER_PATH) as mock_ar, \
             patch(GET_ORCH_PATH):
            mock_ar.run_with_authority.return_value = {"status": "COMPLETED", "run_id": "r1"}
            response = client.post("/api/v1/run-view/runs", json={"requirement": "test"})
            assert response.status_code == 200

    def test_deprecated_get_not_found(self, client):
        """deprecated GET でも 404"""
        with patch(LOAD_STATE_PATH, side_effect=FileNotFoundError):
            response = client.get("/api/v1/run-view/runs/r1")
            assert response.status_code == 404
