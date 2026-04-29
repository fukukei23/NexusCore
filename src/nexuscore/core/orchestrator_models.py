from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any


class OrchestratorPhase(Enum):
    """Development flow phases."""

    REQUIREMENTS = auto()
    PLAN = auto()
    ARCHITECTURE = auto()
    IMPLEMENTATION = auto()
    TESTING = auto()
    REVIEW = auto()


@dataclass
class OrchestratorContext:
    """Orchestrator execution context, carried across phases."""

    task_id: str
    user_requirement: str
    language: str = "ja"
    fast_lane: bool = False
    run_db_id: int | None = None

    specs: dict[str, Any] = field(default_factory=dict)
    plan: dict[str, Any] = field(default_factory=dict)
    architecture: dict[str, Any] = field(default_factory=dict)
    implementation: dict[str, Any] = field(default_factory=dict)
    testing: dict[str, Any] = field(default_factory=dict)
    review: dict[str, Any] = field(default_factory=dict)

    phase_log: list[str] = field(default_factory=list)
