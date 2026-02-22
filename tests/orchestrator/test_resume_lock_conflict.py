"""
test_resume_lock_conflict.py

Test that resume_run() handles lock conflicts correctly (CONFLICT status, no RunState update).
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict

import pytest

from nexuscore.orchestrator import authority_runner
from nexuscore.orchestrator.run_lock import _lock_file_path, _safe_run_id
from nexuscore.orchestrator.run_state_store import load_state, save_state


def test_resume_lock_conflict_does_not_fail_or_mutate_state(monkeypatch: Any, tmp_path: Any) -> None:
    """Test that resume_run() returns CONFLICT and does not update RunState when lock is held."""
    monkeypatch.setenv("NEXUSCORE_RUN_STATE_DIR", str(tmp_path / "run_state"))
    monkeypatch.setenv("NEXUSCORE_RUNSTATE_HMAC_SECRET", "test-secret-key")
    lock_dir = tmp_path / "locks"
    lock_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("NEXUSCORE_RUN_LOCK_DIR", str(lock_dir))

    run_id = "run-lock-conflict"
    state: Dict[str, Any] = {
        "schema_version": "1.0",
        "run_id": run_id,
        "status": "PAUSED",
        "authority_level": "partial",
        "next_phase": "implementation",
        "updated_at": "2025-01-01T00:00:00+00:00",
        "unknown_field": {"keep": True},
    }
    save_state(state)

    # Create a valid lock file before calling resume_run (simulating another process holding the lock)
    lock_path = _lock_file_path(run_id)
    lock_data = {
        "run_id": run_id,
        "pid": 99999,  # Different PID
        "acquired_at": time.time(),
        "expires_at": time.time() + 3600,  # Valid for 1 hour
    }
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with open(lock_path, "w") as f:
        json.dump(lock_data, f)

    # Call resume_run - should return CONFLICT
    result = authority_runner.resume_run(run_id)

    # Primary assertions (must pass regardless of return format):
    # 1) RunState is unchanged (status still PAUSED, unknown_field preserved)
    stored = load_state(run_id)
    assert stored["status"] == "PAUSED", "RunState status must not change on CONFLICT"
    assert stored["unknown_field"] == {"keep": True}, "RunState unknown fields must be preserved"

    # 2) CONFLICT-equivalent reason/why_code is present
    assert "explainability" in result, "Result must include explainability"
    explain = result["explainability"]
    assert "why_code" in explain or "why" in explain or "reason" in explain, "explainability must include why_code/why/reason"
    why_code = explain.get("why_code") or explain.get("why") or explain.get("reason")
    assert "CONFLICT" in str(why_code).upper() or "LOCK" in str(why_code).upper(), f"why_code must indicate CONFLICT (got {why_code})"

    # Secondary assertion (optional, format-dependent):
    if "status" in result:
        assert result["status"] == "CONFLICT", "Result status should be CONFLICT"

    assert result["run_id"] == run_id, "Result must include run_id"
    assert explain.get("next_action") in ["wait/retry", "retry", "wait"], "next_action should suggest wait/retry"

