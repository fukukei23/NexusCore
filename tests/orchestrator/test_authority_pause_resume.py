from __future__ import annotations

from typing import Any

from nexuscore.orchestrator import authority_runner
from nexuscore.orchestrator.run_state_store import load_state


class FakeOrchestrator:
    def __init__(self) -> None:
        self.project_path = "/tmp/nxcore"
        self.constitution: dict[str, Any] = {}
        self.calls: list[str] = []

        class _SC:
            def __init__(self) -> None:
                self.session_id = "run-123"
                self.stop_before_phases: list[str] = []

            def set_stop_before_phases(self, phases: list[str]) -> None:
                self.stop_before_phases = list(phases)

            def checkpoint(self, phase: str, metadata: dict[str, Any] | None = None) -> None:
                # state saving is handled by runner; this is just a stub
                return None

        self.session_controller = _SC()

    def run_full_project(self, *args: Any, **kwargs: Any) -> None:
        self.calls.append("run_full_project")

    def run_requirements_phase(self, context: Any) -> Any:
        self.calls.append("requirements")
        return context

    def run_planning_phase(self, context: Any) -> Any:
        self.calls.append("planning")
        return context

    def run_architecture_phase(self, context: Any) -> Any:
        self.calls.append("architecture")
        return context

    def run_implementation_phase(self, context: Any) -> Any:
        self.calls.append("implementation")
        return context

    def run_testing_phase(self, context: Any) -> Any:
        self.calls.append("testing")
        return context

    def run_review_phase(self, context: Any) -> Any:
        self.calls.append("review")
        return context


def test_pause_saves_state_and_resume_continues_from_next_phase(
    monkeypatch: Any, tmp_path: Any
) -> None:
    monkeypatch.setenv("NEXUSCORE_RUN_STATE_DIR", str(tmp_path / "run_state"))
    monkeypatch.setenv("NEXUSCORE_RUNSTATE_HMAC_SECRET", "test-secret-key")
    monkeypatch.setattr("nexuscore.orchestrator.run_lock._get_lock_refresh_seconds", lambda: 0.1)

    orch = FakeOrchestrator()
    result = authority_runner.run_with_authority(
        orchestrator=orch,
        user_requirement="req",
        authority_level="partial",
        language="ja",
    )

    assert result["status"] == "paused"
    assert result["run_id"] == "run-123"
    assert result["next_phase"] == "implementation"
    assert orch.calls == ["requirements", "planning", "architecture"]

    state = load_state("run-123")
    assert state["status"] == "PAUSED"
    assert state["authority_level"] == "partial"
    assert state["next_phase"] == "implementation"

    # Resume should run from implementation onward and complete.
    orch2 = FakeOrchestrator()
    authority_runner.set_resume_orchestrator(orch2)
    resumed = authority_runner.resume_run("run-123")

    # Resume executes remaining phases (implementation, testing, review).
    assert resumed["status"] == "RUNNING"
    assert orch2.calls == ["implementation", "testing", "review"]


def test_session_controller_should_not_gate_on_stop_before_phases(
    monkeypatch: Any, tmp_path: Any
) -> None:
    from nexuscore.core.session_control import SessionController

    sc = SessionController(session_id="s1", root_dir=str(tmp_path / "sessions"))
    sc.set_stop_before_phases(["planning"])
    sc.checkpoint("planning", {})
    # No external stop/pause command -> should_stop must be False
    assert sc.should_stop() is False

    sc.request_pause()
    assert sc.should_stop() is True
