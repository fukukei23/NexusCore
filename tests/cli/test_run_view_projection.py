"""
test_run_view_projection.py

Tests for RunView projection (CR-NEXUS-027).
"""

from __future__ import annotations

from typing import Any

from nexuscore.cli.run_view import build_run_view, format_run_view_cli


def test_run_view_running(monkeypatch: Any, tmp_path: Any) -> None:
    """Test that RUNNING status shows run_id and status."""
    result: dict[str, Any] = {
        "status": "RUNNING",
        "run_id": "test-run-123",
    }

    run_view = build_run_view(result)
    output = format_run_view_cli(run_view)

    assert "RUN STARTED" in output
    assert "run_id: test-run-123" in output
    assert "RUNNING" in output or "RUN STARTED" in output


def test_run_view_paused_with_phase(monkeypatch: Any, tmp_path: Any) -> None:
    """Test that PAUSED status shows phase and resume instruction."""
    result: dict[str, Any] = {
        "status": "paused",
        "run_id": "test-run-paused",
        "next_phase": "implementation",
    }

    run_state: dict[str, Any] = {
        "run_id": "test-run-paused",
        "status": "PAUSED",
        "next_phase": "implementation",
        "authority_level": "partial",
        "updated_at": "2025-01-01T00:00:00+00:00",
    }

    run_view = build_run_view(result, run_state)
    output = format_run_view_cli(run_view)

    assert "PAUSED" in output
    assert "run_id: test-run-paused" in output
    assert "paused at phase: implementation" in output
    assert "--resume-run-id test-run-paused" in output
    assert "authority_level: partial" in output or "partial" in output


def test_run_view_conflict_shows_explainability(monkeypatch: Any, tmp_path: Any) -> None:
    """Test that CONFLICT status shows explainability."""
    result: dict[str, Any] = {
        "status": "CONFLICT",
        "run_id": "test-run-conflict",
        "explainability": {
            "what": "Resume conflict: run_id=test-run-conflict is already being resumed/executed",
            "why": "CONFLICT",
            "next_action": "wait/retry",
        },
    }

    run_view = build_run_view(result)
    output = format_run_view_cli(run_view)

    assert "RESUME BLOCKED" in output
    assert "run_id: test-run-conflict" in output
    assert "Error:" in output or "Reason:" in output
    assert "CONFLICT" in output
    assert "wait/retry" in output or "Next:" in output


def test_run_view_failed_shows_explainability(monkeypatch: Any, tmp_path: Any) -> None:
    """Test that FAILED status shows explainability."""
    result: dict[str, Any] = {
        "status": "FAILED",
        "run_id": "test-run-failed",
        "explainability": {
            "what": "Resume failed: invalid RunState schema",
            "why_code": "SCHEMA_INVALID",
            "next_action": "Fix RunState or abort and start a new run",
        },
    }

    run_view = build_run_view(result)
    output = format_run_view_cli(run_view)

    assert "RESUME FAILED" in output or "RUN FAILED" in output
    assert "run_id: test-run-failed" in output
    assert "Error:" in output or "Reason:" in output
    assert "SCHEMA_INVALID" in output or "invalid" in output.lower()
    assert "Next:" in output or "next_action" in output.lower()


def test_run_view_aborted_shows_explainability(monkeypatch: Any, tmp_path: Any) -> None:
    """Test that ABORTED status shows explainability."""
    result: dict[str, Any] = {
        "status": "ABORTED",
        "run_id": "test-run-aborted",
        "explainability": {
            "what": "Run aborted due to lock refresh failure",
            "why": "LOCK_REFRESH_FAILED",
            "next_action": "inspect_lock_dir_permissions",
        },
    }

    run_view = build_run_view(result)
    output = format_run_view_cli(run_view)

    assert "RUN ABORTED" in output
    assert "run_id: test-run-aborted" in output
    assert "Error:" in output or "Reason:" in output
    assert "LOCK_REFRESH_FAILED" in output or "lock refresh" in output.lower()
    assert "inspect_lock_dir_permissions" in output or "Next:" in output


def test_run_view_handles_why_code_variation(monkeypatch: Any, tmp_path: Any) -> None:
    """Test that RunView handles why_code / why key variations."""
    # Test with why_code
    result1: dict[str, Any] = {
        "status": "FAILED",
        "run_id": "test-why-code",
        "explainability": {
            "what": "Test error",
            "why_code": "TEST_ERROR",
            "next_action": "retry",
        },
    }

    run_view1 = build_run_view(result1)
    output1 = format_run_view_cli(run_view1)

    assert "TEST_ERROR" in output1 or "Reason:" in output1

    # Test with why (no why_code)
    result2: dict[str, Any] = {
        "status": "FAILED",
        "run_id": "test-why",
        "explainability": {
            "what": "Test error",
            "why": "TEST_ERROR",
            "next_action": "retry",
        },
    }

    run_view2 = build_run_view(result2)
    output2 = format_run_view_cli(run_view2)

    assert "TEST_ERROR" in output2 or "Reason:" in output2


def test_run_view_extracts_authority_level_from_run_state(monkeypatch: Any, tmp_path: Any) -> None:
    """Test that authority_level is extracted from run_state when available."""
    result: dict[str, Any] = {
        "status": "paused",
        "run_id": "test-auth-level",
        "next_phase": "planning",
    }

    run_state: dict[str, Any] = {
        "run_id": "test-auth-level",
        "status": "PAUSED",
        "authority_level": "full",
        "updated_at": "2025-01-01T00:00:00+00:00",
    }

    run_view = build_run_view(result, run_state)

    assert run_view["authority_level"] == "full"
    assert run_view["updated_at"] == "2025-01-01T00:00:00+00:00"


def test_run_view_completed_status(monkeypatch: Any, tmp_path: Any) -> None:
    """Test that completed status is formatted correctly."""
    result: dict[str, Any] = {
        "status": "completed",
        "run_id": "test-completed",
        "next_phase": None,
    }

    run_view = build_run_view(result)
    output = format_run_view_cli(run_view)

    assert "RUN COMPLETED" in output
    assert "run_id: test-completed" in output
