"""C3: NotificationLog モデルの UNIQUE 制約テスト（Slack 重複送信防止）。"""
import pytest
from sqlalchemy.exc import IntegrityError


def test_notification_log_unique_run_event(app):
    """同一 (run_id, event_type) の2件目挿入は失敗（冪等化）"""
    from nexuscore.webapp import db
    from nexuscore.webapp.models import NotificationLog

    with app.app_context():
        db.create_all()
        log1 = NotificationLog(run_id=1, event_type="orchestrator_complete")
        db.session.add(log1)
        db.session.commit()

        # 同一 (run_id, event_type) の2件目は UNIQUE 違反
        log2 = NotificationLog(run_id=1, event_type="orchestrator_complete")
        db.session.add(log2)
        with pytest.raises(IntegrityError):
            db.session.commit()
        db.session.rollback()
        db.drop_all()


def test_notification_log_allows_different_event_types(app):
    """同一 run でも event_type が異なれば複数件挿入可"""
    from nexuscore.webapp import db
    from nexuscore.webapp.models import NotificationLog

    with app.app_context():
        db.create_all()
        db.session.add(NotificationLog(run_id=1, event_type="orchestrator_complete"))
        db.session.add(NotificationLog(run_id=1, event_type="orchestrator_failed"))
        db.session.commit()  # 成功
        db.drop_all()
