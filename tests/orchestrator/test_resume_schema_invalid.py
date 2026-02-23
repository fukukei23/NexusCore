from __future__ import annotations

from typing import Any

from nexuscore.orchestrator import authority_runner
from nexuscore.orchestrator.run_state_store import load_state, save_state


def test_resume_schema_invalid_marks_failed_and_returns_explainability(
    monkeypatch: Any, tmp_path: Any
) -> None:
    monkeypatch.setenv("NEXUSCORE_RUN_STATE_DIR", str(tmp_path / "run_state"))
    monkeypatch.setenv("NEXUSCORE_RUNSTATE_HMAC_SECRET", "test-secret-key")

    # status=PAUSED but next_phase is null -> schema invalid per CR-020 MVP checks
    state: dict[str, Any] = {
        "schema_version": "1.0",
        "run_id": "run-bad",
        "status": "PAUSED",
        "authority_level": "partial",
        "next_phase": None,
        "updated_at": "2025-01-01T00:00:00+00:00",
    }
    save_state(state)

    result = authority_runner.resume_run("run-bad")

    assert result["status"] == "FAILED"
    assert result["run_id"] == "run-bad"
    assert "explainability" in result
    exp = result["explainability"]
    assert set(exp.keys()) >= {"what", "why", "next_action"}

    stored = load_state("run-bad")
    assert stored["status"] == "FAILED"
    assert "last_error" in stored
    assert stored["last_error"]["code"]
    assert stored["last_error"]["message"]
