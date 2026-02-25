"""
============================================================================
Comprehensive Tests for auth.py
============================================================================
高品質テストの原則:
- 外部依存（Flask app）のみモック
- 実際のJWT生成・検証ロジックをテスト
- エッジケースとエラー条件をカバー
============================================================================
"""

import os
import time
from datetime import datetime, timedelta
from unittest.mock import patch

import jwt
import pytest

from nexuscore.api.auth import generate_token, require_auth, verify_token

# ============================================================================
# Tests: generate_token
# ============================================================================


class TestGenerateToken:
    def test_generate_token_default_expiry(self):
        """デフォルトの有効期限でトークンを生成"""
        token = generate_token("test-user")

        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0

        # トークンをデコードして内容を確認
        payload = verify_token(token)
        assert payload is not None
        assert payload["user_id"] == "test-user"
        assert "exp" in payload
        assert "iat" in payload

    def test_generate_token_custom_expiry(self):
        """カスタム有効期限でトークンを生成"""
        token = generate_token("test-user", expires_in_hours=48)

        payload = verify_token(token)
        assert payload is not None
        assert payload["user_id"] == "test-user"

        # 有効期限が約48時間後であることを確認
        exp_time = payload["exp"]
        iat_time = payload["iat"]
        duration_hours = (exp_time - iat_time) / 3600
        assert 47.9 < duration_hours < 48.1

    def test_generate_token_short_expiry(self):
        """短い有効期限でトークンを生成"""
        token = generate_token("test-user", expires_in_hours=0.001)  # 約3.6秒

        # すぐに検証すると有効
        payload = verify_token(token)
        assert payload is not None

    def test_generate_token_different_users(self):
        """異なるユーザーIDで異なるトークンを生成"""
        token1 = generate_token("user-1")
        token2 = generate_token("user-2")

        assert token1 != token2

        payload1 = verify_token(token1)
        payload2 = verify_token(token2)

        assert payload1["user_id"] == "user-1"
        assert payload2["user_id"] == "user-2"

    def test_generate_token_empty_user_id(self):
        """空のユーザーIDでトークンを生成"""
        token = generate_token("")

        payload = verify_token(token)
        assert payload is not None
        assert payload["user_id"] == ""

    def test_generate_token_special_characters(self):
        """特殊文字を含むユーザーIDでトークンを生成"""
        user_id = "test@example.com"
        token = generate_token(user_id)

        payload = verify_token(token)
        assert payload["user_id"] == user_id

    def test_generate_token_unicode_user_id(self):
        """Unicode文字を含むユーザーIDでトークンを生成"""
        user_id = "テストユーザー"
        token = generate_token(user_id)

        payload = verify_token(token)
        assert payload["user_id"] == user_id


# ============================================================================
# Tests: verify_token
# ============================================================================


class TestVerifyToken:
    def test_verify_valid_token(self):
        """有効なトークンを検証"""
        token = generate_token("test-user")
        payload = verify_token(token)

        assert payload is not None
        assert payload["user_id"] == "test-user"
        assert "exp" in payload
        assert "iat" in payload

    def test_verify_invalid_token_format(self):
        """無効なフォーマットのトークンを検証"""
        invalid_tokens = [
            "invalid.token.here",
            "not-a-jwt",
            "abc123",
            "",
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.invalid",
        ]

        for invalid_token in invalid_tokens:
            payload = verify_token(invalid_token)
            assert payload is None

    def test_verify_expired_token(self):
        """期限切れのトークンを検証"""
        # 1秒で期限切れのトークンを生成
        token = generate_token("test-user", expires_in_hours=1 / 3600)

        # すぐに検証すると有効
        payload = verify_token(token)
        assert payload is not None

        # 2秒待つと期限切れ
        time.sleep(2)
        payload = verify_token(token)
        assert payload is None

    def test_verify_token_wrong_secret(self):
        """間違った秘密鍵で署名されたトークンを検証"""
        # 正しい秘密鍵でトークンを生成
        token = generate_token("test-user")

        # 間違った秘密鍵でデコードを試みる
        wrong_secret = "wrong-secret-key"
        try:
            jwt.decode(token, wrong_secret, algorithms=["HS256"])
            raise AssertionError("Should have raised an exception")
        except jwt.InvalidSignatureError:
            pass  # 期待通り

    def test_verify_token_none(self):
        """Noneトークンを検証"""
        payload = verify_token(None)
        assert payload is None

    def test_verify_token_tampered(self):
        """改ざんされたトークンを検証"""
        token = generate_token("test-user")

        # トークンの一部を改ざん
        parts = token.split(".")
        if len(parts) == 3:
            # ペイロード部分を改ざん
            tampered_token = parts[0] + ".eyJzdWIiOiIxMjM0NTY3ODkwIn0." + parts[2]
            payload = verify_token(tampered_token)
            assert payload is None

    def test_verify_token_missing_fields(self):
        """必須フィールドが欠けているトークンを検証"""
        secret = os.getenv("JWT_SECRET_KEY", "change-this-in-production-INSECURE-DEFAULT")

        # user_idフィールドなしでトークンを作成
        payload_data = {
            "exp": datetime.utcnow() + timedelta(hours=24),
            "iat": datetime.utcnow(),
        }
        token = jwt.encode(payload_data, secret, algorithm="HS256")

        # verify_tokenは成功するがuser_idがない
        payload = verify_token(token)
        assert payload is not None
        assert "user_id" not in payload


# ============================================================================
# Tests: require_auth decorator
# ============================================================================


class TestRequireAuthDecorator:
    @pytest.fixture
    def app(self):
        """Flask テストアプリケーション"""
        from flask import Flask, jsonify, request

        app = Flask(__name__)
        app.config["TESTING"] = True

        @app.route("/protected", methods=["POST"])
        @require_auth
        def protected_route():
            return jsonify({"message": "Success", "user_id": request.auth_payload.get("user_id")})

        @app.route("/unprotected", methods=["GET"])
        def unprotected_route():
            return jsonify({"message": "No auth required"})

        return app

    @pytest.fixture
    def client(self, app):
        """Flask テストクライアント"""
        with app.test_client() as client:
            yield client

    def test_require_auth_without_header(self, client):
        """Authorizationヘッダーなしでアクセス"""
        response = client.post("/protected")

        assert response.status_code == 401
        data = response.get_json()
        assert "error" in data
        assert "Authorization header missing" in data["error"]

    def test_require_auth_with_invalid_format(self, client):
        """無効なフォーマットのAuthorizationヘッダー"""
        response = client.post("/protected", headers={"Authorization": "InvalidFormat"})

        assert response.status_code == 401
        data = response.get_json()
        assert "Invalid authorization header format" in data["error"]

    def test_require_auth_with_invalid_token(self, client):
        """無効なトークンでアクセス"""
        response = client.post("/protected", headers={"Authorization": "Bearer invalid.token.here"})

        assert response.status_code == 401
        data = response.get_json()
        assert "Invalid token" in data["error"]

    def test_require_auth_with_valid_token(self, client):
        """有効なトークンでアクセス"""
        token = generate_token("test-user")

        response = client.post("/protected", headers={"Authorization": f"Bearer {token}"})

        assert response.status_code == 200
        data = response.get_json()
        assert data["message"] == "Success"
        assert data["user_id"] == "test-user"

    def test_require_auth_with_expired_token(self, client):
        """期限切れトークンでアクセス"""
        token = generate_token("test-user", expires_in_hours=1 / 3600)

        # 2秒待って期限切れにする
        time.sleep(2)

        response = client.post("/protected", headers={"Authorization": f"Bearer {token}"})

        assert response.status_code == 401
        data = response.get_json()
        assert "expired" in data["error"].lower()

    def test_require_auth_case_sensitive_bearer(self, client):
        """Bearer の大文字小文字の扱い"""
        token = generate_token("test-user")

        # 小文字の "bearer" でもOK（.lower() を使っているため）
        response = client.post("/protected", headers={"Authorization": f"bearer {token}"})

        # 現在の実装では parts[0].lower() なので小文字も受け付ける
        assert response.status_code == 200

    def test_require_auth_extra_spaces(self, client):
        """余分なスペースがある場合"""
        token = generate_token("test-user")

        # 余分なスペース
        response = client.post("/protected", headers={"Authorization": f"Bearer  {token}"})

        # 実装では split() なので余分なスペースも正しく処理される（空文字列は無視される）
        assert response.status_code == 200

    def test_require_auth_preserves_request_data(self, client):
        """認証後もリクエストデータが保持される"""
        from flask import Flask, jsonify, request

        app = Flask(__name__)
        app.config["TESTING"] = True

        @app.route("/data", methods=["POST"])
        @require_auth
        def data_route():
            data = request.get_json()
            return jsonify({"received": data, "user_id": request.auth_payload.get("user_id")})

        with app.test_client() as test_client:
            token = generate_token("test-user")

            response = test_client.post(
                "/data", headers={"Authorization": f"Bearer {token}"}, json={"key": "value"}
            )

            assert response.status_code == 200
            data = response.get_json()
            assert data["received"] == {"key": "value"}
            assert data["user_id"] == "test-user"


# ============================================================================
# Tests: Integration scenarios
# ============================================================================


class TestIntegrationScenarios:
    def test_full_authentication_flow(self):
        """完全な認証フロー"""
        # 1. トークンを生成
        user_id = "integration-test-user"
        token = generate_token(user_id, expires_in_hours=1)

        # 2. トークンを検証
        payload = verify_token(token)
        assert payload is not None
        assert payload["user_id"] == user_id

        # 3. Flaskアプリで使用
        from flask import Flask, jsonify

        app = Flask(__name__)
        app.config["TESTING"] = True

        @app.route("/api/test", methods=["POST"])
        @require_auth
        def test_endpoint():
            return jsonify({"status": "ok"})

        with app.test_client() as client:
            response = client.post("/api/test", headers={"Authorization": f"Bearer {token}"})

            assert response.status_code == 200
            assert response.get_json()["status"] == "ok"

    def test_multiple_users_concurrent_tokens(self):
        """複数ユーザーの同時トークン使用"""
        users = ["user1", "user2", "user3"]
        tokens = {user: generate_token(user) for user in users}

        # すべてのトークンが有効
        for user, token in tokens.items():
            payload = verify_token(token)
            assert payload is not None
            assert payload["user_id"] == user

    def test_token_refresh_scenario(self):
        """トークンリフレッシュシナリオ"""
        user_id = "refresh-user"

        # 古いトークン
        old_token = generate_token(user_id, expires_in_hours=1)

        # 新しいトークン
        new_token = generate_token(user_id, expires_in_hours=24)

        # 両方とも有効
        old_payload = verify_token(old_token)
        new_payload = verify_token(new_token)

        assert old_payload["user_id"] == user_id
        assert new_payload["user_id"] == user_id

        # 有効期限が異なる
        old_exp = old_payload["exp"]
        new_exp = new_payload["exp"]
        assert new_exp > old_exp

    @patch.dict(os.environ, {"JWT_SECRET_KEY": "test-secret-123"})
    def test_custom_secret_key(self):
        """カスタム秘密鍵でのトークン生成・検証"""
        user_id = "custom-secret-user"

        # カスタム秘密鍵でトークンを生成
        token = generate_token(user_id)

        # 検証できる
        payload = verify_token(token)
        assert payload is not None
        assert payload["user_id"] == user_id
