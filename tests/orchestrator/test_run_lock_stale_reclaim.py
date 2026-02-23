"""
test_run_lock_stale_reclaim.py

Test stale lock recovery (expired locks are moved to *.stale.<timestamp> and re-acquisition succeeds).
"""

from __future__ import annotations

import json
import time
from typing import Any

from nexuscore.orchestrator.run_lock import _lock_file_path, release_run_lock, try_acquire_run_lock


def test_stale_lock_reclaim(monkeypatch: Any, tmp_path: Any) -> None:
    """Test that expired locks are reclaimed (moved to *.stale.<ts>) and re-acquisition succeeds."""
    lock_dir = tmp_path / "locks"
    lock_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("NEXUSCORE_RUN_LOCK_DIR", str(lock_dir))

    run_id = "run-stale-test"
    lock_path = _lock_file_path(run_id)

    # Create a stale lock file (expires_at in the past)
    stale_lock_data = {
        "run_id": run_id,
        "pid": 99999,
        "acquired_at": time.time() - 7200,  # 2 hours ago
        "expires_at": time.time() - 3600,  # 1 hour ago (expired)
    }
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with open(lock_path, "w") as f:
        json.dump(stale_lock_data, f)

    # Try to acquire lock - should succeed after reclaiming stale lock
    ok, reason = try_acquire_run_lock(run_id)
    assert ok is True, f"Lock acquisition should succeed after stale reclaim (reason: {reason})"
    assert reason is None, "Reason should be None on success"

    # Verify the old lock file is moved to *.stale.<timestamp>
    stale_files = list(lock_path.parent.glob(f"{lock_path.name}.stale.*"))
    assert len(stale_files) == 1, f"Expected exactly one stale file, got {len(stale_files)}"

    # Verify a new lock file exists
    assert lock_path.exists(), "New lock file should exist after re-acquisition"

    # Verify the new lock file has correct content (run_id preserved, valid expires_at)
    with open(lock_path) as f:
        new_lock_data = json.load(f)
    assert new_lock_data["run_id"] == run_id, "Original run_id must be preserved in lock file"
    assert new_lock_data["expires_at"] > time.time(), "New lock expires_at must be in the future"

    # Cleanup
    release_run_lock(run_id)


def test_stale_lock_reclaim_with_missing_expires_at(monkeypatch: Any, tmp_path: Any) -> None:
    """Test that locks with missing expires_at are treated as stale."""
    lock_dir = tmp_path / "locks"
    lock_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("NEXUSCORE_RUN_LOCK_DIR", str(lock_dir))

    run_id = "run-stale-missing-expires"
    lock_path = _lock_file_path(run_id)

    # Create a lock file without expires_at (should be treated as stale)
    invalid_lock_data = {
        "run_id": run_id,
        "pid": 99999,
        "acquired_at": time.time(),
        # Missing expires_at
    }
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with open(lock_path, "w") as f:
        json.dump(invalid_lock_data, f)

    # Try to acquire lock - should succeed after reclaiming
    ok, reason = try_acquire_run_lock(run_id)
    assert (
        ok is True
    ), "Lock acquisition should succeed when expires_at is missing (treated as stale)"
    assert reason is None

    # Cleanup
    release_run_lock(run_id)


def test_lock_conflict_when_not_stale(monkeypatch: Any, tmp_path: Any) -> None:
    """Test that valid (non-stale) locks cause CONFLICT."""
    lock_dir = tmp_path / "locks"
    lock_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("NEXUSCORE_RUN_LOCK_DIR", str(lock_dir))

    run_id = "run-valid-lock"
    lock_path = _lock_file_path(run_id)

    # Create a valid lock file (expires_at in the future)
    valid_lock_data = {
        "run_id": run_id,
        "pid": 99999,
        "acquired_at": time.time(),
        "expires_at": time.time() + 3600,  # Valid for 1 hour
    }
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with open(lock_path, "w") as f:
        json.dump(valid_lock_data, f)

    # Try to acquire lock - should fail with CONFLICT
    ok, reason = try_acquire_run_lock(run_id)
    assert ok is False, "Lock acquisition should fail when valid lock exists"
    assert reason == "CONFLICT", f"Reason should be CONFLICT (got {reason})"


def test_safe_run_id_filesystem_injection_prevention() -> None:
    """Test that safe_run_id prevents filesystem injection (handles /, :, etc.)."""
    from nexuscore.orchestrator.run_lock import _safe_run_id

    # Test various problematic run_id values
    problematic_ids = [
        "run/with/slashes",
        "run:with:colons",
        "run\\with\\backslashes",
        "run..with..dots",
        "run with spaces",
        "../../etc/passwd",
    ]

    for run_id in problematic_ids:
        safe_id = _safe_run_id(run_id)
        # safe_id should be a hex string (sha256 produces 64 hex chars)
        assert len(safe_id) == 64, f"safe_run_id should be 64 hex chars (got {len(safe_id)})"
        assert all(
            c in "0123456789abcdef" for c in safe_id
        ), f"safe_run_id should be hex (got {safe_id})"
        # Should not contain problematic chars
        assert "/" not in safe_id
        assert ":" not in safe_id
        assert "\\" not in safe_id
        assert ".." not in safe_id
        assert " " not in safe_id
