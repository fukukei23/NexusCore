from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import pytest

from nexuscore.orchestrator.authority_runner import run_with_authority


@dataclass
class DummyContext:
    user_requirement: str


class SpySessionController:
    def __init__(self) -> None:
        self.session_id = "run-123"
        self.stop_before_phases: List[str] = []
        self.last_checkpoint: Optional[str] = None

    def set_stop_before_phases(self, phases: list[str]) -> None:
        self.stop_before_phases = list(phases)

    def checkpoint(self, phase: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        self.last_checkpoint = phase

    def should_stop(self) -> bool:
        if self.last_checkpoint is None:
            return False
        return self.last_checkpoint in self.stop_before_phases


class FakeOrchestrator:
    def __init__(self) -> None:
        self.project_path = "/tmp/nxcore"
        self.constitution: Dict[str, Any] = {}
        self.session_controller = SpySessionController()
        self.calls: List[str] = []

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


def test_human_sets_stop_policy_and_pauses_with_next_phase(monkeypatch: Any, tmp_path: Any) -> None:
    monkeypatch.setenv("NEXUSCORE_RUN_STATE_DIR", str(tmp_path / "run_state"))
    monkeypatch.setenv("NEXUSCORE_RUNSTATE_HMAC_SECRET", "test-secret-key")
    orch = FakeOrchestrator()
    result = run_with_authority(
        orchestrator=orch,
        user_requirement="req",
        authority_level="human",
        language="ja",
    )

    assert orch.session_controller.stop_before_phases == [
        "requirements",
        "planning",
        "architecture",
        "implementation",
        "testing",
        "review",
    ]
    assert result["status"] == "paused"
    assert result["next_phase"] == "requirements"
    assert "run_id" in result
    assert result["run_id"] == "run-123"
    assert orch.calls == []  # stopped before executing any phase


def test_partial_sets_stop_policy_and_pauses_before_implementation(monkeypatch: Any, tmp_path: Any) -> None:
    monkeypatch.setenv("NEXUSCORE_RUN_STATE_DIR", str(tmp_path / "run_state"))
    monkeypatch.setenv("NEXUSCORE_RUNSTATE_HMAC_SECRET", "test-secret-key")
    orch = FakeOrchestrator()
    result = run_with_authority(
        orchestrator=orch,
        user_requirement="req",
        authority_level="partial",
        language="ja",
    )

    assert orch.session_controller.stop_before_phases == ["implementation"]
    assert result["status"] == "paused"
    assert result["next_phase"] == "implementation"
    assert orch.calls == ["requirements", "planning", "architecture"]


def test_full_sets_empty_stop_policy_and_completes(monkeypatch: Any, tmp_path: Any) -> None:
    monkeypatch.setenv("NEXUSCORE_RUN_STATE_DIR", str(tmp_path / "run_state"))
    monkeypatch.setenv("NEXUSCORE_RUNSTATE_HMAC_SECRET", "test-secret-key")
    orch = FakeOrchestrator()
    result = run_with_authority(
        orchestrator=orch,
        user_requirement="req",
        authority_level="full",
        language="ja",
    )

    assert orch.session_controller.stop_before_phases == []
    assert result["status"] == "completed"
    assert result["next_phase"] is None
    # For full, we preserve existing behavior (call run_full_project)
    assert orch.calls == ["run_full_project"]


