# =============================================================================
# Self-healing finalization and session control utilities
# =============================================================================

from __future__ import annotations

import logging
import time
from datetime import UTC
from typing import Any


def maybe_stop(
    session_controller: Any,
    logger: logging.Logger,
    phase: str,
    meta: dict[str, Any] | None = None,
) -> None:
    if not session_controller:
        return
    try:
        session_controller.checkpoint(phase, meta or {})
    except Exception:
        logger.exception("Failed to checkpoint at phase='%s'", phase)
    if session_controller.should_stop():
        logger.warning("Session stop requested at phase='%s'.", phase)
        raise RuntimeError("SessionStopped")


def inject_retry_context(
    debugger_agent: Any | None,
    guardian_agent: Any | None,
    retry_context: Any | None,
) -> None:
    if not retry_context:
        return
    if debugger_agent and hasattr(debugger_agent, "retry_context"):
        debugger_agent.retry_context = retry_context
    if guardian_agent and hasattr(guardian_agent, "retry_context"):
        guardian_agent.retry_context = retry_context


def retry_info(retry_context: Any | None) -> dict[str, Any]:
    if not retry_context:
        return {"retry_count": 0, "last_error_class": None}
    info = retry_context.to_dict()
    return {
        "retry_count": info.get("retry_count", 0),
        "last_error_class": info.get("last_error_class"),
    }


def finalize_run(
    *,
    logger: logging.Logger,
    history_logger: Any,
    project_root: Any,
    run_id: str,
    session_id: str,
    repo_full_name: str,
    pr_number: int,
    head_sha: str,
    status: str,
    summary: str,
    details: dict[str, Any],
    started_at: float,
    started_at_iso: str | None = None,
    started_ts: float | None = None,
) -> dict[str, Any]:
    from datetime import datetime

    finished_at = time.time()
    finished_at_iso = datetime.now(UTC).isoformat()

    if started_ts is not None:
        finished_ts = time.monotonic()
        duration_seconds = round(finished_ts - started_ts, 2)
    else:
        duration_seconds = round(finished_at - started_at, 2)

    if started_at_iso is None:
        started_at_iso = datetime.fromtimestamp(started_at, tz=UTC).isoformat()

    try:
        record = history_logger.new_self_healing_record(
            run_id=run_id, session_id=session_id, repo_full_name=repo_full_name,
            pr_number=pr_number, head_sha=head_sha, status=status,
            summary=summary, details=details,
            started_at=started_at, finished_at=finished_at,
        )
        history_logger.log_run(record)
    except Exception:
        logger.exception("Failed to log self-healing run history.")

    try:
        from nexuscore.integration.run_report_generator import write_run_report_file
        from nexuscore.webapp.models import Run

        run = Run.query.filter_by(run_id=run_id).first()
        if run and hasattr(run, "id"):
            report_path = write_run_report_file(run.id, base_dir=project_root)
            logger.info("Run report generated: %s", report_path)
    except ImportError:
        pass
    except Exception as e:
        logger.warning("Failed to generate run report: %s", e, exc_info=True)

    return {
        "status": status,
        "summary": summary,
        "details": details,
        "run_id": run_id,
        "session_id": session_id,
        "started_at": started_at,
        "started_at_iso": started_at_iso,
        "finished_at": finished_at,
        "finished_at_iso": finished_at_iso,
        "duration_seconds": duration_seconds,
    }
