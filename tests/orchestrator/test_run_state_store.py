from __future__ import annotations

from typing import Any

from nexuscore.orchestrator import run_state_store


def test_run_state_roundtrip_save_load_update(monkeypatch: Any, tmp_path: Any) -> None:
    monkeypatch.setenv("NEXUSCORE_RUN_STATE_DIR", str(tmp_path / "run_state"))
    monkeypatch.setenv("NEXUSCORE_RUNSTATE_HMAC_SECRET", "test-secret-key")

    state: dict[str, Any] = {
        "run_id": "run-1",
        "status": "paused",
        "authority_level": "partial",
        "next_phase": "implementation",
    }

    run_state_store.save_state(state)
    loaded = run_state_store.load_state("run-1")

    assert loaded["run_id"] == "run-1"
    assert loaded["status"] == "paused"
    assert loaded["authority_level"] == "partial"
    assert loaded["next_phase"] == "implementation"
    assert "updated_at" in loaded

    updated = run_state_store.update_state("run-1", status="completed", next_phase=None)
    assert updated["status"] == "completed"
    assert updated["next_phase"] is None
    assert updated["run_id"] == "run-1"
    assert "updated_at" in updated
