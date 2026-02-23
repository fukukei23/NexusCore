"""
explainability.py

CR-018 (Resume Failure Explainability Contract) MVP helper.
"""

from __future__ import annotations

from typing import Any


def build_explainability(
    what: str,
    why_code: str,
    next_action: str,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Build a minimal explainability projection.

    Required keys: what / why / next_action
    """
    payload: dict[str, Any] = {
        "what": what,
        "why": why_code,
        "next_action": next_action,
    }
    if details is not None:
        payload["details"] = details
    return payload
