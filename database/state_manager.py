# ==============================================================================
# ファイル名: state_manager.py
# 配置場所: src/nexuscore/database/
# 日付: 2025/09/02
#
# 使用方法:
#   この内容で既存のファイルを上書きしてください。
#   Redisが利用できない開発環境でもAPIサーバーが起動できるようにする最終FIX版です。
#
# 改修内容:
#   - __init__メソッドの例外処理ブロックを修正。
#   - Redisへの接続に失敗した場合、後続のping()を呼び出さずに終了することで、
#     strict=False（既定）の際にプログラムが停止するのを防ぎます。
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
            msg = "Redis URL not found in environment variables. StateManager will be disabled."
            logger.warning(msg) # errorからwarningに変更
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
            logger.error("❌ Could not connect to Redis. StateManager will be disabled.", exc_info=False) # exc_infoをFalseにしてスタックトレースを抑制
            logger.debug("Redis connection details", exc_info=True) # debugレベルでは詳細を残す
            self._client = None
            self.is_ready = False
            if strict:
                raise

    def _key(self, task_id: str) -> str:
        ns = getattr(self, "namespace", "nexus")
        return f"{ns}:task_state:{task_id}"

    def set_task_state(self, task_id: str, state: dict, ttl_seconds: int = 3600) -> bool:
        if not self.is_ready or not self._client:
            logger.warning("Redis client is not available; skipping set_task_state")
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
        if not self.is_ready or not self._client:
            logger.warning("Redis client is not available; skipping get_task_state")
            return None
        try:
            key = self._key(task_id)
            raw = self._client.get(key)
            return json.loads(raw) if raw else None
        except Exception as e:
            logger.error(f"Failed to get task state for {task_id}: {e}", exc_info=True)
            return None

# モジュールスコープの既定インスタンス
# この時点で __init__ が実行される
state_manager = StateManager()

