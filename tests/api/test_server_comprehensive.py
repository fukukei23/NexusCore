"""
============================================================================
Comprehensive Tests for server.py
============================================================================
高品質テストの原則:
- 外部依存（Orchestrator、各種エージェント）をモック
- 実際のFlaskルーティングとビジネスロジックをテスト
- エッジケースとエラー条件をカバー
============================================================================
"""

import os
from unittest.mock import Mock, patch

import pytest

# server.pyをインポートする前にモックを設定
with (
    patch("nexuscore.api.server.Orchestrator"),
    patch("nexuscore.api.server.ArchitectAgent"),
    patch("nexuscore.api.server.PlannerAgent"),
    patch("nexuscore.api.server.CoderAgent"),
    patch("nexuscore.api.server.TesterAgent"),
    patch("nexuscore.api.server.DebuggerAgent"),
    patch("nexuscore.api.server.GuardianAgent"),
    patch("nexuscore.api.server.PostmortemAgent"),
    patch("nexuscore.api.server.KnowledgeCuratorAgent"),
    patch("nexuscore.api.server.PatchApplier"),
    patch("nexuscore.api.server.PolicyAgent"),
):
    from nexuscore.api.auth import generate_token
    from nexuscore.api.server import app, run_orchestrator_task, tasks


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def client():
    """Flask テストクライアント"""
    os.environ["NEXUSCORE_API_TOKEN"] = "test-api-token-for-testing"
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


@pytest.fixture
def valid_token():
    """有効な認証トークン（平文 - server.py の require_auth と一致）"""
    return "test-api-token-for-testing"


@pytest.fixture
def clear_tasks():
    """各テスト後にタスクをクリア"""
    yield
    tasks.clear()


# ============================================================================
# Tests: /api/v1/execute endpoint
# ============================================================================


class TestExecuteEndpoint:
    def test_execute_without_auth(self, client, clear_tasks):
        """認証なしでリクエスト"""
        response = client.post(
            "/api/v1/execute",
            json={"requirement": "test requirement", "project_path": "/workspace/test"},
        )

        assert response.status_code == 401
        data = response.get_json()
        assert "error" in data
        assert "Authorization" in data["error"]

    def test_execute_with_missing_requirement(self, client, valid_token, clear_tasks):
        """requirement フィールドが欠けている"""
        response = client.post(
            "/api/v1/execute",
            headers={"Authorization": f"Bearer {valid_token}"},
            json={"project_path": "/workspace/test"},
        )

        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data
        assert "requirement" in data["error"]

    def test_execute_with_missing_project_path(self, client, valid_token, clear_tasks):
        """project_path フィールドが欠けている"""
        response = client.post(
            "/api/v1/execute",
            headers={"Authorization": f"Bearer {valid_token}"},
            json={"requirement": "test requirement"},
        )

        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data
        assert "project_path" in data["error"]

    def test_execute_with_empty_json(self, client, valid_token, clear_tasks):
        """空のJSONボディ"""
        response = client.post(
            "/api/v1/execute", headers={"Authorization": f"Bearer {valid_token}"}, json={}
        )

        assert response.status_code == 400

    def test_execute_with_no_json(self, client, valid_token, clear_tasks):
        """JSONボディなし"""
        response = client.post(
            "/api/v1/execute", headers={"Authorization": f"Bearer {valid_token}"}
        )

        assert response.status_code == 415

    @patch.dict(os.environ, {"NEXUS_ALLOWED_PROJECT_BASE": "/workspace"})
    def test_execute_path_traversal_attack(self, client, valid_token, clear_tasks):
        """パストラバーサル攻撃"""
        response = client.post(
            "/api/v1/execute",
            headers={"Authorization": f"Bearer {valid_token}"},
            json={"requirement": "test", "project_path": "/etc/passwd"},
        )

        assert response.status_code == 403
        data = response.get_json()
        assert "error" in data

    @patch.dict(os.environ, {"NEXUS_ALLOWED_PROJECT_BASE": "/workspace"})
    def test_execute_path_traversal_with_relative_path(self, client, valid_token, clear_tasks):
        """相対パスを使ったパストラバーサル攻撃"""
        response = client.post(
            "/api/v1/execute",
            headers={"Authorization": f"Bearer {valid_token}"},
            json={"requirement": "test", "project_path": "/workspace/../../etc/passwd"},
        )

        assert response.status_code == 403

    @patch.dict(os.environ, {"NEXUS_ALLOWED_PROJECT_BASE": "/workspace"})
    @patch("nexuscore.api.server.threading.Thread")
    def test_execute_successful_task_creation(self, mock_thread, client, valid_token, clear_tasks):
        """正常なタスク作成"""
        mock_thread_instance = Mock()
        mock_thread.return_value = mock_thread_instance

        response = client.post(
            "/api/v1/execute",
            headers={"Authorization": f"Bearer {valid_token}"},
            json={"requirement": "Build a web app", "project_path": "/workspace/myproject"},
        )

        assert response.status_code == 202
        data = response.get_json()

        assert "task_id" in data
        assert "message" in data
        assert "status_url" in data
        assert "running in the background" in data["message"]

        # スレッドが起動された
        mock_thread.assert_called_once()
        mock_thread_instance.start.assert_called_once()

    @patch.dict(os.environ, {"NEXUS_ALLOWED_PROJECT_BASE": "/workspace"})
    @patch("nexuscore.api.server.threading.Thread")
    def test_execute_with_constitution_text(self, mock_thread, client, valid_token, clear_tasks):
        """constitution_text パラメータ付きでタスク作成"""
        mock_thread_instance = Mock()
        mock_thread.return_value = mock_thread_instance

        response = client.post(
            "/api/v1/execute",
            headers={"Authorization": f"Bearer {valid_token}"},
            json={
                "requirement": "Build a web app",
                "project_path": "/workspace/myproject",
                "constitution_text": "Custom constitution rules",
            },
        )

        assert response.status_code == 202
        data = response.get_json()
        assert "task_id" in data

        # run_orchestrator_task が constitution を受け取ることを確認
        call_args = mock_thread.call_args[1]["args"]
        assert len(call_args) == 4
        constitution = call_args[3]
        assert constitution["description"] == "Custom constitution rules"

    @patch.dict(os.environ, {"NEXUS_ALLOWED_PROJECT_BASE": "/workspace"})
    @patch("nexuscore.api.server.threading.Thread")
    def test_execute_daemon_thread(self, mock_thread, client, valid_token, clear_tasks):
        """バックグラウンドスレッドがデーモンとして起動"""
        mock_thread_instance = Mock()
        mock_thread.return_value = mock_thread_instance

        client.post(
            "/api/v1/execute",
            headers={"Authorization": f"Bearer {valid_token}"},
            json={"requirement": "test", "project_path": "/workspace/test"},
        )

        # daemon = True が設定される
        assert mock_thread_instance.daemon is True


# ============================================================================
# Tests: /api/v1/status/<task_id> endpoint
# ============================================================================


class TestStatusEndpoint:
    def test_status_task_not_found(self, client, clear_tasks):
        """存在しないタスクIDを照会"""
        response = client.get("/api/v1/status/nonexistent-task-id")

        assert response.status_code == 404
        data = response.get_json()
        assert "error" in data
        assert "not found" in data["error"].lower()

    def test_status_existing_task(self, client, clear_tasks):
        """存在するタスクの状態を照会"""
        task_id = "test-task-123"
        tasks[task_id] = {"status": "running", "message": "Processing..."}

        response = client.get(f"/api/v1/status/{task_id}")

        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "running"
        assert data["message"] == "Processing..."

    def test_status_completed_task(self, client, clear_tasks):
        """完了したタスクの状態を照会"""
        task_id = "completed-task"
        tasks[task_id] = {
            "status": "completed",
            "message": "Development process finished successfully.",
        }

        response = client.get(f"/api/v1/status/{task_id}")

        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "completed"

    def test_status_error_task(self, client, clear_tasks):
        """エラーが発生したタスクの状態を照会"""
        task_id = "error-task"
        tasks[task_id] = {"status": "error", "message": "orchestrator failed: Some error"}

        response = client.get(f"/api/v1/status/{task_id}")

        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "error"
        assert "failed" in data["message"]


# ============================================================================
# Tests: /api/github/webhook endpoint
# ============================================================================


class TestGithubWebhookEndpoint:
    @patch("nexuscore.api.github_webhook_handler.handle_github_webhook")
    def test_github_webhook_success(self, mock_handler, client):
        """GitHub Webhook の正常処理"""
        mock_handler.return_value = {"accepted": True, "result": {"status": "fixed"}}

        response = client.post(
            "/api/github/webhook",
            headers={"X-GitHub-Event": "pull_request"},
            json={"action": "opened"},
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["accepted"] is True
        mock_handler.assert_called_once()

    @patch("nexuscore.api.github_webhook_handler.handle_github_webhook")
    def test_github_webhook_with_tuple_response(self, mock_handler, client):
        """GitHub Webhook ハンドラーがタプルを返す場合"""
        mock_handler.return_value = ({"error": "Bad request"}, 400)

        response = client.post(
            "/api/github/webhook",
            headers={"X-GitHub-Event": "pull_request"},
            json={"action": "opened"},
        )

        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data

    @patch("nexuscore.api.github_webhook_handler.handle_github_webhook")
    def test_github_webhook_handler_exception(self, mock_handler, client):
        """GitHub Webhook ハンドラーが例外を投げる"""
        mock_handler.side_effect = Exception("Handler error")

        response = client.post(
            "/api/github/webhook",
            headers={"X-GitHub-Event": "pull_request"},
            json={"action": "opened"},
        )

        assert response.status_code == 500
        data = response.get_json()
        assert "error" in data


# ============================================================================
# Tests: /api/v1/dev/generate-token endpoint
# ============================================================================


class TestDevTokenEndpoint:
    @patch.dict(os.environ, {}, clear=True)
    def test_dev_token_generation_dev_env(self, client):
        """開発環境でトークン生成"""
        # FLASK_ENV が設定されていない = 開発環境
        response = client.post("/api/v1/dev/generate-token", json={"user_id": "dev-user"})

        assert response.status_code == 200
        data = response.get_json()
        assert "token" in data
        assert data["user_id"] == "dev-user"
        assert "usage" in data
        assert "Bearer" in data["usage"]

    @patch.dict(os.environ, {"FLASK_ENV": "production"})
    def test_dev_token_generation_production_env(self, client):
        """本番環境でトークン生成は拒否"""
        response = client.post("/api/v1/dev/generate-token", json={"user_id": "dev-user"})

        assert response.status_code == 403
        data = response.get_json()
        assert "not available in production" in data["error"]

    @patch.dict(os.environ, {}, clear=True)
    def test_dev_token_default_user_id(self, client):
        """user_id が指定されていない場合のデフォルト値"""
        response = client.post("/api/v1/dev/generate-token", json={})

        assert response.status_code == 200
        data = response.get_json()
        assert data["user_id"] == "dev-user"

    @patch.dict(os.environ, {}, clear=True)
    def test_dev_token_custom_expiry(self, client):
        """カスタム有効期限でトークン生成"""
        response = client.post(
            "/api/v1/dev/generate-token", json={"user_id": "test-user", "expires_in_hours": 48}
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["expires_in_hours"] == 48

    @patch.dict(os.environ, {}, clear=True)
    @patch("nexuscore.api.server.generate_token")
    def test_dev_token_generation_failure(self, mock_generate, client):
        """トークン生成が失敗した場合"""
        mock_generate.side_effect = Exception("Token generation failed")

        response = client.post("/api/v1/dev/generate-token", json={"user_id": "test-user"})

        assert response.status_code == 500
        data = response.get_json()
        assert "error" in data


# ============================================================================
# Tests: run_orchestrator_task function
# ============================================================================


class TestRunOrchestratorTask:
    @patch("nexuscore.api.server.Orchestrator")
    @patch("nexuscore.api.server.ArchitectAgent")
    @patch("nexuscore.api.server.PlannerAgent")
    @patch("nexuscore.api.server.CoderAgent")
    @patch("nexuscore.api.server.TesterAgent")
    @patch("nexuscore.api.server.DebuggerAgent")
    @patch("nexuscore.api.server.GuardianAgent")
    @patch("nexuscore.api.server.PostmortemAgent")
    @patch("nexuscore.api.server.KnowledgeCuratorAgent")
    @patch("nexuscore.api.server.PatchApplier")
    @patch("nexuscore.api.server.PolicyAgent")
    @patch.dict(os.environ, {"GEMINI_API_KEY": "test-api-key"})
    def test_run_orchestrator_task_success(
        self,
        mock_policy,
        mock_patcher,
        mock_curator,
        mock_postmortem,
        mock_guardian,
        mock_debugger,
        mock_tester,
        mock_coder,
        mock_planner,
        mock_architect,
        mock_orchestrator,
        clear_tasks,
    ):
        """Orchestrator タスクの正常実行"""
        # Orchestrator のモック
        mock_orch_instance = Mock()
        mock_orchestrator.return_value = mock_orch_instance

        task_id = "test-task"
        requirement = "Build a web app"
        project_path = "/workspace/test"
        constitution = {"description": "Test constitution"}

        run_orchestrator_task(task_id, requirement, project_path, constitution)

        # タスクステータスが更新される
        assert task_id in tasks
        assert tasks[task_id]["status"] == "completed"

        # Orchestrator が初期化される
        mock_orchestrator.assert_called_once()

        # design_phase が呼ばれる
        mock_orch_instance.design_phase.assert_called_once_with(requirement)

        # development_cycle が呼ばれる
        mock_orch_instance.development_cycle.assert_called_once()

    @patch.dict(os.environ, {}, clear=True)
    def test_run_orchestrator_task_missing_api_key(self, clear_tasks):
        """API キーが設定されていない場合"""
        task_id = "test-task"
        requirement = "Build a web app"
        project_path = "/workspace/test"
        constitution = {}

        run_orchestrator_task(task_id, requirement, project_path, constitution)

        # タスクがエラー状態になる
        assert task_id in tasks
        assert tasks[task_id]["status"] == "error"
        assert "API key" in tasks[task_id]["message"]

    @patch("nexuscore.api.server.Orchestrator")
    @patch("nexuscore.api.server.ArchitectAgent")
    @patch("nexuscore.api.server.PlannerAgent")
    @patch("nexuscore.api.server.CoderAgent")
    @patch("nexuscore.api.server.TesterAgent")
    @patch("nexuscore.api.server.DebuggerAgent")
    @patch("nexuscore.api.server.GuardianAgent")
    @patch("nexuscore.api.server.PostmortemAgent")
    @patch("nexuscore.api.server.KnowledgeCuratorAgent")
    @patch("nexuscore.api.server.PatchApplier")
    @patch("nexuscore.api.server.PolicyAgent")
    @patch.dict(os.environ, {"GEMINI_API_KEY": "test-api-key"})
    def test_run_orchestrator_task_exception(
        self,
        mock_policy,
        mock_patcher,
        mock_curator,
        mock_postmortem,
        mock_guardian,
        mock_debugger,
        mock_tester,
        mock_coder,
        mock_planner,
        mock_architect,
        mock_orchestrator,
        clear_tasks,
    ):
        """Orchestrator 実行中に例外が発生"""
        mock_orch_instance = Mock()
        mock_orch_instance.design_phase.side_effect = Exception("Design failed")
        mock_orchestrator.return_value = mock_orch_instance

        task_id = "error-task"
        run_orchestrator_task(task_id, "requirement", "/workspace/test", {})

        # エラー状態になる
        assert tasks[task_id]["status"] == "error"
        assert "failed" in tasks[task_id]["message"]


# ============================================================================
# Tests: Integration scenarios
# ============================================================================


class TestIntegrationScenarios:
    @patch.dict(os.environ, {"NEXUS_ALLOWED_PROJECT_BASE": "/workspace"})
    @patch("nexuscore.api.server.threading.Thread")
    def test_full_task_lifecycle(self, mock_thread, client, valid_token, clear_tasks):
        """タスクの完全なライフサイクル"""
        mock_thread_instance = Mock()
        mock_thread.return_value = mock_thread_instance

        # 1. タスクを作成
        response = client.post(
            "/api/v1/execute",
            headers={"Authorization": f"Bearer {valid_token}"},
            json={"requirement": "Build a todo app", "project_path": "/workspace/todoapp"},
        )

        assert response.status_code == 202
        data = response.get_json()
        task_id = data["task_id"]

        # 2. ステータスを確認（タスクが辞書に追加される前）
        # 実際にはバックグラウンドタスクが動かないのでタスクが存在しない
        response = client.get(f"/api/v1/status/{task_id}")
        assert response.status_code == 404

        # 3. タスクを手動で追加してステータスを確認
        tasks[task_id] = {"status": "running", "message": "Processing"}
        response = client.get(f"/api/v1/status/{task_id}")
        assert response.status_code == 200
        assert response.get_json()["status"] == "running"

    @patch.dict(os.environ, {}, clear=True)
    def test_dev_workflow(self, client):
        """開発ワークフロー: トークン生成 → APIコール"""
        # 1. 開発用トークンを生成
        response = client.post("/api/v1/dev/generate-token", json={"user_id": "developer"})

        assert response.status_code == 200
        token = response.get_json()["token"]

        # 2. 生成したトークンでAPIコール（認証確認のみ）
        # project_path が許可されていないのでエラーになるはずだが、認証は通過する
        response = client.post(
            "/api/v1/execute",
            headers={"Authorization": f"Bearer {token}"},
            json={"requirement": "test", "project_path": "/tmp/test"},
        )

        # 認証は通過するが、パストラバーサルチェックでエラーになる可能性
        assert response.status_code != 401  # 認証エラーではない
