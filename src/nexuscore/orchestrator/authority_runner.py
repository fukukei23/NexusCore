from __future__ import annotations

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

from ._authority_runner_helpers.context import default_context_factory
from ._authority_runner_helpers.lock_lease import RunLockLease  # noqa: F401
from ._authority_runner_helpers.phase_logging import log_phase_done, log_phase_pause, log_phase_start
from ._authority_runner_helpers.resume import (  # noqa: F401
    _execute_remaining_phases,
    resume_run,
    set_resume_orchestrator,
    set_resume_orchestrator_factory,
)
from ._authority_runner_helpers.state import (
    apply_context_snapshot,
    extract_context_snapshot,
    get_or_create_session_controller,
    persist_run_state,
    set_stop_policy,
)

# Backward-compatible re-exports for tests and external callers
from .run_state_store import load_state, save_state, update_state  # noqa: F401


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

    factory = context_factory or default_context_factory
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
        log_phase_start(phase, phases)
        t0 = time.monotonic()
        context = method(context)
        log_phase_done(phase, t0)
        if _HAS_TQDM and hasattr(phase_iter, "set_postfix"):
            phase_iter.set_postfix_str(phase)  # type: ignore[union-attr]

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
        except Exception:  # noqa: BLE001 — 外部dictの安全な更新（フォールバック）
            pass

    stop_before = stop_before_phases_for_authority_level(authority_level)

    execution_context: dict[str, Any] = {
        "authority_level": authority_level,
        "stop_before_phases": list(stop_before),
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
        stop_before_phases=stop_before,
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

    context = _default_context_factory(
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
        except Exception:  # noqa: BLE001 — チェックポイント失敗は処理を止めない
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
            phase_iter.set_postfix_str(phase)  # type: ignore[union-attr]

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


# -- Backward-compatible aliases for tests that patch private names --
_default_context_factory = default_context_factory
_extract_context_snapshot = extract_context_snapshot
_apply_context_snapshot = apply_context_snapshot
_get_or_create_session_controller = get_or_create_session_controller
_set_stop_policy = set_stop_policy
_persist_run_state = persist_run_state
_log_phase_start = log_phase_start
_log_phase_done = log_phase_done
_log_phase_pause = log_phase_pause
