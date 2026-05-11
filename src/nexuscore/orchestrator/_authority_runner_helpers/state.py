"""
State persistence and session management helpers for authority_runner.

Extracted from authority_runner.py to reduce the main module size and
improve testability of state management logic.
"""

from __future__ import annotations

import os
import uuid
from typing import Any

from ..run_state_store import save_state


def extract_context_snapshot(context: Any) -> dict[str, Any]:
    """Snapshot the portable fields from an orchestrator context."""
    snapshot: dict[str, Any] = {}
    for key in ("user_requirement", "language", "fast_lane", "run_db_id"):
        if hasattr(context, key):
            snapshot[key] = getattr(context, key)
    for key in ("specs", "plan", "architecture", "implementation", "testing", "review"):
        val = getattr(context, key, None)
        if isinstance(val, dict):
            snapshot[key] = val
    return snapshot


def apply_context_snapshot(context: Any, snapshot: dict[str, Any]) -> None:
    """Restore a previously captured snapshot onto a context object."""
    for key, val in snapshot.items():
        try:
            setattr(context, key, val)
        except Exception:
            continue


def persist_run_state(
    *,
    run_id: str,
    status: str,
    authority_level: str | None,
    next_phase: str | None,
    execution_context: dict[str, Any],
    context_snapshot: dict[str, Any] | None,
) -> None:
    """Save a run-state record for pause/resume support."""
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


def get_or_create_session_controller(orchestrator: Any) -> Any:
    """Return the orchestrator's SessionController, creating one if absent."""
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


def set_stop_policy(session_controller: Any, stop_before_phases: list[str]) -> None:
    """Configure the stop-before-phases policy on a SessionController."""
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
