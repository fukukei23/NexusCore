from __future__ import annotations

from typing import Any


def build_explainability(
    what: str,
    why_code: str,
    next_action: str,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a structured explainability projection dict.

    Args:
        what: Short description of what happened (e.g. "phase completed").
        why_code: Machine-readable reason code (e.g. "TESTS_PASSED").
        next_action: Suggested next step (e.g. "proceed to next phase").
        details: Optional arbitrary metadata to attach.

    Returns:
        Dict with keys: what, why, next_action, and optionally details.
    """
    payload: dict[str, Any] = {
        "what": what,
        "why": why_code,
        "next_action": next_action,
    }
    if details is not None:
        payload["details"] = details
    return payload
