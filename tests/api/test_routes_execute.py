"""
Tests for nexuscore.api.routes.execute module.

assemble_agent_team() 経由でエージェントを生成するリファクタリング後のテスト。
"""

import os
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from nexuscore.api.dependencies.auth import AuthenticatedUser, get_current_user
from nexuscore.api.fastapi_app import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def auth_user():
    return AuthenticatedUser(user_id="test-user", roles=["api_user"])


@pytest.fixture
def override_auth(client, auth_user):
    """FastAPI 依存関係オーバーライドで認証を回避"""
    app.dependency_overrides[get_current_user] = lambda: auth_user
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def mock_tasks():
    """execute.py の tasks 辞書をクリア"""
    from nexuscore.api.routes import execute as exec_mod

    original = exec_mod.tasks.copy()
    exec_mod.tasks.clear()
    yield exec_mod.tasks
    exec_mod.tasks.clear()
    exec_mod.tasks.update(original)


def _make_mock_agents():
    """assemble_agent_team() の戻り値をモック"""
    return {
        "requirement_agent": MagicMock(),
        "architect_agent": MagicMock(),
        "planner_agent": MagicMock(),
        "coder_agent": MagicMock(),
        "tester_agent": MagicMock(),
        "debugger_agent": MagicMock(),
        "guardian_agent": MagicMock(),
        "policy_agent": MagicMock(),
        "postmortem_agent": MagicMock(),
        "knowledge_curator_agent": MagicMock(),
        "patch_applier_agent": MagicMock(),
        "llm_router": MagicMock(),
    }


class TestRunOrchestratorTask:
    """run_orchestrator_task 関数のテスト"""

    def test_run_success(self, mock_tasks):
        from nexuscore.api.routes.execute import run_orchestrator_task

        mock_agents = _make_mock_agents()
        mock_orch_instance = MagicMock()

        with patch("nexuscore.api.routes.execute.assemble_agent_team", return_value=mock_agents):
            with patch("nexuscore.api.routes.execute.Orchestrator", return_value=mock_orch_instance):
                run_orchestrator_task("task-1", "Build app", "/tmp/test", {})

        assert mock_tasks["task-1"]["status"] == "completed"
        mock_orch_instance.design_phase.assert_called_once_with("Build app")

    def test_run_assemble_fails(self, mock_tasks):
        from nexuscore.api.routes.execute import run_orchestrator_task

        with patch("nexuscore.api.routes.execute.assemble_agent_team", side_effect=RuntimeError("No GLM_API_KEY")):
            run_orchestrator_task("task-2", "Build app", "/tmp/test", {})

        assert mock_tasks["task-2"]["status"] == "error"
        assert "failed" in mock_tasks["task-2"]["message"]

    def test_run_orchestrator_exception(self, mock_tasks):
        from nexuscore.api.routes.execute import run_orchestrator_task

        mock_agents = _make_mock_agents()
        mock_orch_instance = MagicMock()
        mock_orch_instance.design_phase.side_effect = RuntimeError("Design failed")

        with patch("nexuscore.api.routes.execute.assemble_agent_team", return_value=mock_agents):
            with patch("nexuscore.api.routes.execute.Orchestrator", return_value=mock_orch_instance):
                run_orchestrator_task("task-3", "Build app", "/tmp/test", {})

        assert mock_tasks["task-3"]["status"] == "error"
        assert "failed" in mock_tasks["task-3"]["message"]


class TestExecuteEndpoint:
    """POST /api/v1/execute エンドポイントのテスト"""

    def test_execute_success(self, client, override_auth, mock_tasks):
        with patch("nexuscore.api.routes.execute.threading.Thread") as mock_thread:
            mock_thread_instance = MagicMock()
            mock_thread.return_value = mock_thread_instance

            response = client.post(
                "/api/v1/execute",
                json={"requirement": "Build app", "project_path": "/tmp/test"},
                headers={"X-API-Key": "test-key"},
            )

        assert response.status_code == 202
        data = response.json()
        assert "task_id" in data
        assert "status_url" in data
        mock_thread_instance.start.assert_called_once()

    def test_execute_requires_auth(self, client, mock_tasks):
        response = client.post(
            "/api/v1/execute",
            json={"requirement": "Build app", "project_path": "/tmp/test"},
        )
        assert response.status_code == 422

    def test_execute_with_constitution(self, client, override_auth, mock_tasks):
        with patch("nexuscore.api.routes.execute.threading.Thread") as mock_thread:
            mock_thread.return_value = MagicMock()
            response = client.post(
                "/api/v1/execute",
                json={
                    "requirement": "Build app",
                    "project_path": "/tmp/test",
                    "constitution_text": "Custom rules",
                },
                headers={"X-API-Key": "test-key"},
            )

        assert response.status_code == 202


class TestGetTaskStatus:
    """GET /api/v1/status/{task_id} エンドポイントのテスト"""

    def test_status_not_found(self, client, override_auth, mock_tasks):
        response = client.get("/api/v1/status/nonexistent", headers={"X-API-Key": "test-key"})
        assert response.status_code == 404

    def test_status_found(self, client, override_auth, mock_tasks):
        mock_tasks["task-1"] = {"status": "running", "message": "Processing"}
        response = client.get("/api/v1/status/task-1", headers={"X-API-Key": "test-key"})
        assert response.status_code == 200
        assert response.json()["status"] == "running"

    def test_status_completed(self, client, override_auth, mock_tasks):
        mock_tasks["task-2"] = {"status": "completed", "message": "Done"}
        response = client.get("/api/v1/status/task-2", headers={"X-API-Key": "test-key"})
        assert response.status_code == 200
        assert response.json()["status"] == "completed"
