"""Tests for WorkflowRegistry."""

from __future__ import annotations

from nexuscore.plugins.base_workflow import BaseWorkflow
from nexuscore.plugins.workflow_registry import WorkflowRegistry


class _DummyWorkflow(BaseWorkflow):
    name = "dummy"
    description = "test workflow"

    def execute(self, context):
        return {"result": "ok"}


class TestWorkflowRegistry:
    def setup_method(self):
        WorkflowRegistry.clear()

    def test_register_and_get(self):
        WorkflowRegistry.register("dummy", _DummyWorkflow)
        assert WorkflowRegistry.get("dummy") is _DummyWorkflow

    def test_list_all(self):
        WorkflowRegistry.register("w", _DummyWorkflow)
        assert "w" in WorkflowRegistry.list_all()

    def test_has(self):
        assert not WorkflowRegistry.has("missing")
        WorkflowRegistry.register("present", _DummyWorkflow)
        assert WorkflowRegistry.has("present")

    def test_get_missing_raises(self):
        import pytest

        with pytest.raises(KeyError, match="not registered"):
            WorkflowRegistry.get("nope")

    def test_decorator(self):
        @WorkflowRegistry.register_workflow("decorated")
        class DecoratedWF(BaseWorkflow):
            def execute(self, context):
                return {}

        assert WorkflowRegistry.get("decorated") is DecoratedWF

    def test_clear(self):
        WorkflowRegistry.register("x", _DummyWorkflow)
        WorkflowRegistry.clear()
        assert not WorkflowRegistry.has("x")

    def test_base_workflow_execute_raises(self):
        import pytest

        wf = BaseWorkflow()
        with pytest.raises(NotImplementedError):
            wf.execute({})

    def test_execute_concrete(self):
        wf = _DummyWorkflow()
        result = wf.execute({"input": "test"})
        assert result == {"result": "ok"}
