"""
Pytest 共通フィクスチャ

Flask SaaS UI のスモークテストで使用する共通フィクスチャを集約。
"""

from __future__ import annotations

import pytest
from datetime import datetime, timedelta
import json

# webapp 関連のインポートは条件付き（Gradio/analyzer テストでは不要）
try:
    from nexuscore.webapp import create_app, db
    from nexuscore.webapp.models import Project, Run, User, ExecutionLog, PatchRecord, ApiKey
    HAS_WEBAPP = True
except ImportError:
    HAS_WEBAPP = False
    create_app = None  # type: ignore
    db = None  # type: ignore
    Project = None  # type: ignore
    Run = None  # type: ignore
    User = None  # type: ignore
    ExecutionLog = None  # type: ignore
    PatchRecord = None  # type: ignore
    ApiKey = None  # type: ignore


@pytest.fixture
def app():
    """テスト用 Flask アプリ"""
    if not HAS_WEBAPP:
        pytest.skip("webapp modules not available")
    app = create_app(config_overrides={
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "TESTING": True,
        "SECRET_KEY": "test-secret-key",
    })
    return app


@pytest.fixture
def client(app):
    """テスト用クライアント"""
    if not HAS_WEBAPP:
        pytest.skip("webapp modules not available")
    with app.app_context():
        db.create_all()
        yield app.test_client()
        db.drop_all()


@pytest.fixture
def test_user(app):
    """テスト用ユーザー"""
    if not HAS_WEBAPP:
        pytest.skip("webapp modules not available")
    with app.app_context():
        user = User(
            github_id="123",
            github_login="test_user",
        )
        db.session.add(user)
        db.session.commit()
        return user


@pytest.fixture
def test_project(app, test_user):
    """テスト用プロジェクト"""
    if not HAS_WEBAPP:
        pytest.skip("webapp modules not available")
    with app.app_context():
        project = Project(
            owner_id=test_user.id,
            name="Test Project",
            repo_url="https://github.com/example/repo",
            local_path="/tmp/test",
        )
        db.session.add(project)
        db.session.commit()
        return project


@pytest.fixture
def test_run_with_metrics(app, test_project, test_user):
    """テスト用 Run（メトリクス付き）"""
    if not HAS_WEBAPP:
        pytest.skip("webapp modules not available")
    with app.app_context():
        run = Run(
            project_id=test_project.id,
            run_id="test-run-123",
            triggered_by=test_user.id,
            status="SUCCESS",
            started_at=datetime.utcnow() - timedelta(seconds=30),
            finished_at=datetime.utcnow(),
        )
        db.session.add(run)
        db.session.flush()

        # ExecutionLog に retry_count と last_error_class を含める
        log1 = ExecutionLog(
            run_id=run.id,
            source="NPE",
            level="INFO",
            message="Test log",
            payload_json=json.dumps({
                "model": "gpt-4.1",
                "retry_count": 2,
                "last_error_class": "rate_limit",
            }),
        )
        db.session.add(log1)

        log2 = ExecutionLog(
            run_id=run.id,
            source="ORCHESTRATOR",
            level="INFO",
            message="Test log 2",
            payload_json=json.dumps({
                "execution_ms": 1234,
                "files_changed": 3,
            }),
        )
        db.session.add(log2)

        db.session.commit()
        return run


@pytest.fixture
def test_run_with_self_healing_metrics(app, test_project, test_user):
    """
    テスト用 Run（Self-Healing メトリクス付き）
    ExecutionLog に retry_count, last_error_class, model を含める
    """
    if not HAS_WEBAPP:
        pytest.skip("webapp modules not available")
    with app.app_context():
        run = Run(
            project_id=test_project.id,
            run_id="test-run-sh-123",
            triggered_by=test_user.id,
            status="SUCCESS",
            started_at=datetime.utcnow() - timedelta(seconds=30),
            finished_at=datetime.utcnow(),
        )
        db.session.add(run)
        db.session.flush()

        # ExecutionLog に Self-Healing メトリクスを含める
        log1 = ExecutionLog(
            run_id=run.id,
            source="NPE",
            level="INFO",
            message="LLM call",
            payload_json=json.dumps({
                "model": "gpt-4.1",
                "retry_count": 2,
                "last_error_class": "rate_limit",
                "estimated_cost": 10.0,
            }),
        )
        db.session.add(log1)

        log2 = ExecutionLog(
            run_id=run.id,
            source="ORCHESTRATOR",
            level="INFO",
            message="Guardian review",
            payload_json=json.dumps({
                "guardian_review": {
                    "decision": "approved",
                    "reason": "Patch looks safe",
                },
            }),
        )
        db.session.add(log2)

        # PatchRecord を作成（files_changed を計算するため）
        patch1 = PatchRecord(
            run_id=run.id,
            file_path="src/test1.py",
            diff_text="--- a/src/test1.py\n+++ b/src/test1.py\n@@ -1,1 +1,2 @@\n+new line",
            applied=True,
        )
        db.session.add(patch1)

        patch2 = PatchRecord(
            run_id=run.id,
            file_path="src/test2.py",
            diff_text="--- a/src/test2.py\n+++ b/src/test2.py\n@@ -1,1 +1,2 @@\n+new line",
            applied=True,
        )
        db.session.add(patch2)

        db.session.commit()
        return run


@pytest.fixture
def test_api_key(app, test_user):
    """テスト用 API Key"""
    if not HAS_WEBAPP:
        pytest.skip("webapp modules not available")
    with app.app_context():
        raw_token = ApiKey.generate_token()
        token_hash = ApiKey.hash_token(raw_token)

        api_key = ApiKey(
            user_id=test_user.id,
            token_hash=token_hash,
            name="Test API Key",
        )
        db.session.add(api_key)
        db.session.commit()
        return raw_token, api_key

