"""
orchestrator/authority_runner.py

Authority-level execution controller for NexusCore Orchestrator.

This module intentionally avoids importing frozen `nexuscore.core.orchestrator`
at import time. It controls execution by calling existing public phase methods
on an orchestrator instance (duck-typed).
"""

from __future__ import annotations

import logging
import os
import time
import uuid
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any

try:
    from tqdm import tqdm

    _HAS_TQDM = True
except ImportError:
    _HAS_TQDM = False

from .constants import AuthorityLevel
from .explainability import build_explainability  # noqa: F401
from .run_state_store import save_state

from ._authority_runner_helpers.lock_lease import RunLockLease  # noqa: F401
from ._authority_runner_helpers.resume import (  # noqa: F401
    _execute_remaining_phases,
    resume_run,
    set_resume_orchestrator,
    set_resume_orchestrator_factory,
)

# Backward-compatible re-exports for tests and external callers
from .run_state_store import load_state, update_state  # noqa: F401


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
    if authority_level == AuthorityLevel.HUMAN_CONTROLLED:
        return ("requirements",)
    if authority_level == AuthorityLevel.PARTIALLY_AUTONOMOUS:
        return ("requirements", "planning", "architecture")
    if authority_level == AuthorityLevel.FULLY_AUTONOMOUS:
        return PHASES_ORDER
    raise ValueError(f"Invalid authority level: {authority_level}")


@dataclass(frozen=True)
class RunnerConfig:
    authority_level: int
    allowed_phases: Sequence[str] | None = None


def _default_context_factory(
    *,
    user_requirement: str,
    language: str,
    fast_lane: bool,
    run_db_id: int | None,
) -> Any:
    try:
        from nexuscore.core.orchestrator_models import OrchestratorContext

        return OrchestratorContext(
            task_id=uuid.uuid4().hex,
            user_requirement=user_requirement,
            language=language,
            fast_lane=fast_lane,
            run_db_id=run_db_id,
        )
    except Exception:
        @dataclass
        class _FallbackContext:
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

    phase_iter = tqdm(phases, desc="NexusCore phases", unit="phase") if _HAS_TQDM else phases
    for phase in phase_iter:
        method_name = PHASE_TO_METHOD[phase]
        method = getattr(orchestrator, method_name, None)
        if not callable(method):
            raise AttributeError(f"Orchestrator does not provide required method: {method_name}")
        _log_phase_start(phase, phases)
        t0 = time.monotonic()
        context = method(context)
        _log_phase_done(phase, t0)
        if _HAS_TQDM and hasattr(phase_iter, "set_postfix"):
            phase_iter.set_postfix_str(phase)

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
    if authority_level is not None:
        try:
            constitution = getattr(orchestrator, "constitution", None)
            if isinstance(constitution, dict):
                constitution.setdefault("automation_policy", {})[
                    "authority_level"
                ] = authority_level
        except Exception:
            pass

    stop_before_phases = stop_before_phases_for_authority_level(authority_level)

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
    if authority_level is None:
        return []
    if authority_level == "human":
        return list(PHASES_ORDER)
    if authority_level == "partial":
        return ["implementation"]
    if authority_level == "full":
        return []
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
    session_controller = _get_or_create_session_controller(orchestrator)
    _set_stop_policy(session_controller, stop_before_phases)

    run_id = getattr(session_controller, "session_id", None) or uuid.uuid4().hex

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

    context_factory = _default_context_factory
    context = context_factory(
        user_requirement=user_requirement,
        language=language,
        fast_lane=fast_lane,
        run_db_id=run_db_id,
    )

    phase_iter = tqdm(PHASES_ORDER, desc="NexusCore phases", unit="phase") if _HAS_TQDM else PHASES_ORDER
    for phase in phase_iter:
        try:
            session_controller.checkpoint(
                phase=phase,
                metadata={"execution_context": execution_context, "next_phase": phase},
            )
        except Exception:
            pass

        if phase in stop_before_phases:
            _log_phase_pause(phase)
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
        _log_phase_start(phase, PHASES_ORDER)
        t0 = time.monotonic()
        context = method(context)
        _log_phase_done(phase, t0)
        if _HAS_TQDM and hasattr(phase_iter, "set_postfix"):
            phase_iter.set_postfix_str(phase)

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


def _extract_context_snapshot(context: Any) -> dict[str, Any]:
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
    sc = getattr(orchestrator, "session_controller", None)
    if sc is not None:
        return sc

    try:
        from nexuscore.core.session_control import SessionController
    except Exception:
        return None

    project_path = getattr(orchestrator, "project_path", None)
    root_dir = ".nexus/sessions"
    if isinstance(project_path, str) and project_path:
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
    try:
        session_controller.stop_before_phases = list(stop_before_phases)
    except Exception:
        pass


_phase_logger = logging.getLogger(__name__)


def _log_phase_start(phase: str, all_phases: Sequence[str]) -> None:
    idx = list(all_phases).index(phase) + 1 if phase in all_phases else "?"
    total = len(all_phases)
    _phase_logger.info("[%s/%s] Phase: %s — starting", idx, total, phase)


def _log_phase_done(phase: str, start_time: float) -> None:
    elapsed = time.monotonic() - start_time
    _phase_logger.info("Phase: %s — done (%.1fs)", phase, elapsed)


def _log_phase_pause(phase: str) -> None:
    _phase_logger.info("Phase: %s — pausing before execution (stop_before)", phase)
