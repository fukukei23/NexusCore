"""C3: タスク先頭冪等ガード（_acquire_execution_lock）のテスト。"""
from unittest.mock import MagicMock

import fakeredis
import pytest

from nexuscore.webapp import task_lock
from nexuscore.webapp.celery_app import _acquire_execution_lock


@pytest.fixture
def fake_redis():
    return fakeredis.FakeStrictRedis()


def _make_run(status="PENDING", run_id=1):
    run = MagicMock()
    run.id = run_id
    run.status = status
    return run


def test_guard_allows_pending_run(fake_redis):
    """status=PENDING なら実行可・ロック取得"""
    run = _make_run("PENDING")
    can_run, client, key = _acquire_execution_lock(run, "worker-A", redis_client=fake_redis)
    assert can_run is True
    assert key == "lock:run:1"
    # ロックが実際に取得されている
    assert fake_redis.get("lock:run:1") == b"worker-A"


def test_guard_skips_success_run(fake_redis):
    """status=SUCCESS なら2重実行 skip（ロック取得しない）"""
    run = _make_run("SUCCESS")
    can_run, client, key = _acquire_execution_lock(run, "worker-A", redis_client=fake_redis)
    assert can_run is False
    # ロックは未取得
    assert fake_redis.get("lock:run:1") is None


def test_guard_skips_when_lock_contended(fake_redis):
    """別 worker がロック中なら skip（Race Condition 回避）"""
    # 先に別 worker がロック取得済み
    task_lock.acquire_lock(fake_redis, "lock:run:1", "other-worker", ttl=30)
    run = _make_run("PENDING")
    can_run, client, key = _acquire_execution_lock(run, "worker-B", redis_client=fake_redis)
    assert can_run is False


def test_guard_release_after_skip_does_not_touch_others_lock(fake_redis):
    """skip 時（ロック未取得）は他 worker のロックを解放しない"""
    task_lock.acquire_lock(fake_redis, "lock:run:1", "other-worker", ttl=30)
    run = _make_run("PENDING")
    can_run, _, _ = _acquire_execution_lock(run, "worker-B", redis_client=fake_redis)
    assert can_run is False
    # 他 worker のロックは生存
    assert fake_redis.get("lock:run:1") == b"other-worker"
