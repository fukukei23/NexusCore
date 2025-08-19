# ==============================================================================
# ファイル名: state_manager.py
# 配置場所: src/nexuscore/database/
# 目的: Redisを使い、タスクの実行状態など一時的な情報を管理する
# バージョン: 2.0 (Production Ready)
# ==============================================================================
import os
import json
import logging
import redis
from typing import Optional

logger = logging.getLogger(__name__)

class StateManager:
    def __init__(self, redis_url: Optional[str] = None, strict: bool = False, namespace: Optional[str] = None):
        url = redis_url or os.getenv("REDIS_URL")
        if not url:
            msg = "Redis URL not found in environment variables."
            logger.error(msg)
            if strict:
                raise ValueError(msg)
            self._client = None
            self.is_ready = False
            return

        try:
            self._client = redis.from_url(
                url,
                decode_responses=True,
                socket_timeout=2.0,
                socket_connect_timeout=2.0,
                health_check_interval=30,
                retry_on_timeout=True,
            )
            self._client.ping()
            self.is_ready = True
            self.namespace = namespace or os.getenv("REDIS_NAMESPACE", "nexus")
            logger.info("✅ Successfully connected to Redis.")
        except Exception as e:
            logger.error("❌ Could not connect to Redis", exc_info=True)
            self._client = None
            self.is_ready = False
            if strict:
                raise

    def _key(self, task_id: str) -> str:
        ns = getattr(self, "namespace", "nexus")
        return f"{ns}:task_state:{task_id}"

    def set_task_state(self, task_id: str, state: dict, ttl_seconds: int = 3600) -> bool:
        if not self._client:
            logger.warning("Redis client is not initialized; skip set_task_state")
            return False
        try:
            payload = json.dumps(state, default=str)
            key = self._key(task_id)
            self._client.set(key, payload, ex=ttl_seconds)
            return True
        except Exception as e:
            logger.error(f"Failed to set task state for {task_id}: {e}", exc_info=True)
            return False

    def get_task_state(self, task_id: str) -> Optional[dict]:
        if not self._client:
            logger.warning("Redis client is not initialized; skip get_task_state")
            return None
        try:
            key = self._key(task_id)
            raw = self._client.get(key)
            return json.loads(raw) if raw else None
        except Exception as e:
            logger.error(f"Failed to get task state for {task_id}: {e}", exc_info=True)
            return None

state_manager = StateManager()