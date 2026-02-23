"""
orchestrator/authority_runner.py

Authority-level execution controller for NexusCore Orchestrator.

This module intentionally avoids importing frozen `nexuscore.core.orchestrator`
at import time. It controls execution by calling existing public phase methods
on an orchestrator instance (duck-typed).
"""

from __future__ import annotations

import threading
import uuid
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any

from .constants import AuthorityLevel
from .explainability import build_explainability
from .run_lock import refresh_run_lock, release_run_lock, try_acquire_run_lock
from .run_state_integrity import verify_integrity
from .run_state_schema_validator import validate_run_state
from .run_state_store import load_state, save_state, update_state


class RunLockLease:
    """
    Context manager for holding a run lock during execution (Mode B).

    Acquires lock on enter, starts a background refresh loop, and releases on exit.
    If refresh fails, sets a flag that can be checked to trigger safe shutdown.
    """

    def __init__(self, run_id: str, refresh_interval_seconds: float | None = None):
        self.run_id = run_id
        self.refresh_interval = refresh_interval_seconds
        if self.refresh_interval is None:
            # Default: read from env or use ttl // 3 (minimum 5 seconds)
            from .run_lock import _get_lock_refresh_seconds

            self.refresh_interval = float(_get_lock_refresh_seconds())
        self._lock_acquired = False
        self._refresh_thread: threading.Thread | None = None
        self._stop_refresh = threading.Event()
        self._refresh_failed = threading.Event()
        self._refresh_failure_reason: str | None = None
        self._refresh_failure_details: dict[str, Any] | None = None

    def __enter__(self) -> RunLockLease:
        """Acquire lock and start refresh loop."""
        ok, reason = try_acquire_run_lock(self.run_id)
        if not ok:
            raise RuntimeError(f"Failed to acquire lock for {self.run_id}: {reason}")

        self._lock_acquired = True
        self._stop_refresh.clear()
        self._refresh_failed.clear()
        self._refresh_failure_reason = None
        self._refresh_failure_details = None

        # Start background refresh thread
        self._refresh_thread = threading.Thread(target=self._refresh_loop, daemon=True)
        self._refresh_thread.start()

        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Stop refresh loop and release lock."""
        # Stop refresh loop
        self._stop_refresh.set()
        if self._refresh_thread is not None:
            self._refresh_thread.join(
                timeout=self.refresh_interval * 2
            )  # Wait up to 2 refresh cycles

        # Release lock
        if self._lock_acquired:
            release_run_lock(self.run_id)
            self._lock_acquired = False

    def _refresh_loop(self) -> None:
        """Background thread that periodically refreshes the lock."""
        while not self._stop_refresh.is_set():
            # Wait for refresh interval (or until stop event is set)
            if self._stop_refresh.wait(timeout=self.refresh_interval):
                break  # Stop event was set

            # Try to refresh lock
            ok, reason, details = refresh_run_lock(self.run_id)
            if not ok:
                # Refresh failed: set flag and stop loop
                self._refresh_failure_reason = reason
                self._refresh_failure_details = details
                self._refresh_failed.set()
                break

    def is_refresh_failed(self) -> bool:
        """Check if refresh has failed (caller should trigger safe shutdown)."""
        return self._refresh_failed.is_set()

    def get_refresh_failure(self) -> tuple[str | None, dict[str, Any] | None]:
        """Get refresh failure reason and details (if failed)."""
        return self._refresh_failure_reason, self._refresh_failure_details


PHASES_ORDER: tuple[str, ...] = (
    "requirements",
    "planning",
    "architecture",
    "implementation",
    "testing",
    "review",
)

PHASE_TO_METHOD: dict[str, str] = {
    "requirements": "run_requirements_phase",
    "planning": "run_planning_phase",
    "architecture": "run_architecture_phase",
    "implementation": "run_implementation_phase",
    "testing": "run_testing_phase",
    "review": "run_review_phase",
}


def phases_for_authority_level(authority_level: int) -> tuple[str, ...]:
    """
    Map AuthorityLevel to the phases that are allowed to run.

    Minimal default policy:
    - HUMAN_CONTROLLED: requirements only (human review gate after requirement capture)
    - PARTIALLY_AUTONOMOUS: through architecture
    - FULLY_AUTONOMOUS: all phases
    """
    if authority_level == AuthorityLevel.HUMAN_CONTROLLED:
        return ("requirements",)
    if authority_level == AuthorityLevel.PARTIALLY_AUTONOMOUS:
        return ("requirements", "planning", "architecture")
    if authority_level == AuthorityLevel.FULLY_AUTONOMOUS:
        return PHASES_ORDER
    raise ValueError(f"Invalid authority level: {authority_level}")


@dataclass(frozen=True)
class RunnerConfig:
    """
    Configuration for authority runner.

    `allowed_phases` can override the default mapping when needed.
    """

    authority_level: int
    allowed_phases: Sequence[str] | None = None


def _default_context_factory(
    *,
    user_requirement: str,
    language: str,
    fast_lane: bool,
    run_db_id: int | None,
) -> Any:
    """
    Create an OrchestratorContext without importing core at module import time.
    Falls back to a lightweight object if core context cannot be imported.
    """
    try:
        # Local import: avoid importing frozen core during module import.
        from nexuscore.core.orchestrator import OrchestratorContext  # type: ignore

        return OrchestratorContext(
            task_id=uuid.uuid4().hex,
            user_requirement=user_requirement,
            language=language,
            fast_lane=fast_lane,
            run_db_id=run_db_id,
        )
    except Exception:
        # Minimal fallback for tests / limited environments.
        @dataclass
        class _FallbackContext:  # noqa: N801 (internal helper)
            task_id: str
            user_requirement: str
            language: str
            fast_lane: bool
            run_db_id: int | None
            specs: dict[str, Any]
            plan: dict[str, Any]
            architecture: dict[str, Any]
            implementation: dict[str, Any]
            testing: dict[str, Any]
            review: dict[str, Any]
            phase_log: list[str]

        return _FallbackContext(
            task_id=uuid.uuid4().hex,
            user_requirement=user_requirement,
            language=language,
            fast_lane=fast_lane,
            run_db_id=run_db_id,
            specs={},
            plan={},
            architecture={},
            implementation={},
            testing={},
            review={},
            phase_log=[],
        )


def run_with_authority_level(
    orchestrator: Any,
    user_requirement: str,
    *,
    authority_level: int,
    language: str = "ja",
    fast_lane: bool = False,
    run_db_id: int | None = None,
    allowed_phases: Sequence[str] | None = None,
    context_factory: Callable[..., Any] | None = None,
) -> Any:
    """
    Run Orchestrator phases up to the allowed authority level.

    This does NOT call `orchestrator.run_full_project` to avoid executing phases
    outside the configured authority gate. Instead, it calls public phase methods
    (`run_requirements_phase`, `run_planning_phase`, ...).
    """
    config = RunnerConfig(authority_level=authority_level, allowed_phases=allowed_phases)

    phases: Sequence[str]
    if config.allowed_phases is not None:
        phases = tuple(config.allowed_phases)
    else:
        phases = phases_for_authority_level(config.authority_level)

    invalid = [p for p in phases if p not in PHASE_TO_METHOD]
    if invalid:
        raise ValueError(f"Unknown phase(s): {invalid}")

    factory = context_factory or _default_context_factory
    context = factory(
        user_requirement=user_requirement,
        language=language,
        fast_lane=fast_lane,
        run_db_id=run_db_id,
    )

    for phase in phases:
        method_name = PHASE_TO_METHOD[phase]
        method = getattr(orchestrator, method_name, None)
        if not callable(method):
            raise AttributeError(f"Orchestrator does not provide required method: {method_name}")
        context = method(context)

    return context


def run_with_authority(
    *,
    orchestrator: Any,
    user_requirement: str,
    authority_level: str | None = None,
    language: str = "ja",
    fast_lane: bool = False,
    run_db_id: int | None = None,
) -> Any:
    """
    STEP2 wiring entrypoint.

    This function accepts `authority_level` as a *string* (human|partial|full|None)
    and **does not interpret** it here (no phase control, no session control).
    It simply forwards to the existing Orchestrator execution path while keeping
    the value as contextual information.
    """
    if authority_level is not None:
        try:
            constitution = getattr(orchestrator, "constitution", None)
            if isinstance(constitution, dict):
                constitution.setdefault("automation_policy", {})[
                    "authority_level"
                ] = authority_level
        except Exception:
            # Wiring must not fail the run if metadata attachment fails.
            pass

    stop_before_phases = stop_before_phases_for_authority_level(authority_level)

    # L1 reachability: always construct an execution context that includes authority_level.
    execution_context: dict[str, Any] = {
        "authority_level": authority_level,
        "stop_before_phases": list(stop_before_phases),
        "user_requirement": user_requirement,
        "language": language,
    }

    return _invoke_orchestrator(
        orchestrator=orchestrator,
        user_requirement=user_requirement,
        language=language,
        fast_lane=fast_lane,
        run_db_id=run_db_id,
        execution_context=execution_context,
        stop_before_phases=stop_before_phases,
    )


def stop_before_phases_for_authority_level(authority_level: str | None) -> list[str]:
    """
    Convert authority_level (human|partial|full|None) into a stop policy.

    - human: stop before every phase
    - partial: stop before "implementation" (requirements/planning/architecture run)
    - full: no stops
    - None: no stops (preserve existing behavior)
    """
    if authority_level is None:
        return []
    if authority_level == "human":
        return list(PHASES_ORDER)
    if authority_level == "partial":
        return ["implementation"]
    if authority_level == "full":
        return []
    # CLI validation should prevent this, but keep it safe.
    raise ValueError(f"Invalid authority_level: {authority_level}")


def _invoke_orchestrator(
    *,
    orchestrator: Any,
    user_requirement: str,
    language: str,
    fast_lane: bool,
    run_db_id: int | None,
    execution_context: dict[str, Any],
    stop_before_phases: list[str],
) -> Any:
    """
    Runner-side wrapper for Orchestrator invocation.

    core/orchestrator.py is frozen, so we cannot extend its public signatures.
    This wrapper exists solely to carry `execution_context` as L1 reachability
    evidence and to enable unit tests to observe the propagated context.
    """
    session_controller = _get_or_create_session_controller(orchestrator)
    _set_stop_policy(session_controller, stop_before_phases)

    run_id = getattr(session_controller, "session_id", None) or uuid.uuid4().hex

    # No gating -> preserve existing behavior (core flow)
    if not stop_before_phases:
        orchestrator.run_full_project(
            user_requirement=user_requirement,
            language=language,
            fast_lane=fast_lane,
            run_db_id=run_db_id,
        )
        result = {
            "status": "completed",
            "next_phase": None,
            "run_id": run_id,
            "execution_context": execution_context,
        }
        _persist_run_state(
            run_id=run_id,
            status="completed",
            authority_level=execution_context.get("authority_level"),
            next_phase=None,
            execution_context=execution_context,
            context_snapshot=None,
        )
        return result

    # Human/Partial gating: drive phases externally and stop at boundaries.
    context_factory = _default_context_factory
    context = context_factory(
        user_requirement=user_requirement,
        language=language,
        fast_lane=fast_lane,
        run_db_id=run_db_id,
    )

    for phase in PHASES_ORDER:
        # checkpoint before each phase so SessionController can enforce gating.
        try:
            session_controller.checkpoint(
                phase=phase,
                metadata={"execution_context": execution_context, "next_phase": phase},
            )
        except Exception:
            pass

        if phase in stop_before_phases:
            result = {
                "status": "paused",
                "next_phase": phase,
                "run_id": run_id,
                "execution_context": execution_context,
            }
            _persist_run_state(
                run_id=run_id,
                status="paused",
                authority_level=execution_context.get("authority_level"),
                next_phase=phase,
                execution_context=execution_context,
                context_snapshot=_extract_context_snapshot(context),
            )
            return result

        method_name = PHASE_TO_METHOD[phase]
        method = getattr(orchestrator, method_name, None)
        if not callable(method):
            raise AttributeError(f"Orchestrator does not provide required method: {method_name}")
        context = method(context)

    result = {
        "status": "completed",
        "next_phase": None,
        "run_id": run_id,
        "execution_context": execution_context,
    }
    _persist_run_state(
        run_id=run_id,
        status="completed",
        authority_level=execution_context.get("authority_level"),
        next_phase=None,
        execution_context=execution_context,
        context_snapshot=_extract_context_snapshot(context),
    )
    return result


_RESUME_ORCHESTRATOR: Any = None
_RESUME_ORCHESTRATOR_FACTORY: Callable[[], Any] | None = None


def set_resume_orchestrator(orchestrator: Any) -> None:
    """
    Set the orchestrator instance used by `resume_run(run_id)`.

    This keeps `resume_run(run_id)` signature minimal while allowing CLI to supply
    the orchestrator object it already constructs.
    """
    global _RESUME_ORCHESTRATOR
    _RESUME_ORCHESTRATOR = orchestrator


def set_resume_orchestrator_factory(factory: Callable[[], Any]) -> None:
    """
    Set a factory that creates a *new* orchestrator instance for each resume.

    CR-017 requires resume to reconstruct orchestrator (no instance reuse).
    This is the preferred injection mechanism for resume_run().
    """
    global _RESUME_ORCHESTRATOR_FACTORY
    _RESUME_ORCHESTRATOR_FACTORY = factory


def resume_run(
    run_id: str,
    *,
    orchestrator_factory: Callable[[], Any] | None = None,
) -> dict[str, Any]:
    """
    Contract Layer resume entrypoint (MVP).

    Fixed gate order (CR-019/020/022/023/017/018):
      1) load_state (untrusted)
      2) schema.validate
      3) integrity.verify
      4) require status==PAUSED
      5) lock.try_acquire (CONFLICT -> no state change)
      6) status: PAUSED -> RESUMING (store update; RMW)
      7) orchestrator rebuild (factory preferred; no reuse)
      8) start (dummy/optional)
      9) status: RESUMING -> RUNNING (store update; RMW)

    Args:
        run_id: Run ID to resume
        orchestrator_factory: Optional factory function that returns an Orchestrator instance.
            If None, falls back to global setter/factory (for CLI backward compatibility).
            API routes should always provide this argument.

    Returns:
        Dict with status, run_id, and optionally explainability
    """
    lock_acquired = False
    state: dict[str, Any]

    # 1) Load (untrusted)
    try:
        state = load_state(run_id)
    except FileNotFoundError:
        # Not found -> FAILED + explainability (create minimal state for auditability).
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
        except Exception:
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
        # 2) Schema gate (CR-020)
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

        # 3) Integrity gate (CR-022 / CR-NEXUS-026)
        ok, code, message = verify_integrity(state)
        if not ok:
            # Integrity verification failed - do not update RunState, release lock if acquired
            # Note: Lock is not acquired yet at this point (acquired after integrity gate)
            return {
                "status": "FAILED",
                "run_id": run_id,
                "explainability": build_explainability(
                    what=f"Resume failed: RunState integrity verification failed for run_id={run_id}",
                    why_code=code or "STATE_INTEGRITY_VIOLATION",
                    next_action="Abort this run_id and start a new run",
                ),
            }

        # 4) Status gate (CR-019)
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
        # Normalize legacy values (e.g. "paused") into the contract value.
        state["status"] = "PAUSED"

        # 5) Lock acquire (CR-023) - Mode B: lock is held during RUNNING
        # We acquire the lock first to check for conflicts
        ok, reason = try_acquire_run_lock(run_id)
        if not ok:
            # CONFLICT -> do not change state, do not mark FAILED
            return {
                "status": "CONFLICT",
                "run_id": run_id,
                "explainability": build_explainability(
                    what=f"Resume conflict: run_id={run_id} is already being resumed/executed",
                    why_code=reason or "CONFLICT",
                    next_action="wait/retry",
                ),
            }

        # Release immediately - we'll re-acquire with RunLockLease for Mode B
        release_run_lock(run_id)

        # 6) Transition: PAUSED -> RESUMING
        state["status"] = "RESUMING"
        update_state(state)

        # 7) Orchestrator rebuild (CR-017 / CR-NEXUS-030)
        # Use provided factory if available (API route), otherwise fall back to global (CLI backward compat)
        if orchestrator_factory is not None:
            orchestrator = orchestrator_factory()
        else:
            # Backward compatibility: Use global factory or setter (CLI path)
            orch_factory = _RESUME_ORCHESTRATOR_FACTORY
            if orch_factory is not None:
                orchestrator = orch_factory()
            else:
                # Backwards-compat fallback (legacy setter): may reuse instance.
                orchestrator = _RESUME_ORCHESTRATOR

            if orchestrator is None:
                raise RuntimeError(
                    "resume orchestrator is not set (call set_resume_orchestrator_factory or set_resume_orchestrator, "
                    "or provide orchestrator_factory argument)"
                )

        # 8) Mode B: Hold lock during RUNNING with refresh loop
        with RunLockLease(run_id) as lock_lease:
            # 9) Transition: RESUMING -> RUNNING
            state["status"] = "RUNNING"
            update_state(state)

            # 10) Start (dummy/optional)
            start_fn = getattr(orchestrator, "start", None)
            if callable(start_fn):
                try:
                    start_fn(run_id=run_id, state=state)
                except TypeError:
                    start_fn()

            # Check if refresh failed during execution (polling with delay to allow refresh loop to detect failure)
            # Poll for at least 2x refresh_interval to ensure we catch refresh failures
            import time

            # Get refresh interval for polling duration
            from .run_lock import _get_lock_refresh_seconds

            refresh_interval = float(_get_lock_refresh_seconds())
            max_poll_time = refresh_interval * 2.5  # Poll for 2.5x refresh interval
            poll_delay = min(0.1, refresh_interval / 5)  # Poll 5 times per refresh interval
            max_polls = int(max_poll_time / poll_delay) + 1

            for _ in range(max_polls):
                if lock_lease.is_refresh_failed():
                    # Refresh failure -> safe stop (ABORTED)
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
                time.sleep(poll_delay)  # Small delay to allow refresh loop to run

            # Normal completion (lock released automatically by context manager)
            return {
                "status": "RUNNING",
                "run_id": run_id,
            }

    except Exception as e:
        # Exception -> FAILED + last_error + explainability
        try:
            state["status"] = "FAILED"
            state["last_error"] = {
                "code": "INTERNAL_ERROR",
                "message": str(e),
                "next_action": "Check logs and retry",
            }
            update_state(state)
        except Exception:
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


def _extract_context_snapshot(context: Any) -> dict[str, Any]:
    """
    Extract a JSON-serializable subset of orchestration context for resume.
    """
    snapshot: dict[str, Any] = {}
    for key in ("user_requirement", "language", "fast_lane", "run_db_id"):
        if hasattr(context, key):
            snapshot[key] = getattr(context, key)
    for key in ("specs", "plan", "architecture", "implementation", "testing", "review"):
        val = getattr(context, key, None)
        if isinstance(val, dict):
            snapshot[key] = val
    return snapshot


def _apply_context_snapshot(context: Any, snapshot: dict[str, Any]) -> None:
    for key, val in snapshot.items():
        try:
            setattr(context, key, val)
        except Exception:
            continue


def _persist_run_state(
    *,
    run_id: str,
    status: str,
    authority_level: str | None,
    next_phase: str | None,
    execution_context: dict[str, Any],
    context_snapshot: dict[str, Any] | None,
) -> None:
    # Persist contract-aligned statuses while keeping runner return values unchanged.
    status_map = {
        "paused": "PAUSED",
        "completed": "SUCCEEDED",
    }
    persisted_status = status_map.get(status, status)
    state: dict[str, Any] = {
        "schema_version": "1.0",
        "run_id": run_id,
        "status": persisted_status,
        "authority_level": authority_level,
        "next_phase": next_phase,
        "execution_context": execution_context,
    }
    if context_snapshot is not None:
        state["context_snapshot"] = context_snapshot
    save_state(state)


def _get_or_create_session_controller(orchestrator: Any) -> Any:
    """
    Attach a SessionController to the orchestrator instance if missing.

    core/orchestrator.py is frozen, so we only set the existing attribute.
    """
    sc = getattr(orchestrator, "session_controller", None)
    if sc is not None:
        return sc

    try:
        from nexuscore.core.session_control import SessionController  # local import
    except Exception:
        return None

    project_path = getattr(orchestrator, "project_path", None)
    root_dir = ".nexus/sessions"
    if isinstance(project_path, str) and project_path:
        import os

        root_dir = os.path.join(project_path, ".nexus", "sessions")

    sc = SessionController(session_id=uuid.uuid4().hex, root_dir=root_dir)
    try:
        orchestrator.session_controller = sc
    except Exception:
        pass
    return sc


def _set_stop_policy(session_controller: Any, stop_before_phases: list[str]) -> None:
    if session_controller is None:
        return
    if hasattr(session_controller, "set_stop_before_phases"):
        try:
            session_controller.set_stop_before_phases(list(stop_before_phases))
            return
        except Exception:
            return
    # Fallback: attach attribute (best-effort).
    try:
        session_controller.stop_before_phases = list(stop_before_phases)
    except Exception:
        pass
