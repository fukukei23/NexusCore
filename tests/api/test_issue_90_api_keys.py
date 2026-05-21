"""Issue #90: api_keys.py エンドポイントテスト

対象: API key作成（上限超過・DB例外）、一覧取得、削除（権限チェック・不存在）
FastAPI DependencyOverridesを使用してget_current_userをモック
"""

import os
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from nexuscore.api.dependencies.auth import AuthenticatedUser
from nexuscore.api.routes.api_keys import router, MAX_API_KEYS_PER_USER


def _create_test_app():
    """テスト用FastAPIアプリ"""
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")

    # 認証をバイパス
    async def override_get_current_user():
        return AuthenticatedUser(user_id="1", roles=["api_user"])

    from nexuscore.api.dependencies.auth import get_current_user
    app.dependency_overrides[get_current_user] = override_get_current_user
    return app


class TestIssueApiKeyEndpoint:
    """POST /api/v1/api-keys のテスト"""

    def test_issue_key_limit_exceeded(self):
        """API key上限超過時に403を返す"""
        app = _create_test_app()

        mock_apikey_cls = MagicMock()
        mock_apikey_cls.query.filter_by.return_value.count.return_value = MAX_API_KEYS_PER_USER

        with patch("nexuscore.webapp.db", MagicMock()), \
             patch("nexuscore.webapp.models.ApiKey", mock_apikey_cls):
            client = TestClient(app)
            resp = client.post(
                "/api/v1/api-keys",
                json={"name": "Excess Key"},
                headers={"X-API-Key": "test-key"},
            )
            assert resp.status_code == 403

    def test_issue_key_success(self):
        """正常なAPI key作成"""
        app = _create_test_app()

        mock_apikey_instance = MagicMock()
        mock_apikey_instance.id = 1
        mock_apikey_instance.name = "Test Key"
        mock_apikey_instance.created_at = "2026-01-01T00:00:00Z"

        mock_apikey_cls = MagicMock()
        mock_apikey_cls.query.filter_by.return_value.count.return_value = 0
        mock_apikey_cls.generate_token.return_value = "nexus_test_token"
        mock_apikey_cls.hash_token.return_value = "hashed_abc"
        mock_apikey_cls.return_value = mock_apikey_instance

        mock_db = MagicMock()

        with patch("nexuscore.webapp.db", mock_db), \
             patch("nexuscore.webapp.models.ApiKey", mock_apikey_cls):
            client = TestClient(app)
            resp = client.post(
                "/api/v1/api-keys",
                json={"name": "Test Key"},
                headers={"X-API-Key": "test-key"},
            )
            assert resp.status_code == 201
            assert resp.json()["token"] == "nexus_test_token"

    def test_issue_key_default_name(self):
        """名前未指定時にデフォルト名が付く"""
        app = _create_test_app()

        mock_apikey_instance = MagicMock()
        mock_apikey_instance.id = 2
        mock_apikey_instance.name = "API Key 1"
        mock_apikey_instance.created_at = "2026-01-01T00:00:00Z"

        mock_apikey_cls = MagicMock()
        mock_apikey_cls.query.filter_by.return_value.count.return_value = 0
        mock_apikey_cls.generate_token.return_value = "nexus_token"
        mock_apikey_cls.hash_token.return_value = "hashed"
        mock_apikey_cls.return_value = mock_apikey_instance

        with patch("nexuscore.webapp.db", MagicMock()), \
             patch("nexuscore.webapp.models.ApiKey", mock_apikey_cls):
            client = TestClient(app)
            resp = client.post(
                "/api/v1/api-keys",
                json={},
                headers={"X-API-Key": "test-key"},
            )
            assert resp.status_code == 201
            call_kwargs = mock_apikey_cls.call_args[1]
            assert call_kwargs["name"] == "API Key 1"


class TestListApiKeyEndpoint:
    """GET /api/v1/api-keys のテスト"""

    def test_list_keys_success(self):
        """API key一覧取得"""
        app = _create_test_app()

        mock_key = MagicMock()
        mock_key.id = 1
        mock_key.name = "My Key"
        mock_key.created_at = "2026-01-01T00:00:00Z"

        mock_apikey_cls = MagicMock()
        mock_apikey_cls.query.filter_by.return_value.order_by.return_value.all.return_value = [mock_key]

        with patch("nexuscore.webapp.models.ApiKey", mock_apikey_cls):
            client = TestClient(app)
            resp = client.get("/api/v1/api-keys", headers={"X-API-Key": "test-key"})
            assert resp.status_code == 200
            data = resp.json()
            assert len(data["items"]) == 1

    def test_list_keys_empty(self):
        """API keyが1つもない場合"""
        app = _create_test_app()

        mock_apikey_cls = MagicMock()
        mock_apikey_cls.query.filter_by.return_value.order_by.return_value.all.return_value = []

        with patch("nexuscore.webapp.models.ApiKey", mock_apikey_cls):
            client = TestClient(app)
            resp = client.get("/api/v1/api-keys", headers={"X-API-Key": "test-key"})
            assert resp.status_code == 200
            assert resp.json()["items"] == []


class TestRevokeApiKeyEndpoint:
    """DELETE /api/v1/api-keys/{id} のテスト"""

    def test_revoke_own_key_success(self):
        """自分のAPI key削除"""
        app = _create_test_app()

        mock_key = MagicMock()
        mock_key.id = 1
        mock_key.user_id = 1

        mock_apikey_cls = MagicMock()
        mock_apikey_cls.query.filter_by.return_value.first.return_value = mock_key

        with patch("nexuscore.webapp.db", MagicMock()), \
             patch("nexuscore.webapp.models.ApiKey", mock_apikey_cls):
            client = TestClient(app)
            resp = client.delete("/api/v1/api-keys/1", headers={"X-API-Key": "test-key"})
            assert resp.status_code == 204

    def test_revoke_not_found(self):
        """存在しないAPI key削除で404"""
        app = _create_test_app()

        mock_apikey_cls = MagicMock()
        mock_apikey_cls.query.filter_by.return_value.first.return_value = None

        with patch("nexuscore.webapp.db", MagicMock()), \
             patch("nexuscore.webapp.models.ApiKey", mock_apikey_cls):
            client = TestClient(app)
            resp = client.delete("/api/v1/api-keys/999", headers={"X-API-Key": "test-key"})
            assert resp.status_code == 404

    def test_revoke_other_users_key_forbidden(self):
        """他ユーザーのAPI key削除で403"""
        app = _create_test_app()

        mock_key = MagicMock()
        mock_key.id = 1
        mock_key.user_id = 999

        mock_apikey_cls = MagicMock()
        mock_apikey_cls.query.filter_by.return_value.first.return_value = mock_key

        with patch("nexuscore.webapp.db", MagicMock()), \
             patch("nexuscore.webapp.models.ApiKey", mock_apikey_cls):
            client = TestClient(app)
            resp = client.delete("/api/v1/api-keys/1", headers={"X-API-Key": "test-key"})
            assert resp.status_code == 403
