"""Tests for NexusCore CLI application."""

from __future__ import annotations

from click.testing import CliRunner

from nexuscore.cli.app import main


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
