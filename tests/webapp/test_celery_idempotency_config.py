"""C3: Celery 冪等性設定（_celery_idempotency_config）のテスト。"""
import os
from unittest.mock import patch

from nexuscore.webapp.celery_app import _celery_idempotency_config


def test_config_defaults_off():
    """環境変数未設定時は acks_late 等は off（既存挙動維持・後方互換）"""
    env = {k: v for k, v in os.environ.items()
           if not k.startswith("CELERY_TASK_") and k != "CELERY_BROKER_VISIBILITY_TIMEOUT"}
    with patch.dict(os.environ, env, clear=True):
        cfg = _celery_idempotency_config()
    assert cfg["task_acks_late"] is False
    assert cfg["task_reject_on_worker_lost"] is False
    assert cfg["task_track_started"] is False
    assert cfg["broker_transport_options"]["visibility_timeout"] == 3600


def test_config_enabled_via_env():
    """環境変数で冪等性設定を有効化（docker-compose と同じ）"""
    env = {
        "CELERY_TASK_ACKS_LATE": "1",
        "CELERY_TASK_REJECT_ON_WORKER_LOST": "1",
        "CELERY_TASK_TRACK_STARTED": "1",
        "CELERY_BROKER_VISIBILITY_TIMEOUT": "7200",
    }
    with patch.dict(os.environ, env, clear=False):
        cfg = _celery_idempotency_config()
    assert cfg["task_acks_late"] is True
    assert cfg["task_reject_on_worker_lost"] is True
    assert cfg["task_track_started"] is True
    assert cfg["broker_transport_options"]["visibility_timeout"] == 7200
