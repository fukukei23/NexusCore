"""
Comprehensive tests for cli/bootstrap_apikey.py

API Key ブートストラップ CLI の完全な包括的テスト
"""

import io
import sys

import pytest

from nexuscore.cli.bootstrap_apikey import (
    bootstrap_apikey_for_app,
    bootstrap_apikey_main,
)
from nexuscore.webapp import create_app, db
from nexuscore.webapp.models import ApiKey, User


# ============================================================================
# Fixtures
# ============================================================================
@pytest.fixture
def app(tmp_path):
    """テスト用 Flask app + SQLite DB を用意する。"""
    app = create_app()
    db_path = tmp_path / "test_cli_bootstrap.db"
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path}"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    with app.app_context():
        db.drop_all()
        db.create_all()

    return app


def _capture_stdout_stderr(func, *args, **kwargs):
    """関数実行時の stdout/stderr をキャプチャして返す簡易ヘルパー。"""
    old_out, old_err = sys.stdout, sys.stderr
    out_buf, err_buf = io.StringIO(), io.StringIO()
    sys.stdout, sys.stderr = out_buf, err_buf
    try:
        ret = func(*args, **kwargs)
    finally:
        sys.stdout, sys.stderr = old_out, old_err
    return ret, out_buf.getvalue(), err_buf.getvalue()


# ============================================================================
# bootstrap_apikey_for_app 基本テスト
# ============================================================================
class TestBootstrapApikeyForAppBasic:
    def test_first_time_creates_user_and_key(self, app):
        """初回実行で User + ApiKey が作成されること"""
        with app.app_context():
            assert User.query.count() == 0
            assert ApiKey.query.count() == 0

        user, api_key, token = bootstrap_apikey_for_app(
            app,
            user_login="dev",
            user_name="Dev User",
            key_name="Local Dev Key",
        )

        with app.app_context():
            assert User.query.count() == 1
            u = User.query.filter_by(github_login="dev").one()
            assert u.id == user.id

            keys = ApiKey.query.filter_by(user_id=user.id).all()
            assert len(keys) == 1
            assert keys[0].id == api_key.id

        assert isinstance(token, str)
        assert len(token) > 0

    def test_second_time_reuses_user(self, app):
        """2 回目実行時は User を再利用し、ApiKey だけ増えること"""
        # 1 回目
        user1, api_key1, token1 = bootstrap_apikey_for_app(
            app,
            user_login="dev",
            user_name="Dev User",
            key_name="Key1",
        )

        # 2 回目
        user2, api_key2, token2 = bootstrap_apikey_for_app(
            app,
            user_login="dev",
            user_name="Another Name",
            key_name="Key2",
        )

        assert user1.id == user2.id
        assert api_key1.id != api_key2.id
        assert token1 != token2

        with app.app_context():
            assert User.query.count() == 1
            keys = ApiKey.query.filter_by(user_id=user1.id).all()
            assert len(keys) == 2

    def test_default_key_name(self, app):
        """key_name 未指定時にデフォルト名が使われること"""
        user, api_key, token = bootstrap_apikey_for_app(
            app,
            user_login="dev",
            user_name=None,
            key_name="Bootstrap Dev Key",
        )

        with app.app_context():
            stored = ApiKey.query.filter_by(id=api_key.id).one()
            assert stored.name == "Bootstrap Dev Key"

    def test_user_name_none_uses_login(self, app):
        """user_name が None の場合、user_login が name として使われること"""
        user, api_key, token = bootstrap_apikey_for_app(
            app,
            user_login="testuser",
            user_name=None,
            key_name="Test Key",
        )

        with app.app_context():
            u = User.query.filter_by(github_login="testuser").one()
            assert u.name == "testuser"  # effective_name = user_name or user_login

    def test_user_name_provided(self, app):
        """user_name が指定された場合、それが使われること"""
        user, api_key, token = bootstrap_apikey_for_app(
            app,
            user_login="testuser",
            user_name="Test User Full Name",
            key_name="Test Key",
        )

        with app.app_context():
            u = User.query.filter_by(github_login="testuser").one()
            assert u.name == "Test User Full Name"

    def test_token_is_valid_format(self, app):
        """生成されたトークンが有効な形式であること"""
        user, api_key, token = bootstrap_apikey_for_app(
            app,
            user_login="dev",
            user_name="Dev User",
            key_name="Key",
        )

        # トークンは文字列で、空でないこと
        assert isinstance(token, str)
        assert len(token) > 0

        # トークンがハッシュ化されて保存されていること
        with app.app_context():
            stored_key = ApiKey.query.filter_by(id=api_key.id).one()
            assert stored_key.token_hash is not None
            assert stored_key.token_hash != token  # ハッシュ化されている

    def test_github_id_format(self, app):
        """github_id が正しい形式で作成されること"""
        user, api_key, token = bootstrap_apikey_for_app(
            app,
            user_login="myuser",
            user_name="My User",
            key_name="Key",
        )

        with app.app_context():
            u = User.query.filter_by(github_login="myuser").one()
            assert u.github_id == "cli_bootstrap_myuser"


# ============================================================================
# bootstrap_apikey_for_app エラーケース
# ============================================================================
class TestBootstrapApikeyForAppErrors:
    def test_duplicate_github_id_raises_error(self, app):
        """同じ github_id が既に存在する場合エラーになること"""
        with app.app_context():
            # 手動で github_id が衝突するユーザーを作成
            existing = User(
                github_id="cli_bootstrap_testuser",
                github_login="different_login",
                name="Existing User",
            )
            db.session.add(existing)
            db.session.commit()

        # 同じ github_id を生成しようとするとエラー
        with pytest.raises(RuntimeError, match="already exists"):
            bootstrap_apikey_for_app(
                app,
                user_login="testuser",  # これは cli_bootstrap_testuser になる
                user_name="Test User",
                key_name="Key",
            )

    def test_empty_user_login_creates_user(self, app):
        """空の user_login でもユーザーが作成されること（エッジケース）"""
        user, api_key, token = bootstrap_apikey_for_app(
            app,
            user_login="",
            user_name="Empty Login User",
            key_name="Key",
        )

        with app.app_context():
            u = User.query.filter_by(github_login="").one()
            assert u.name == "Empty Login User"

    def test_special_characters_in_login(self, app):
        """特殊文字を含む user_login"""
        user, api_key, token = bootstrap_apikey_for_app(
            app,
            user_login="user-name_123",
            user_name="Special User",
            key_name="Key",
        )

        with app.app_context():
            u = User.query.filter_by(github_login="user-name_123").one()
            assert u.github_id == "cli_bootstrap_user-name_123"

    def test_unicode_in_user_name(self, app):
        """Unicode文字を含む user_name"""
        user, api_key, token = bootstrap_apikey_for_app(
            app,
            user_login="unicode_user",
            user_name="ユーザー名前",
            key_name="Unicodeキー",
        )

        with app.app_context():
            u = User.query.filter_by(github_login="unicode_user").one()
            assert u.name == "ユーザー名前"

            k = ApiKey.query.filter_by(id=api_key.id).one()
            assert k.name == "Unicodeキー"

    def test_very_long_names(self, app):
        """非常に長い名前"""
        long_login = "a" * 100
        long_name = "b" * 200
        long_key_name = "c" * 150

        user, api_key, token = bootstrap_apikey_for_app(
            app,
            user_login=long_login,
            user_name=long_name,
            key_name=long_key_name,
        )

        with app.app_context():
            u = User.query.filter_by(github_login=long_login).one()
            assert len(u.name) == 200

    def test_empty_key_name(self, app):
        """空の key_name"""
        user, api_key, token = bootstrap_apikey_for_app(
            app,
            user_login="user",
            user_name="User",
            key_name="",
        )

        with app.app_context():
            k = ApiKey.query.filter_by(id=api_key.id).one()
            assert k.name == ""


# ============================================================================
# bootstrap_apikey_for_app トークン・DB操作テスト
# ============================================================================
class TestBootstrapApikeyForAppTokenAndDB:
    def test_token_uniqueness(self, app):
        """生成されるトークンがユニークであること"""
        tokens = []
        for i in range(5):
            user, api_key, token = bootstrap_apikey_for_app(
                app,
                user_login="dev",
                user_name="Dev User",
                key_name=f"Key {i}",
            )
            tokens.append(token)

        # 全てのトークンがユニーク
        assert len(set(tokens)) == 5

    def test_token_hash_storage(self, app):
        """トークンがハッシュ化されて保存されること"""
        user, api_key, token = bootstrap_apikey_for_app(
            app,
            user_login="dev",
            user_name="Dev User",
            key_name="Key",
        )

        with app.app_context():
            stored_key = ApiKey.query.filter_by(id=api_key.id).one()

            # token_hash が設定されている
            assert stored_key.token_hash is not None

            # 生トークンとは異なる
            assert stored_key.token_hash != token

            # ハッシュの長さチェック
            assert len(stored_key.token_hash) > 0

    def test_expunge_allows_access_outside_context(self, app):
        """expunge されたオブジェクトがコンテキスト外でアクセス可能なこと"""
        user, api_key, token = bootstrap_apikey_for_app(
            app,
            user_login="dev",
            user_name="Dev User",
            key_name="Key",
        )

        # app_context 外でもアクセス可能
        assert user.id is not None
        assert user.github_login == "dev"
        assert api_key.id is not None
        assert api_key.name == "Key"

    def test_multiple_keys_for_same_user(self, app):
        """同じユーザーに複数のキーを発行できること"""
        key_names = ["Key1", "Key2", "Key3", "Key4", "Key5"]
        api_keys = []

        for name in key_names:
            user, api_key, token = bootstrap_apikey_for_app(
                app,
                user_login="dev",
                user_name="Dev User",
                key_name=name,
            )
            api_keys.append(api_key)

        with app.app_context():
            assert User.query.count() == 1
            user = User.query.filter_by(github_login="dev").one()

            keys = ApiKey.query.filter_by(user_id=user.id).all()
            assert len(keys) == 5

            # 全てのキー名が正しいこと
            stored_names = {k.name for k in keys}
            assert stored_names == set(key_names)

    def test_different_users_have_different_keys(self, app):
        """異なるユーザーは異なるキーを持つこと"""
        user1, key1, token1 = bootstrap_apikey_for_app(
            app, user_login="user1", user_name="User 1", key_name="Key1"
        )
        user2, key2, token2 = bootstrap_apikey_for_app(
            app, user_login="user2", user_name="User 2", key_name="Key2"
        )
        user3, key3, token3 = bootstrap_apikey_for_app(
            app, user_login="user3", user_name="User 3", key_name="Key3"
        )

        assert user1.id != user2.id != user3.id
        assert key1.id != key2.id != key3.id
        assert token1 != token2 != token3

        with app.app_context():
            assert User.query.count() == 3
            assert ApiKey.query.count() == 3


# ============================================================================
# bootstrap_apikey_main 基本テスト
# ============================================================================
class TestBootstrapApikeyMainBasic:
    def test_returns_zero_on_success(self, app, monkeypatch):
        """bootstrap_apikey_main が成功時に 0 を返すこと"""
        monkeypatch.setattr(
            "nexuscore.cli.bootstrap_apikey.create_app",
            lambda: app,
        )

        code, out, err = _capture_stdout_stderr(
            bootstrap_apikey_main,
            ["--user-login", "dev", "--key-name", "Local Dev Key"],
        )

        assert code == 0
        assert "export NEXUSCORE_API_KEY=" in out

    def test_outputs_export_command(self, app, monkeypatch):
        """bootstrap_apikey_main が export コマンドを stdout に出すこと"""
        monkeypatch.setattr(
            "nexuscore.cli.bootstrap_apikey.create_app",
            lambda: app,
        )

        code, out, err = _capture_stdout_stderr(
            bootstrap_apikey_main,
            ["--user-login", "dev", "--key-name", "Local Dev Key"],
        )

        assert code == 0
        lines = [line_ for line_ in out.splitlines() if line_.strip()]
        assert any(line_.startswith("export NEXUSCORE_API_KEY=") for line_ in lines)

    def test_outputs_info_to_stderr(self, app, monkeypatch):
        """メタ情報が stderr に出力されること"""
        monkeypatch.setattr(
            "nexuscore.cli.bootstrap_apikey.create_app",
            lambda: app,
        )

        code, out, err = _capture_stdout_stderr(
            bootstrap_apikey_main,
            ["--user-login", "testuser", "--key-name", "Test Key"],
        )

        assert code == 0
        assert "[INFO]" in err
        assert "testuser" in err
        assert "Test Key" in err

    def test_with_user_name_argument(self, app, monkeypatch):
        """--user-name 引数が正しく処理されること"""
        monkeypatch.setattr(
            "nexuscore.cli.bootstrap_apikey.create_app",
            lambda: app,
        )

        code, out, err = _capture_stdout_stderr(
            bootstrap_apikey_main,
            [
                "--user-login",
                "dev",
                "--user-name",
                "Developer User",
                "--key-name",
                "Dev Key",
            ],
        )

        assert code == 0

        with app.app_context():
            user = User.query.filter_by(github_login="dev").one()
            assert user.name == "Developer User"

    def test_without_user_name_argument(self, app, monkeypatch):
        """--user-name なしで実行できること"""
        monkeypatch.setattr(
            "nexuscore.cli.bootstrap_apikey.create_app",
            lambda: app,
        )

        code, out, err = _capture_stdout_stderr(
            bootstrap_apikey_main,
            ["--user-login", "dev", "--key-name", "Key"],
        )

        assert code == 0

        with app.app_context():
            user = User.query.filter_by(github_login="dev").one()
            # user_name が None なので login が使われる
            assert user.name == "dev"

    def test_default_key_name_when_not_specified(self, app, monkeypatch):
        """--key-name を省略した場合デフォルト値が使われること"""
        monkeypatch.setattr(
            "nexuscore.cli.bootstrap_apikey.create_app",
            lambda: app,
        )

        code, out, err = _capture_stdout_stderr(
            bootstrap_apikey_main,
            ["--user-login", "dev"],
        )

        assert code == 0

        with app.app_context():
            user = User.query.filter_by(github_login="dev").one()
            keys = ApiKey.query.filter_by(user_id=user.id).all()
            assert len(keys) == 1
            assert keys[0].name == "Bootstrap Dev Key"


# ============================================================================
# bootstrap_apikey_main エラーケース
# ============================================================================
class TestBootstrapApikeyMainErrors:
    def test_missing_required_argument_returns_nonzero(self):
        """必須引数が欠けている場合、非ゼロコードを返すこと"""
        with pytest.raises(SystemExit) as exc_info:
            bootstrap_apikey_main([])

        # argparse が SystemExit(2) を発生させる
        assert exc_info.value.code == 2

    def test_missing_user_login_argument(self):
        """--user-login が欠けている場合エラー"""
        with pytest.raises(SystemExit) as exc_info:
            bootstrap_apikey_main(["--key-name", "Key"])

        assert exc_info.value.code == 2

    def test_exception_in_app_creation_returns_one(self, monkeypatch):
        """アプリ作成中の例外で終了コード 1 を返すこと"""

        def _failing_create_app():
            raise RuntimeError("Failed to create app")

        monkeypatch.setattr(
            "nexuscore.cli.bootstrap_apikey.create_app",
            _failing_create_app,
        )

        code, out, err = _capture_stdout_stderr(
            bootstrap_apikey_main,
            ["--user-login", "dev"],
        )

        assert code == 1
        assert "Error:" in err

    def test_exception_in_bootstrap_returns_one(self, app, monkeypatch):
        """bootstrap中の例外で終了コード 1 を返すこと"""
        monkeypatch.setattr(
            "nexuscore.cli.bootstrap_apikey.create_app",
            lambda: app,
        )

        # github_id 衝突を起こす
        with app.app_context():
            existing = User(
                github_id="cli_bootstrap_dev",
                github_login="other",
                name="Other",
            )
            db.session.add(existing)
            db.session.commit()

        code, out, err = _capture_stdout_stderr(
            bootstrap_apikey_main,
            ["--user-login", "dev"],
        )

        assert code == 1
        assert "Error:" in err

    def test_help_argument(self):
        """--help で SystemExit(0) が発生すること"""
        with pytest.raises(SystemExit) as exc_info:
            bootstrap_apikey_main(["--help"])

        assert exc_info.value.code == 0

    def test_unknown_argument(self):
        """不明な引数でエラー"""
        with pytest.raises(SystemExit) as exc_info:
            bootstrap_apikey_main(["--unknown-arg", "value"])

        assert exc_info.value.code == 2


# ============================================================================
# bootstrap_apikey_main 引数パーステスト
# ============================================================================
class TestBootstrapApikeyMainArgumentParsing:
    def test_argv_none_uses_sys_argv(self, app, monkeypatch):
        """argv=None の場合 sys.argv を使用すること"""
        monkeypatch.setattr(
            "nexuscore.cli.bootstrap_apikey.create_app",
            lambda: app,
        )

        # sys.argv を偽装
        original_argv = sys.argv
        try:
            sys.argv = ["bootstrap_apikey", "--user-login", "dev"]

            code, out, err = _capture_stdout_stderr(
                bootstrap_apikey_main,
                None,  # argv=None
            )

            assert code == 0
        finally:
            sys.argv = original_argv

    def test_argv_list_overrides_sys_argv(self, app, monkeypatch):
        """argv リストが指定された場合、sys.argv を上書きすること"""
        monkeypatch.setattr(
            "nexuscore.cli.bootstrap_apikey.create_app",
            lambda: app,
        )

        original_argv = sys.argv
        try:
            sys.argv = ["should", "be", "ignored"]

            code, out, err = _capture_stdout_stderr(
                bootstrap_apikey_main,
                ["--user-login", "custom"],
            )

            assert code == 0

            with app.app_context():
                user = User.query.filter_by(github_login="custom").one()
                assert user is not None
        finally:
            sys.argv = original_argv

    def test_all_arguments_together(self, app, monkeypatch):
        """全引数を同時に指定"""
        monkeypatch.setattr(
            "nexuscore.cli.bootstrap_apikey.create_app",
            lambda: app,
        )

        code, out, err = _capture_stdout_stderr(
            bootstrap_apikey_main,
            [
                "--user-login",
                "fulluser",
                "--user-name",
                "Full User Name",
                "--key-name",
                "Full Key Name",
            ],
        )

        assert code == 0

        with app.app_context():
            user = User.query.filter_by(github_login="fulluser").one()
            assert user.name == "Full User Name"

            keys = ApiKey.query.filter_by(user_id=user.id).all()
            assert len(keys) == 1
            assert keys[0].name == "Full Key Name"


# ============================================================================
# 統合テスト
# ============================================================================
class TestIntegration:
    def test_full_workflow_new_user(self, app, monkeypatch):
        """完全なワークフロー: 新規ユーザー作成"""
        monkeypatch.setattr(
            "nexuscore.cli.bootstrap_apikey.create_app",
            lambda: app,
        )

        # 初期状態確認
        with app.app_context():
            assert User.query.count() == 0
            assert ApiKey.query.count() == 0

        # CLI実行
        code, out, err = _capture_stdout_stderr(
            bootstrap_apikey_main,
            [
                "--user-login",
                "newuser",
                "--user-name",
                "New User",
                "--key-name",
                "First Key",
            ],
        )

        assert code == 0
        assert "export NEXUSCORE_API_KEY=" in out

        # 結果確認
        with app.app_context():
            assert User.query.count() == 1
            user = User.query.filter_by(github_login="newuser").one()
            assert user.name == "New User"
            assert user.github_id == "cli_bootstrap_newuser"

            assert ApiKey.query.count() == 1
            key = ApiKey.query.filter_by(user_id=user.id).one()
            assert key.name == "First Key"

    def test_full_workflow_existing_user(self, app, monkeypatch):
        """完全なワークフロー: 既存ユーザーに追加キー発行"""
        monkeypatch.setattr(
            "nexuscore.cli.bootstrap_apikey.create_app",
            lambda: app,
        )

        # 1回目: ユーザー作成
        code1, out1, err1 = _capture_stdout_stderr(
            bootstrap_apikey_main,
            ["--user-login", "existing", "--key-name", "Key1"],
        )
        assert code1 == 0

        # 2回目: 同じユーザーに追加キー
        code2, out2, err2 = _capture_stdout_stderr(
            bootstrap_apikey_main,
            ["--user-login", "existing", "--key-name", "Key2"],
        )
        assert code2 == 0

        # トークンが異なること
        token1 = out1.split('"')[1]
        token2 = out2.split('"')[1]
        assert token1 != token2

        # 結果確認
        with app.app_context():
            assert User.query.count() == 1
            user = User.query.filter_by(github_login="existing").one()

            keys = ApiKey.query.filter_by(user_id=user.id).all()
            assert len(keys) == 2

            key_names = {k.name for k in keys}
            assert key_names == {"Key1", "Key2"}

    def test_multiple_users_workflow(self, app, monkeypatch):
        """複数ユーザー作成ワークフロー"""
        monkeypatch.setattr(
            "nexuscore.cli.bootstrap_apikey.create_app",
            lambda: app,
        )

        users = [
            ("user1", "User One", "Key1"),
            ("user2", "User Two", "Key2"),
            ("user3", "User Three", "Key3"),
        ]

        for login, name, key_name in users:
            code, out, err = _capture_stdout_stderr(
                bootstrap_apikey_main,
                [
                    "--user-login",
                    login,
                    "--user-name",
                    name,
                    "--key-name",
                    key_name,
                ],
            )
            assert code == 0

        with app.app_context():
            assert User.query.count() == 3
            assert ApiKey.query.count() == 3

            for login, name, key_name in users:
                user = User.query.filter_by(github_login=login).one()
                assert user.name == name

                keys = ApiKey.query.filter_by(user_id=user.id).all()
                assert len(keys) == 1
                assert keys[0].name == key_name

    def test_token_format_in_output(self, app, monkeypatch):
        """出力されたトークンの形式が正しいこと"""
        monkeypatch.setattr(
            "nexuscore.cli.bootstrap_apikey.create_app",
            lambda: app,
        )

        code, out, err = _capture_stdout_stderr(
            bootstrap_apikey_main,
            ["--user-login", "dev"],
        )

        assert code == 0

        # export コマンドの形式チェック
        assert out.startswith("export NEXUSCORE_API_KEY=")

        # トークンを抽出
        token = out.split('"')[1]
        assert len(token) > 0
        assert isinstance(token, str)


# ============================================================================
# エッジケース・境界値テスト
# ============================================================================
class TestEdgeCases:
    def test_empty_string_arguments(self, app, monkeypatch):
        """空文字列の引数"""
        monkeypatch.setattr(
            "nexuscore.cli.bootstrap_apikey.create_app",
            lambda: app,
        )

        code, out, err = _capture_stdout_stderr(
            bootstrap_apikey_main,
            [
                "--user-login",
                "",
                "--user-name",
                "",
                "--key-name",
                "",
            ],
        )

        assert code == 0

        with app.app_context():
            user = User.query.filter_by(github_login="").one()
            assert user.name == ""  # user_name が空なので login も空

            keys = ApiKey.query.filter_by(user_id=user.id).all()
            assert keys[0].name == ""

    def test_whitespace_only_arguments(self, app, monkeypatch):
        """空白のみの引数"""
        monkeypatch.setattr(
            "nexuscore.cli.bootstrap_apikey.create_app",
            lambda: app,
        )

        code, out, err = _capture_stdout_stderr(
            bootstrap_apikey_main,
            [
                "--user-login",
                "   ",
                "--user-name",
                "  \t  ",
                "--key-name",
                "  \n  ",
            ],
        )

        assert code == 0

    def test_special_shell_characters(self, app, monkeypatch):
        """シェル特殊文字を含む引数"""
        monkeypatch.setattr(
            "nexuscore.cli.bootstrap_apikey.create_app",
            lambda: app,
        )

        code, out, err = _capture_stdout_stderr(
            bootstrap_apikey_main,
            [
                "--user-login",
                "user$with&special",
                "--key-name",
                "key;with|pipes",
            ],
        )

        assert code == 0

        with app.app_context():
            user = User.query.filter_by(github_login="user$with&special").one()
            assert user is not None

    def test_very_long_arguments(self, app, monkeypatch):
        """非常に長い引数"""
        monkeypatch.setattr(
            "nexuscore.cli.bootstrap_apikey.create_app",
            lambda: app,
        )

        long_login = "x" * 500
        long_name = "y" * 1000
        long_key = "z" * 750

        code, out, err = _capture_stdout_stderr(
            bootstrap_apikey_main,
            [
                "--user-login",
                long_login,
                "--user-name",
                long_name,
                "--key-name",
                long_key,
            ],
        )

        assert code == 0

        with app.app_context():
            user = User.query.filter_by(github_login=long_login).one()
            assert len(user.github_login) == 500


# ============================================================================
# セキュリティテスト
# ============================================================================
class TestSecurity:
    def test_token_is_not_logged_to_stderr(self, app, monkeypatch):
        """トークンが stderr にログ出力されないこと"""
        monkeypatch.setattr(
            "nexuscore.cli.bootstrap_apikey.create_app",
            lambda: app,
        )

        code, out, err = _capture_stdout_stderr(
            bootstrap_apikey_main,
            ["--user-login", "dev"],
        )

        assert code == 0

        # stdout からトークンを抽出
        token = out.split('"')[1]

        # stderr にトークンが含まれていないこと
        assert token not in err

    def test_token_hash_is_different_from_raw(self, app):
        """保存されたハッシュが生トークンと異なること"""
        user, api_key, raw_token = bootstrap_apikey_for_app(
            app,
            user_login="dev",
            user_name="Dev",
            key_name="Key",
        )

        with app.app_context():
            stored = ApiKey.query.filter_by(id=api_key.id).one()
            assert stored.token_hash != raw_token
            assert len(stored.token_hash) > 0

    def test_multiple_tokens_have_different_hashes(self, app):
        """複数のトークンが異なるハッシュを持つこと"""
        hashes = []

        for i in range(5):
            user, api_key, token = bootstrap_apikey_for_app(
                app,
                user_login="dev",
                user_name="Dev",
                key_name=f"Key{i}",
            )

            with app.app_context():
                stored = ApiKey.query.filter_by(id=api_key.id).one()
                hashes.append(stored.token_hash)

        # 全てのハッシュがユニーク
        assert len(set(hashes)) == 5
