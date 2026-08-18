"""Orchestrator 内部冪等性（C3 Plan2）: phase チェックポイント＋LLM 結果キャッシュ。

Celery worker 死亡→再配送時に完了済み phase をスキップし、
コンテキストスナップショットから再開するための基盤。
Redis 障害時はすべて no-op（timeout 1s + 60sサーキットブレーカ付きのフル再実行に退化）。

層序注記: webapp.task_lock と同じ env 変数を参照する独自実装
（core → webapp import は層序違反のため避ける）。heartbeat は heartbeat_fn で依存注入。
"""
from __future__ import annotations

import logging
import os
import time
from typing import Any

logger = logging.getLogger(__name__)

PHASE_SEQUENCE: list[tuple[str, str]] = [
    ("context", "run_context_phase"),
    ("requirements", "run_requirements_phase"),
    ("planning", "run_planning_phase"),
    ("architecture", "run_architecture_phase"),
    ("implementation", "run_implementation_phase"),
    ("testing", "run_testing_phase"),
    ("review", "run_review_phase"),
]
PHASE_INDEX: dict[str, int] = {name: i for i, (name, _) in enumerate(PHASE_SEQUENCE)}

_CHECKPOINT_TTL = 86400        # 24h（改訂案指定）
_SNAPSHOT_MAX_BYTES = 512 * 1024  # A5: 超過時はzlib圧縮
LOCK_TTL = 600                 # A3: 1phase（LLM数回×数十秒）をカバーし visibility_timeout(7200) < に収める

# A2: 簡易サーキットブレーカ（Redis失敗後60s間はget_client即None）
_BREAKER_COOLDOWN = 60.0
_breaker_until = 0.0


def _note_failure() -> None:
    global _breaker_until
    _breaker_until = time.monotonic() + _BREAKER_COOLDOWN


def get_client() -> Any | None:
    """Redis クライアント。NEXUSCORE_CHECKPOINT=0 で None。ブレーカ作動中も None。"""
    if os.getenv("NEXUSCORE_CHECKPOINT", "1") == "0":
        return None
    if time.monotonic() < _breaker_until:
        return None
    try:
        import redis

        url = os.getenv("REDIS_URL") or os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
        return redis.from_url(url, socket_connect_timeout=1.0, socket_timeout=1.0)
    except Exception:  # noqa: BLE001
        _note_failure()
        return None


def checkpoint_key(run_db_id: int) -> str:
    """A1: チェックポイント単一キー（last_done+contextを1エントリで保持）"""
    return f"checkpoint:{run_db_id}"
