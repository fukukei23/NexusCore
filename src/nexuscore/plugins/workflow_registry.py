from __future__ import annotations

import logging
from importlib.metadata import entry_points
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from nexuscore.plugins.base_workflow import BaseWorkflow

logger = logging.getLogger(__name__)


class WorkflowRegistry:
    """Central registry for workflow classes.

    Built-in workflows are registered at import time.
    External workflows are discovered via ``importlib.metadata.entry_points("nexuscore.workflows")``.
    """

    _workflows: dict[str, type[BaseWorkflow]] = {}

    @classmethod
    def register(cls, name: str, workflow_class: type[BaseWorkflow]) -> None:
        if name in cls._workflows:
            logger.warning("Workflow '%s' already registered, overwriting.", name)
        cls._workflows[name] = workflow_class

    @classmethod
    def register_workflow(cls, name: str):
        """Decorator to register a workflow class."""

        def decorator(wf_class: type[BaseWorkflow]) -> type[BaseWorkflow]:
            cls.register(name, wf_class)
            return wf_class

        return decorator

    @classmethod
    def get(cls, name: str) -> type[BaseWorkflow]:
        if name not in cls._workflows:
            raise KeyError(f"Workflow '{name}' not registered. Available: {list(cls._workflows)}")
        return cls._workflows[name]

    @classmethod
    def list_all(cls) -> dict[str, type[BaseWorkflow]]:
        return cls._workflows.copy()

    @classmethod
    def has(cls, name: str) -> bool:
        return name in cls._workflows

    @classmethod
    def discover(cls) -> None:
        """Discover and register workflows from entry_points("nexuscore.workflows")."""
        wf_eps = entry_points(group="nexuscore.workflows")
        for ep in wf_eps:
            try:
                wf_class = ep.load()
                cls.register(ep.name, wf_class)
                logger.info("Discovered external workflow: %s", ep.name)
            except Exception as e:
                logger.warning("Failed to load workflow plugin '%s': %s", ep.name, e)

    @classmethod
    def clear(cls) -> None:
        cls._workflows.clear()
