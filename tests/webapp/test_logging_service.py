"""
NexusCore Webapp - logging_service のテスト

app context あり/なしでの動作を確認する。
"""
from __future__ import annotations

import pytest
from nexuscore.webapp import create_app, db
from nexuscore.webapp.models import ExecutionLog
from nexuscore.webapp.logging_service import log_execution_event


def test_log_execution_event_with_app_context():
    """
    app context ありで log_execution_event() → ExecutionLog 1件
    """
    app = create_app(config_overrides={
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "TESTING": True,
    })

    with app.app_context():
        db.create_all()

        # ログを記録
        log_execution_event(
            run_id=None,
            source="TEST",
            level="INFO",
            message="Test message",
            payload={"key": "value"},
        )

        # ExecutionLog が1件追加されていることを確認
        logs = ExecutionLog.query.all()
        assert len(logs) == 1
        assert logs[0].source == "TEST"
        assert logs[0].level == "INFO"
        assert logs[0].message == "Test message"
        assert logs[0].payload_json is not None


def test_log_execution_event_without_app_context():
    """
    app context なしで何も起きない（例外にならない）
    """
    # app context なしで実行
    # 例外が発生しないことを確認
    log_execution_event(
        run_id=None,
        source="TEST",
        level="INFO",
        message="Test message",
        payload={"key": "value"},
    )

    # 何も起きない（正常終了）
    assert True


def test_log_execution_event_with_run_id():
    """
    run_id を指定した場合のテスト
    """
    app = create_app(config_overrides={
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "TESTING": True,
    })

    with app.app_context():
        db.create_all()

        # Run を作成（簡易版）
        from nexuscore.webapp.models import Run, Project, User
        user = User(
            github_id="123",
            github_login="test_user",
        )
        db.session.add(user)
        db.session.commit()

        project = Project(
            owner_id=user.id,
            name="Test Project",
            local_path="/tmp/test",
        )
        db.session.add(project)
        db.session.commit()

        run = Run(
            project_id=project.id,
            run_id="test-run-123",
            triggered_by=user.id,
            status="RUNNING",
        )
        db.session.add(run)
        db.session.commit()

        # ログを記録
        log_execution_event(
            run_id=run.id,
            source="ORCHESTRATOR",
            level="INFO",
            message="Test message with run_id",
            payload={"run_id": run.id},
        )

        # ExecutionLog が1件追加されていることを確認
        logs = ExecutionLog.query.filter_by(run_id=run.id).all()
        assert len(logs) == 1
        assert logs[0].run_id == run.id
        assert logs[0].source == "ORCHESTRATOR"

