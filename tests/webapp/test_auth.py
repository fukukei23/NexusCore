# ruff: noqa: F821
"""
webapp/auth.py の高品質なテスト

注意: このテストファイルは Flask レガシー前提です。
CR-FASTAPI-010 で Flask API が削除されたため、このテストファイルは skip されます。
FastAPI 側の認証テストは tests/api/test_fastapi_*.py を参照してください。
"""

import pytest

# CR-FASTAPI-010: Flask レガシー前提のテストは削除済み
# FastAPI 側の認証テストは tests/api/test_fastapi_*.py を参照してください
pytest.skip(
    "Flask legacy auth tests have been removed in CR-FASTAPI-010. "
    "Use FastAPI tests in tests/api/test_fastapi_*.py instead.",
    allow_module_level=True,
)


@pytest.fixture(scope="function")
def app():
    """Flask test app with in-memory SQLite database"""
    from nexuscore.webapp import create_app, db

    config_overrides = {
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "SQLALCHEMY_TRACK_MODIFICATIONS": False,
        "SECRET_KEY": "test-secret-key",
        "WTF_CSRF_ENABLED": False,
    }

    # OAuth 設定を環境変数でモック
    with patch.dict(
        "os.environ",
        {
            "GITHUB_CLIENT_ID": "test_client_id",
            "GITHUB_CLIENT_SECRET": "test_client_secret",
            "GITHUB_REDIRECT_URI": "http://localhost:5000/auth/github/callback",
        },
    ):
        app = create_app(config_overrides=config_overrides)

        with app.app_context():
            db.create_all()
            yield app
            db.session.remove()
            db.drop_all()


@pytest.fixture
def client(app):
    """Test client"""
    return app.test_client()


@pytest.fixture
def db_session(app):
    """Database session for tests"""
    from nexuscore.webapp import db

    with app.app_context():
        yield db.session


class TestInitOAuth:
    """init_oauth() のテスト"""

    def test_init_oauth_registers_github_client(self, app):
        """init_oauth() が GitHub クライアントを登録する"""
        from nexuscore.webapp.auth import oauth

        # OAuth インスタンスが初期化されている
        assert oauth is not None
        # github クライアントが登録されている（create_app で init_oauth が呼ばれる）
        assert hasattr(oauth, "github")


class TestLoginGitHub:
    """login_github() のテスト"""

    def test_login_github_redirects_to_oauth(self, client):
        """login_github() が OAuth 認証にリダイレクトする"""
        from flask import redirect

        with patch("nexuscore.webapp.auth.oauth.github.authorize_redirect") as mock_redirect:
            # redirect オブジェクトを返す
            mock_redirect.return_value = redirect("https://github.com/login/oauth/authorize")

            response = client.get("/auth/login/github")

            # authorize_redirect が呼ばれた
            mock_redirect.assert_called_once()
            # redirect_uri が正しい（callback エンドポイントが含まれる）
            call_args = mock_redirect.call_args
            assert "/auth/github/callback" in str(call_args)

            # リダイレクトされる
            assert response.status_code == 302

    def test_login_github_without_client_id(self, app):
        """GITHUB_CLIENT_ID が未設定の場合エラーを返す"""
        with app.test_client() as client:
            with patch.dict("os.environ", {"GITHUB_CLIENT_ID": "", "GITHUB_CLIENT_SECRET": ""}):
                # auth.py をリロードして環境変数を反映（実際にはモジュールをリロードしないとダメ）
                # ここでは auth.py の GITHUB_CLIENT_ID を直接パッチ
                with patch("nexuscore.webapp.auth.GITHUB_CLIENT_ID", None):
                    with patch("nexuscore.webapp.auth.GITHUB_CLIENT_SECRET", None):
                        response = client.get("/auth/login/github")

                        assert response.status_code == 500
                        data = response.get_json()
                        assert "error" in data
                        assert "OAuth not configured" in data["error"]


class TestGitHubCallback:
    """github_callback() のテスト"""

    def test_github_callback_creates_new_user(self, client, db_session):
        """github_callback() が新規ユーザーを作成する"""
        # OAuth トークンをモック
        mock_token = {"access_token": "test_access_token"}

        # GitHub API レスポンスをモック
        mock_user_response = Mock()
        mock_user_response.status_code = 200
        mock_user_response.json.return_value = {
            "id": 12345,
            "login": "testuser",
            "name": "Test User",
            "avatar_url": "https://example.com/avatar.png",
        }
        mock_user_response.raise_for_status = Mock()

        mock_email_response = Mock()
        mock_email_response.status_code = 200
        mock_email_response.json.return_value = [
            {"email": "test@example.com", "primary": True, "verified": True}
        ]

        with patch(
            "nexuscore.webapp.auth.oauth.github.authorize_access_token", return_value=mock_token
        ):
            with patch("nexuscore.webapp.auth.requests.get") as mock_get:
                mock_get.side_effect = [mock_user_response, mock_email_response]

                with client.session_transaction() as sess:
                    # セッションに何か入れておく（OAuth state など）
                    sess["_oauth_state"] = "test_state"

                response = client.get("/auth/github/callback?code=test_code&state=test_state")

                # プロジェクト一覧にリダイレクト
                assert response.status_code == 302
                assert "/projects" in response.location

                # User が作成されている
                user = User.query.filter_by(github_id="12345").first()
                assert user is not None
                assert user.github_login == "testuser"
                assert user.name == "Test User"
                assert user.avatar_url == "https://example.com/avatar.png"
                assert user.email == "test@example.com"

    def test_github_callback_updates_existing_user(self, client, db_session):
        """github_callback() が既存ユーザーを更新する"""
        # 既存ユーザーを作成
        existing_user = User(
            github_id="12345",
            github_login="oldusername",
            name="Old Name",
        )
        db_session.add(existing_user)
        db_session.commit()

        # OAuth トークンをモック
        mock_token = {"access_token": "test_access_token"}

        # GitHub API レスポンスをモック（更新された情報）
        mock_user_response = Mock()
        mock_user_response.status_code = 200
        mock_user_response.json.return_value = {
            "id": 12345,
            "login": "newusername",
            "name": "New Name",
            "avatar_url": "https://example.com/new_avatar.png",
        }
        mock_user_response.raise_for_status = Mock()

        mock_email_response = Mock()
        mock_email_response.status_code = 200
        mock_email_response.json.return_value = [
            {"email": "new@example.com", "primary": True, "verified": True}
        ]

        with patch(
            "nexuscore.webapp.auth.oauth.github.authorize_access_token", return_value=mock_token
        ):
            with patch("nexuscore.webapp.auth.requests.get") as mock_get:
                mock_get.side_effect = [mock_user_response, mock_email_response]

                client.get("/auth/github/callback?code=test_code")

                # User が更新されている
                user = User.query.filter_by(github_id="12345").first()
                assert user is not None
                assert user.github_login == "newusername"
                assert user.name == "New Name"
                assert user.avatar_url == "https://example.com/new_avatar.png"
                assert user.email == "new@example.com"

    def test_github_callback_handles_email_not_found(self, client, db_session):
        """github_callback() がメールアドレスなしでもユーザーを作成する"""
        mock_token = {"access_token": "test_access_token"}

        mock_user_response = Mock()
        mock_user_response.status_code = 200
        mock_user_response.json.return_value = {
            "id": 12345,
            "login": "testuser",
            "name": "Test User",
        }
        mock_user_response.raise_for_status = Mock()

        # メールアドレス取得失敗
        mock_email_response = Mock()
        mock_email_response.status_code = 404

        with patch(
            "nexuscore.webapp.auth.oauth.github.authorize_access_token", return_value=mock_token
        ):
            with patch("nexuscore.webapp.auth.requests.get") as mock_get:
                mock_get.side_effect = [mock_user_response, mock_email_response]

                client.get("/auth/github/callback?code=test_code")

                # User が作成されている（メールなし）
                user = User.query.filter_by(github_id="12345").first()
                assert user is not None
                assert user.email is None

    def test_github_callback_selects_primary_verified_email(self, client, db_session):
        """github_callback() がプライマリかつ検証済みのメールを選択する"""
        mock_token = {"access_token": "test_access_token"}

        mock_user_response = Mock()
        mock_user_response.status_code = 200
        mock_user_response.json.return_value = {
            "id": 12345,
            "login": "testuser",
        }
        mock_user_response.raise_for_status = Mock()

        # 複数のメールアドレス
        mock_email_response = Mock()
        mock_email_response.status_code = 200
        mock_email_response.json.return_value = [
            {"email": "secondary@example.com", "primary": False, "verified": True},
            {"email": "primary@example.com", "primary": True, "verified": True},
            {"email": "unverified@example.com", "primary": False, "verified": False},
        ]

        with patch(
            "nexuscore.webapp.auth.oauth.github.authorize_access_token", return_value=mock_token
        ):
            with patch("nexuscore.webapp.auth.requests.get") as mock_get:
                mock_get.side_effect = [mock_user_response, mock_email_response]

                client.get("/auth/github/callback?code=test_code")

                # プライマリかつ検証済みのメールが選択されている
                user = User.query.filter_by(github_id="12345").first()
                assert user.email == "primary@example.com"

    def test_github_callback_selects_first_verified_email_if_no_primary(self, client, db_session):
        """github_callback() がプライマリがない場合は最初の検証済みメールを選択する"""
        mock_token = {"access_token": "test_access_token"}

        mock_user_response = Mock()
        mock_user_response.status_code = 200
        mock_user_response.json.return_value = {
            "id": 12345,
            "login": "testuser",
        }
        mock_user_response.raise_for_status = Mock()

        # プライマリなし、検証済みメールのみ
        mock_email_response = Mock()
        mock_email_response.status_code = 200
        mock_email_response.json.return_value = [
            {"email": "first@example.com", "primary": False, "verified": True},
            {"email": "second@example.com", "primary": False, "verified": True},
        ]

        with patch(
            "nexuscore.webapp.auth.oauth.github.authorize_access_token", return_value=mock_token
        ):
            with patch("nexuscore.webapp.auth.requests.get") as mock_get:
                mock_get.side_effect = [mock_user_response, mock_email_response]

                client.get("/auth/github/callback?code=test_code")

                # 最初の検証済みメールが選択されている
                user = User.query.filter_by(github_id="12345").first()
                assert user.email == "first@example.com"

    def test_github_callback_fails_without_token(self, client):
        """github_callback() がトークン取得失敗時にエラーを返す"""
        with patch("nexuscore.webapp.auth.oauth.github.authorize_access_token", return_value=None):
            response = client.get("/auth/github/callback?code=test_code")

            assert response.status_code == 400
            data = response.get_json()
            assert "error" in data
            assert "access token" in data["error"].lower()

    def test_github_callback_handles_api_error(self, client):
        """github_callback() が GitHub API エラーを処理する"""
        mock_token = {"access_token": "test_access_token"}

        with patch(
            "nexuscore.webapp.auth.oauth.github.authorize_access_token", return_value=mock_token
        ):
            with patch("nexuscore.webapp.auth.requests.get") as mock_get:
                # GitHub API がエラーを返す
                mock_get.side_effect = Exception("GitHub API error")

                response = client.get("/auth/github/callback?code=test_code")

                assert response.status_code == 500
                data = response.get_json()
                assert "error" in data
                assert "OAuth callback failed" in data["error"]

    def test_github_callback_stores_session(self, client, db_session):
        """github_callback() がセッションに user_id を保存する"""
        mock_token = {"access_token": "test_access_token"}

        mock_user_response = Mock()
        mock_user_response.status_code = 200
        mock_user_response.json.return_value = {
            "id": 12345,
            "login": "testuser",
        }
        mock_user_response.raise_for_status = Mock()

        mock_email_response = Mock()
        mock_email_response.status_code = 404

        with patch(
            "nexuscore.webapp.auth.oauth.github.authorize_access_token", return_value=mock_token
        ):
            with patch("nexuscore.webapp.auth.requests.get") as mock_get:
                mock_get.side_effect = [mock_user_response, mock_email_response]

                client.get("/auth/github/callback?code=test_code")

                # セッションに user_id が保存されている
                with client.session_transaction() as sess:
                    assert "user_id" in sess
                    assert "github_login" in sess
                    assert sess["github_login"] == "testuser"

                    # user_id が正しい
                    user = User.query.filter_by(github_id="12345").first()
                    assert sess["user_id"] == user.id


class TestLogout:
    """logout() のテスト"""

    def test_logout_clears_session(self, client):
        """logout() がセッションをクリアする"""
        # セッションに何か入れておく
        with client.session_transaction() as sess:
            sess["user_id"] = 123
            sess["github_login"] = "testuser"

        response = client.get("/auth/logout")

        # ログインページにリダイレクト
        assert response.status_code == 302
        assert "/auth/login/github" in response.location

        # セッションがクリアされている
        with client.session_transaction() as sess:
            assert "user_id" not in sess
            assert "github_login" not in sess


class TestGetCurrentUser:
    """get_current_user() のテスト"""

    def test_get_current_user_returns_user_if_logged_in(self, app, db_session):
        """get_current_user() がログイン中のユーザーを返す"""
        from flask import session

        from nexuscore.webapp.auth import get_current_user

        # ユーザーを作成
        user = User(github_id="12345", github_login="testuser")
        db_session.add(user)
        db_session.commit()

        with app.test_client() as client:
            # セッションに user_id を設定
            with client.session_transaction() as sess:
                sess["user_id"] = user.id

            # リクエストコンテキスト内で get_current_user を呼ぶ
            client.get("/")  # ダミーリクエスト
            # リクエストコンテキスト内で get_current_user を実行
            with app.test_request_context():
                session["user_id"] = user.id
                current_user = get_current_user()

                assert current_user is not None
                assert current_user.id == user.id
                assert current_user.github_login == "testuser"

    def test_get_current_user_returns_none_if_not_logged_in(self, app):
        """get_current_user() が未ログイン時に None を返す"""
        from nexuscore.webapp.auth import get_current_user

        # リクエストコンテキスト内で get_current_user を呼ぶ
        with app.test_request_context():
            current_user = get_current_user()

            assert current_user is None

    def test_get_current_user_returns_none_if_user_not_found(self, app):
        """get_current_user() がユーザーが存在しない場合 None を返す"""
        from flask import session

        from nexuscore.webapp.auth import get_current_user

        # リクエストコンテキスト内で get_current_user を呼ぶ
        with app.test_request_context():
            # 存在しない user_id をセッションに設定
            session["user_id"] = 99999
            current_user = get_current_user()

            assert current_user is None


class TestRequireAuth:
    """require_auth() デコレータのテスト"""

    def test_require_auth_allows_authenticated_user(self, app, db_session):
        """require_auth() が認証済みユーザーを通す"""
        from flask import Blueprint

        from nexuscore.webapp.auth import require_auth

        # テスト用 blueprint
        test_bp = Blueprint("test", __name__)

        @test_bp.route("/protected")
        @require_auth
        def protected_route():
            return "Protected content"

        app.register_blueprint(test_bp)

        # ユーザーを作成
        user = User(github_id="12345", github_login="testuser")
        db_session.add(user)
        db_session.commit()

        with app.test_client() as client:
            # セッションに user_id を設定
            with client.session_transaction() as sess:
                sess["user_id"] = user.id

            response = client.get("/protected")

            # アクセスできる
            assert response.status_code == 200
            assert b"Protected content" in response.data

    def test_require_auth_redirects_unauthenticated_user(self, app):
        """require_auth() が未認証ユーザーをログインページにリダイレクトする"""
        from flask import Blueprint

        from nexuscore.webapp.auth import require_auth

        # テスト用 blueprint
        test_bp = Blueprint("test2", __name__)

        @test_bp.route("/protected2")
        @require_auth
        def protected_route():
            return "Protected content"

        app.register_blueprint(test_bp)

        with app.test_client() as client:
            # セッションに user_id がない
            response = client.get("/protected2")

            # ログインページにリダイレクト
            assert response.status_code == 302
            assert "/auth/login/github" in response.location
