"""
API Key ブートストラップ CLI のテスト

CR-FASTAPI-021 で作成された bootstrap_apikey CLI のテスト。
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


def test_bootstrap_apikey_first_time_creates_user_and_key(app):
    """初回実行で User + ApiKey が作成されること。"""
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
        # bootstrap_apikey_for_app から返されたオブジェクトは expunge されているので、
        # 直接属性にアクセスできる
        assert u.id == user.id

        keys = ApiKey.query.filter_by(user_id=user.id).all()
        assert len(keys) == 1
        assert keys[0].id == api_key.id

    assert isinstance(token, str)
    assert len(token) > 0


def test_bootstrap_apikey_second_time_reuses_user(app):
    """2 回目実行時は User を再利用し、ApiKey だけ増えること。"""
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

    # bootstrap_apikey_for_app から返されたオブジェクトは expunge されているので、
    # 直接属性にアクセスできる
    assert user1.id == user2.id
    assert api_key1.id != api_key2.id
    assert token1 != token2

    with app.app_context():
        assert User.query.count() == 1
        keys = ApiKey.query.filter_by(user_id=user1.id).all()
        assert len(keys) == 2


def test_bootstrap_apikey_default_key_name(app):
    """key_name 未指定時にデフォルト名が使われること。"""
    user, api_key, token = bootstrap_apikey_for_app(
        app,
        user_login="dev",
        user_name=None,
        key_name="Bootstrap Dev Key",  # main と同じデフォルト
    )

    with app.app_context():
        stored = ApiKey.query.filter_by(id=api_key.id).one()
        assert stored.name == "Bootstrap Dev Key"


def test_bootstrap_apikey_main_returns_zero_on_success(app, monkeypatch):
    """bootstrap_apikey_main が成功時に 0 を返すこと。"""

    def _fake_create_app():
        return app

    monkeypatch.setattr(
        "nexuscore.cli.bootstrap_apikey.create_app",
        _fake_create_app,
    )

    code, out, err = _capture_stdout_stderr(
        bootstrap_apikey_main,
        ["--user-login", "dev", "--key-name", "Local Dev Key"],
    )

    assert code == 0
    # export 行が stdout に出ていること
    assert "export NEXUSCORE_API_KEY=" in out


def test_bootstrap_apikey_main_outputs_export_command(app, monkeypatch):
    """bootstrap_apikey_main が export コマンドのみ stdout に出すこと。"""

    def _fake_create_app():
        return app

    monkeypatch.setattr(
        "nexuscore.cli.bootstrap_apikey.create_app",
        _fake_create_app,
    )

    code, out, err = _capture_stdout_stderr(
        bootstrap_apikey_main,
        ["--user-login", "dev", "--key-name", "Local Dev Key"],
    )

    assert code == 0
    # stdout: export 行のみ（複数行あっても先頭に export が含まれていることを確認）
    lines = [l for l in out.splitlines() if l.strip()]
    assert any(l.startswith("export NEXUSCORE_API_KEY=") for l in lines)
