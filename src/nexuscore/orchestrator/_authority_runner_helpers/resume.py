from __future__ import annotations

from collections.abc import Callable
from typing import Any

from ..explainability import build_explainability
from ..run_lock import release_run_lock, try_acquire_run_lock
from ..run_state_integrity import verify_integrity
from ..run_state_schema_validator import validate_run_state
from ..run_state_store import load_state, save_state, update_state
from .lock_lease import RunLockLease


_RESUME_ORCHESTRATOR: Any = None
_RESUME_ORCHESTRATOR_FACTORY: Callable[[], Any] | None = None


def set_resume_orchestrator(orchestrator: Any) -> None:
    global _RESUME_ORCHESTRATOR
    _RESUME_ORCHESTRATOR = orchestrator


def set_resume_orchestrator_factory(factory: Callable[[], Any]) -> None:
    global _RESUME_ORCHESTRATOR_FACTORY
    _RESUME_ORCHESTRATOR_FACTORY = factory


def _execute_remaining_phases(orchestrator: Any, state: dict[str, Any]) -> None:
    from nexuscore.core.orchestrator import OrchestratorContext

    _PHASE_MAP = {
        "requirements": "run_requirements_phase",
        "planning": "run_planning_phase",
        "architecture": "run_architecture_phase",
        "implementation": "run_implementation_phase",
        "testing": "run_testing_phase",
        "review": "run_review_phase",
    }
    _PHASE_ORDER = ["requirements", "planning", "architecture", "implementation", "testing", "review"]

    next_phase = state.get("next_phase")
    if not next_phase or next_phase not in _PHASE_MAP:
        import logging
        logging.getLogger(__name__).warning(
            "resume: no valid next_phase in state (got %r), skipping phase execution",
            next_phase,
        )
        return

    context = OrchestratorContext(
        task_id=state.get("run_id", ""),
        user_requirement=state.get("user_requirement", ""),
        language=state.get("language", "ja"),
        fast_lane=state.get("fast_lane", False),
        run_db_id=state.get("run_db_id"),
    )

    if "requirement_result" in state:
        context.requirement = state["requirement_result"]
    if "plan" in state:
        context.plan = state["plan"]
    if "architecture" in state:
        context.architecture = state["architecture"]
    if "implementation" in state:
        context.implementation = state["implementation"]
    if "testing" in state:
        context.testing = state["testing"]

    start_idx = _PHASE_ORDER.index(next_phase)
    for phase_name in _PHASE_ORDER[start_idx:]:
        method_name = _PHASE_MAP[phase_name]
        phase_fn = getattr(orchestrator, method_name, None)
        if not callable(phase_fn):
            break
        context = phase_fn(context)
        state["next_phase"] = _PHASE_ORDER[_PHASE_ORDER.index(phase_name) + 1] if phase_name != "review" else None
        update_state(state)


def resume_run(
    run_id: str,
    *,
    orchestrator_factory: Callable[[], Any] | None = None,
) -> dict[str, Any]:
    state: dict[str, Any]

    try:
        state = load_state(run_id)
    except FileNotFoundError:
        failed_state: dict[str, Any] = {
            "schema_version": "1.0",
            "run_id": run_id,
            "status": "FAILED",
            "authority_level": None,
            "next_phase": None,
            "last_error": {"code": "STATE_NOT_FOUND", "message": "RunState not found"},
        }
        try:
            save_state(failed_state)
        except Exception:  # noqa: BLE001 — 失敗状態の保存失敗は握りつぶす
            pass
        return {
            "status": "FAILED",
            "run_id": run_id,
            "explainability": build_explainability(
                what=f"Resume failed: RunState not found for run_id={run_id}",
                why_code="STATE_NOT_FOUND",
                next_action="Check run_id or start a new run",
            ),
        }

    try:
        ok, code, message = validate_run_state(state)
        if not ok:
            state["status"] = "FAILED"
            state["last_error"] = {
                "code": code or "SCHEMA_INVALID",
                "message": message or "Schema invalid",
            }
            update_state(state)
            return {
                "status": "FAILED",
                "run_id": run_id,
                "explainability": build_explainability(
                    what=f"Resume failed: invalid RunState schema for run_id={run_id}",
                    why_code=code or "SCHEMA_INVALID",
                    next_action="Fix RunState or abort and start a new run",
                ),
            }

        ok, code, message = verify_integrity(state)
        if not ok:
            return {
                "status": "FAILED",
                "run_id": run_id,
                "explainability": build_explainability(
                    what=f"Resume failed: RunState integrity verification failed for run_id={run_id}",
                    why_code=code or "STATE_INTEGRITY_VIOLATION",
                    next_action="Abort this run_id and start a new run",
                ),
            }

        status = state.get("status")
        normalized_status = status.upper() if isinstance(status, str) else status
        if normalized_status != "PAUSED":
            state["status"] = "FAILED"
            state["last_error"] = {
                "code": "STATE_NOT_PAUSED",
                "message": f"RunState status must be PAUSED to resume (got {status!r})",
            }
            update_state(state)
            return {
                "status": "FAILED",
                "run_id": run_id,
                "explainability": build_explainability(
                    what=f"Resume failed: run is not paused (run_id={run_id})",
                    why_code="STATE_NOT_PAUSED",
                    next_action="Pause the run first or start a new run",
                ),
            }
        state["status"] = "PAUSED"

        ok, reason = try_acquire_run_lock(run_id)
        if not ok:
            return {
                "status": "CONFLICT",
                "run_id": run_id,
                "explainability": build_explainability(
                    what=f"Resume conflict: run_id={run_id} is already being resumed/executed",
                    why_code=reason or "CONFLICT",
                    next_action="wait/retry",
                ),
            }

        release_run_lock(run_id)

        state["status"] = "RESUMING"
        update_state(state)

        if orchestrator_factory is not None:
            orchestrator = orchestrator_factory()
        else:
            orch_factory = _RESUME_ORCHESTRATOR_FACTORY
            if orch_factory is not None:
                orchestrator = orch_factory()
            else:
                orchestrator = _RESUME_ORCHESTRATOR

            if orchestrator is None:
                raise RuntimeError(
                    "resume orchestrator is not set (call set_resume_orchestrator_factory or set_resume_orchestrator, "
                    "or provide orchestrator_factory argument)"
                )

        with RunLockLease(run_id) as lock_lease:
            state["status"] = "RUNNING"
            update_state(state)

            _execute_remaining_phases(orchestrator, state)

            import time
            from ..run_lock import _get_lock_refresh_seconds

            refresh_interval = float(_get_lock_refresh_seconds())
            max_poll_time = refresh_interval * 2.5
            poll_delay = min(0.1, refresh_interval / 5)
            max_polls = int(max_poll_time / poll_delay) + 1

            for _ in range(max_polls):
                if lock_lease.is_refresh_failed():
                    reason, details = lock_lease.get_refresh_failure()
                    state["status"] = "ABORTED"
                    state["last_error"] = {
                        "code": "LOCK_REFRESH_FAILED",
                        "message": f"Lock refresh failed: {reason}",
                        "next_action": "inspect_lock_dir_permissions",
                        "details": details,
                    }
                    update_state(state)
                    return {
                        "status": "ABORTED",
                        "run_id": run_id,
                        "explainability": build_explainability(
                            what=f"Run aborted due to lock refresh failure (run_id={run_id})",
                            why_code="LOCK_REFRESH_FAILED",
                            next_action="inspect_lock_dir_permissions",
                            details=details,
                        ),
                    }
                time.sleep(poll_delay)

            return {
                "status": "RUNNING",
                "run_id": run_id,
            }

    except Exception as e:  # noqa: BLE001 — レジューム全体のフォールバック
        try:
            state["status"] = "FAILED"
            state["last_error"] = {
                "code": "INTERNAL_ERROR",
                "message": str(e),
                "next_action": "Check logs and retry",
            }
            update_state(state)
        except Exception:  # noqa: BLE001 — エラー状態更新の失敗は握りつぶす
            pass
        return {
            "status": "FAILED",
            "run_id": run_id,
            "explainability": build_explainability(
                what=f"Resume failed due to internal error (run_id={run_id})",
                why_code="INTERNAL_ERROR",
                next_action="Check logs and retry or start a new run",
                details={"error": str(e)},
            ),
        }
