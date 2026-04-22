"""run_lock.py カバレッジブースト — 65%→95%+ 目標"""
import json
import os
import time
from unittest.mock import patch

import pytest

from nexuscore.orchestrator.run_lock import (
    _get_lock_dir,
    _get_lock_ttl_seconds,
    _get_lock_refresh_seconds,
    _safe_run_id,
    _lock_file_path,
    _is_lock_stale,
    _move_to_stale,
    try_acquire_run_lock,
    refresh_run_lock,
    release_run_lock,
)


class TestGetLockDir:
    @patch.dict(os.environ, {"NEXUSCORE_RUN_LOCK_DIR": "/custom/locks"})
    def test_custom_dir(self):
        assert _get_lock_dir() == __import__("pathlib").Path("/custom/locks")

    @patch.dict(os.environ, {"NEXUSCORE_RUN_STATE_DIR": "/state"}, clear=False)
    def test_run_state_dir_fallback(self):
        os.environ.pop("NEXUSCORE_RUN_LOCK_DIR", None)
        assert _get_lock_dir() == __import__("pathlib").Path("/state/locks")

    @patch.dict(os.environ, {}, clear=False)
    def test_default_dir(self):
        for key in ["NEXUSCORE_RUN_LOCK_DIR", "NEXUSCORE_RUN_STATE_DIR"]:
            os.environ.pop(key, None)
        assert _get_lock_dir() == __import__("pathlib").Path("/tmp/nexuscore_locks")


class TestGetLockTtl:
    @patch.dict(os.environ, {"NEXUSCORE_RUN_LOCK_TTL_SECONDS": "7200"})
    def test_custom_ttl(self):
        assert _get_lock_ttl_seconds() == 7200

    @patch.dict(os.environ, {"NEXUSCORE_RUN_LOCK_TTL_SECONDS": "not-a-number"})
    def test_invalid_ttl_uses_default(self):
        assert _get_lock_ttl_seconds() == 3600

    def test_default_ttl(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("NEXUSCORE_RUN_LOCK_TTL_SECONDS", None)
            assert _get_lock_ttl_seconds() == 3600


class TestGetLockRefresh:
    @patch.dict(os.environ, {"NEXUSCORE_RUN_LOCK_REFRESH_SECONDS": "60"})
    def test_custom_refresh(self):
        assert _get_lock_refresh_seconds() == 60

    @patch.dict(os.environ, {"NEXUSCORE_RUN_LOCK_REFRESH_SECONDS": "2"})
    def test_minimum_refresh(self):
        assert _get_lock_refresh_seconds() == 5

    @patch.dict(os.environ, {"NEXUSCORE_RUN_LOCK_REFRESH_SECONDS": "abc"})
    def test_invalid_uses_default(self):
        with patch.dict(os.environ, {"NEXUSCORE_RUN_LOCK_TTL_SECONDS": "3600"}):
            assert _get_lock_refresh_seconds() == 1200


class TestSafeRunId:
    def test_produces_hex_string(self):
        result = _safe_run_id("test-run")
        assert len(result) == 64
        assert all(c in "0123456789abcdef" for c in result)

    def test_deterministic(self):
        assert _safe_run_id("abc") == _safe_run_id("abc")


class TestIsLockStale:
    def test_expired_lock_is_stale(self, tmp_path):
        lock_file = tmp_path / "test.lock"
        lock_file.write_text(json.dumps({"expires_at": time.time() - 100}))
        assert _is_lock_stale(lock_file) is True

    def test_valid_lock_not_stale(self, tmp_path):
        lock_file = tmp_path / "test.lock"
        lock_file.write_text(json.dumps({"expires_at": time.time() + 3600}))
        assert _is_lock_stale(lock_file) is False

    def test_missing_expires_at_is_stale(self, tmp_path):
        lock_file = tmp_path / "test.lock"
        lock_file.write_text(json.dumps({"run_id": "test"}))
        assert _is_lock_stale(lock_file) is True

    def test_missing_file_is_stale(self, tmp_path):
        assert _is_lock_stale(tmp_path / "nonexistent.lock") is True

    def test_corrupted_json_is_stale(self, tmp_path):
        lock_file = tmp_path / "test.lock"
        lock_file.write_text("not json")
        assert _is_lock_stale(lock_file) is True


class TestMoveToStale:
    def test_moves_file(self, tmp_path):
        lock_file = tmp_path / "test.lock"
        lock_file.write_text("data")
        _move_to_stale(lock_file)
        assert not lock_file.exists()
        stale_files = list(tmp_path.glob("*.stale.*"))
        assert len(stale_files) == 1

    def test_handles_missing_file(self, tmp_path):
        # Should not raise
        _move_to_stale(tmp_path / "nonexistent.lock")


class TestTryAcquireRunLock:
    @patch.dict(os.environ, {"NEXUSCORE_RUN_LOCK_DIR": ""})
    def test_invalid_run_id(self, tmp_path):
        ok, reason = try_acquire_run_lock("")
        assert ok is False
        assert reason == "INVALID_RUN_ID"

    def test_acquire_new_lock(self, tmp_path):
        with patch("nexuscore.orchestrator.run_lock._get_lock_dir", return_value=tmp_path):
            ok, reason = try_acquire_run_lock("test-run-1")
            assert ok is True
            assert reason is None

            # Verify lock file exists
            lock_files = list(tmp_path.glob("*.lock"))
            assert len(lock_files) == 1

    def test_conflict_with_active_lock(self, tmp_path):
        with patch("nexuscore.orchestrator.run_lock._get_lock_dir", return_value=tmp_path):
            # Create an active lock
            ok1, _ = try_acquire_run_lock("test-run-2")
            assert ok1 is True

            # Second attempt should fail
            ok2, reason = try_acquire_run_lock("test-run-2")
            assert ok2 is False
            assert reason == "CONFLICT"

    def test_acquires_stale_lock(self, tmp_path):
        with patch("nexuscore.orchestrator.run_lock._get_lock_dir", return_value=tmp_path):
            safe_id = _safe_run_id("test-stale")
            lock_path = tmp_path / f"{safe_id}.lock"
            lock_data = {
                "run_id": "test-stale",
                "pid": 99999,
                "acquired_at": time.time() - 7200,
                "expires_at": time.time() - 3600,
            }
            lock_path.write_text(json.dumps(lock_data))

            ok, reason = try_acquire_run_lock("test-stale")
            assert ok is True

    def test_whitespace_run_id_rejected(self, tmp_path):
        ok, reason = try_acquire_run_lock("   ")
        assert ok is False
        assert reason == "INVALID_RUN_ID"


class TestRefreshRunLock:
    def test_refresh_success(self, tmp_path):
        with patch("nexuscore.orchestrator.run_lock._get_lock_dir", return_value=tmp_path):
            try_acquire_run_lock("refresh-test")

            ok, reason, details = refresh_run_lock("refresh-test")
            assert ok is True
            assert reason is None

    def test_refresh_invalid_run_id(self, tmp_path):
        ok, reason, details = refresh_run_lock("")
        assert ok is False
        assert reason == "INVALID_RUN_ID"

    def test_refresh_not_found(self, tmp_path):
        with patch("nexuscore.orchestrator.run_lock._get_lock_dir", return_value=tmp_path):
            ok, reason, details = refresh_run_lock("nonexistent-run")
            assert ok is False
            assert reason == "LOCK_NOT_FOUND"

    def test_refresh_not_owned(self, tmp_path):
        with patch("nexuscore.orchestrator.run_lock._get_lock_dir", return_value=tmp_path):
            safe_id = _safe_run_id("owned-by-other")
            lock_path = tmp_path / f"{safe_id}.lock"
            lock_data = {
                "run_id": "owned-by-other",
                "pid": 99999,  # different pid
                "acquired_at": time.time(),
                "expires_at": time.time() + 3600,
            }
            lock_path.write_text(json.dumps(lock_data))

            ok, reason, details = refresh_run_lock("owned-by-other")
            assert ok is False
            assert reason == "LOCK_NOT_OWNED"

    def test_refresh_corrupted_lock(self, tmp_path):
        with patch("nexuscore.orchestrator.run_lock._get_lock_dir", return_value=tmp_path):
            safe_id = _safe_run_id("corrupted")
            lock_path = tmp_path / f"{safe_id}.lock"
            lock_path.write_text("not json")

            ok, reason, details = refresh_run_lock("corrupted")
            assert ok is False
            assert reason == "LOCK_REFRESH_FAILED"


class TestReleaseRunLock:
    def test_release_success(self, tmp_path):
        with patch("nexuscore.orchestrator.run_lock._get_lock_dir", return_value=tmp_path):
            try_acquire_run_lock("release-test")
            release_run_lock("release-test")
            # Lock file should be gone
            safe_id = _safe_run_id("release-test")
            lock_path = tmp_path / f"{safe_id}.lock"
            assert not lock_path.exists()

    def test_release_nonexistent(self, tmp_path):
        with patch("nexuscore.orchestrator.run_lock._get_lock_dir", return_value=tmp_path):
            # Should not raise
            release_run_lock("nonexistent")

    def test_release_invalid_run_id(self, tmp_path):
        # Should not raise
        release_run_lock("")
        release_run_lock(None)
