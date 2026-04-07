from __future__ import annotations

from typing import Any

from nexuscore.orchestrator import authority_runner
from nexuscore.orchestrator.run_state_store import load_state, save_state


def test_resume_status_transition_and_orchestrator_rebuild(monkeypatch: Any, tmp_path: Any) -> None:
    monkeypatch.setenv("NEXUSCORE_RUN_STATE_DIR", str(tmp_path / "run_state"))
    monkeypatch.setenv("NEXUSCORE_RUNSTATE_HMAC_SECRET", "test-secret-key")
    monkeypatch.setattr("nexuscore.orchestrator.run_lock._get_lock_refresh_seconds", lambda: 0.1)

    # Arrange: a valid PAUSED RunState (with an unknown field to verify RMW preservation)
    state: dict[str, Any] = {
        "schema_version": "1.0",
        "run_id": "run-1",
        "status": "PAUSED",
        "authority_level": "partial",
        "next_phase": "implementation",
        "updated_at": "2025-01-01T00:00:00+00:00",
        "unknown_field": {"k": "v"},
    }
    save_state(state)

    # Spy on update_state calls to confirm RESUMING -> RUNNING transitions.
    seen_statuses: list[str] = []
    real_update_state = authority_runner.update_state  # type: ignore[attr-defined]

    def _spy_update_state(arg: Any, **kwargs: Any) -> Any:
        if isinstance(arg, dict):
            st = arg.get("status")
            if isinstance(st, str):
                seen_statuses.append(st)
        else:
            st = kwargs.get("status")
            if isinstance(st, str):
                seen_statuses.append(st)
        return real_update_state(arg, **kwargs)

    monkeypatch.setattr(authority_runner, "update_state", _spy_update_state)

    # Orchestrator factory must be used (new instance per resume).
    factory_calls: list[str] = []

    class DummyOrchestrator:
        def __init__(self, marker: str) -> None:
            self.marker = marker

    def _factory() -> DummyOrchestrator:
        factory_calls.append("called")
        return DummyOrchestrator(marker="new")

    authority_runner.set_resume_orchestrator_factory(_factory)

    # Act
    result = authority_runner.resume_run("run-1")

    # Assert: entry returns RUNNING and state transitions happened in order.
    assert result["status"] == "RUNNING"
    assert result["run_id"] == "run-1"
    assert seen_statuses[:2] == ["RESUMING", "RUNNING"]
    assert factory_calls == ["called"]

    # Assert: final stored status is RUNNING and unknown fields are preserved.
    stored = load_state("run-1")
    assert stored["status"] == "RUNNING"
    assert stored["unknown_field"] == {"k": "v"}
