"""
explainability.py

CR-018 (Resume Failure Explainability Contract) MVP helper.
"""

from __future__ import annotations

from typing import Any, Dict, Optional


def build_explainability(
    what: str,
    why_code: str,
    next_action: str,
    details: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Build a minimal explainability projection.

    Required keys: what / why / next_action
    """
    payload: Dict[str, Any] = {
        "what": what,
        "why": why_code,
        "next_action": next_action,
    }
    if details is not None:
        payload["details"] = details
    return payload


