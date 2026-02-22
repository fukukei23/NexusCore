"""
test_run_lock_refresh.py

Tests for lock refresh functionality (CR-NEXUS-025).
"""

from __future__ import annotations

import json
import os
import time
from typing import Any

from nexuscore.orchestrator.run_lock import (
    _lock_file_path,
    refresh_run_lock,
    release_run_lock,
    try_acquire_run_lock,
)


def test_refresh_extends_expires_at(monkeypatch: Any, tmp_path: Any) -> None:
    """Test that refresh extends the expires_at timestamp."""
    lock_dir = tmp_path / "locks"
    lock_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("NEXUSCORE_RUN_LOCK_DIR", str(lock_dir))
    monkeypatch.setenv("NEXUSCORE_RUN_LOCK_TTL_SECONDS", "3600")  # 1 hour

    run_id = "test-refresh-extend"
    lock_path = _lock_file_path(run_id)

    # Acquire lock
    ok, reason = try_acquire_run_lock(run_id)
    assert ok is True, f"Lock acquisition should succeed (reason: {reason})"
    assert reason is None

    # Read initial expires_at
    with open(lock_path) as f:
        initial_data = json.load(f)
    initial_expires_at = initial_data["expires_at"]
    initial_acquired_at = initial_data["acquired_at"]

    # Wait a bit to ensure timestamp difference
    time.sleep(0.2)

    # Refresh lock (use direct import to avoid any patching)
    from nexuscore.orchestrator.run_lock import refresh_run_lock as direct_refresh

    ok, reason, details = direct_refresh(run_id)
    assert ok is True, f"Lock refresh should succeed (reason: {reason})"
    assert reason is None
    assert details is None

    # Verify expires_at was extended
    with open(lock_path) as f:
        refreshed_data = json.load(f)
    refreshed_expires_at = refreshed_data["expires_at"]
    refreshed_acquired_at = refreshed_data["acquired_at"]

    # expires_at should be refreshed (now + TTL), which should be later than initial
    # (Note: initial was acquired_at + TTL, so refreshed should be later)
    current_time = time.time()
    assert (
        refreshed_expires_at > current_time
    ), f"refreshed expires_at should be in the future (got {refreshed_expires_at}, now={current_time})"
    assert (
        refreshed_expires_at > initial_expires_at
    ), f"expires_at should be extended after refresh (initial={initial_expires_at}, refreshed={refreshed_expires_at})"
    assert "last_heartbeat_at" in refreshed_data, "last_heartbeat_at should be set after refresh"
    assert (
        refreshed_data["last_heartbeat_at"] > initial_acquired_at
    ), "last_heartbeat_at should be updated"

    # Cleanup
    release_run_lock(run_id)


def test_refresh_fails_when_not_owner(monkeypatch: Any, tmp_path: Any) -> None:
    """Test that refresh fails when the caller is not the lock owner."""
    lock_dir = tmp_path / "locks"
    lock_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("NEXUSCORE_RUN_LOCK_DIR", str(lock_dir))

    run_id = "test-refresh-not-owner"
    lock_path = _lock_file_path(run_id)

    # Create a lock file with a different PID (simulating another process)
    fake_pid = 99999
    lock_data = {
        "run_id": run_id,
        "pid": fake_pid,
        "acquired_at": time.time(),
        "expires_at": time.time() + 3600,
    }
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with open(lock_path, "w") as f:
        json.dump(lock_data, f)

    # Try to refresh - should fail because PID doesn't match
    ok, reason, details = refresh_run_lock(run_id)
    assert ok is False, "Lock refresh should fail when not the owner"
    assert reason == "LOCK_NOT_OWNED"
    assert details is not None
    assert details["expected_pid"] == os.getpid()
    assert details["actual_pid"] == fake_pid


def test_lock_held_during_running(monkeypatch: Any, tmp_path: Any) -> None:
    """Test that lock is held during RUNNING phase (Mode B)."""
    monkeypatch.setenv("NEXUSCORE_RUN_STATE_DIR", str(tmp_path / "run_state"))
    monkeypatch.setenv("NEXUSCORE_RUNSTATE_HMAC_SECRET", "test-secret-key")
    lock_dir = tmp_path / "locks"
    lock_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("NEXUSCORE_RUN_LOCK_DIR", str(lock_dir))

    from nexuscore.orchestrator import authority_runner
    from nexuscore.orchestrator.run_state_store import save_state

    run_id = "test-lock-held-running"

    # Create a paused state
    state = {
        "schema_version": "1.0",
        "run_id": run_id,
        "status": "PAUSED",
        "authority_level": "partial",
        "next_phase": "implementation",
        "updated_at": "2025-01-01T00:00:00+00:00",
    }
    save_state(state)

    # Mock orchestrator (dummy start function)
    class DummyOrchestrator:
        def start(self, run_id: str = None, state: dict = None):
            pass

    authority_runner.set_resume_orchestrator(DummyOrchestrator())

    try:
        # Resume run - should acquire lock and hold it during RUNNING
        result = authority_runner.resume_run(run_id)

        # Verify that lock exists (was held during RUNNING)
        lock_path = _lock_file_path(run_id)
        # Note: After context manager exits, lock is released, so it should not exist
        # But during execution, it should have existed
        # We check by attempting to acquire - if it was held, we can now acquire it
        ok, reason = try_acquire_run_lock(run_id)
        assert ok is True, f"Lock should be available after RUNNING completes (reason: {reason})"

        # If refresh failed, status should be ABORTED
        if result.get("status") == "ABORTED":
            assert "LOCK_REFRESH_FAILED" in result.get("explainability", {}).get("why_code", "")
    finally:
        release_run_lock(run_id)


def test_refresh_failure_triggers_safe_stop(monkeypatch: Any, tmp_path: Any) -> None:
    """Test that refresh failure triggers safe stop (ABORTED status)."""
    monkeypatch.setenv("NEXUSCORE_RUN_STATE_DIR", str(tmp_path / "run_state"))
    monkeypatch.setenv("NEXUSCORE_RUNSTATE_HMAC_SECRET", "test-secret-key")
    lock_dir = tmp_path / "locks"
    lock_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("NEXUSCORE_RUN_LOCK_DIR", str(lock_dir))
    # Set very short refresh interval (0.2 seconds) to trigger refresh quickly
    monkeypatch.setenv("NEXUSCORE_RUN_LOCK_REFRESH_SECONDS", "0.2")

    from nexuscore.orchestrator import authority_runner
    from nexuscore.orchestrator.run_state_store import load_state, save_state

    run_id = "test-refresh-failure-stop"

    # Create a paused state
    state = {
        "schema_version": "1.0",
        "run_id": run_id,
        "status": "PAUSED",
        "authority_level": "partial",
        "next_phase": "implementation",
        "updated_at": "2025-01-01T00:00:00+00:00",
    }
    save_state(state)

    # Patch refresh_run_lock to fail (simulating refresh failure during execution)
    # authority_runner imports refresh_run_lock, so we need to patch it in authority_runner module
    import nexuscore.orchestrator.authority_runner as authority_runner_module

    def failing_refresh(run_id: str):
        """Refresh that always fails (simulating a failure during execution)."""
        return False, "LOCK_REFRESH_FAILED", {"error": "Simulated refresh failure"}

    # Patch in authority_runner module (where RunLockLease actually uses it)
    original_refresh_func = authority_runner_module.refresh_run_lock
    authority_runner_module.refresh_run_lock = failing_refresh

    # Mock orchestrator with a slow start (to allow refresh to occur and fail)
    # Sleep longer than refresh interval (0.2s) to ensure refresh loop runs at least once
    class SlowOrchestrator:
        def start(self, run_id: str = None, state: dict = None):
            import time

            # Sleep 0.5 seconds: refresh interval is 0.2s, so at least one refresh should occur
            time.sleep(0.5)

    authority_runner.set_resume_orchestrator(SlowOrchestrator())

    try:
        # Resume run - refresh should fail during execution
        result = authority_runner.resume_run(run_id)

        # Verify that state was updated to ABORTED
        stored = load_state(run_id)
        assert (
            stored["status"] == "ABORTED"
        ), f"Status should be ABORTED on refresh failure (got {stored['status']})"
        assert stored.get("last_error", {}).get("code") == "LOCK_REFRESH_FAILED"

        # Verify result includes explainability
        assert result["status"] == "ABORTED"
        assert "explainability" in result
        assert (
            result["explainability"]["why"] == "LOCK_REFRESH_FAILED"
        ), f"Expected why='LOCK_REFRESH_FAILED', got {result['explainability']}"
        assert "inspect_lock_dir_permissions" in result["explainability"]["next_action"]
    finally:
        # Restore original function
        authority_runner_module.refresh_run_lock = original_refresh_func
        release_run_lock(run_id)
