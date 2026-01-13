"""
webapp/auth_api.py の高品質なテスト

注意: このテストファイルは Flask レガシー前提です。
CR-FASTAPI-010 で Flask API が削除されたため、このテストファイルは skip されます。
FastAPI 側の認証テストは tests/api/test_fastapi_*.py を参照してください。
"""
import pytest

# CR-FASTAPI-010: Flask レガシー前提のテストは削除済み
# FastAPI 側の認証テストは tests/api/test_fastapi_*.py を参照してください
pytest.skip(
    "Flask legacy auth_api tests have been removed in CR-FASTAPI-010. "
    "Use FastAPI tests in tests/api/test_fastapi_*.py instead.",
    allow_module_level=True
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


@pytest.fixture
def test_user(db_session):
    """テスト用ユーザー"""
    user = User(
        github_id="12345",
        github_login="testuser",
        name="Test User",
    )
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def test_api_key(db_session, test_user):
    """テスト用 API キー（生トークンを返す）"""
    raw_token = ApiKey.generate_token()
    token_hash = ApiKey.hash_token(raw_token)

    api_key = ApiKey(
        user_id=test_user.id,
        token_hash=token_hash,
        name="Test API Key",
    )
    db_session.add(api_key)
    db_session.commit()

    return raw_token


class TestResolveUserFromApiKey:
    """_resolve_user_from_api_key() のテスト"""

    def test_resolve_user_with_valid_token(self, app, test_user, test_api_key):
        """有効なトークンでユーザーを解決できる"""
        from nexuscore.webapp.auth_api import _resolve_user_from_api_key

        with app.app_context():
            user = _resolve_user_from_api_key(test_api_key)

            assert user is not None
            assert user.id == test_user.id
            assert user.github_login == "testuser"

    def test_resolve_user_with_invalid_token(self, app):
        """無効なトークンは None を返す"""
        from nexuscore.webapp.auth_api import _resolve_user_from_api_key

        with app.app_context():
            user = _resolve_user_from_api_key("invalid_token_12345")

            assert user is None

    def test_resolve_user_with_empty_token(self, app):
        """空のトークンは None を返す"""
        from nexuscore.webapp.auth_api import _resolve_user_from_api_key

        with app.app_context():
            user = _resolve_user_from_api_key("")

            assert user is None

    def test_resolve_user_without_token(self, app):
        """None トークンは None を返す"""
        from nexuscore.webapp.auth_api import _resolve_user_from_api_key

        with app.app_context():
            user = _resolve_user_from_api_key(None)

            assert user is None

    def test_resolve_user_with_hash_token_method(self, app, test_user, test_api_key):
        """hash_token メソッドが存在する場合に正しく動作する"""
        from nexuscore.webapp.auth_api import _resolve_user_from_api_key

        with app.app_context():
            # ApiKey.hash_token が存在することを確認
            assert callable(getattr(ApiKey, "hash_token", None))

            user = _resolve_user_from_api_key(test_api_key)

            assert user is not None
            assert user.id == test_user.id

    def test_resolve_user_fallback_without_hash_token(self, app, db_session, test_user):
        """hash_token メソッドがない場合のフォールバック動作"""
        from nexuscore.webapp.auth_api import _resolve_user_from_api_key

        with app.app_context():
            # hash_token メソッドをモック（存在しない状態をシミュレート）
            raw_token = "direct_token_hash"
            api_key = ApiKey(
                user_id=test_user.id,
                token_hash=raw_token,  # ハッシュ化せずに直接保存
                name="Direct Token",
            )
            db_session.add(api_key)
            db_session.commit()

            with patch.object(ApiKey, "hash_token", None):
                user = _resolve_user_from_api_key(raw_token)

                # フォールバックで直接比較される
                assert user is not None
                assert user.id == test_user.id

    def test_resolve_user_loads_relationship(self, app, db_session, test_user, test_api_key):
        """User リレーションが読み込まれていない場合でも取得できる"""
        from nexuscore.webapp.auth_api import _resolve_user_from_api_key

        with app.app_context():
            # リレーションがロードされていない状態をシミュレート
            user = _resolve_user_from_api_key(test_api_key)

            # User が取得できる
            assert user is not None
            assert user.id == test_user.id


class TestApiKeyRequired:
    """api_key_required() デコレータのテスト"""

    def test_api_key_required_allows_valid_key_in_header(self, app, client, test_user, test_api_key):
        """有効な API キーが X-Api-Key ヘッダにある場合アクセスを許可"""
        from nexuscore.webapp.auth_api import api_key_required

        # テスト用エンドポイントを作成
        test_bp = Blueprint("test_api", __name__)

        @test_bp.route("/test")
        @api_key_required
        def test_endpoint():
            user = g.current_api_user
            return {"user_id": user.id, "github_login": user.github_login}

        app.register_blueprint(test_bp)

        response = client.get(
            "/test",
            headers={"X-Api-Key": test_api_key}
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["user_id"] == test_user.id
        assert data["github_login"] == "testuser"

    def test_api_key_required_allows_valid_key_in_query(self, app, client, test_user, test_api_key):
        """有効な API キーがクエリパラメータにある場合アクセスを許可"""
        from nexuscore.webapp.auth_api import api_key_required

        test_bp = Blueprint("test_api2", __name__)

        @test_bp.route("/test2")
        @api_key_required
        def test_endpoint():
            user = g.current_api_user
            return {"user_id": user.id}

        app.register_blueprint(test_bp)

        response = client.get(f"/test2?api_key={test_api_key}")

        assert response.status_code == 200
        data = response.get_json()
        assert data["user_id"] == test_user.id

    def test_api_key_required_rejects_invalid_key(self, app, client):
        """無効な API キーは 401 を返す"""
        from nexuscore.webapp.auth_api import api_key_required

        test_bp = Blueprint("test_api3", __name__)

        @test_bp.route("/test3")
        @api_key_required
        def test_endpoint():
            return {"success": True}

        app.register_blueprint(test_bp)

        response = client.get(
            "/test3",
            headers={"X-Api-Key": "invalid_key"}
        )

        assert response.status_code == 401
        data = response.get_json()
        assert "error" in data
        assert "api key" in data["error"].lower()

    def test_api_key_required_rejects_missing_key(self, app, client):
        """API キーがない場合 401 を返す"""
        from nexuscore.webapp.auth_api import api_key_required

        test_bp = Blueprint("test_api4", __name__)

        @test_bp.route("/test4")
        @api_key_required
        def test_endpoint():
            return {"success": True}

        app.register_blueprint(test_bp)

        response = client.get("/test4")

        assert response.status_code == 401
        data = response.get_json()
        assert "error" in data

    def test_api_key_required_prefers_header_over_query(self, app, client, db_session, test_user, test_api_key):
        """ヘッダーとクエリパラメータの両方がある場合ヘッダーを優先"""
        from nexuscore.webapp.auth_api import api_key_required

        # 別の API キーを作成
        another_token = ApiKey.generate_token()
        another_api_key = ApiKey(
            user_id=test_user.id,
            token_hash=ApiKey.hash_token(another_token),
            name="Another Key",
        )
        db_session.add(another_api_key)
        db_session.commit()

        test_bp = Blueprint("test_api5", __name__)

        @test_bp.route("/test5")
        @api_key_required
        def test_endpoint():
            return {"success": True}

        app.register_blueprint(test_bp)

        # ヘッダーに有効なキー、クエリに無効なキー
        response = client.get(
            f"/test5?api_key=invalid_key",
            headers={"X-Api-Key": test_api_key}
        )

        # ヘッダーが優先されるので成功
        assert response.status_code == 200

    def test_api_key_required_sets_current_api_user_in_g(self, app, client, test_user, test_api_key):
        """api_key_required が g.current_api_user をセットする"""
        from nexuscore.webapp.auth_api import api_key_required

        test_bp = Blueprint("test_api6", __name__)

        @test_bp.route("/test6")
        @api_key_required
        def test_endpoint():
            # g.current_api_user にアクセスできる
            assert hasattr(g, "current_api_user")
            assert g.current_api_user.id == test_user.id
            return {"success": True}

        app.register_blueprint(test_bp)

        response = client.get(
            "/test6",
            headers={"X-Api-Key": test_api_key}
        )

        assert response.status_code == 200

    def test_api_key_required_preserves_function_metadata(self):
        """api_key_required がデコレートされた関数のメタデータを保持する"""
        from nexuscore.webapp.auth_api import api_key_required

        @api_key_required
        def my_endpoint():
            """This is my endpoint"""
            return {"success": True}

        # @wraps により関数名とドキュメントが保持される
        assert my_endpoint.__name__ == "my_endpoint"
        assert my_endpoint.__doc__ == "This is my endpoint"
