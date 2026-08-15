"""task_lock utility のテスト（fakeredis 使用）。

C3 Celery 冪等性のための Redis SETNX 分散ロック機能を検証。
"""
import fakeredis
import pytest

from nexuscore.webapp.task_lock import (
    acquire_lock,
    deterministic_task_id,
    heartbeat,
    producer_lock,
    release_lock,
    task_lock_key,
)


@pytest.fixture
def fake_client():
    return fakeredis.FakeStrictRedis()


def test_acquire_lock_success(fake_client):
    """最初のロック取得は成功"""
    assert acquire_lock(fake_client, "lock:run:1", "worker-A", ttl=30) is True


def test_acquire_lock_contended(fake_client):
    """既に取得済みのロックは別 worker が取得失敗（SET NX セマンティクス）"""
    assert acquire_lock(fake_client, "lock:run:1", "worker-A", ttl=30) is True
    assert acquire_lock(fake_client, "lock:run:1", "worker-B", ttl=30) is False


def test_release_lock_owner_only(fake_client):
    """所有者のみロック解放（他人は解放できない＝誤解放防止）"""
    acquire_lock(fake_client, "lock:run:1", "worker-A", ttl=30)
    assert release_lock(fake_client, "lock:run:1", "worker-B") is False
    assert release_lock(fake_client, "lock:run:1", "worker-A") is True
    # 解放後は再取得可
    assert acquire_lock(fake_client, "lock:run:1", "worker-C", ttl=30) is True


def test_heartbeat_extends_ttl_owner_only(fake_client):
    """所有者のみ TTL 延長（他人の heartbeat は失敗）"""
    acquire_lock(fake_client, "lock:run:1", "worker-A", ttl=30)
    assert heartbeat(fake_client, "lock:run:1", "worker-A", ttl=60) is True
    assert heartbeat(fake_client, "lock:run:1", "worker-B", ttl=60) is False


def test_producer_lock_prevents_duplicate(fake_client):
    """producer_lock は短時間の重複 enqueue を防止"""
    assert producer_lock(fake_client, run_id=1, ttl=10) is True
    assert producer_lock(fake_client, run_id=1, ttl=10) is False


def test_key_helpers():
    """キー名・task_id の決定論的生成"""
    assert task_lock_key(42) == "lock:run:42"
    assert deterministic_task_id(42) == "orchestrator-run-42"
