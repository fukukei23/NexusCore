from __future__ import annotations

import os
from collections.abc import Callable
from datetime import UTC, datetime

from celery import Celery

from nexuscore.config.unified_config import get_config

celery: Celery | None = None
run_orchestrator_task: Callable | None = None


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
        from nexuscore.core.notifier import get_notifier

        notifier = get_notifier()
        if notifier:
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


def _register_tasks(celery_instance: Celery) -> None:
    """Celery タスクを登録する"""
    global run_orchestrator_task

    @celery_instance.task(name="nexuscore.run_orchestrator")
    def _run_orchestrator_task_internal(run_db_id: int) -> None:
        """
        単一 Run を対象に Orchestrator を非同期実行する Celery タスク（JobStateMachine統合版）。

        Args:
            run_db_id: Run.id（Webapp側でRunレコードを作成したときのID）
        """
        import logging
        import os

        logger = logging.getLogger(__name__)

        run: Run | None = Run.query.get(run_db_id)
        if run is None:
            logger.error(f"Run not found: run_db_id={run_db_id}")
            return

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

            run_orchestrator_sync(
                project_path=project.local_path,
                user_requirement=run.requirement,
                run_db_id=run.id,
                autonomy_level=run.autonomy_level or 1,
                language="ja",
                fast_lane=False,
            )

            state_machine.complete(details={"run_db_id": run.id, "project_name": project.name})
            run.status = "SUCCESS"
            final_status = "success"

        except Exception as exc:  # noqa: BLE001
            logger.error(f"Orchestrator execution failed for run_id={run.id}: {exc}", exc_info=True)
            state_machine.fail(
                error_message=str(exc),
                details={"run_db_id": run.id, "project_name": project.name, "exception_type": type(exc).__name__},
            )
            run.status = "FAILED"

        finally:
            _finalize_run(run, project, final_status)

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
