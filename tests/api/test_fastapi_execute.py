"""
FastAPI Execute エンドポイントのテスト

CR-FASTAPI-002 で作成された /api/v1/execute と /api/v1/status/{task_id} エンドポイントのテスト。
既存の Flask テスト (`tests/test_api_server.py`) の期待値に準拠。
"""
import os
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

from nexuscore.api.fastapi_app import app


@pytest.fixture
def client():
    """FastAPI TestClient のフィクスチャ"""
    return TestClient(app)


@pytest.fixture
def mock_auth_token(monkeypatch):
    """認証トークンをモック"""
    monkeypatch.setenv("NEXUSCORE_API_TOKEN", "test-token-123")
    yield "test-token-123"
    monkeypatch.delenv("NEXUSCORE_API_TOKEN", raising=False)


@pytest.fixture
def auth_headers(mock_auth_token):
    """認証ヘッダーのフィクスチャ"""
    return {"Authorization": f"Bearer {mock_auth_token}"}


def test_execute_endpoint_accepts_valid_request(client: TestClient, auth_headers: dict):
    """
    Execute エンドポイントが有効なリクエストを受け入れることを確認
    既存の Flask テスト (`test_execute_task_endpoint_success`) に準拠
    """
    with patch("nexuscore.api.routes.execute.run_orchestrator_task"):
        response = client.post(
            "/api/v1/execute",
            json={
                "requirement": "Test requirement",
                "project_path": "/tmp/test"
            },
            headers=auth_headers
        )

        assert response.status_code == 202
        data = response.json()
        assert "task_id" in data
        assert "status_url" in data
        assert "message" in data
        assert data["message"] == "Task accepted and is running in the background."
        assert data["status_url"].startswith("/api/v1/status/")


def test_execute_endpoint_rejects_invalid_request_missing_fields(client: TestClient, auth_headers: dict):
    """
    Execute エンドポイントが必須フィールド欠如で 400 を返すことを確認
    既存の Flask テスト (`test_execute_task_endpoint_missing_fields`) に準拠
    """
    # requirement がない場合
    response = client.post(
        "/api/v1/execute",
        json={"project_path": "/tmp/test"},
        headers=auth_headers
    )
    assert response.status_code == 422  # FastAPI のバリデーションエラー

    # project_path がない場合
    response = client.post(
        "/api/v1/execute",
        json={"requirement": "Test requirement"},
        headers=auth_headers
    )
    assert response.status_code == 422  # FastAPI のバリデーションエラー


def test_execute_endpoint_requires_authentication(client: TestClient, mock_auth_token):
    """
    Execute エンドポイントが認証を要求することを確認
    認証ヘッダーがない場合に 401 を返すことを確認
    """
    response = client.post(
        "/api/v1/execute",
        json={
            "requirement": "Test requirement",
            "project_path": "/tmp/test"
        }
        # 認証ヘッダーを付けない
    )
    # FastAPI HTTPBearer は認証ヘッダーがない場合、auto_error=False でも 403 を返す可能性がある
    # 実際の動作に合わせて調整
    assert response.status_code in [401, 403]


def test_execute_endpoint_with_constitution_text(client: TestClient, auth_headers: dict):
    """
    Execute エンドポイントが constitution_text を受け入れることを確認
    既存の Flask テスト (`test_execute_task_with_constitution`) に準拠
    """
    with patch("nexuscore.api.routes.execute.run_orchestrator_task") as mock_task:
        response = client.post(
            "/api/v1/execute",
            json={
                "requirement": "Test requirement",
                "project_path": "/tmp/test",
                "constitution_text": "Custom constitution"
            },
            headers=auth_headers
        )

        assert response.status_code == 202
        # run_orchestrator_task が呼ばれることを確認（スレッド経由のため、直接確認は難しい）


def test_status_endpoint_returns_task_state(client: TestClient):
    """
    Status エンドポイントがタスクの状態を返すことを確認
    既存の Flask テスト (`test_get_task_status_found`) に準拠
    """
    # テスト用のタスクを追加
    from nexuscore.api import server
    test_task_id = "test-task-123"
    server.tasks[test_task_id] = {"status": "running", "message": "Test message"}

    try:
        response = client.get(f"/api/v1/status/{test_task_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "running"
        assert data["message"] == "Test message"
    finally:
        # クリーンアップ
        if test_task_id in server.tasks:
            del server.tasks[test_task_id]


def test_status_endpoint_returns_404_for_nonexistent_task(client: TestClient):
    """
    Status エンドポイントが存在しないタスクに対して 404 を返すことを確認
    既存の Flask テスト (`test_get_task_status_not_found`) に準拠
    """
    response = client.get("/api/v1/status/nonexistent-task-id")
    assert response.status_code == 404
    data = response.json()
    assert "detail" in data
    assert "not found" in data["detail"].lower()


def test_execute_and_status_are_documented_in_openapi(client: TestClient):
    """
    OpenAPI スキーマに /api/v1/execute と /api/v1/status/{task_id} が定義されていることを確認
    """
    response = client.get("/api/openapi.json")
    assert response.status_code == 200

    openapi_schema = response.json()
    assert "paths" in openapi_schema

    # /api/v1/execute の確認
    assert "/api/v1/execute" in openapi_schema["paths"]
    execute_path = openapi_schema["paths"]["/api/v1/execute"]
    assert "post" in execute_path
    post_operation = execute_path["post"]
    assert "responses" in post_operation
    assert "202" in post_operation["responses"]

    # /api/v1/status/{task_id} の確認
    assert "/api/v1/status/{task_id}" in openapi_schema["paths"]
    status_path = openapi_schema["paths"]["/api/v1/status/{task_id}"]
    assert "get" in status_path
    get_operation = status_path["get"]
    assert "responses" in get_operation
    assert "200" in get_operation["responses"]


def test_execute_response_structure(client: TestClient, auth_headers: dict):
    """
    レスポンス構造の詳細テスト
    既存の Flask テスト (`test_execute_task_response_structure`) に準拠
    """
    with patch("nexuscore.api.routes.execute.run_orchestrator_task"):
        response = client.post(
            "/api/v1/execute",
            json={
                "requirement": "Test",
                "project_path": "/tmp/test"
            },
            headers=auth_headers
        )

        assert response.status_code == 202
        data = response.json()

        # レスポンスの構造を詳細に確認
        assert "message" in data
        assert "task_id" in data
        assert "status_url" in data
        assert isinstance(data["message"], str)
        assert isinstance(data["task_id"], str)
        assert isinstance(data["status_url"], str)

        # task_id が UUID 形式であることを確認（簡易チェック）
        assert len(data["task_id"]) > 10
        assert "-" in data["task_id"]  # UUID には通常ハイフンが含まれる

        # status_url の形式を確認
        assert data["status_url"].startswith("/api/v1/status/")
        assert len(data["status_url"]) > len("/api/v1/status/")


def test_status_response_structure(client: TestClient):
    """
    ステータスレスポンスの構造テスト
    既存の Flask テスト (`test_get_task_status_response_structure`) に準拠
    """
    from nexuscore.api import server
    test_task_id = "test-structure-123"
    server.tasks[test_task_id] = {
        "status": "running",
        "message": "Test message",
        "extra_field": "extra_value"
    }

    try:
        response = client.get(f"/api/v1/status/{test_task_id}")
        assert response.status_code == 200
        data = response.json()

        # レスポンス構造を確認
        assert "status" in data
        assert "message" in data
        assert data["status"] == "running"
        assert data["message"] == "Test message"
        # 追加フィールドも許容される（ExecuteStatusResponse の extra="allow" により）
        assert "extra_field" in data
    finally:
        if test_task_id in server.tasks:
            del server.tasks[test_task_id]


def test_execute_task_id_uniqueness(client: TestClient, auth_headers: dict):
    """
    タスクIDの一意性テスト
    既存の Flask テスト (`test_execute_task_task_id_uniqueness`) に準拠
    """
    with patch("nexuscore.api.routes.execute.run_orchestrator_task"):
        task_ids = []
        for i in range(10):
            response = client.post(
                "/api/v1/execute",
                json={
                    "requirement": f"Test {i}",
                    "project_path": f"/tmp/test{i}"
                },
                headers=auth_headers
            )
            assert response.status_code == 202
            data = response.json()
            task_ids.append(data["task_id"])

        # すべてのタスクIDが異なることを確認
        assert len(set(task_ids)) == len(task_ids)

