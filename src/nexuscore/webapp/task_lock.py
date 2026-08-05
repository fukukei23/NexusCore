"""Redis SETNX ベースの分散ロック utility（C3 Celery 冪等性）。

Celery タスクの冪等性・producer 側の重複 enqueue 防止に使用。
所有者チェック付きの安全な解放（Lua script）で誤解放を防止。
"""
from __future__ import annotations

import os
from typing import Any

import redis

# 所有者のみ解放するための Lua script（CHECK-AND-DEL を原子的に実行）
_RELEASE_SCRIPT = """
if redis.call('get', KEYS[1]) == ARGV[1] then
    return redis.call('del', KEYS[1])
else
    return 0
end
"""

# 所有者のみ TTL 延長する Lua script
_EXTEND_SCRIPT = """
if redis.call('get', KEYS[1]) == ARGV[1] then
    return redis.call('expire', KEYS[1], ARGV[2])
else
    return 0
end
"""


def get_redis() -> redis.Redis:
    """Redis クライアントを取得（Celery broker URL を流用）。"""
    url = os.getenv("REDIS_URL") or os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
    return redis.from_url(url)


def acquire_lock(client: Any, lock_key: str, worker_id: str, ttl: int = 30) -> bool:
    """SET NX EX でロック取得。成功=True・既取得=False。"""
    return bool(client.set(lock_key, worker_id, nx=True, ex=ttl))


def release_lock(client: Any, lock_key: str, worker_id: str) -> bool:
    """所有者のみ解放（Lua で原子的 CHECK-AND-DEL・誤解放防止）。"""
    return bool(client.eval(_RELEASE_SCRIPT, 1, lock_key, worker_id))


def heartbeat(client: Any, lock_key: str, worker_id: str, ttl: int = 30) -> bool:
    """所有者のみ TTL 延長（長時間タスク用）。"""
    return bool(client.eval(_EXTEND_SCRIPT, 1, lock_key, worker_id, str(ttl)))


def producer_lock(client: Any, run_id: int, ttl: int = 10) -> bool:
    """producer 側の重複 enqueue 防止（短 TTL・二重防御）。"""
    return acquire_lock(client, f"producer_lock:{run_id}", "producer", ttl=ttl)


def task_lock_key(run_db_id: int) -> str:
    """タスク実行ロックのキー名。"""
    return f"lock:run:{run_db_id}"


def deterministic_task_id(run_db_id: int) -> str:
    """決定論的 task_id（broker レベルで重複 enqueue 拒否に使用）。"""
    return f"orchestrator-run-{run_db_id}"
