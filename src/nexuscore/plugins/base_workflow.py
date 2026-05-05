"""Base class for workflow plugins."""

from __future__ import annotations

from typing import Any


class BaseWorkflow:
    """Base class for NexusCore workflow plugins.

    Subclass this and implement ``execute()`` to create a custom workflow.
    Register via ``WorkflowRegistry.register("name", MyWorkflow)`` or
    ``project.entry-points."nexuscore.workflows"`` in pyproject.toml.
    """

    name: str = "unnamed"
    description: str = ""

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Run the workflow with the given context.

        Args:
            context: Arbitrary context data for the workflow.

        Returns:
            Workflow result as a dict.
        """
        raise NotImplementedError
