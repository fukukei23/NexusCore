"""API認証のテスト"""

import time

import pytest

from src.nexuscore.api.auth import generate_token, verify_token


def test_generate_token():
    """トークン生成のテスト"""
    token = generate_token("test-user")
    assert token is not None
    assert isinstance(token, str)
    assert len(token) > 0


def test_verify_valid_token():
    """有効なトークンの検証テスト"""
    token = generate_token("test-user")
    payload = verify_token(token)

    assert payload is not None
    assert payload["user_id"] == "test-user"
    assert "exp" in payload
    assert "iat" in payload


def test_verify_invalid_token():
    """無効なトークンの検証テスト"""
    invalid_token = "invalid.token.here"
    payload = verify_token(invalid_token)

    assert payload is None


def test_token_expiration():
    """トークン有効期限のテスト（短時間）"""
    # 1秒で期限切れのトークンを生成
    token = generate_token("test-user", expires_in_hours=1 / 3600)  # 1秒

    # すぐに検証すると有効
    payload = verify_token(token)
    assert payload is not None

    # 2秒待つと期限切れ
    time.sleep(2)
    payload = verify_token(token)
    assert payload is None


# ==============================================================================
# Flask アプリケーションテスト（require_auth デコレータ）
# ==============================================================================


@pytest.fixture
def client(monkeypatch):
    """Flask テストクライアント"""
    monkeypatch.setenv("NEXUSCORE_API_TOKEN", "test-api-token-for-testing")
    monkeypatch.setenv("NEXUS_ALLOWED_PROJECT_BASE", "/workspace")
    from src.nexuscore.api.server import app

    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_require_auth_without_token(client):
    """認証なしアクセスのテスト"""
    response = client.post(
        "/api/v1/execute", json={"requirement": "test", "project_path": "/workspace/test"}
    )

    assert response.status_code == 401
    assert b"Authorization required" in response.data


def test_require_auth_with_invalid_format(client):
    """無効なAuthorizationヘッダー形式のテスト"""
    response = client.post(
        "/api/v1/execute",
        headers={"Authorization": "InvalidFormat"},
        json={"requirement": "test", "project_path": "/workspace/test"},
    )

    assert response.status_code == 401


def test_require_auth_with_valid_token(client):
    """有効なトークンでのアクセステスト"""
    response = client.post(
        "/api/v1/execute",
        headers={"Authorization": "Bearer test-api-token-for-testing"},
        json={"requirement": "test", "project_path": "/workspace/test"},
    )

    # 認証は通過するが、他のバリデーションでエラーになる可能性がある
    # 重要なのは401（認証エラー）ではないこと
    assert response.status_code != 401


def test_path_traversal_blocked(client):
    """パストラバーサル攻撃のテスト"""
    response = client.post(
        "/api/v1/execute",
        headers={"Authorization": "Bearer test-api-token-for-testing"},
        json={"requirement": "test", "project_path": "/etc/passwd"},
    )

    assert response.status_code == 403
    data = response.get_json()
    assert "not allowed" in data["error"]


def test_path_traversal_with_relative_path(client):
    """相対パスによるパストラバーサル攻撃のテスト"""
    response = client.post(
        "/api/v1/execute",
        headers={"Authorization": "Bearer test-api-token-for-testing"},
        json={"requirement": "test", "project_path": "/workspace/../../etc/passwd"},
    )

    assert response.status_code == 403


def test_dev_token_generation_endpoint(client, monkeypatch):
    """開発用トークン生成エンドポイントのテスト"""
    monkeypatch.delenv("FLASK_ENV", raising=False)

    response = client.post("/api/v1/dev/generate-token", json={"user_id": "dev-test-user"})

    assert response.status_code == 200
    data = response.get_json()
    assert "token" in data
    assert data["user_id"] == "dev-test-user"
    assert "usage" in data


def test_dev_token_disabled_in_production(client, monkeypatch):
    """本番環境でトークン生成が無効化されることのテスト"""
    monkeypatch.setenv("FLASK_ENV", "production")

    response = client.post("/api/v1/dev/generate-token", json={"user_id": "dev-test-user"})

    assert response.status_code == 403
    assert b"not available in production" in response.data
