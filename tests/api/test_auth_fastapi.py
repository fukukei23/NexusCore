"""FastAPI auth router のテスト"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """テスト用FastAPIクライアント"""
    import os

    os.environ.setdefault("NEXUSCORE_API_KEY", "test-key-for-unit-tests")
    os.environ.pop("GITHUB_CLIENT_ID", None)
    os.environ.pop("GITHUB_CLIENT_SECRET", None)

    from nexuscore.api.fastapi_app import create_app

    app = create_app(test_db_path="/tmp/test_auth.db")
    return TestClient(app)


class TestLoginGithub:
    def test_returns_500_when_oauth_not_configured(self, client):
        """OAuth未設定時は500を返す"""
        response = client.get("/api/v1/auth/login/github", follow_redirects=False)
        assert response.status_code == 500
        assert response.json()["error"] == "GitHub OAuth not configured"

    @patch.dict("os.environ", {"GITHUB_CLIENT_ID": "test-id", "GITHUB_CLIENT_SECRET": "test-secret"})
    def test_redirects_to_github_when_configured(self, client):
        """OAuth設定済み時はGitHubにリダイレクト"""
        with patch.dict("os.environ", {"GITHUB_CLIENT_ID": "test-id", "GITHUB_CLIENT_SECRET": "test-secret"}):
            from nexuscore.api.routes import auth

            auth.GITHUB_CLIENT_ID = "test-id"
            auth.GITHUB_CLIENT_SECRET = "test-secret"
            auth.init_oauth(client.app)

            response = client.get("/api/v1/auth/login/github", follow_redirects=False)
            assert response.status_code in (302, 303, 307)


class TestLogout:
    def test_redirects_after_logout(self, client):
        """ログアウト後にリダイレクト"""
        response = client.get("/api/v1/auth/logout", follow_redirects=False)
        assert response.status_code in (302, 303, 307)


class TestHelperFunctions:
    def test_fetch_primary_email_success(self):
        """プライマリメール取得"""
        from nexuscore.api.routes.auth import _fetch_primary_email

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {"email": "secondary@example.com", "primary": False, "verified": True},
            {"email": "primary@example.com", "primary": True, "verified": True},
        ]

        with patch("nexuscore.api.routes.auth.requests.get", return_value=mock_response):
            import asyncio

            email = asyncio.get_event_loop().run_until_complete(
                _fetch_primary_email({"Authorization": "token abc"})
            )
            assert email == "primary@example.com"

    def test_fetch_primary_email_no_primary(self):
        """プライマリなし時はフォールバック"""
        from nexuscore.api.routes.auth import _fetch_primary_email

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {"email": "verified@example.com", "primary": False, "verified": True},
        ]

        with patch("nexuscore.api.routes.auth.requests.get", return_value=mock_response):
            import asyncio

            email = asyncio.get_event_loop().run_until_complete(
                _fetch_primary_email({"Authorization": "token abc"})
            )
            assert email == "verified@example.com"

    def test_fetch_primary_email_api_error(self):
        """API エラー時は None"""
        from nexuscore.api.routes.auth import _fetch_primary_email

        mock_response = MagicMock()
        mock_response.status_code = 403

        with patch("nexuscore.api.routes.auth.requests.get", return_value=mock_response):
            import asyncio

            email = asyncio.get_event_loop().run_until_complete(
                _fetch_primary_email({"Authorization": "token abc"})
            )
            assert email is None
