"""
CR-002: /api/v1/execute エンドポイントの認証テスト（Flask版）

NOTE: server.py (Flask) has been archived. FastAPI equivalents exist in test_fastapi_execute.py.
This test is skipped.
"""

import pytest

pytest.skip("Flask server.py archived; use FastAPI tests", allow_module_level=True)


@pytest.fixture
def client():
    """Flask テストクライアント"""
    return app.test_client()


def test_execute_unauthorized_no_header(client, monkeypatch):
    """Authorization ヘッダなしで /api/v1/execute を叩く"""
    monkeypatch.setenv("NEXUSCORE_API_TOKEN", "secret-token")

    response = client.post(
        "/api/v1/execute", json={"requirement": "test requirement", "project_path": "/tmp/test"}
    )

    assert response.status_code == 401
    data = response.get_json()
    assert "error" in data
    assert "Authorization" in data["error"].lower() or "required" in data["error"].lower()


def test_execute_unauthorized_invalid_token(client, monkeypatch):
    """不正なトークンで /api/v1/execute を叩く"""
    monkeypatch.setenv("NEXUSCORE_API_TOKEN", "secret-token")

    response = client.post(
        "/api/v1/execute",
        json={"requirement": "test requirement", "project_path": "/tmp/test"},
        headers={"Authorization": "Bearer wrong-token"},
    )

    assert response.status_code == 401
    data = response.get_json()
    assert "error" in data
    assert "Authorization" in data["error"].lower() or "required" in data["error"].lower()


def test_execute_authorized_success(client, monkeypatch):
    """正しいトークンで /api/v1/execute を叩く"""
    monkeypatch.setenv("NEXUSCORE_API_TOKEN", "secret-token")
    monkeypatch.setenv("NEXUS_ALLOWED_PROJECT_BASE", "/tmp")

    response = client.post(
        "/api/v1/execute",
        json={"requirement": "test requirement", "project_path": "/tmp/test"},
        headers={"Authorization": "Bearer secret-token"},
    )

    assert response.status_code == 202  # 既存の正常系レスポンスコード
    data = response.get_json()
    assert "message" in data
    assert "task_id" in data
    assert "status_url" in data
    assert "Task accepted" in data["message"]


def test_execute_server_misconfigured_when_env_missing(client, monkeypatch):
    """NEXUSCORE_API_TOKEN が未設定の状態でリクエストを送る"""
    # 環境変数を削除
    monkeypatch.delenv("NEXUSCORE_API_TOKEN", raising=False)

    response = client.post(
        "/api/v1/execute",
        json={"requirement": "test requirement", "project_path": "/tmp/test"},
        headers={"Authorization": "Bearer any-token"},
    )

    assert response.status_code == 500
    data = response.get_json()
    assert "error" in data
    assert "NEXUSCORE_API_TOKEN" in data["error"] or "misconfigured" in data["error"].lower()
