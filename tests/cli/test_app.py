"""Tests for NexusCore CLI application."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from nexuscore.cli.app import main
from nexuscore.core.orchestrator_models import OrchestratorContext


def test_version():
    runner = CliRunner()
    result = runner.invoke(main, ["version"])
    assert result.exit_code == 0
    assert "NexusCore" in result.output


def test_agents_lists_builtin():
    runner = CliRunner()
    result = runner.invoke(main, ["agents"])
    assert result.exit_code == 0
    assert "coder" in result.output
    assert "tester" in result.output
    assert "guardian" in result.output


def test_plugin_list():
    runner = CliRunner()
    result = runner.invoke(main, ["plugin", "list"])
    assert result.exit_code == 0
    assert "Agent Plugins" in result.output
    assert "Workflow Plugins" in result.output


def test_plugin_info_existing():
    runner = CliRunner()
    result = runner.invoke(main, ["plugin", "info", "coder"])
    assert result.exit_code == 0
    assert "Agent: coder" in result.output


def test_plugin_info_missing():
    runner = CliRunner()
    result = runner.invoke(main, ["plugin", "info", "nonexistent_agent"])
    assert result.exit_code == 1
    assert "not found" in result.output


def test_help():
    runner = CliRunner()
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "run" in result.output
    assert "agents" in result.output
    assert "plugin" in result.output


def _invoke_run_with_result(project_path: Path, run_result: object):
    """Invoke `nexus run` with the orchestrator patched to return run_result."""
    fake_orch = MagicMock()
    fake_orch.run_full_project.return_value = run_result
    with patch(
        "nexuscore.core.agent_factory.assemble_agent_team", return_value={}
    ), patch("nexuscore.core.orchestrator.Orchestrator", return_value=fake_orch):
        runner = CliRunner()
        return runner.invoke(
            main, ["run", "build a thing", "--project-path", str(project_path)]
        )


def test_run_reports_completed_when_context_returned(tmp_path: Path) -> None:
    """A completed run returns an OrchestratorContext, not a dict — report success."""
    ctx = OrchestratorContext(task_id="t1", user_requirement="build a thing")
    ctx.phase_log = ["CONTEXT", "REQUIREMENTS", "PLAN", "REVIEW"]

    result = _invoke_run_with_result(tmp_path, ctx)

    assert result.exit_code == 0, result.output
    assert "completed" in result.output
    assert "AttributeError" not in result.output


def test_run_reports_interrupted_when_none_returned(tmp_path: Path) -> None:
    """A user-stopped run returns None — report interrupted, not an AttributeError."""
    result = _invoke_run_with_result(tmp_path, None)

    assert result.exit_code == 0, result.output
    assert "interrupted" in result.output
    assert "AttributeError" not in result.output
