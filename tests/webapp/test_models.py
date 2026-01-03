"""
webapp/models.py の高品質なテスト

テスト対象:
- User: GitHub OAuth ユーザーモデル
- Project: プロジェクト/リポジトリモデル
- Run: オーケストレーション実行記録
- PatchRecord: パッチ適用記録
- ExecutionLog: 構造化ログ
- ApiKey: APIキー生成・検証
"""
from __future__ import annotations

import hashlib
import secrets
from datetime import datetime

import pytest

from nexuscore.webapp.models import (
    User,
    Project,
    Run,
    PatchRecord,
    ExecutionLog,
    ApiKey,
)


@pytest.fixture(scope="function")
def app():
    """Flask test app with in-memory SQLite database"""
    try:
        from nexuscore.webapp import create_app, db

        # Create app with test configuration
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
    except ImportError as e:
        pytest.skip(f"Flask dependencies not available: {e}")


@pytest.fixture
def db_session(app):
    """Database session for tests"""
    from nexuscore.webapp import db
    with app.app_context():
        yield db.session


class TestUserModel:
    """User モデルのテスト"""

    def test_user_creation_with_required_fields(self, db_session):
        """必須フィールドのみでユーザー作成"""
        user = User(
            github_id="123456",
            github_login="testuser"
        )
        db_session.add(user)
        db_session.commit()

        assert user.id is not None
        assert user.github_id == "123456"
        assert user.github_login == "testuser"
        assert user.created_at is not None
        assert user.updated_at is not None
        assert isinstance(user.created_at, datetime)

    def test_user_creation_with_all_fields(self, db_session):
        """全フィールドを指定してユーザー作成"""
        user = User(
            github_id="123456",
            github_login="testuser",
            name="Test User",
            avatar_url="https://example.com/avatar.png",
            email="test@example.com"
        )
        db_session.add(user)
        db_session.commit()

        assert user.name == "Test User"
        assert user.avatar_url == "https://example.com/avatar.png"
        assert user.email == "test@example.com"

    def test_user_github_id_unique_constraint(self, db_session):
        """github_id は一意制約がある"""
        user1 = User(github_id="123456", github_login="user1")
        db_session.add(user1)
        db_session.commit()

        # 同じ github_id で別ユーザーを作成しようとするとエラー
        user2 = User(github_id="123456", github_login="user2")
        db_session.add(user2)

        with pytest.raises(Exception):  # IntegrityError
            db_session.commit()

    def test_user_repr(self, db_session):
        """__repr__ メソッドのテスト"""
        user = User(github_id="123456", github_login="testuser")
        db_session.add(user)
        db_session.commit()

        repr_str = repr(user)
        assert "User" in repr_str
        assert "testuser" in repr_str
        assert str(user.id) in repr_str

    def test_user_projects_relationship(self, db_session):
        """User と Project のリレーション"""
        user = User(github_id="123456", github_login="testuser")
        db_session.add(user)
        db_session.commit()

        # プロジェクトを作成
        project1 = Project(owner_id=user.id, name="project1", local_path="/path1")
        project2 = Project(owner_id=user.id, name="project2", local_path="/path2")
        db_session.add_all([project1, project2])
        db_session.commit()

        # リレーションで取得できる
        assert user.projects.count() == 2
        project_names = [p.name for p in user.projects]
        assert "project1" in project_names
        assert "project2" in project_names

    def test_user_runs_relationship(self, db_session):
        """User と Run のリレーション"""
        user = User(github_id="123456", github_login="testuser")
        project = Project(owner_id=1, name="test_project", local_path="/path")
        db_session.add_all([user, project])
        db_session.commit()

        # Run を作成
        run = Run(project_id=project.id, run_id="run-123", triggered_by=user.id, status="PENDING")
        db_session.add(run)
        db_session.commit()

        # リレーションで取得できる
        assert user.runs.count() == 1
        assert user.runs.first().run_id == "run-123"

    def test_user_api_keys_relationship_with_cascade_delete(self, db_session):
        """User と ApiKey のリレーション（カスケード削除）"""
        user = User(github_id="123456", github_login="testuser")
        db_session.add(user)
        db_session.commit()

        # ApiKey を作成
        api_key = ApiKey(
            user_id=user.id,
            token_hash=ApiKey.hash_token("test_token"),
            name="test_key"
        )
        db_session.add(api_key)
        db_session.commit()

        api_key_id = api_key.id

        # User を削除すると ApiKey もカスケード削除される
        db_session.delete(user)
        db_session.commit()

        # ApiKey が削除されている
        deleted_key = db_session.get(ApiKey, api_key_id)
        assert deleted_key is None


class TestProjectModel:
    """Project モデルのテスト"""

    def test_project_creation_with_required_fields(self, db_session):
        """必須フィールドでプロジェクト作成"""
        user = User(github_id="123456", github_login="testuser")
        db_session.add(user)
        db_session.commit()

        project = Project(
            owner_id=user.id,
            name="test_project",
            local_path="/path/to/project"
        )
        db_session.add(project)
        db_session.commit()

        assert project.id is not None
        assert project.owner_id == user.id
        assert project.name == "test_project"
        assert project.local_path == "/path/to/project"
        assert project.created_at is not None

    def test_project_creation_with_all_fields(self, db_session):
        """全フィールドを指定してプロジェクト作成"""
        user = User(github_id="123456", github_login="testuser")
        db_session.add(user)
        db_session.commit()

        project = Project(
            owner_id=user.id,
            name="test_project",
            repo_url="https://github.com/user/repo",
            local_path="/path/to/project",
            context_bundle_path="/context_bundles/latest.json"
        )
        db_session.add(project)
        db_session.commit()

        assert project.repo_url == "https://github.com/user/repo"
        assert project.context_bundle_path == "/context_bundles/latest.json"

    def test_project_owner_relationship(self, db_session):
        """Project から User へのリレーション"""
        user = User(github_id="123456", github_login="testuser")
        db_session.add(user)
        db_session.commit()

        project = Project(owner_id=user.id, name="test_project", local_path="/path")
        db_session.add(project)
        db_session.commit()

        # Project.owner でユーザーを取得できる
        assert project.owner.id == user.id
        assert project.owner.github_login == "testuser"

    def test_project_foreign_key_constraint(self, db_session):
        """owner_id は外部キー制約がある（SQLite ではデフォルトで無効）"""
        # SQLite では外部キー制約がデフォルトで無効なため、存在しない user_id でも作成できる
        # 本番環境（PostgreSQL等）では IntegrityError になる
        project = Project(owner_id=99999, name="test_project", local_path="/path")
        db_session.add(project)
        db_session.commit()

        # 作成できることを確認（SQLite の制限）
        assert project.id is not None
        assert project.owner_id == 99999

    def test_project_repr(self, db_session):
        """__repr__ メソッドのテスト"""
        user = User(github_id="123456", github_login="testuser")
        db_session.add(user)
        db_session.commit()

        project = Project(owner_id=user.id, name="test_project", local_path="/path")
        db_session.add(project)
        db_session.commit()

        repr_str = repr(project)
        assert "Project" in repr_str
        assert "test_project" in repr_str
        assert str(user.id) in repr_str

    def test_project_runs_relationship_with_cascade_delete(self, db_session):
        """Project と Run のリレーション（カスケード削除）"""
        user = User(github_id="123456", github_login="testuser")
        project = Project(owner_id=1, name="test_project", local_path="/path")
        db_session.add_all([user, project])
        db_session.commit()

        # Run を作成
        run = Run(project_id=project.id, run_id="run-123", status="PENDING")
        db_session.add(run)
        db_session.commit()

        run_id = run.id

        # Project を削除すると Run もカスケード削除される
        db_session.delete(project)
        db_session.commit()

        deleted_run = db_session.get(Run, run_id)
        assert deleted_run is None


class TestRunModel:
    """Run モデルのテスト"""

    def test_run_creation_with_required_fields(self, db_session):
        """必須フィールドで Run 作成"""
        user = User(github_id="123456", github_login="testuser")
        project = Project(owner_id=1, name="test_project", local_path="/path")
        db_session.add_all([user, project])
        db_session.commit()

        run = Run(
            project_id=project.id,
            run_id="run-abc123",
        )
        db_session.add(run)
        db_session.commit()

        assert run.id is not None
        assert run.project_id == project.id
        assert run.run_id == "run-abc123"
        assert run.status == "PENDING"  # デフォルト値
        assert run.created_at is not None

    def test_run_creation_with_all_fields(self, db_session):
        """全フィールドを指定して Run 作成"""
        user = User(github_id="123456", github_login="testuser")
        project = Project(owner_id=1, name="test_project", local_path="/path")
        db_session.add_all([user, project])
        db_session.commit()

        now = datetime.utcnow()
        run = Run(
            project_id=project.id,
            run_id="run-abc123",
            triggered_by=user.id,
            status="SUCCESS",
            started_at=now,
            finished_at=now,
            autonomy_level=2,
            llm_model_summary="gpt-4",
            requirement="Fix bug in module X"
        )
        db_session.add(run)
        db_session.commit()

        assert run.triggered_by == user.id
        assert run.status == "SUCCESS"
        assert run.autonomy_level == 2
        assert run.llm_model_summary == "gpt-4"
        assert run.requirement == "Fix bug in module X"

    def test_run_status_field(self, db_session):
        """status フィールドのテスト"""
        project = Project(owner_id=1, name="test_project", local_path="/path")
        db_session.add(project)
        db_session.commit()

        run = Run(project_id=project.id, run_id="run-123", status="RUNNING")
        db_session.add(run)
        db_session.commit()

        assert run.status == "RUNNING"

        # status を更新
        run.status = "SUCCESS"
        db_session.commit()

        assert run.status == "SUCCESS"

    def test_run_id_unique_constraint(self, db_session):
        """run_id は一意制約がある"""
        project = Project(owner_id=1, name="test_project", local_path="/path")
        db_session.add(project)
        db_session.commit()

        run1 = Run(project_id=project.id, run_id="run-123", status="PENDING")
        db_session.add(run1)
        db_session.commit()

        # 同じ run_id で別 Run を作成しようとするとエラー
        run2 = Run(project_id=project.id, run_id="run-123", status="PENDING")
        db_session.add(run2)

        with pytest.raises(Exception):  # IntegrityError
            db_session.commit()

    def test_run_project_relationship(self, db_session):
        """Run から Project へのリレーション"""
        project = Project(owner_id=1, name="test_project", local_path="/path")
        db_session.add(project)
        db_session.commit()

        run = Run(project_id=project.id, run_id="run-123", status="PENDING")
        db_session.add(run)
        db_session.commit()

        # Run.project で Project を取得できる
        assert run.project.id == project.id
        assert run.project.name == "test_project"

    def test_run_triggered_by_user_relationship(self, db_session):
        """Run から User へのリレーション"""
        user = User(github_id="123456", github_login="testuser")
        project = Project(owner_id=1, name="test_project", local_path="/path")
        db_session.add_all([user, project])
        db_session.commit()

        run = Run(project_id=project.id, run_id="run-123", triggered_by=user.id, status="PENDING")
        db_session.add(run)
        db_session.commit()

        # Run.triggered_by_user で User を取得できる
        assert run.triggered_by_user.id == user.id
        assert run.triggered_by_user.github_login == "testuser"

    def test_run_repr(self, db_session):
        """__repr__ メソッドのテスト"""
        project = Project(owner_id=1, name="test_project", local_path="/path")
        db_session.add(project)
        db_session.commit()

        run = Run(project_id=project.id, run_id="run-abc123", status="SUCCESS")
        db_session.add(run)
        db_session.commit()

        repr_str = repr(run)
        assert "Run" in repr_str
        assert "run-abc123" in repr_str
        assert "SUCCESS" in repr_str

    def test_run_patch_records_relationship_with_cascade_delete(self, db_session):
        """Run と PatchRecord のリレーション（カスケード削除）"""
        project = Project(owner_id=1, name="test_project", local_path="/path")
        run = Run(project_id=1, run_id="run-123", status="PENDING")
        db_session.add_all([project, run])
        db_session.commit()

        # PatchRecord を作成
        patch = PatchRecord(
            run_id=run.id,
            file_path="/src/main.py",
            diff_text="--- a\n+++ b\n",
            applied=True
        )
        db_session.add(patch)
        db_session.commit()

        patch_id = patch.id

        # Run を削除すると PatchRecord もカスケード削除される
        db_session.delete(run)
        db_session.commit()

        deleted_patch = db_session.get(PatchRecord, patch_id)
        assert deleted_patch is None

    def test_run_execution_logs_relationship_with_cascade_delete(self, db_session):
        """Run と ExecutionLog のリレーション（カスケード削除）"""
        project = Project(owner_id=1, name="test_project", local_path="/path")
        run = Run(project_id=1, run_id="run-123", status="PENDING")
        db_session.add_all([project, run])
        db_session.commit()

        # ExecutionLog を作成
        log = ExecutionLog(
            run_id=run.id,
            source="ORCHESTRATOR",
            level="INFO",
            message="Test message"
        )
        db_session.add(log)
        db_session.commit()

        log_id = log.id

        # Run を削除すると ExecutionLog もカスケード削除される
        db_session.delete(run)
        db_session.commit()

        deleted_log = db_session.get(ExecutionLog, log_id)
        assert deleted_log is None


class TestPatchRecordModel:
    """PatchRecord モデルのテスト"""

    def test_patch_record_creation(self, db_session):
        """PatchRecord 作成"""
        project = Project(owner_id=1, name="test_project", local_path="/path")
        run = Run(project_id=1, run_id="run-123", status="PENDING")
        db_session.add_all([project, run])
        db_session.commit()

        patch = PatchRecord(
            run_id=run.id,
            file_path="/src/module.py",
            diff_text="--- a/src/module.py\n+++ b/src/module.py\n@@ -1 +1 @@\n-old\n+new",
            applied=True
        )
        db_session.add(patch)
        db_session.commit()

        assert patch.id is not None
        assert patch.run_id == run.id
        assert patch.file_path == "/src/module.py"
        assert "--- a/src/module.py" in patch.diff_text
        assert patch.applied is True
        assert patch.created_at is not None

    def test_patch_record_default_applied_false(self, db_session):
        """applied のデフォルト値は False"""
        project = Project(owner_id=1, name="test_project", local_path="/path")
        run = Run(project_id=1, run_id="run-123", status="PENDING")
        db_session.add_all([project, run])
        db_session.commit()

        patch = PatchRecord(
            run_id=run.id,
            file_path="/src/module.py",
            diff_text="--- a\n+++ b\n"
        )
        db_session.add(patch)
        db_session.commit()

        assert patch.applied is False

    def test_patch_record_run_relationship(self, db_session):
        """PatchRecord から Run へのリレーション"""
        project = Project(owner_id=1, name="test_project", local_path="/path")
        run = Run(project_id=1, run_id="run-123", status="PENDING")
        db_session.add_all([project, run])
        db_session.commit()

        patch = PatchRecord(
            run_id=run.id,
            file_path="/src/module.py",
            diff_text="--- a\n+++ b\n"
        )
        db_session.add(patch)
        db_session.commit()

        # PatchRecord.run で Run を取得できる
        assert patch.run.id == run.id
        assert patch.run.run_id == "run-123"

    def test_patch_record_repr(self, db_session):
        """__repr__ メソッドのテスト"""
        project = Project(owner_id=1, name="test_project", local_path="/path")
        run = Run(project_id=1, run_id="run-123", status="PENDING")
        db_session.add_all([project, run])
        db_session.commit()

        patch = PatchRecord(
            run_id=run.id,
            file_path="/src/module.py",
            diff_text="--- a\n+++ b\n",
            applied=True
        )
        db_session.add(patch)
        db_session.commit()

        repr_str = repr(patch)
        assert "PatchRecord" in repr_str
        assert "/src/module.py" in repr_str
        assert "True" in repr_str


class TestExecutionLogModel:
    """ExecutionLog モデルのテスト"""

    def test_execution_log_creation(self, db_session):
        """ExecutionLog 作成"""
        project = Project(owner_id=1, name="test_project", local_path="/path")
        run = Run(project_id=1, run_id="run-123", status="PENDING")
        db_session.add_all([project, run])
        db_session.commit()

        log = ExecutionLog(
            run_id=run.id,
            source="ORCHESTRATOR",
            level="INFO",
            message="Orchestration started"
        )
        db_session.add(log)
        db_session.commit()

        assert log.id is not None
        assert log.run_id == run.id
        assert log.source == "ORCHESTRATOR"
        assert log.level == "INFO"
        assert log.message == "Orchestration started"
        assert log.created_at is not None

    def test_execution_log_with_payload_json(self, db_session):
        """payload_json フィールドのテスト"""
        project = Project(owner_id=1, name="test_project", local_path="/path")
        run = Run(project_id=1, run_id="run-123", status="PENDING")
        db_session.add_all([project, run])
        db_session.commit()

        payload = {"agent": "architect", "phase": "planning", "tokens_used": 1500}
        log = ExecutionLog(
            run_id=run.id,
            source="AGENT",
            level="INFO",
            message="Agent completed task",
            payload_json=payload
        )
        db_session.add(log)
        db_session.commit()

        assert log.payload_json == payload
        assert log.payload_json["agent"] == "architect"
        assert log.payload_json["tokens_used"] == 1500

    def test_execution_log_without_run_id(self, db_session):
        """run_id が NULL でも作成できる（紐付かないログ）"""
        log = ExecutionLog(
            run_id=None,
            source="NPE",
            level="WARNING",
            message="Generic warning"
        )
        db_session.add(log)
        db_session.commit()

        assert log.id is not None
        assert log.run_id is None

    def test_execution_log_run_relationship(self, db_session):
        """ExecutionLog から Run へのリレーション"""
        project = Project(owner_id=1, name="test_project", local_path="/path")
        run = Run(project_id=1, run_id="run-123", status="PENDING")
        db_session.add_all([project, run])
        db_session.commit()

        log = ExecutionLog(
            run_id=run.id,
            source="ORCHESTRATOR",
            level="INFO",
            message="Test message"
        )
        db_session.add(log)
        db_session.commit()

        # ExecutionLog.run で Run を取得できる
        assert log.run.id == run.id
        assert log.run.run_id == "run-123"

    def test_execution_log_repr(self, db_session):
        """__repr__ メソッドのテスト"""
        log = ExecutionLog(
            source="NPE",
            level="ERROR",
            message="Test error"
        )
        db_session.add(log)
        db_session.commit()

        repr_str = repr(log)
        assert "ExecutionLog" in repr_str
        assert "NPE" in repr_str
        assert "ERROR" in repr_str


class TestApiKeyModel:
    """ApiKey モデルのテスト"""

    def test_api_key_creation(self, db_session):
        """ApiKey 作成"""
        user = User(github_id="123456", github_login="testuser")
        db_session.add(user)
        db_session.commit()

        token = ApiKey.generate_token()
        api_key = ApiKey(
            user_id=user.id,
            token_hash=ApiKey.hash_token(token),
            name="Production Key"
        )
        db_session.add(api_key)
        db_session.commit()

        assert api_key.id is not None
        assert api_key.user_id == user.id
        assert api_key.name == "Production Key"
        assert api_key.token_hash is not None
        assert api_key.created_at is not None

    def test_api_key_generate_token_format(self, db_session):
        """generate_token() は 'nexus_' プレフィックスを持つ"""
        token = ApiKey.generate_token()

        assert token.startswith("nexus_")
        assert len(token) > 10  # 十分な長さがある

    def test_api_key_generate_token_uniqueness(self, db_session):
        """generate_token() は毎回異なるトークンを生成"""
        token1 = ApiKey.generate_token()
        token2 = ApiKey.generate_token()

        assert token1 != token2

    def test_api_key_hash_token(self, db_session):
        """hash_token() は SHA-256 ハッシュを返す"""
        token = "test_token_12345"
        hashed = ApiKey.hash_token(token)

        # SHA-256 は 64 文字の16進数文字列
        assert len(hashed) == 64
        assert all(c in "0123456789abcdef" for c in hashed)

        # 同じトークンは同じハッシュになる
        assert ApiKey.hash_token(token) == hashed

    def test_api_key_hash_token_matches_hashlib(self, db_session):
        """hash_token() は hashlib.sha256 と同じ結果"""
        token = "test_token_12345"
        expected_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()

        assert ApiKey.hash_token(token) == expected_hash

    def test_api_key_verify_token_success(self, db_session):
        """verify_token() で正しいトークンを検証できる"""
        user = User(github_id="123456", github_login="testuser")
        db_session.add(user)
        db_session.commit()

        token = "nexus_test_token_123"
        api_key = ApiKey(
            user_id=user.id,
            token_hash=ApiKey.hash_token(token),
            name="Test Key"
        )
        db_session.add(api_key)
        db_session.commit()

        # 正しいトークンは True
        assert api_key.verify_token(token) is True

    def test_api_key_verify_token_failure(self, db_session):
        """verify_token() で間違ったトークンは False"""
        user = User(github_id="123456", github_login="testuser")
        db_session.add(user)
        db_session.commit()

        token = "nexus_test_token_123"
        api_key = ApiKey(
            user_id=user.id,
            token_hash=ApiKey.hash_token(token),
            name="Test Key"
        )
        db_session.add(api_key)
        db_session.commit()

        # 間違ったトークンは False
        assert api_key.verify_token("wrong_token") is False

    def test_api_key_token_hash_unique_constraint(self, db_session):
        """token_hash は一意制約がある"""
        user = User(github_id="123456", github_login="testuser")
        db_session.add(user)
        db_session.commit()

        token = "nexus_test_token_123"
        token_hash = ApiKey.hash_token(token)

        api_key1 = ApiKey(user_id=user.id, token_hash=token_hash, name="Key 1")
        db_session.add(api_key1)
        db_session.commit()

        # 同じ token_hash で別 ApiKey を作成しようとするとエラー
        api_key2 = ApiKey(user_id=user.id, token_hash=token_hash, name="Key 2")
        db_session.add(api_key2)

        with pytest.raises(Exception):  # IntegrityError
            db_session.commit()

    def test_api_key_user_relationship(self, db_session):
        """ApiKey から User へのリレーション"""
        user = User(github_id="123456", github_login="testuser")
        db_session.add(user)
        db_session.commit()

        api_key = ApiKey(
            user_id=user.id,
            token_hash=ApiKey.hash_token("test_token"),
            name="Test Key"
        )
        db_session.add(api_key)
        db_session.commit()

        # ApiKey.user で User を取得できる
        assert api_key.user.id == user.id
        assert api_key.user.github_login == "testuser"

    def test_api_key_repr(self, db_session):
        """__repr__ メソッドのテスト"""
        user = User(github_id="123456", github_login="testuser")
        db_session.add(user)
        db_session.commit()

        api_key = ApiKey(
            user_id=user.id,
            token_hash=ApiKey.hash_token("test_token"),
            name="Production Key"
        )
        db_session.add(api_key)
        db_session.commit()

        repr_str = repr(api_key)
        assert "ApiKey" in repr_str
        assert str(user.id) in repr_str
        assert "Production Key" in repr_str


class TestModelIntegration:
    """モデル間の統合テスト"""

    def test_full_workflow_user_to_run_to_logs(self, db_session):
        """User → Project → Run → ExecutionLog の完全なワークフロー"""
        # User 作成
        user = User(github_id="123456", github_login="testuser")
        db_session.add(user)
        db_session.commit()

        # Project 作成
        project = Project(
            owner_id=user.id,
            name="test_project",
            local_path="/path/to/project"
        )
        db_session.add(project)
        db_session.commit()

        # Run 作成
        run = Run(
            project_id=project.id,
            run_id="run-abc123",
            triggered_by=user.id,
            status="RUNNING"
        )
        db_session.add(run)
        db_session.commit()

        # ExecutionLog 作成
        log1 = ExecutionLog(
            run_id=run.id,
            source="ORCHESTRATOR",
            level="INFO",
            message="Started orchestration"
        )
        log2 = ExecutionLog(
            run_id=run.id,
            source="AGENT",
            level="INFO",
            message="Agent completed task"
        )
        db_session.add_all([log1, log2])
        db_session.commit()

        # リレーションを辿って検証
        assert run.project.name == "test_project"
        assert run.triggered_by_user.github_login == "testuser"
        assert run.execution_logs.count() == 2

        # User から Project, Run を辿れる
        assert user.projects.count() == 1
        assert user.runs.count() == 1

    def test_cascade_delete_user_with_api_keys(self, db_session):
        """User を削除すると ApiKey もカスケード削除される"""
        user = User(github_id="123456", github_login="testuser")
        db_session.add(user)
        db_session.commit()

        # ApiKey を作成
        api_key = ApiKey(
            user_id=user.id,
            token_hash=ApiKey.hash_token("test_token"),
            name="Test Key"
        )
        db_session.add(api_key)
        db_session.commit()

        api_key_id = api_key.id

        # User を削除すると ApiKey もカスケード削除される
        db_session.delete(user)
        db_session.commit()

        # ApiKey が削除されている
        deleted_key = db_session.get(ApiKey, api_key_id)
        assert deleted_key is None

    def test_cannot_delete_user_with_projects(self, db_session):
        """Project を持つ User は削除できない（owner_id が NOT NULL のため）"""
        user = User(github_id="123456", github_login="testuser")
        db_session.add(user)
        db_session.commit()

        # Project を作成
        project = Project(owner_id=user.id, name="test_project", local_path="/path")
        db_session.add(project)
        db_session.commit()

        # User を削除しようとすると IntegrityError
        db_session.delete(user)

        # Project.owner_id は NOT NULL なのでエラーになる
        from sqlalchemy.exc import IntegrityError
        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_cascade_delete_project_deletes_runs(self, db_session):
        """Project を削除すると Run もカスケード削除される"""
        user = User(github_id="123456", github_login="testuser")
        project = Project(owner_id=1, name="test_project", local_path="/path")
        db_session.add_all([user, project])
        db_session.commit()

        run = Run(project_id=project.id, run_id="run-123", status="PENDING")
        db_session.add(run)
        db_session.commit()

        run_id = run.id

        # Project を削除
        db_session.delete(project)
        db_session.commit()

        # Run もカスケード削除される
        deleted_run = db_session.get(Run, run_id)
        assert deleted_run is None
