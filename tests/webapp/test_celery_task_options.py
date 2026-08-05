"""C3: Celery タスク装飾子オプションの静的検証。

run_orchestrator タスクが冪等性・再実行保護のための正しいオプションを持つか検証。
（celery 初期化を伴わず、TASK_OPTIONS 定数で検証）
"""
import redis
import sqlalchemy

from nexuscore.webapp.celery_app import TASK_OPTIONS


def test_task_acks_late_enabled():
    """acks_late=True: タスク完了後にack（worker落ちで再配送・タスクロスト防止）"""
    assert TASK_OPTIONS["acks_late"] is True


def test_task_reject_on_worker_lost_enabled():
    """reject_on_worker_lost=True: worker ロスト時にメッセージをbrokerへ戻す"""
    assert TASK_OPTIONS["reject_on_worker_lost"] is True


def test_task_bind_true():
    """bind=True: タスク本体で self（task request）参照可・self.request.id で worker_id 取得"""
    assert TASK_OPTIONS["bind"] is True


def test_autoretry_covers_transient_errors():
    """autoretry_for が主要な一時的例外を網羅"""
    retry_targets = TASK_OPTIONS["autoretry_for"]
    # DB接続一時断
    assert sqlalchemy.exc.OperationalError in retry_targets
    # Redis broker 接続エラー
    assert redis.exceptions.ConnectionError in retry_targets
    assert redis.exceptions.TimeoutError in retry_targets
    # 汎用タイムアウト/接続エラー
    assert TimeoutError in retry_targets
    assert ConnectionError in retry_targets


def test_retry_backoff_settings():
    """バックオフ・ジッタ・上限・最大試行回数の設定"""
    assert TASK_OPTIONS["retry_backoff"] is True
    assert TASK_OPTIONS["retry_backoff_max"] == 120
    assert TASK_OPTIONS["retry_jitter"] is True
    assert TASK_OPTIONS["max_retries"] == 5
