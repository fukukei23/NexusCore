"""Orchestrator 内部冪等性（C3 Plan2）: phase チェックポイント＋LLM 結果キャッシュ。

Celery worker 死亡→再配送時に完了済み phase をスキップし、
コンテキストスナップショットから再開するための基盤。
Redis 障害時はすべて no-op（timeout 1s + 60sサーキットブレーカ付きのフル再実行に退化）。

層序注記: webapp.task_lock と同じ env 変数を参照する独自実装
（core → webapp import は層序違反のため避ける）。heartbeat は heartbeat_fn で依存注入。
"""
from __future__ import annotations

import atexit
import hashlib
import json
import logging
import os
import time
from collections.abc import Callable
from dataclasses import asdict
from typing import Any

from nexuscore.core.orchestrator_models import OrchestratorContext

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
# ※ブレーカ状態はプロセスローカル（prefork環境ではworkerプロセス毎に独立・
#   共有化するとRedis依存のブレーカになるため意図的にローカル）
_BREAKER_COOLDOWN = 60.0
_breaker_until = 0.0
_client_cache: dict[str, Any] = {}  # URL -> client（接続プール再利用）


def _close_cached_clients() -> None:
    """interpreter shutdown時の __del__ ノイズ防止（os tear-down後のgetpid AttributeError回避）"""
    for c in _client_cache.values():
        try:
            c.close()
        except Exception:  # noqa: BLE001
            pass
    _client_cache.clear()


atexit.register(_close_cached_clients)


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

        url = str(os.getenv("REDIS_URL") or os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0"))
        if url not in _client_cache:
            _client_cache[url] = redis.from_url(url, socket_connect_timeout=1.0, socket_timeout=1.0)
        return _client_cache[url]
    except Exception:  # noqa: BLE001
        _note_failure()
        return None


def checkpoint_key(run_db_id: int) -> str:
    """A1: チェックポイント単一キー（last_done+contextを1エントリで保持）"""
    return f"checkpoint:{run_db_id}"


def mark_phase_done(client: Any, run_db_id: int, phase: str, context: Any) -> None:
    """A1: 単一キー1回SET（アトミック）。A5: 512KB超はzlib+base64。"""
    try:
        payload = json.dumps(
            {"schema_version": 1, "last_done": phase, "context": asdict(context)},
            ensure_ascii=False,
        ).encode("utf-8")
        if len(payload) > _SNAPSHOT_MAX_BYTES:
            import base64
            import zlib

            payload = b"C" + base64.b64encode(zlib.compress(payload))
        else:
            payload = b"R" + payload
        client.set(checkpoint_key(run_db_id), payload, ex=_CHECKPOINT_TTL)
        logger.info("checkpoint saved (run_db_id=%s phase=%s bytes=%d)", run_db_id, phase, len(payload))  # A7
    except TypeError:
        # A6: シリアライズ不能型の混入＝実装バグ。サイレント退化を防ぐためERRORで可視化
        logger.error(
            "checkpoint serialize failed (run_db_id=%s phase=%s): contextにJSON不能型が混入の疑い",
            run_db_id, phase, exc_info=True,
        )
    except Exception:  # noqa: BLE001 — Redis 障害はチェックポイント放棄で継続
        _note_failure()
        logger.warning("checkpoint write failed (run_db_id=%s phase=%s)", run_db_id, phase, exc_info=True)


def load_checkpoint(client: Any | None, run_db_id: int) -> tuple[str | None, Any | None]:
    """last_done と復元済み context。無し/破損/スキーマ不一致は (None, None)。"""
    if client is None:
        return None, None
    try:
        raw = client.get(checkpoint_key(run_db_id))
        if raw is None:
            return None, None
        if raw[:1] == b"C":
            import base64
            import zlib

            payload = zlib.decompress(base64.b64decode(raw[1:])).decode("utf-8")
        else:
            payload = raw[1:].decode("utf-8")
        data = json.loads(payload)
        if data.get("schema_version") != 1:
            logger.warning("checkpoint schema mismatch (run_db_id=%s) -> discard", run_db_id)
            return None, None
        restored = OrchestratorContext(**data["context"])
        logger.info("checkpoint restore (run_db_id=%s last_done=%s)", run_db_id, data.get("last_done"))  # A7
        return data.get("last_done"), restored
    except Exception:  # noqa: BLE001
        _note_failure()
        logger.warning("checkpoint load failed (run_db_id=%s)", run_db_id, exc_info=True)
        return None, None


def clear_checkpoints(client: Any | None, run_db_id: int) -> None:
    """SUCCESS 確定時のみ呼ぶ。FAILED 時は保持して retry の再開に使う。"""
    if client is None:
        return
    try:
        client.delete(checkpoint_key(run_db_id))
    except Exception:  # noqa: BLE001
        _note_failure()
        logger.warning("checkpoint clear failed (run_db_id=%s)", run_db_id, exc_info=True)


def run_phases_with_checkpoint(
    runner: Any,
    context: Any,
    client: Any | None,
    run_db_id: int | None,
    heartbeat_fn: Callable[[], None] | None = None,
) -> Any:
    """phase 直列実行＋チェックポイント。

    runner: run_<name>_phase(context) を持つオブジェクト（Orchestrator 本体）。
    heartbeat_fn: 各phase完了時に呼ぶ実行ロックTTL延長（A3・依存注入で層序維持）。
    """
    last_done, restored = load_checkpoint(client, run_db_id) if run_db_id is not None else (None, None)
    if restored is not None:
        context = restored
        logger.info("resuming run_db_id=%s after phase '%s' (checkpoint restore)", run_db_id, last_done)

    if last_done is None:
        start = 0
    else:
        idx = PHASE_INDEX.get(last_done, -1)
        if idx < 0:
            logger.warning("unknown phase '%s' in checkpoint (run_db_id=%s) -> full rerun", last_done, run_db_id)
        start = idx + 1
    for name, method_name in PHASE_SEQUENCE[start:]:
        context = getattr(runner, method_name)(context)
        if client is not None and run_db_id is not None:
            mark_phase_done(client, run_db_id, name, context)
        if heartbeat_fn is not None:
            try:
                heartbeat_fn()
            except Exception:  # noqa: BLE001 — heartbeat失敗でrunは止めない
                logger.warning("lock heartbeat failed (run_db_id=%s)", run_db_id, exc_info=True)
    return context


def llm_cache_key(model: str, task: str, system_prompt: str, user_prompt: str) -> str:
    """llm_cache:{prompt_hash}:{input_hash}（A4: フル64hex・衝突回避）。"""
    model_part = model if model else "default"  # task_model_map未登録時のNoneガード
    prompt_hash = hashlib.sha256(f"{model_part}|{task}|{system_prompt}".encode()).hexdigest()
    input_hash = hashlib.sha256(user_prompt.encode("utf-8")).hexdigest()
    return f"llm_cache:{prompt_hash}:{input_hash}"


def llm_cache_get(client: Any | None, key: str) -> str | None:
    if client is None:
        return None
    try:
        raw = client.get(key)
        return raw.decode("utf-8") if raw is not None else None
    except Exception:  # noqa: BLE001
        _note_failure()
        return None


def llm_cache_set(client: Any | None, key: str, value: str, ttl: int = 86400) -> None:
    if client is None:
        return
    try:
        client.set(key, value, ex=ttl)
    except Exception:  # noqa: BLE001
        _note_failure()
        logger.warning("llm_cache set failed (key=%s...)", key[:32], exc_info=True)
