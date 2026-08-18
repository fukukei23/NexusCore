from __future__ import annotations

import os
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

import redis
import sqlalchemy
from celery import Celery

from nexuscore.config.unified_config import get_config

celery: Celery | None = None
run_orchestrator_task: Callable | None = None


def _celery_idempotency_config() -> dict:
    """C3: 冪等性・再実行保護のための Celery 設定（環境変数から・テスト可能）。

    - task_acks_late/task_reject_on_worker_lost: worker落ちで再配送
    - task_track_started: STARTED 状態を追跡（モニタリング向上）
    - broker_transport_options.visibility_timeout: Redis broker の再配送閾値
      （acks_late + 長時間タスクには visibility_timeout 延長が必須・デフォルト3600s→7200s推奨）
    """
    return {
        "task_acks_late": os.getenv("CELERY_TASK_ACKS_LATE", "0") == "1",
        "task_reject_on_worker_lost": os.getenv("CELERY_TASK_REJECT_ON_WORKER_LOST", "0") == "1",
        "task_track_started": os.getenv("CELERY_TASK_TRACK_STARTED", "0") == "1",
        "broker_transport_options": {
            "visibility_timeout": int(os.getenv("CELERY_BROKER_VISIBILITY_TIMEOUT", "3600")),
        },
    }

# C3: run_orchestrator タスクの装飾子オプション（テストで静的検証）
# - acks_late/reject_on_worker_lost: worker 落ちで broker へ再配送（タスクロスト防止）
# - autoretry_for: 一時的例外のみ自動再試行（Orchestrator 例外は部分適用リスクで対象外）
# - retry_backoff/jitter: 指数バックオフ + ジッタでレート制限・スタampede 回避
TASK_OPTIONS: dict = dict(
    name="nexuscore.run_orchestrator",
    bind=True,
    acks_late=True,
    reject_on_worker_lost=True,
    autoretry_for=(
        sqlalchemy.exc.OperationalError,
        redis.exceptions.ConnectionError,
        redis.exceptions.TimeoutError,
        TimeoutError,
        ConnectionError,
    ),
    retry_backoff=True,
    retry_backoff_max=120,
    retry_jitter=True,
    max_retries=5,
)


def make_celery(flask_app) -> Celery:
    """
    Flask アプリと連携した Celery インスタンスを作成する。

    Args:
        flask_app: Flask アプリケーションインスタンス

    Returns:
        Celery インスタンス
    """
    global celery

    if celery is not None:
        return celery

    _cfg = get_config()
    celery_app = Celery(
        flask_app.import_name,
        broker=_cfg.celery.broker_url,
        backend=_cfg.celery.result_backend,
    )
    celery_app.conf.update(flask_app.config)
    # C3: 冪等性・再実行保護設定（環境変数から・_celery_idempotency_config で検証）
    celery_app.conf.update(_celery_idempotency_config())

    # Flask アプリコンテキスト内でタスクを実行するためのカスタムタスククラス
    class ContextTask(celery_app.Task):  # type: ignore[name-defined]
        """Flask アプリコンテキスト内でタスクを実行するカスタムタスククラス"""

        def __call__(self, *args, **kwargs):
            # Flask アプリコンテキスト内でタスクを実行
            with flask_app.app_context():
                return super().__call__(*args, **kwargs)

    celery_app.Task = ContextTask
    celery = celery_app  # グローバル変数に保存

    # タスクを登録
    _register_tasks(celery_app)

    return celery_app


def init_celery() -> Celery:
    """
    Celery インスタンスを初期化する（Celery worker 用）。

    Returns:
        Celery インスタンス
    """
    global celery
    if celery is not None:
        return celery

    from nexuscore.webapp import create_app

    flask_app = create_app()
    celery_instance = make_celery(flask_app)
    return celery_instance


# ==============================================================================
# Celery タスク定義
# ==============================================================================

from nexuscore.core.job_state_machine import JobStateMachine
from nexuscore.core.run_history import RunHistoryLogger
from nexuscore.core.session_control import SessionController
from nexuscore.webapp import db
from nexuscore.webapp.models import Project, Run
from nexuscore.webapp.orchestrator_helper import run_orchestrator_sync


def _finalize_run(run: Run, project: Project, status: str) -> None:
    """Run完了後のレポート生成 + Slack通知"""
    import logging
    logger = logging.getLogger(__name__)

    run.finished_at = datetime.now(UTC)
    try:
        db.session.commit()
    except Exception as e:  # noqa: BLE001
        logger.error(f"Failed to update Run status in finally block: {e}", exc_info=True)
        db.session.rollback()

    try:
        from nexuscore.integration.run_report_generator import write_run_report_file

        report_path = write_run_report_file(run.id)
        logger.info(f"Run report generated: {report_path}")

        try:
            from nexuscore.webapp.models import ExecutionLog

            db.session.add(ExecutionLog(
                run_id=run.id,
                source="SYSTEM",
                level="INFO",
                message=f"Run report generated: {report_path}",
                payload_json={"report_path": str(report_path)},
            ))
            db.session.commit()
        except Exception as log_exc:  # noqa: BLE001
            logger.warning(f"Failed to log report generation: {log_exc}", exc_info=True)
    except Exception as e:  # noqa: BLE001
        logger.warning(f"Failed to generate run report: {e}", exc_info=True)

    try:
        from sqlalchemy.exc import IntegrityError

        from nexuscore.core.notifier import get_notifier
        from nexuscore.webapp.models import NotificationLog

        notifier = get_notifier()
        if notifier:
            event_type = "orchestrator_complete" if status == "success" else "orchestrator_failed"
            # C3: 冪等ガード（NotificationLog UNIQUE 制約で Slack 重複送信防止）
            try:
                db.session.add(NotificationLog(run_id=run.id, event_type=event_type))
                db.session.commit()
            except IntegrityError:
                db.session.rollback()
                logger.info(
                    f"Notification {event_type} for run {run.id} already sent — skipping (idempotency)"
                )
            else:
                session_id = run.run_id or str(run.id)
                notifier.notify_orchestrator_complete(
                    project_path=project.local_path,
                    requirement=run.requirement,
                    status=status,
                    session_id=session_id,
                    details={"Run ID": run.run_id, "プロジェクト名": project.name},
                )
    except Exception as e:  # noqa: BLE001
        logger.warning(f"Failed to send Slack notification: {e}", exc_info=True)


def _acquire_execution_lock(run: Run, worker_id: str, redis_client: Any = None) -> tuple[bool, Any, str]:
    """C3 冪等ガンド: SUCCESS skip + Redis SETNX ロック取得。

    戻り値: (実行可, redis_client, lock_key)。
    - run.status == "SUCCESS" → (False, client, key)（2重実行防止）
    - ロック取得失敗（別 worker 実行中）→ (False, client, key)
    - ロック取得成功 → (True, client, key)
    ※ redis_client はテストで fakeredis を注入可能。
    """
    from nexuscore.webapp import task_lock

    client = redis_client if redis_client is not None else task_lock.get_redis()
    lock_key = task_lock.task_lock_key(run.id)

    if run.status == "SUCCESS":
        return (False, client, lock_key)

    from nexuscore.core import run_checkpoint

    if not task_lock.acquire_lock(client, lock_key, worker_id, ttl=run_checkpoint.LOCK_TTL):
        return (False, client, lock_key)

    return (True, client, lock_key)


def _register_tasks(celery_instance: Celery) -> None:
    """Celery タスクを登録する"""
    global run_orchestrator_task

    @celery_instance.task(**TASK_OPTIONS)
    def _run_orchestrator_task_internal(self, run_db_id: int) -> None:
        """
        単一 Run を対象に Orchestrator を非同期実行する Celery タスク（JobStateMachine統合版）。

        Args:
            run_db_id: Run.id（Webapp側でRunレコードを作成したときのID）
        """
        import logging
        import os
        import uuid

        logger = logging.getLogger(__name__)

        run: Run | None = Run.query.get(run_db_id)
        if run is None:
            logger.error(f"Run not found: run_db_id={run_db_id}")
            return

        # C3: 冪等ガード（SUCCESS skip + Redis SETNX ロック・Race Condition 回避）
        # ※ self.request.id はタスク直接呼び出し（テスト等）では None になる。
        #    そのまま渡すと redis SET の値が None で DataError のため uuid にフォールバック
        #    （broker 経由の実運行では常に request.id が設定される）
        worker_id = self.request.id or f"direct-{uuid.uuid4().hex}"
        can_run, redis_client, lock_key = _acquire_execution_lock(run, worker_id)
        if run.status == "SUCCESS":
            logger.info(f"Run {run_db_id} skipped by idempotency guard (already SUCCESS)")
            return
        if not can_run:
            # A3: skip-return-ACK だと再配送workerが消えてタスク消失する。
            # ロック残り<TTL(600s)後に遅延再試行させる（retryはautoretry_forと別系統・
            # max_retries到達で失敗終了するため有界）
            from nexuscore.core import run_checkpoint

            logger.info(f"Run {run_db_id} locked by another worker -> retry in {run_checkpoint.LOCK_TTL + 60}s")
            raise self.retry(countdown=run_checkpoint.LOCK_TTL + 60)

        try:
            project: Project = run.project
            job_id = run.run_id or str(run.id)

            if not run.requirement:
                logger.error(f"Run.requirement is empty for run_id={run.id}")
                run.status = "FAILED"
                run.finished_at = datetime.now(UTC)
                db.session.commit()
                return

            session_controller = SessionController(
                session_id=job_id,
                root_dir=os.path.join(project.local_path, ".nexus", "sessions"),
            )
            history_logger = RunHistoryLogger(project_root=project.local_path)
            state_machine = JobStateMachine(
                job_id=job_id,
                session_controller=session_controller,
                history_logger=history_logger,
                job_type="orchestrator",
            )

            final_status = "error"
            try:
                state_machine.start()
                run.status = "RUNNING"
                run.started_at = datetime.now(UTC)
                db.session.commit()

                from nexuscore.core import run_checkpoint
                from nexuscore.webapp import task_lock

                heartbeat_fn: Callable[[], None] | None
                if redis_client is not None:
                    def heartbeat_fn() -> None:
                        task_lock.heartbeat(redis_client, lock_key, worker_id, ttl=run_checkpoint.LOCK_TTL)
                else:
                    heartbeat_fn = None
                run_orchestrator_sync(
                    project_path=project.local_path,
                    user_requirement=run.requirement,
                    run_db_id=run.id,
                    autonomy_level=run.autonomy_level or 1,
                    language="ja",
                    fast_lane=False,
                    heartbeat_fn=heartbeat_fn,
                )

                state_machine.complete(details={"run_db_id": run.id, "project_name": project.name})
                run.status = "SUCCESS"
                final_status = "success"

                # C3 Plan2: SUCCESS 確定時のみチェックポイント掃除
                # （FAILED は保持→autoretry の再実行が途中再開する・TTL 24h で自動消滅）
                from nexuscore.core import run_checkpoint as _rc

                _rc.clear_checkpoints(_rc.get_client(), run.id)

            except Exception as exc:  # noqa: BLE001
                logger.error(f"Orchestrator execution failed for run_id={run.id}: {exc}", exc_info=True)
                state_machine.fail(
                    error_message=str(exc),
                    details={"run_db_id": run.id, "project_name": project.name, "exception_type": type(exc).__name__},
                )
                run.status = "FAILED"

            finally:
                _finalize_run(run, project, final_status)

        finally:
            # C3: ロック解放（所有者のみ・例外時も確実に解放）
            from nexuscore.webapp import task_lock
            task_lock.release_lock(redis_client, lock_key, worker_id)

    run_orchestrator_task = _run_orchestrator_task_internal


# Celery worker 用のエントリポイント
# worker 起動時に `celery -A nexuscore.webapp.celery_app.celery` で celery が参照される
# その時点で init_celery() を呼び出して初期化する

# Celery worker 起動時に自動的に初期化されるようにする
# テスト時や環境変数で無効化された場合は初期化をスキップ
if celery is None and os.getenv("SKIP_CELERY_AUTO_INIT") != "1":
    try:
        celery = init_celery()
    except (ImportError, ModuleNotFoundError):
        # テスト時や依存関係が不足している場合は初期化をスキップ
        # Celery worker 起動時には依存関係が揃っている前提
        pass
