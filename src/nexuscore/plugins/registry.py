"""Agent registry for plugin discovery and instantiation."""

from __future__ import annotations

import logging
from importlib.metadata import entry_points
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from nexuscore.agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)


class AgentRegistry:
    """Central registry for agent classes.

    Built-in agents are registered at import time.
    External agents are discovered via ``importlib.metadata.entry_points("nexuscore.agents")``.
    """

    _agents: dict[str, type[BaseAgent]] = {}

    @classmethod
    def register(cls, name: str, agent_class: type[BaseAgent]) -> None:
        if name in cls._agents:
            logger.warning("Agent '%s' already registered, overwriting.", name)
        cls._agents[name] = agent_class

    @classmethod
    def register_agent(cls, name: str):
        """Decorator to register an agent class."""

        def decorator(agent_class: type[BaseAgent]) -> type[BaseAgent]:
            cls.register(name, agent_class)
            return agent_class

        return decorator

    @classmethod
    def get(cls, name: str) -> type[BaseAgent]:
        if name not in cls._agents:
            raise KeyError(f"Agent '{name}' not registered. Available: {list(cls._agents)}")
        return cls._agents[name]

    @classmethod
    def list_all(cls) -> dict[str, type[BaseAgent]]:
        return cls._agents.copy()

    @classmethod
    def has(cls, name: str) -> bool:
        return name in cls._agents

    @classmethod
    def discover(cls) -> None:
        """Discover and register agents from entry_points("nexuscore.agents")."""
        agent_eps = entry_points(group="nexuscore.agents")
        for ep in agent_eps:
            try:
                agent_class = ep.load()
                cls.register(ep.name, agent_class)
                logger.info("Discovered external agent: %s", ep.name)
            except Exception as e:
                logger.warning("Failed to load agent plugin '%s': %s", ep.name, e)

    @classmethod
    def clear(cls) -> None:
        cls._agents.clear()
