from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List, Optional

import pytest

from nexuscore.orchestrator.authority_runner import run_with_authority_level
from nexuscore.orchestrator.constants import AuthorityLevel


@dataclass
class FakeContext:
    user_requirement: str
    language: str = "ja"
    fast_lane: bool = False
    run_db_id: Optional[int] = None


class FakeOrchestrator:
    def __init__(self) -> None:
        self.calls: List[str] = []

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


def _ctx_factory(**kwargs: Any) -> FakeContext:
    return FakeContext(
        user_requirement=kwargs["user_requirement"],
        language=kwargs["language"],
        fast_lane=kwargs["fast_lane"],
        run_db_id=kwargs["run_db_id"],
    )


def test_human_controlled_runs_requirements_only() -> None:
    orch = FakeOrchestrator()

    run_with_authority_level(
        orch,
        "Test requirement",
        authority_level=AuthorityLevel.HUMAN_CONTROLLED,
        context_factory=_ctx_factory,
    )

    assert orch.calls == ["requirements"]


def test_partially_autonomous_runs_through_architecture() -> None:
    orch = FakeOrchestrator()

    run_with_authority_level(
        orch,
        "Test requirement",
        authority_level=AuthorityLevel.PARTIALLY_AUTONOMOUS,
        context_factory=_ctx_factory,
    )

    assert orch.calls == ["requirements", "planning", "architecture"]


def test_fully_autonomous_runs_all_phases() -> None:
    orch = FakeOrchestrator()

    run_with_authority_level(
        orch,
        "Test requirement",
        authority_level=AuthorityLevel.FULLY_AUTONOMOUS,
        context_factory=_ctx_factory,
    )

    assert orch.calls == [
        "requirements",
        "planning",
        "architecture",
        "implementation",
        "testing",
        "review",
    ]


def test_invalid_authority_level_raises_value_error() -> None:
    orch = FakeOrchestrator()

    with pytest.raises(ValueError):
        run_with_authority_level(
            orch,
            "Test requirement",
            authority_level=999,
            context_factory=_ctx_factory,
        )


