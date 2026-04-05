"""
Core test suite conftest — sys.modules isolation.

test_orchestrator_comprehensive.py monkey-patches sys.modules at module level
(with MagicMock for gradio and nexuscore.agents.*).  Those patches leak into
subsequent test modules and cause AttributeError / import failures.

This autouse fixture snapshots sys.modules before every test module in this
directory runs and restores it afterwards, so each module starts clean.
"""

import sys
from unittest.mock import MagicMock

import pytest

# Keys that test_orchestrator_comprehensive.py injects at module level
_ORCHESTRATOR_MOCK_KEYS = [
    "gradio",
    "nexuscore.agents.requirement_agent",
    "nexuscore.agents.architect_agent",
    "nexuscore.agents.planner_agent",
    "nexuscore.agents.coder_agent",
    "nexuscore.agents.tester_agent",
    "nexuscore.agents.debugger_agent",
    "nexuscore.agents.guardian_agent",
    "nexuscore.agents.policy_agent",
    "nexuscore.agents.postmortem_agent",
    "nexuscore.agents.knowledge_curator_agent",
    "nexuscore.agents.patch_applier",
]


@pytest.fixture(autouse=True)
def _restore_agent_sys_modules():
    """
    Ensure that MagicMock entries injected by test_orchestrator_comprehensive
    don't leak to other test modules.

    Strategy: snapshot the relevant keys, yield, then restore originals.
    If a key was injected as MagicMock by the orchestrator test (and wasn't
    a real module before), remove it on teardown.
    """
    # Snapshot originals
    saved: dict[str, object] = {}
    for key in _ORCHESTRATOR_MOCK_KEYS:
        saved[key] = sys.modules.get(key, _SENTINEL)

    yield

    # Restore: put back originals, remove injected mocks
    for key in _ORCHESTRATOR_MOCK_KEYS:
        original = saved[key]
        if original is _SENTINEL:
            sys.modules.pop(key, None)
        else:
            sys.modules[key] = original


class _SentinelType:
    """Singleton sentinel for 'key was not in sys.modules'."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance


_SENTINEL = _SentinelType()
