"""
api/auth.py 認証ユーティリティ テスト (Issue #94)

JWT有効・無効パス両方をカバー
"""

import os
from unittest.mock import MagicMock, patch

import pytest
from flask import Flask

from nexuscore.api.auth import (
    ALGORITHM,
    SECRET_KEY,
    generate_token,
    require_auth,
    verify_token,
)


@pytest.fixture
def flask_app():
    """Flask app context for jsonify"""
    app = Flask(__name__)
    with app.app_context():
        yield app


# === generate_token + verify_token 正常系 ===


def test_generate_and_verify_token():
    """正常トークン生成 → 検証成功"""
    token = generate_token("user-123", expires_in_hours=1)
    assert isinstance(token, str)
    payload = verify_token(token)
    assert payload is not None
    assert payload["user_id"] == "user-123"


def test_generate_token_default_expiry():
    """デフォルト24時間有効"""
    token = generate_token("admin")
    payload = verify_token(token)
    assert payload is not None
    assert "exp" in payload
    assert "iat" in payload


def test_verify_token_invalid():
    """無効トークン → None"""
    assert verify_token("not-a-valid-token") is None


def test_verify_token_expired():
    """期限切れトークン → None"""
    import jwt as real_jwt
    from datetime import datetime, timedelta

    payload = {
        "user_id": "expired",
        "exp": datetime.utcnow() - timedelta(hours=1),
        "iat": datetime.utcnow() - timedelta(hours=2),
    }
    token = real_jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    assert verify_token(token) is None


# === require_auth デコレータ (Flask context) ===


def test_require_auth_no_header(flask_app):
    """Authorization ヘッダーなし → 401"""
    mock_request = MagicMock()
    mock_request.headers = {}

    @require_auth
    def protected():
        return "ok"

    with patch("nexuscore.api.auth.request", mock_request):
        resp, status = protected()
        assert status == 401
        assert "missing" in resp.get_json()["error"].lower()


def test_require_auth_bad_format(flask_app):
    """不正なAuthorization形式 → 401"""
    mock_request = MagicMock()
    mock_request.headers = {"Authorization": "Token abc123"}

    @require_auth
    def protected():
        return "ok"

    with patch("nexuscore.api.auth.request", mock_request):
        resp, status = protected()
        assert status == 401
        assert "format" in resp.get_json()["error"].lower()


def test_require_auth_invalid_token(flask_app):
    """無効トークン → 401"""
    mock_request = MagicMock()
    mock_request.headers = {"Authorization": "Bearer invalid-token"}

    @require_auth
    def protected():
        return "ok"

    with patch("nexuscore.api.auth.request", mock_request):
        resp, status = protected()
        assert status == 401
        assert "invalid" in resp.get_json()["error"].lower()


def test_require_auth_valid_token(flask_app):
    """有効トークン → 関数実行"""
    token = generate_token("test-user")
    mock_request = MagicMock()
    mock_request.headers = {"Authorization": f"Bearer {token}"}

    @require_auth
    def protected():
        return "success"

    with patch("nexuscore.api.auth.request", mock_request):
        result = protected()
        assert result == "success"
        assert mock_request.auth_payload["user_id"] == "test-user"


# === HAS_JWT=False フォールバック ===


def test_require_auth_no_jwt(flask_app):
    """HAS_JWT=False → 503"""
    mock_request = MagicMock()

    @require_auth
    def protected():
        return "ok"

    with (
        patch("nexuscore.api.auth.request", mock_request),
        patch("nexuscore.api.auth.HAS_JWT", False),
    ):
        resp, status = protected()
        assert status == 503
        assert "not available" in resp.get_json()["error"].lower()


def test_generate_token_no_jwt():
    """HAS_JJWT=False で generate_token → ImportError"""
    with patch("nexuscore.api.auth.HAS_JWT", False):
        with pytest.raises(ImportError, match="PyJWT"):
            generate_token("user")


def test_verify_token_no_jwt():
    """HAS_JJWT=False で verify_token → None"""
    with patch("nexuscore.api.auth.HAS_JWT", False):
        assert verify_token("any-token") is None
