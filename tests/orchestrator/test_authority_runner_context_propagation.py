from __future__ import annotations

from typing import Any, Dict, Optional

import pytest

from nexuscore.orchestrator import authority_runner


class DummyOrchestrator:
    def __init__(self) -> None:
        self.constitution: Dict[str, Any] = {}

    def run_full_project(self, *args: Any, **kwargs: Any) -> None:
        # Should not be reached in this test (we patch _invoke_orchestrator).
        raise AssertionError("run_full_project should not be called in this test")


@pytest.mark.parametrize(
    "authority_level",
    ["partial", None],
)
def test_run_with_authority_propagates_authority_level_in_execution_context(
    monkeypatch: Any,
    authority_level: Optional[str],
) -> None:
    orch = DummyOrchestrator()

    captured: Dict[str, Any] = {}

    def fake_invoke_orchestrator(**kwargs: Any) -> None:
        captured.update(kwargs)

    monkeypatch.setattr(authority_runner, "_invoke_orchestrator", fake_invoke_orchestrator)

    authority_runner.run_with_authority(
        orchestrator=orch,
        user_requirement="Example requirement",
        authority_level=authority_level,
        language="ja",
    )

    assert "execution_context" in captured
    ctx = captured["execution_context"]
    assert "authority_level" in ctx
    assert ctx["authority_level"] == authority_level


