"""
Tests for nexuscore.api.routes.execute module.
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


class TestRunOrchestratorTask:
    """run_orchestrator_task 関数のテスト"""

    def test_run_success(self, mock_tasks):
        from nexuscore.api.routes.execute import run_orchestrator_task

        # モックエージェントに __name__ を設定
        mock_agents = {}
        for name in [
            "ArchitectAgent", "PlannerAgent", "CoderAgent", "TesterAgent",
            "DebuggerAgent", "GuardianAgent", "PolicyAgent", "PostmortemAgent",
            "KnowledgeCuratorAgent", "PatchApplier",
        ]:
            m = MagicMock()
            m.__name__ = name
            mock_agents[name] = m

        mock_orch_instance = MagicMock()

        with patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}):
            with patch("nexuscore.api.routes.execute.ArchitectAgent", mock_agents["ArchitectAgent"]):
                with patch("nexuscore.api.routes.execute.PlannerAgent", mock_agents["PlannerAgent"]):
                    with patch("nexuscore.api.routes.execute.CoderAgent", mock_agents["CoderAgent"]):
                        with patch("nexuscore.api.routes.execute.TesterAgent", mock_agents["TesterAgent"]):
                            with patch("nexuscore.api.routes.execute.DebuggerAgent", mock_agents["DebuggerAgent"]):
                                with patch("nexuscore.api.routes.execute.GuardianAgent", mock_agents["GuardianAgent"]):
                                    with patch("nexuscore.api.routes.execute.PolicyAgent", mock_agents["PolicyAgent"]):
                                        with patch("nexuscore.api.routes.execute.PostmortemAgent", mock_agents["PostmortemAgent"]):
                                            with patch("nexuscore.api.routes.execute.KnowledgeCuratorAgent", mock_agents["KnowledgeCuratorAgent"]):
                                                with patch("nexuscore.api.routes.execute.PatchApplier", mock_agents["PatchApplier"]):
                                                    with patch("nexuscore.api.routes.execute.Orchestrator", return_value=mock_orch_instance):
                                                        # llm_router グローバルをモック
                                                        with patch("nexuscore.api.routes.execute.llm_router") as mock_router:
                                                            mock_router.task_model_map = {}
                                                            mock_router.default_model = "test-model"
                                                            run_orchestrator_task("task-1", "Build app", "/tmp/test", {})

        assert mock_tasks["task-1"]["status"] == "completed"
        mock_orch_instance.design_phase.assert_called_once_with("Build app")

    def test_run_missing_api_key(self, mock_tasks):
        from nexuscore.api.routes.execute import run_orchestrator_task

        with patch.dict(os.environ, {}, clear=True):
            run_orchestrator_task("task-2", "Build app", "/tmp/test", {})
        assert mock_tasks["task-2"]["status"] == "error"
        assert "API key" in mock_tasks["task-2"]["message"]

    def test_run_orchestrator_exception(self, mock_tasks):
        from nexuscore.api.routes.execute import run_orchestrator_task

        mock_agents = {}
        for name in [
            "ArchitectAgent", "PlannerAgent", "CoderAgent", "TesterAgent",
            "DebuggerAgent", "GuardianAgent", "PolicyAgent", "PostmortemAgent",
            "KnowledgeCuratorAgent", "PatchApplier",
        ]:
            m = MagicMock()
            m.__name__ = name
            mock_agents[name] = m

        mock_orch_instance = MagicMock()
        mock_orch_instance.design_phase.side_effect = RuntimeError("Design failed")

        with patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}):
            with patch("nexuscore.api.routes.execute.ArchitectAgent", mock_agents["ArchitectAgent"]):
                with patch("nexuscore.api.routes.execute.PlannerAgent", mock_agents["PlannerAgent"]):
                    with patch("nexuscore.api.routes.execute.CoderAgent", mock_agents["CoderAgent"]):
                        with patch("nexuscore.api.routes.execute.TesterAgent", mock_agents["TesterAgent"]):
                            with patch("nexuscore.api.routes.execute.DebuggerAgent", mock_agents["DebuggerAgent"]):
                                with patch("nexuscore.api.routes.execute.GuardianAgent", mock_agents["GuardianAgent"]):
                                    with patch("nexuscore.api.routes.execute.PolicyAgent", mock_agents["PolicyAgent"]):
                                        with patch("nexuscore.api.routes.execute.PostmortemAgent", mock_agents["PostmortemAgent"]):
                                            with patch("nexuscore.api.routes.execute.KnowledgeCuratorAgent", mock_agents["KnowledgeCuratorAgent"]):
                                                with patch("nexuscore.api.routes.execute.PatchApplier", mock_agents["PatchApplier"]):
                                                    with patch("nexuscore.api.routes.execute.Orchestrator", return_value=mock_orch_instance):
                                                        with patch("nexuscore.api.routes.execute.llm_router") as mock_router:
                                                            mock_router.task_model_map = {}
                                                            mock_router.default_model = "test-model"
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
