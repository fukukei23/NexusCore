"""C3: producer 側ガードのテスト（_dispatch_celery_run）。

producer_lock（短時間重複防止）と決定論的 task_id（broker 重複拒否）が
正しく適用されるか検証。
"""
from unittest.mock import MagicMock, patch

import fakeredis
import pytest

from nexuscore.webapp import task_lock


def _make_run(run_id=1):
    run = MagicMock()
    run.id = run_id
    run.run_id = f"run-uuid-{run_id}"
    run.status = "PENDING"
    return run


def _make_project():
    project = MagicMock()
    project.id = 1
    return project


@pytest.fixture
def flask_app():
    """Flask test app（celery 自動初期化スキップ）"""
    from nexuscore.webapp import create_app

    app = create_app(config_overrides={
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "WTF_CSRF_ENABLED": False,
    })
    with app.test_request_context("/", headers={"Accept": "application/json"}):
        yield app


def test_dispatch_uses_producer_lock_and_deterministic_task_id(flask_app, monkeypatch):
    """_dispatch_celery_run は producer_lock 取得後・決定論的 task_id で apply_async する"""
    fake_redis = fakeredis.FakeStrictRedis()
    monkeypatch.setattr(task_lock, "get_redis", lambda: fake_redis)

    captured = {}

    def fake_apply_async(args=None, task_id=None, **kwargs):
        captured["args"] = args
        captured["task_id"] = task_id

    fake_task = MagicMock()
    fake_task.apply_async.side_effect = fake_apply_async

    run = _make_run(1)
    project = _make_project()

    with patch("nexuscore.webapp.celery_app.run_orchestrator_task", fake_task):
        from nexuscore.webapp.views_projects import _dispatch_celery_run
        response = _dispatch_celery_run(run, project)

    # apply_async が決定論的 task_id で呼ばれた
    assert captured["args"] == [1]
    assert captured["task_id"] == "orchestrator-run-1"
    # producer_lock が取得済み（2回目は拒否される状態）
    assert task_lock.producer_lock(fake_redis, 1, ttl=10) is False
    # 202 レスポンス（JSON）
    assert response[1] == 202


def test_dispatch_rejects_duplicate_within_lock_window(flask_app, monkeypatch):
    """producer_lock 期限内の2回目は 409（重複 enqueue 拒否）"""
    fake_redis = fakeredis.FakeStrictRedis()
    monkeypatch.setattr(task_lock, "get_redis", lambda: fake_redis)

    # 先に producer_lock 取得済みにする
    task_lock.producer_lock(fake_redis, 1, ttl=10)

    fake_task = MagicMock()
    run = _make_run(1)
    project = _make_project()

    with patch("nexuscore.webapp.celery_app.run_orchestrator_task", fake_task):
        from nexuscore.webapp.views_projects import _dispatch_celery_run
        response = _dispatch_celery_run(run, project)

    # apply_async は呼ばれない（重複拒否）
    fake_task.apply_async.assert_not_called()
    # 409 レスポンス
    assert response[1] == 409
