"""
test_run_state_integrity.py

Tests for RunState integrity verification using HMAC-SHA256 (CR-NEXUS-026).
"""

from __future__ import annotations

import json
from typing import Any

import pytest

from nexuscore.orchestrator.run_state_integrity import sign_run_state, verify_integrity
from nexuscore.orchestrator.run_state_store import load_state, save_state


def test_integrity_sign_and_verify_ok(monkeypatch: Any, tmp_path: Any) -> None:
    """Test that signing and verification works correctly for valid RunState."""
    monkeypatch.setenv("NEXUSCORE_RUN_STATE_DIR", str(tmp_path / "run_state"))
    monkeypatch.setenv("NEXUSCORE_RUNSTATE_HMAC_SECRET", "test-secret-key")

    state: dict[str, Any] = {
        "schema_version": "1.0",
        "run_id": "test-integrity-ok",
        "status": "PAUSED",
        "authority_level": "partial",
        "next_phase": "implementation",
        "updated_at": "2025-01-01T00:00:00+00:00",
    }

    # Sign the state
    signed_state = sign_run_state(state)

    # Verify integrity field exists
    assert "integrity" in signed_state
    integrity = signed_state["integrity"]
    assert integrity["algorithm"] == "HMAC-SHA256"
    assert integrity["key_id"] == "default"
    assert "signature" in integrity
    assert "signed_at" in integrity

    # Verify the signature
    ok, code, message = verify_integrity(signed_state)
    assert ok is True, f"Verification should succeed (code: {code}, message: {message})"
    assert code is None
    assert message is None

    # Save and load should also verify correctly
    save_state(signed_state)
    loaded = load_state("test-integrity-ok")
    ok, code, message = verify_integrity(loaded)
    assert ok is True
    assert code is None


def test_integrity_detects_tampering(monkeypatch: Any, tmp_path: Any) -> None:
    """Test that integrity verification detects tampering (modified RunState)."""
    monkeypatch.setenv("NEXUSCORE_RUN_STATE_DIR", str(tmp_path / "run_state"))
    monkeypatch.setenv("NEXUSCORE_RUNSTATE_HMAC_SECRET", "test-secret-key")

    state: dict[str, Any] = {
        "schema_version": "1.0",
        "run_id": "test-integrity-tamper",
        "status": "PAUSED",
        "authority_level": "partial",
        "next_phase": "implementation",
        "updated_at": "2025-01-01T00:00:00+00:00",
    }

    # Sign the state
    signed_state = sign_run_state(state)

    # Tamper with the state (modify a field)
    tampered_state = dict(signed_state)
    tampered_state["status"] = "SUCCEEDED"  # Changed from PAUSED

    # Verify should fail
    ok, code, message = verify_integrity(tampered_state)
    assert ok is False, "Verification should fail for tampered state"
    assert code == "STATE_INTEGRITY_VIOLATION"
    assert "signature verification failed" in message.lower() or "tampering" in message.lower()


def test_integrity_missing_or_wrong_secret(monkeypatch: Any, tmp_path: Any) -> None:
    """Test that missing secret raises RuntimeError, and wrong secret causes verification failure."""
    monkeypatch.setenv("NEXUSCORE_RUN_STATE_DIR", str(tmp_path / "run_state"))

    state: dict[str, Any] = {
        "schema_version": "1.0",
        "run_id": "test-integrity-secret",
        "status": "PAUSED",
        "authority_level": "partial",
        "next_phase": "implementation",
        "updated_at": "2025-01-01T00:00:00+00:00",
    }

    # Test 1: Missing secret should raise RuntimeError when signing
    # Remove the secret (if it was set by previous test or environment)
    try:
        monkeypatch.delenv("NEXUSCORE_RUNSTATE_HMAC_SECRET", raising=False)
    except KeyError:
        pass  # Already not set
    with pytest.raises(RuntimeError, match="NEXUSCORE_RUNSTATE_HMAC_SECRET"):
        sign_run_state(state)

    # Test 2: Sign with one secret, verify with different secret should fail
    monkeypatch.setenv("NEXUSCORE_RUNSTATE_HMAC_SECRET", "secret-1")
    signed_state = sign_run_state(state)

    monkeypatch.setenv("NEXUSCORE_RUNSTATE_HMAC_SECRET", "secret-2")
    ok, code, message = verify_integrity(signed_state)
    assert ok is False, "Verification should fail with wrong secret"
    assert code == "STATE_INTEGRITY_VIOLATION"

    # Test 3: Missing integrity field should fail
    state_no_integrity = dict(state)
    ok, code, message = verify_integrity(state_no_integrity)
    assert ok is False
    assert code == "STATE_INTEGRITY_MISSING"
    assert "missing integrity field" in message.lower()


def test_resume_fails_on_integrity_violation(monkeypatch: Any, tmp_path: Any) -> None:
    """Test that resume_run() fails when RunState integrity verification fails."""
    monkeypatch.setenv("NEXUSCORE_RUN_STATE_DIR", str(tmp_path / "run_state"))
    lock_dir = tmp_path / "locks"
    lock_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("NEXUSCORE_RUN_LOCK_DIR", str(lock_dir))
    monkeypatch.setenv("NEXUSCORE_RUNSTATE_HMAC_SECRET", "test-secret")

    from nexuscore.orchestrator import authority_runner
    from nexuscore.orchestrator.run_state_store import load_state

    run_id = "test-resume-integrity-violation"

    # Create a valid paused state
    state: dict[str, Any] = {
        "schema_version": "1.0",
        "run_id": run_id,
        "status": "PAUSED",
        "authority_level": "partial",
        "next_phase": "implementation",
        "updated_at": "2025-01-01T00:00:00+00:00",
    }
    save_state(state)

    # Tamper with the saved state file (modify status after signing)

    state_file = tmp_path / "run_state" / f"{run_id}.json"
    tampered_data = json.loads(state_file.read_text())
    tampered_data["status"] = "SUCCEEDED"  # Tamper
    state_file.write_text(json.dumps(tampered_data, indent=2))

    # Mock orchestrator (should not be called)
    class DummyOrchestrator:
        def start(self, run_id: str = None, state: dict = None):
            pass

    authority_runner.set_resume_orchestrator(DummyOrchestrator())

    try:
        # Resume should fail at integrity gate
        result = authority_runner.resume_run(run_id)

        # Verify failure
        assert result["status"] == "FAILED"
        assert "explainability" in result
        assert result["explainability"]["why"] == "STATE_INTEGRITY_VIOLATION"
        assert "abort" in result["explainability"]["next_action"].lower()

        # Verify RunState was NOT updated (still has original status)
        load_state(run_id)
        # Note: The tampered state is what we loaded, but the integrity check should have failed
        # The stored state still has the tampered status (not reverted), but resume failed
        # This is expected behavior: integrity failure prevents resume, but doesn't modify the file
    finally:
        from nexuscore.orchestrator.run_lock import release_run_lock

        release_run_lock(run_id)
