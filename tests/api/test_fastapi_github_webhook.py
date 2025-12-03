"""
FastAPI GitHub Webhook エンドポイントのテスト

CR-FASTAPI-003 で作成された /api/v1/github/webhook エンドポイントのテスト。
既存の Flask テスト (`tests/api/test_github_self_healing_webhook.py`) の期待値に準拠。
"""
import hashlib
import hmac
import json
import os
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from nexuscore.api.fastapi_app import app


@pytest.fixture
def client():
    """FastAPI TestClient のフィクスチャ"""
    return TestClient(app)


@pytest.fixture
def mock_webhook_secret(monkeypatch):
    """Webhook Secret をモック"""
    secret = "test-webhook-secret-123"
    monkeypatch.setenv("GITHUB_WEBHOOK_SECRET", secret)
    yield secret
    monkeypatch.delenv("GITHUB_WEBHOOK_SECRET", raising=False)


def _create_signature(payload_body: bytes, secret: str) -> str:
    """GitHub Webhook の署名を生成"""
    signature = hmac.new(
        secret.encode("utf-8"),
        payload_body,
        hashlib.sha256,
    ).hexdigest()
    return f"sha256={signature}"


def test_webhook_endpoint_accepts_valid_pull_request_event(client: TestClient, mock_webhook_secret):
    """
    正常系：署名 OK、対象イベント（PR opened/synchronize）
    既存の Flask テストに準拠
    """
    payload = {
        "action": "opened",
        "repository": {
            "full_name": "owner/repo",
        },
        "pull_request": {
            "number": 123,
            "draft": False,
            "labels": [
                {"name": "self-healing"},
            ],
            "head": {
                "sha": "abc123def456",
            },
            "base": {
                "ref": "main",
            },
        },
    }

    payload_body = json.dumps(payload).encode("utf-8")
    signature = _create_signature(payload_body, mock_webhook_secret)

    with patch("nexuscore.api.github_self_healing_webhook.github_webhook") as mock_webhook:
        mock_webhook.return_value = {
            "status": "fixed",
            "summary": "Tests are now passing",
            "run_id": "sh-123",
        }

        response = client.post(
            "/api/v1/github/webhook",
            content=payload_body,
            headers={
                "X-GitHub-Event": "pull_request",
                "X-GitHub-Delivery": "test-delivery-123",
                "X-Hub-Signature-256": signature,
                "Content-Type": "application/json",
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["accepted"] is True
        assert "result" in data
        assert data["result"]["status"] == "fixed"


def test_webhook_endpoint_rejects_invalid_signature(client: TestClient, mock_webhook_secret):
    """
    エラー系：署名不正 → 401
    """
    payload = {
        "action": "opened",
        "repository": {"full_name": "owner/repo"},
        "pull_request": {
            "number": 123,
            "draft": False,
            "labels": [{"name": "self-healing"}],
            "head": {"sha": "abc123"},
            "base": {"ref": "main"},
        },
    }

    payload_body = json.dumps(payload).encode("utf-8")
    invalid_signature = "sha256=invalid_signature"

    response = client.post(
        "/api/v1/github/webhook",
        content=payload_body,
        headers={
            "X-GitHub-Event": "pull_request",
            "X-GitHub-Delivery": "test-delivery-123",
            "X-Hub-Signature-256": invalid_signature,
            "Content-Type": "application/json",
        }
    )

    assert response.status_code == 401
    data = response.json()
    assert "detail" in data
    assert "signature" in data["detail"].lower()


def test_webhook_endpoint_ignores_non_pull_request_event(client: TestClient):
    """
    イベント対象外：pull_request 以外のイベント → status == "ignored"
    """
    payload = {
        "action": "opened",
        "repository": {"full_name": "owner/repo"},
    }

    payload_body = json.dumps(payload).encode("utf-8")

    response = client.post(
        "/api/v1/github/webhook",
        content=payload_body,
        headers={
            "X-GitHub-Event": "push",  # pull_request 以外
            "X-GitHub-Delivery": "test-delivery-123",
            "Content-Type": "application/json",
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert data["accepted"] is False
    assert "reason" in data
    assert "pull_request" in data["reason"]


def test_webhook_endpoint_handles_missing_signature_header(client: TestClient, mock_webhook_secret):
    """
    署名ヘッダーがない場合の処理
    """
    payload = {
        "action": "opened",
        "repository": {"full_name": "owner/repo"},
        "pull_request": {
            "number": 123,
            "draft": False,
            "labels": [{"name": "self-healing"}],
            "head": {"sha": "abc123"},
            "base": {"ref": "main"},
        },
    }

    payload_body = json.dumps(payload).encode("utf-8")

    # 署名ヘッダーを付けない
    response = client.post(
        "/api/v1/github/webhook",
        content=payload_body,
        headers={
            "X-GitHub-Event": "pull_request",
            "X-GitHub-Delivery": "test-delivery-123",
            "Content-Type": "application/json",
        }
    )

    # シークレットが設定されている場合、署名ヘッダーがないと401を返す
    assert response.status_code == 401


def test_webhook_endpoint_handles_skipped_pr(client: TestClient, mock_webhook_secret):
    """
    PRが条件を満たさない場合（ラベルなし、draft PRなど）の処理
    """
    payload = {
        "action": "opened",
        "repository": {"full_name": "owner/repo"},
        "pull_request": {
            "number": 123,
            "draft": False,
            "labels": [],  # self-healing ラベルなし
            "head": {"sha": "abc123"},
            "base": {"ref": "main"},
        },
    }

    payload_body = json.dumps(payload).encode("utf-8")
    signature = _create_signature(payload_body, mock_webhook_secret)

    with patch("nexuscore.api.github_self_healing_webhook.github_webhook") as mock_webhook:
        mock_webhook.return_value = {
            "status": "skipped",
            "summary": "PR does not meet criteria for self-healing (missing label, draft, etc.)",
        }

        response = client.post(
            "/api/v1/github/webhook",
            content=payload_body,
            headers={
                "X-GitHub-Event": "pull_request",
                "X-GitHub-Delivery": "test-delivery-123",
                "X-Hub-Signature-256": signature,
                "Content-Type": "application/json",
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["accepted"] is True
        assert data["status"] == "skipped"


def test_webhook_endpoint_is_documented_in_openapi(client: TestClient):
    """
    OpenAPI スキーマに /api/v1/github/webhook が定義されていることを確認
    """
    response = client.get("/api/openapi.json")
    assert response.status_code == 200

    openapi_schema = response.json()
    assert "paths" in openapi_schema

    # /api/v1/github/webhook の確認
    assert "/api/v1/github/webhook" in openapi_schema["paths"]
    webhook_path = openapi_schema["paths"]["/api/v1/github/webhook"]
    assert "post" in webhook_path
    post_operation = webhook_path["post"]
    assert "responses" in post_operation
    assert "200" in post_operation["responses"]

    # リクエストボディスキーマの確認（FastAPIはリクエストボディを自動検出しないため、オプション）
    # 実際のリクエストではボディが受け入れられることを確認


def test_webhook_endpoint_handles_invalid_json(client: TestClient):
    """
    不正なJSONペイロードの処理
    """
    invalid_payload = b"invalid json"

    response = client.post(
        "/api/v1/github/webhook",
        content=invalid_payload,
        headers={
            "X-GitHub-Event": "pull_request",
            "X-GitHub-Delivery": "test-delivery-123",
            "Content-Type": "application/json",
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert data["accepted"] is False
    assert "reason" in data


def test_webhook_endpoint_without_secret_allows_requests(client: TestClient, monkeypatch):
    """
    シークレットが設定されていない場合、署名検証をスキップする
    """
    # シークレットを削除
    monkeypatch.delenv("GITHUB_WEBHOOK_SECRET", raising=False)

    payload = {
        "action": "opened",
        "repository": {"full_name": "owner/repo"},
        "pull_request": {
            "number": 123,
            "draft": False,
            "labels": [{"name": "self-healing"}],
            "head": {"sha": "abc123"},
            "base": {"ref": "main"},
        },
    }

    payload_body = json.dumps(payload).encode("utf-8")

    with patch("nexuscore.api.github_self_healing_webhook.github_webhook") as mock_webhook:
        mock_webhook.return_value = {
            "status": "fixed",
            "summary": "Tests are now passing",
        }

        # 署名ヘッダーなしでもリクエストが通る（開発環境など）
        response = client.post(
            "/api/v1/github/webhook",
            content=payload_body,
            headers={
                "X-GitHub-Event": "pull_request",
                "X-GitHub-Delivery": "test-delivery-123",
                "Content-Type": "application/json",
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["accepted"] is True

