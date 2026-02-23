"""
run_state_schema_validator.py

CR-020 (RunState JSON Schema Contract) minimal validator.

This module is intentionally lightweight and side-effect free.
"""

from __future__ import annotations

from typing import Any


def validate_run_state(state: dict[str, Any]) -> tuple[bool, str | None, str | None]:
    """
    Validate RunState shape with minimal checks required by CR-020 MVP.

    Returns:
      (ok, code, message)
    """
    required_keys = ("schema_version", "run_id", "status", "authority_level", "updated_at")
    missing = [k for k in required_keys if k not in state]
    if missing:
        return False, "SCHEMA_MISSING_FIELD", f"Missing required field(s): {missing}"

    run_id = state.get("run_id")
    if not isinstance(run_id, str) or not run_id:
        return False, "SCHEMA_INVALID_RUN_ID", "run_id must be a non-empty string"

    status = state.get("status")
    if not isinstance(status, str) or not status:
        return False, "SCHEMA_INVALID_STATUS", "status must be a non-empty string"

    # CR-020 minimal consistency constraint:
    # status == "PAUSED" -> next_phase must not be null.
    if status == "PAUSED":
        if state.get("next_phase") is None:
            return (
                False,
                "SCHEMA_PAUSED_NEXT_PHASE_REQUIRED",
                "next_phase must be set when status=PAUSED",
            )

    # Unknown fields are allowed by design (Forward compatibility).
    return True, None, None
