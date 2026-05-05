"""Tests for AgentRegistry."""

from __future__ import annotations

from unittest.mock import MagicMock

from nexuscore.agents.base_agent import BaseAgent
from nexuscore.plugins.registry import AgentRegistry


class _DummyAgent(BaseAgent):
    SYSTEM_PROMPT = "test"


class _AnotherAgent(BaseAgent):
    SYSTEM_PROMPT = "another"


class TestAgentRegistry:
    def setup_method(self):
        AgentRegistry.clear()

    def test_register_and_get(self):
        AgentRegistry.register("dummy", _DummyAgent)
        assert AgentRegistry.get("dummy") is _DummyAgent

    def test_list_all(self):
        AgentRegistry.register("a", _DummyAgent)
        AgentRegistry.register("b", _AnotherAgent)
        all_agents = AgentRegistry.list_all()
        assert len(all_agents) == 2
        assert "a" in all_agents
        assert "b" in all_agents

    def test_has(self):
        assert not AgentRegistry.has("missing")
        AgentRegistry.register("present", _DummyAgent)
        assert AgentRegistry.has("present")

    def test_get_missing_raises(self):
        import pytest

        with pytest.raises(KeyError, match="not registered"):
            AgentRegistry.get("nope")

    def test_decorator(self):
        @AgentRegistry.register_agent("decorated")
        class DecoratedAgent(BaseAgent):
            pass

        assert AgentRegistry.get("decorated") is DecoratedAgent

    def test_clear(self):
        AgentRegistry.register("x", _DummyAgent)
        AgentRegistry.clear()
        assert not AgentRegistry.has("x")
