"""
API Key ブートストラップ CLI のテスト

CR-FASTAPI-021 で作成された bootstrap_apikey CLI のテスト。
"""
import pytest
import sys
from io import StringIO
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent.parent
src_path = project_root / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from nexuscore.webapp import create_app, db
from nexuscore.webapp.models import User, ApiKey
from nexuscore.cli.bootstrap_apikey import bootstrap_apikey_main


@pytest.fixture
def app():
    """テスト用 Flask アプリケーション"""
    app = create_app(config_overrides={
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "TESTING": True,
        "SECRET_KEY": "test-secret-key",
    })
    
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


def test_bootstrap_apikey_first_time_creates_user_and_key(app):
    """
    初回実行 → User + ApiKey が 1 レコードずつ作成される
    """
    with app.app_context():
        # 実行前の状態確認
        assert User.query.count() == 0
        assert ApiKey.query.count() == 0

        # CLI を実行
        argv = [
            "--user-login", "dev",
            "--user-name", "Dev User",
            "--key-name", "Local Dev Key",
        ]
        
        # 標準出力をキャプチャ
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        sys.stdout = StringIO()
        sys.stderr = StringIO()
        
        try:
            exit_code = bootstrap_apikey_main(argv)
            stdout_output = sys.stdout.getvalue()
            stderr_output = sys.stderr.getvalue()
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr

        # 検証
        assert exit_code == 0
        
        # User が作成された
        user = User.query.filter_by(github_login="dev").first()
        assert user is not None
        assert user.name == "Dev User"
        assert user.github_id.startswith("cli_bootstrap_")
        
        # ApiKey が作成された
        api_keys = ApiKey.query.filter_by(user_id=user.id).all()
        assert len(api_keys) == 1
        assert api_keys[0].name == "Local Dev Key"
        
        # 標準出力に export NEXUSCORE_API_KEY="..." が含まれる
        assert "export NEXUSCORE_API_KEY=" in stdout_output
        assert "nexus_" in stdout_output
        
        # 標準エラーに INFO メッセージが含まれる
        assert "Created user" in stderr_output or "Using existing user" in stderr_output
        assert "Created API key" in stderr_output


def test_bootstrap_apikey_second_time_reuses_user(app):
    """
    2回目以降 → User は再利用され、ApiKey が増えるだけ
    """
    with app.app_context():
        # 初回実行
        argv1 = [
            "--user-login", "dev",
            "--user-name", "Dev User",
            "--key-name", "First Key",
        ]
        
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        sys.stdout = StringIO()
        sys.stderr = StringIO()
        
        try:
            exit_code1 = bootstrap_apikey_main(argv1)
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr

        assert exit_code1 == 0
        
        # User が作成された
        user = User.query.filter_by(github_login="dev").first()
        assert user is not None
        user_id = user.id
        
        # 初回の ApiKey が作成された
        api_keys_after_first = ApiKey.query.filter_by(user_id=user_id).all()
        assert len(api_keys_after_first) == 1

        # 2回目実行
        argv2 = [
            "--user-login", "dev",
            "--key-name", "Second Key",
        ]
        
        sys.stdout = StringIO()
        sys.stderr = StringIO()
        
        try:
            exit_code2 = bootstrap_apikey_main(argv2)
            stderr_output = sys.stderr.getvalue()
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr

        assert exit_code2 == 0
        
        # User は再利用されている（ID が同じ）
        user_after_second = User.query.filter_by(github_login="dev").first()
        assert user_after_second.id == user_id
        
        # ApiKey が増えた（2本）
        api_keys_after_second = ApiKey.query.filter_by(user_id=user_id).all()
        assert len(api_keys_after_second) == 2
        
        # 標準エラーに "Using existing user" が含まれる
        assert "Using existing user" in stderr_output


def test_bootstrap_apikey_default_key_name(app):
    """
    デフォルト名が使用される（--key-name 未指定）
    """
    with app.app_context():
        argv = [
            "--user-login", "testuser",
        ]
        
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        sys.stdout = StringIO()
        sys.stderr = StringIO()
        
        try:
            exit_code = bootstrap_apikey_main(argv)
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr

        assert exit_code == 0
        
        # デフォルト名の ApiKey が作成された
        user = User.query.filter_by(github_login="testuser").first()
        assert user is not None
        api_key = ApiKey.query.filter_by(user_id=user.id).first()
        assert api_key.name == "Bootstrap Dev Key"


def test_bootstrap_apikey_returns_zero_on_success(app):
    """
    bootstrap_apikey_main() が 0 を返す
    """
    with app.app_context():
        argv = [
            "--user-login", "success_test",
            "--key-name", "Test Key",
        ]
        
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        sys.stdout = StringIO()
        sys.stderr = StringIO()
        
        try:
            exit_code = bootstrap_apikey_main(argv)
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr

        assert exit_code == 0


def test_bootstrap_apikey_outputs_export_command(app):
    """
    標準出力に export NEXUSCORE_API_KEY="..." が出力される
    """
    with app.app_context():
        argv = [
            "--user-login", "export_test",
            "--key-name", "Export Test Key",
        ]
        
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        sys.stdout = StringIO()
        sys.stderr = StringIO()
        
        try:
            exit_code = bootstrap_apikey_main(argv)
            stdout_output = sys.stdout.getvalue()
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr

        assert exit_code == 0
        assert stdout_output.startswith("export NEXUSCORE_API_KEY=")
        assert stdout_output.count("nexus_") == 1  # API Key が1回だけ含まれる
        assert stdout_output.endswith("\n") or stdout_output.endswith('"')

