"""
Shared helper utilities for LLM routing and provider modules.

The legacy ``llm_router`` module defined a number of helper functions that were
also consumed by individual provider implementations.  Splitting them into this
module lets both layers import the same helpers without introducing circular
dependencies.
"""

from __future__ import annotations

import json
import os
from typing import Any

from nexuscore.llm.runtime import CONFIG

DEFAULT_STUB_CONTENT: dict[str, Any] = {
    "summary": "Stubbed response: real LLM call was skipped or unavailable.",
    "plan": [
        {"step": "analyze_requirement", "owner": "PlannerAgent", "status": "pending"},
        {
            "step": "implement_core_logic",
            "owner": "CoderAgent",
            "status": "blocked_stub",
        },
        {
            "step": "write_tests_and_docs",
            "owner": "TesterAgent",
            "status": "blocked_stub",
        },
    ],
}


def normalize_model(name: str) -> str:
    """Normalize model aliases (vendor prefixes, -latest suffix etc.)."""
    if not name:
        return "local-mock"
    name = name.strip()
    if ":" in name:
        vendor, model = name.split(":", 1)
        name = f"{vendor.strip()}:{model.strip()}"
    replacements = {
        "gemini-2.5-flash-latest": "gemini-2.5-flash",
        "gemini-2.5-pro-latest": "gemini-2.5-pro",
        "kimi-k2-0711-preview": "kimi-k2-0711-preview",
        "kimi-k2-turbo-preview": "kimi-k2-turbo-preview",
    }
    return replacements.get(name, name)


def _env_flag(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _real_call_enabled(api_key: str | None) -> bool:
    """Determine if real LLM calls should execute."""
    dry_run = _env_flag("LLM_DRY_RUN", CONFIG.dry_run)
    real_calls = _env_flag("NEXUS_REAL_CALLS", CONFIG.real_calls_enabled)
    if dry_run:
        return False
    return bool(api_key) and real_calls


def _stub_response(model_name: str, mode: str, reason: str, as_json: bool) -> str:
    """Create a consistent stub response payload."""
    payload = {
        "model": model_name,
        "mode": mode,
        "preview": reason,
        "content": DEFAULT_STUB_CONTENT,
    }
    return json.dumps(payload, ensure_ascii=False) if as_json else reason


def _strip_jsonish(text: str) -> str:
    """
    Remove Markdown fences / prefixes that providers often wrap JSON responses
    with so that downstream JSON decoding is more robust.
    """
    if not text:
        return text
    t = text.strip()
    if t.startswith("```"):
        t = t.strip("`")
        if t.lower().startswith("json"):
            t = t[4:].strip()
    if "{" in t:
        t = t[t.index("{") :]
    if "}" in t:
        t = t[: t.rindex("}") + 1]
    return t


__all__ = [
    "DEFAULT_STUB_CONTENT",
    "normalize_model",
    "_env_flag",
    "_real_call_enabled",
    "_stub_response",
    "_strip_jsonish",
]
