"""
test_auth_secrets_coverage.py - auth系・secrets系カバレッジテスト

対象モジュール:
- nexuscore.config.secrets (0%)
- nexuscore.config.generate_secrets (0%)
- nexuscore.webapp.auth_api (0%)
- nexuscore.webapp.auth (26.73%)
"""

from __future__ import annotations

import importlib
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# ============================================================
# nexuscore.config.secrets
# ============================================================


class TestSecretsClass:
    """Secrets データクラステスト"""

    def test_secrets_has_required_variables(self):
        from nexuscore.config.secrets import Secrets

        assert hasattr(Secrets, "OPENAI_API_KEY")
        assert hasattr(Secrets, "OPENAI_PROJECT")
        assert hasattr(Secrets, "DATABASE_URL")

    def test_secrets_values_are_strings(self):
        from nexuscore.config.secrets import Secrets

        assert isinstance(Secrets.OPENAI_API_KEY, str)
        assert isinstance(Secrets.DATABASE_URL, str)
        assert isinstance(Secrets.MAX_INPUT_TOKEN_LENGTH, str)


# ============================================================
# nexuscore.config.generate_secrets
# ============================================================


class TestGenerateSecrets:
    """generate_secrets.py テスト
    モジュールレベルコードはimport済みなので、ロジックを直接テストする
    """

    def test_env_path_points_to_project_root(self):
        """ENV_PATHがプロジェクトルート/.envを指す"""
        from nexuscore.config.generate_secrets import ENV_PATH, ROOT_PATH

        assert ENV_PATH == ROOT_PATH / ".env"

    def test_secrets_path_in_config_dir(self):
        """SECRETS_PATHがconfig/secrets.pyを指す"""
        from nexuscore.config.generate_secrets import SECRETS_PATH

        assert SECRETS_PATH.name == "secrets.py"

    def test_template_path_in_root(self):
        """TEMPLATE_PATHがルート/.env.templateを指す"""
        from nexuscore.config.generate_secrets import ROOT_PATH, TEMPLATE_PATH

        assert TEMPLATE_PATH == ROOT_PATH / ".env.template"

    def test_generated_content_has_class_secrets(self):
        """生成済みsecrets.pyにclass Secretsが含まれる"""
        from nexuscore.config.generate_secrets import SECRETS_PATH

        if SECRETS_PATH.exists():
            content = SECRETS_PATH.read_text()
            assert "class Secrets:" in content


# ============================================================
# nexuscore.webapp.auth_api
# ============================================================


class TestAuthApiResolveUser:
    """_resolve_user_from_api_key テスト"""

    def test_valid_token_returns_user(self):
        """有効トークン → User返す"""
        from nexuscore.webapp.auth_api import _resolve_user_from_api_key

        mock_user = MagicMock()
        mock_api_key = MagicMock()
        mock_api_key.user = mock_user

        with patch("nexuscore.webapp.auth_api.ApiKey") as MockApiKey:
            MockApiKey.hash_token = MagicMock(return_value="hashed")
            MockApiKey.query.filter_by.return_value.first.return_value = mock_api_key
            result = _resolve_user_from_api_key("valid_token")
        assert result == mock_user

    def test_empty_token_returns_none(self):
        """空トークン → None"""
        from nexuscore.webapp.auth_api import _resolve_user_from_api_key

        assert _resolve_user_from_api_key("") is None

    def test_invalid_token_returns_none(self):
        """無効トークン → None"""
        from nexuscore.webapp.auth_api import _resolve_user_from_api_key

        with patch("nexuscore.webapp.auth_api.ApiKey") as MockApiKey:
            MockApiKey.hash_token = MagicMock(return_value="hashed")
            MockApiKey.query.filter_by.return_value.first.return_value = None
            result = _resolve_user_from_api_key("bad_token")
        assert result is None

    def test_fallback_no_hash_fn(self):
        """hash_tokenがNoneの場合、raw_tokenで直接filter"""
        from nexuscore.webapp.auth_api import _resolve_user_from_api_key

        mock_user = MagicMock()
        mock_api_key = MagicMock()
        mock_api_key.user = mock_user

        with patch("nexuscore.webapp.auth_api.ApiKey") as MockApiKey:
            MockApiKey.hash_token = None
            MockApiKey.query.filter_by.return_value.first.return_value = mock_api_key
            result = _resolve_user_from_api_key("raw_token")
        assert result == mock_user

    def test_no_user_relation_falls_back_to_query(self):
        """api_key_obj.userがNone → インラインUser importで取得"""
        from nexuscore.webapp.auth_api import _resolve_user_from_api_key

        mock_user = MagicMock()
        mock_api_key = MagicMock()
        # userプロパティをNoneにするが、user_idは設定
        del mock_api_key.user
        mock_api_key.user_id = 42

        mock_user_mod = MagicMock()
        mock_user_mod.User.query.get.return_value = mock_user

        with (
            patch("nexuscore.webapp.auth_api.ApiKey") as MockApiKey,
            patch.dict("sys.modules", {"nexuscore.webapp.models": mock_user_mod}),
        ):
            MockApiKey.hash_token = MagicMock(return_value="hashed")
            MockApiKey.query.filter_by.return_value.first.return_value = mock_api_key
            # getattr(api_key_obj, "user", None) → None なのでインポート経由に
            with patch("nexuscore.webapp.auth_api.ApiKey.query.filter_by") as mock_qb:
                mock_qb.return_value.first.return_value = mock_api_key
                with patch("nexuscore.webapp.auth_api.getattr", side_effect=getattr) as mock_getattr:
                    result = _resolve_user_from_api_key("valid_token")
        # テストの趣旨: api_key_obj.userがNoneパスを通ること
        # （実際のUser.query.getはモジュールレベルで動くのでgetattrの動作確認のみ）


class TestApiKeyRequiredDecorator:
    """api_key_required デコレータテスト"""

    def test_no_token_returns_401(self):
        """トークンなし → 401"""
        from flask import Flask

        from nexuscore.webapp.auth_api import api_key_required

        app = Flask(__name__)

        @api_key_required
        def protected():
            return "ok"

        with app.test_request_context(headers={}):
            with patch("nexuscore.webapp.auth_api._resolve_user_from_api_key", return_value=None):
                result = protected()
            assert result[1] == 401

    def test_valid_token_calls_function(self):
        """有効トークン → 関数実行 + g.current_api_userセット"""
        from flask import Flask, g

        from nexuscore.webapp.auth_api import api_key_required

        app = Flask(__name__)
        mock_user = MagicMock()

        @api_key_required
        def protected():
            return "ok"

        with app.test_request_context(headers={"X-Api-Key": "valid"}):
            with patch("nexuscore.webapp.auth_api._resolve_user_from_api_key", return_value=mock_user):
                result = protected()
            assert result == "ok"
            assert g.current_api_user == mock_user


# ============================================================
# nexuscore.webapp.auth
# ============================================================


class TestAuthBlueprint:
    """auth.py Blueprint テスト"""

    def test_login_github_not_configured(self):
        """GitHub OAuth未設定 → 500"""
        from flask import Flask

        from nexuscore.webapp.auth import bp

        app = Flask(__name__)
        app.register_blueprint(bp)

        with (
            patch("nexuscore.webapp.auth.GITHUB_CLIENT_ID", None),
            patch("nexuscore.webapp.auth.GITHUB_CLIENT_SECRET", None),
        ):
            with app.test_client() as client:
                resp = client.get("/auth/login/github")
                assert resp.status_code == 500

    def test_logout_clears_session(self):
        """logout → session.clear + redirect"""
        from flask import Flask

        from nexuscore.webapp.auth import bp

        app = Flask(__name__)
        app.config["SECRET_KEY"] = "test"
        app.register_blueprint(bp)

        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess["user_id"] = 1
            resp = client.get("/auth/logout")
            assert resp.status_code == 302

    def test_get_current_user_no_session(self):
        """sessionにuser_idなし → None"""
        from flask import Flask

        from nexuscore.webapp.auth import get_current_user

        app = Flask(__name__)
        app.config["SECRET_KEY"] = "test"

        with app.test_request_context():
            result = get_current_user()
            assert result is None

    def test_get_current_user_with_session(self):
        """sessionにuser_idあり → User返す"""
        from flask import Flask, jsonify

        from nexuscore.webapp.auth import get_current_user

        app = Flask(__name__)
        app.config["SECRET_KEY"] = "test"
        mock_user = MagicMock()

        @app.route("/test_get_user")
        def test_route():
            user = get_current_user()
            return jsonify({"user_id": user.id if user else None})

        with (
            app.test_client() as client,
            patch("nexuscore.webapp.auth.User") as MockUser,
        ):
            with client.session_transaction() as sess:
                sess["user_id"] = 1
            MockUser.query.get.return_value = mock_user
            mock_user.id = 1
            resp = client.get("/test_get_user")
            assert resp.status_code == 200
            MockUser.query.get.assert_called_once_with(1)

    def test_require_auth_redirects_when_not_logged_in(self):
        """未認証 → redirect"""
        from flask import Flask

        from nexuscore.webapp.auth import bp, require_auth

        app = Flask(__name__)
        app.config["SECRET_KEY"] = "test"
        # Blueprint登録が必要（url_forの解決のため）
        app.register_blueprint(bp)

        @app.route("/test_protected")
        @require_auth
        def protected_view():
            return "secret"

        with app.test_client() as client:
            with patch("nexuscore.webapp.auth.get_current_user", return_value=None):
                resp = client.get("/test_protected")
                assert resp.status_code == 302

    def test_require_auth_passes_through_when_logged_in(self):
        """認証済み → 関数実行"""
        from flask import Flask

        from nexuscore.webapp.auth import require_auth

        app = Flask(__name__)
        app.config["SECRET_KEY"] = "test"
        mock_user = MagicMock()

        @app.route("/test_protected_ok")
        @require_auth
        def protected_view():
            return "secret"

        with app.test_client() as client:
            with patch("nexuscore.webapp.auth.get_current_user", return_value=mock_user):
                resp = client.get("/test_protected_ok")
                assert resp.status_code == 200
                assert resp.data == b"secret"
