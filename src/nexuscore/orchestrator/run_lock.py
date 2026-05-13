from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any


def _get_lock_dir() -> Path:
    """Get the lock directory from env or default."""
    lock_dir = os.getenv("NEXUSCORE_RUN_LOCK_DIR")
    if lock_dir:
        return Path(lock_dir)
    # Fallback: use run_state_dir/locks if available, else /tmp
    run_state_dir = os.getenv("NEXUSCORE_RUN_STATE_DIR")
    if run_state_dir:
        return Path(run_state_dir) / "locks"
    return Path("/tmp/nexuscore_locks")


def _get_lock_ttl_seconds() -> int:
    """Get lock TTL from env or default (3600 seconds = 1 hour)."""
    ttl_str = os.getenv("NEXUSCORE_RUN_LOCK_TTL_SECONDS")
    if ttl_str:
        try:
            return int(ttl_str)
        except ValueError:
            pass
    return 3600


def _get_lock_refresh_seconds() -> int:
    """Get lock refresh interval from env or default (ttl // 3, minimum 5 seconds)."""
    refresh_str = os.getenv("NEXUSCORE_RUN_LOCK_REFRESH_SECONDS")
    if refresh_str:
        try:
            refresh = int(refresh_str)
            return max(5, refresh)  # Minimum 5 seconds
        except ValueError:
            pass
    # Default: ttl // 3, minimum 5 seconds
    ttl = _get_lock_ttl_seconds()
    return max(5, ttl // 3)


def _safe_run_id(run_id: str) -> str:
    """Convert run_id to a safe filesystem name (sha256 hex digest)."""
    return hashlib.sha256(run_id.encode("utf-8")).hexdigest()


def _lock_file_path(run_id: str) -> Path:
    """Get the lock file path for a given run_id."""
    lock_dir = _get_lock_dir()
    lock_dir.mkdir(parents=True, exist_ok=True)
    safe_id = _safe_run_id(run_id)
    return lock_dir / f"{safe_id}.lock"


def _is_lock_stale(lock_path: Path) -> bool:
    """Check if a lock file is stale (expires_at < now)."""
    try:
        with open(lock_path) as f:
            data = json.load(f)
        expires_at = data.get("expires_at")
        if not expires_at:
            return True  # Missing expires_at is considered stale
        return float(expires_at) < time.time()
    except (json.JSONDecodeError, FileNotFoundError, OSError, ValueError, KeyError):
        return True  # Corrupted or missing lock is considered stale


def _move_to_stale(lock_path: Path) -> None:
    """Move a stale lock file to *.stale.<timestamp>."""
    timestamp = int(time.time())
    stale_path = lock_path.parent / f"{lock_path.name}.stale.{timestamp}"
    try:
        lock_path.rename(stale_path)
    except (OSError, FileNotFoundError):
        # Race condition: file already removed or renamed by another process
        pass


def try_acquire_run_lock(run_id: str) -> tuple[bool, str | None]:
    """
    Attempt to acquire a filesystem lock for a given run_id.

    Returns:
      (ok, reason)
      - ok=True, reason=None when lock acquired successfully
      - ok=False, reason="CONFLICT" when lock is held by another process
      - ok=False, reason="INVALID_RUN_ID" when run_id is invalid
      - ok=False, reason=<other> for other errors
    """
    if not run_id or not isinstance(run_id, str) or not run_id.strip():
        return False, "INVALID_RUN_ID"

    lock_path = _lock_file_path(run_id)
    current_time = time.time()
    expires_at = current_time + _get_lock_ttl_seconds()

    # Check for stale lock and recover
    if lock_path.exists():
        if _is_lock_stale(lock_path):
            _move_to_stale(lock_path)
        else:
            # Lock exists and is not stale -> CONFLICT
            return False, "CONFLICT"

    # Try to create lock file with O_EXCL (atomic creation)
    lock_data = {
        "run_id": run_id,  # Original run_id preserved in JSON
        "pid": os.getpid(),
        "acquired_at": current_time,
        "expires_at": expires_at,
    }

    try:
        # Open with O_EXCL to ensure atomic creation
        fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
        try:
            # Write JSON (if this fails, we'll clean up below)
            json_str = json.dumps(lock_data, indent=2)
            os.write(fd, json_str.encode("utf-8"))
            os.fsync(fd)  # Ensure data is written to disk
        finally:
            os.close(fd)
        return True, None
    except FileExistsError:
        # Race condition: another process created the lock file
        # Check again if it's stale
        if lock_path.exists() and _is_lock_stale(lock_path):
            _move_to_stale(lock_path)
            # Retry once
            try:
                fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
                try:
                    json_str = json.dumps(lock_data, indent=2)
                    os.write(fd, json_str.encode("utf-8"))
                    os.fsync(fd)
                finally:
                    os.close(fd)
                return True, None
            except FileExistsError:
                return False, "CONFLICT"
        return False, "CONFLICT"
    except Exception as e:
        # Write failure or other error: clean up incomplete lock file
        try:
            if lock_path.exists():
                _move_to_stale(lock_path)
        except Exception:
            pass
        return False, f"LOCK_ERROR: {str(e)}"


def refresh_run_lock(run_id: str) -> tuple[bool, str | None, dict[str, Any] | None]:
    """
    Refresh the lock expiration time for a given run_id (owner verification required).

    Args:
        run_id: The run_id to refresh the lock for.

    Returns:
        (ok, reason, details)
        - ok=True, reason=None, details=None when lock refreshed successfully
        - ok=False, reason="LOCK_NOT_OWNED" when owner_id (pid) does not match
        - ok=False, reason="LOCK_REFRESH_FAILED" when write fails (details contains error info)
        - ok=False, reason="INVALID_RUN_ID" when run_id is invalid
        - ok=False, reason="LOCK_NOT_FOUND" when lock file does not exist
    """
    if not run_id or not isinstance(run_id, str) or not run_id.strip():
        return False, "INVALID_RUN_ID", None

    lock_path = _lock_file_path(run_id)
    current_pid = os.getpid()
    current_time = time.time()
    new_expires_at = current_time + _get_lock_ttl_seconds()

    # Read existing lock file
    try:
        if not lock_path.exists():
            return False, "LOCK_NOT_FOUND", None

        with open(lock_path) as f:
            lock_data = json.load(f)
    except (json.JSONDecodeError, OSError, FileNotFoundError) as e:
        return False, "LOCK_REFRESH_FAILED", {"error": str(e), "error_type": type(e).__name__}

    # Verify ownership (pid must match)
    owner_pid = lock_data.get("pid")
    if owner_pid != current_pid:
        return False, "LOCK_NOT_OWNED", {"expected_pid": current_pid, "actual_pid": owner_pid}

    # Update lock data
    lock_data["expires_at"] = new_expires_at
    lock_data["last_heartbeat_at"] = current_time

    # Write updated lock file (atomic write: write to temp, then rename)
    try:
        # Write to temporary file first
        temp_path = lock_path.parent / f"{lock_path.name}.tmp"
        with open(temp_path, "w") as f:
            json.dump(lock_data, f, indent=2)
            f.flush()
            os.fsync(f.fileno())
        # Atomic rename
        temp_path.replace(lock_path)
        return True, None, None
    except (OSError, json.JSONDecodeError) as e:
        # Clean up temp file if it exists
        try:
            if temp_path.exists():
                temp_path.unlink()
        except Exception:
            pass
        return False, "LOCK_REFRESH_FAILED", {"error": str(e), "error_type": type(e).__name__}


def release_run_lock(run_id: str) -> None:
    """
    Release the filesystem lock for a given run_id (best-effort).
    """
    if not run_id or not isinstance(run_id, str):
        return

    lock_path = _lock_file_path(run_id)
    try:
        if lock_path.exists():
            lock_path.unlink()
    except (OSError, FileNotFoundError):
        # Best-effort: ignore errors (file may have been removed by another process or stale recovery)
        pass
