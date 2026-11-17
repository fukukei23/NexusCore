"""GitHub webhook の fail-closed 化テスト（2026-11-17・Strix診断A案②）

Strix診断（nexuscore_bfa5）で「`GITHUB_WEBHOOK_SECRET` 未設定時に署名検証が
完全にスキップされ（＝fail-open）、攻撃者が偽装 pull_request payload で
攻撃者リポジトリのコードを実行できる」と指摘（critical / CVSS 9.8）。

対応方針（B案・明示 opt-in 付き fail-closed）:
  - `GITHUB_WEBHOOK_SECRET` が設定済み → 従来どおり HMAC 検証（fail-closed）
  - 未設定 → **原則拒否（401）**
  - 開発用の意図的な例外は `GITHUB_WEBHOOK_ALLOW_UNSIGNED=1` で明示 opt-in した
    場合のみ許可（暗黙の fail-open を残さない）
"""
from __future__ import annotations

import json
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from nexuscore.api.fastapi_app import create_app


@pytest.fixture()
def client() -> TestClient:
    app = create_app()
    return TestClient(app)


def _payload() -> dict:
    return {
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


def test_webhook_without_secret_is_rejected(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """シークレット未設定 + 署名なし → 401（fail-closed・既定の挙動）"""
    monkeypatch.delenv("GITHUB_WEBHOOK_SECRET", raising=False)
    monkeypatch.delenv("GITHUB_WEBHOOK_ALLOW_UNSIGNED", raising=False)

    with patch("nexuscore.api.github_self_healing_webhook.github_webhook") as mock_webhook:
        mock_webhook.return_value = {"status": "fixed", "summary": "ok"}
        response = client.post(
            "/api/v1/github/webhook",
            content=json.dumps(_payload()).encode("utf-8"),
            headers={
                "X-GitHub-Event": "pull_request",
                "X-GitHub-Delivery": "test-delivery-unsigned",
                "Content-Type": "application/json",
            },
        )

    assert response.status_code == 401, response.text
    mock_webhook.assert_not_called()


def test_webhook_without_secret_but_explicit_optin_is_allowed(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """明示 opt-in（GITHUB_WEBHOOK_ALLOW_UNSIGNED=1）のみ fail-open を許可する"""
    monkeypatch.delenv("GITHUB_WEBHOOK_SECRET", raising=False)
    monkeypatch.setenv("GITHUB_WEBHOOK_ALLOW_UNSIGNED", "1")

    with patch("nexuscore.api.github_self_healing_webhook.github_webhook") as mock_webhook:
        mock_webhook.return_value = {"status": "fixed", "summary": "ok"}
        response = client.post(
            "/api/v1/github/webhook",
            content=json.dumps(_payload()).encode("utf-8"),
            headers={
                "X-GitHub-Event": "pull_request",
                "X-GitHub-Delivery": "test-delivery-optin",
                "Content-Type": "application/json",
            },
        )

    assert response.status_code == 200, response.text
    mock_webhook.assert_called_once()


def test_webhook_with_secret_still_verifies_signature(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """シークレット設定済みは従来どおり HMAC 検証を行う（opt-in による迂回も不可）"""
    secret = "test-secret-value"
    monkeypatch.setenv("GITHUB_WEBHOOK_SECRET", secret)
    monkeypatch.setenv("GITHUB_WEBHOOK_ALLOW_UNSIGNED", "1")

    with patch("nexuscore.api.github_self_healing_webhook.github_webhook") as mock_webhook:
        mock_webhook.return_value = {"status": "fixed", "summary": "ok"}
        response = client.post(
            "/api/v1/github/webhook",
            content=json.dumps(_payload()).encode("utf-8"),
            headers={
                "X-GitHub-Event": "pull_request",
                "X-GitHub-Delivery": "test-delivery-badsig",
                "Content-Type": "application/json",
            },
        )

    assert response.status_code == 401, response.text
    mock_webhook.assert_not_called()
