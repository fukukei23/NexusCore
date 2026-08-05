"""C3: _finalize_run の Slack 通知冪等化テスト。"""
from unittest.mock import patch


def test_finalize_run_slack_idempotent(app):
    """2回 _finalize_run を呼んでも Slack 通知は1回のみ（NotificationLog UNIQUE）"""
    from nexuscore.webapp import db
    from nexuscore.webapp.celery_app import _finalize_run
    from nexuscore.webapp.models import NotificationLog, Project, Run, User

    with app.app_context():
        db.create_all()

        user = User(github_id="1", github_login="u")
        db.session.add(user)
        db.session.commit()
        project = Project(owner_id=user.id, name="p", local_path="/tmp")
        db.session.add(project)
        db.session.commit()
        run = Run(project_id=project.id, run_id="r1", status="RUNNING", requirement="req")
        db.session.add(run)
        db.session.commit()

        sent = {"count": 0}

        class FakeNotifier:
            def notify_orchestrator_complete(self, **kwargs):
                sent["count"] += 1

        with patch("nexuscore.integration.run_report_generator.write_run_report_file", return_value="/tmp/fake"), \
             patch("nexuscore.core.notifier.get_notifier", return_value=FakeNotifier()):
            _finalize_run(run, project, "success")
            _finalize_run(run, project, "success")  # 2回目

        # 通知は1回のみ
        assert sent["count"] == 1
        # NotificationLog も1件
        logs = NotificationLog.query.filter_by(run_id=run.id, event_type="orchestrator_complete").all()
        assert len(logs) == 1
        db.drop_all()
