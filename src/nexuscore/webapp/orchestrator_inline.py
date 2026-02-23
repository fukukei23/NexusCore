"""
NexusCore Webapp - Orchestrator インライン実行ヘルパー

同期実行用のヘルパー関数（デバッグ用）。
"""

from __future__ import annotations

import logging
from datetime import datetime

from nexuscore.webapp import db
from nexuscore.webapp.models import Project, Run
from nexuscore.webapp.orchestrator_helper import run_orchestrator_sync

logger = logging.getLogger(__name__)


def run_orchestrator_inline(
    run: Run,
    project: Project,
    requirement: str,
    autonomy_level: int = 1,
    fast_lane: bool = False,
) -> None:
    """
    Orchestrator を同期的に実行する（インライン実行）。

    Args:
        run: Run レコード
        project: Project レコード
        requirement: ユーザー要件
        autonomy_level: 自動化レベル
        fast_lane: 高速レーン実行フラグ

    Raises:
        Exception: Orchestrator 実行時のエラー
    """
    status = "SUCCESS"
    try:
        # 実行開始
        run.status = "RUNNING"
        run.started_at = datetime.utcnow()
        db.session.commit()

        # Orchestrator を同期的に実行
        run_orchestrator_sync(
            project_path=project.local_path,
            user_requirement=requirement,
            run_db_id=run.id,
            autonomy_level=autonomy_level,
            language="ja",
            fast_lane=fast_lane,
        )

        run.status = "SUCCESS"
        status = "success"
    except Exception as exc:
        # エラーハンドリング
        logger.error(f"Orchestrator execution failed for run_id={run.id}: {exc}", exc_info=True)
        run.status = "FAILED"
        status = "error"
        # ログ自体は orchestrator_db_hook / logging_service 経由で ExecutionLog に入る
        raise
    finally:
        run.finished_at = datetime.utcnow()
        db.session.commit()

        # Slack 通知を送信
        try:
            from nexuscore.core.notifier import get_notifier

            notifier = get_notifier()
            if notifier:
                # セッションIDを取得（run.run_id を使用）
                session_id = run.run_id or str(run.id)
                notifier.notify_orchestrator_complete(
                    project_path=project.local_path,
                    requirement=requirement,
                    status=status,
                    session_id=session_id,
                    details={
                        "Run ID": run.run_id,
                        "プロジェクト名": project.name,
                    },
                )
        except Exception as e:
            logger.warning(f"Failed to send Slack notification: {e}", exc_info=True)
