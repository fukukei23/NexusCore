"""NexusCore CLI application with subcommand structure.

Provides:
    nexus run <requirement> --project-path <path>
    nexus agents
    nexus plugin list
    nexus plugin info <name>
    nexus version
"""

from __future__ import annotations

import importlib
import sys

import click

from nexuscore.plugins.builtin_agents import (
    get_agent_description,
    get_all_descriptions,
    register_builtin_agents,
)
from nexuscore.plugins.registry import AgentRegistry
from nexuscore.plugins.workflow_registry import WorkflowRegistry


def _ensure_discovery() -> None:
    """Register built-ins and discover external plugins (idempotent)."""
    if not AgentRegistry.list_all():
        register_builtin_agents()
        AgentRegistry.discover()
    if not WorkflowRegistry.list_all():
        # Import built-in workflow modules to trigger decorator registration
        importlib.import_module("nexuscore.workflows.multi_llm_review")
        WorkflowRegistry.discover()


@click.group()
@click.version_option(package_name="nexuscore", prog_name="nexus")
def main() -> None:
    """NexusCore - Multi-agent AI development framework."""


@main.command()
@click.argument("requirement")
@click.option("--project-path", required=True, help="Target project directory")
@click.option("--language", default="ja", help="Language (ja/en)")
@click.option("--verbose", "-v", is_flag=True, help="Enable debug logging")
def run(requirement: str, project_path: str, language: str, verbose: bool) -> None:
    """Run a full development cycle with the given requirement."""
    import logging
    import os

    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    project_root = os.path.abspath(os.path.dirname(os.path.join(os.path.dirname(__file__), "..", "..", "..")))
    src_path = os.path.join(project_root, "src")
    if src_path not in sys.path:
        sys.path.insert(0, src_path)

    try:
        from nexuscore.core.agent_factory import assemble_agent_team
        from nexuscore.core.orchestrator import Orchestrator
    except ImportError as e:
        click.echo("Error: Failed to load NexusCore modules. Run 'pip install -e .' first.", err=True)
        if verbose:
            click.echo(f"  Details: {e}", err=True)
        raise SystemExit(1)

    if not os.path.isdir(project_path):
        click.echo(f"Error: Project path '{project_path}' does not exist.", err=True)
        click.echo("  Hint: Provide a valid directory with --project-path", err=True)
        raise SystemExit(1)

    click.echo(f"Starting NexusCore with requirement: {requirement}")
    click.echo(f"Project path: {project_path}")

    try:
        agents = assemble_agent_team(project_path)
        orchestrator = Orchestrator(**agents)

        result = orchestrator.run_full_project(requirement, language)
        click.echo(f"Result: {result.get('status', 'unknown')}")
    except FileNotFoundError as e:
        click.echo(f"Error: Required file not found: {e}", err=True)
        click.echo("  Hint: Check that the project directory contains the expected files.", err=True)
        raise SystemExit(1)
    except KeyError as e:
        click.echo(f"Error: Configuration error — missing key: {e}", err=True)
        click.echo("  Hint: Check your .env file and ensure all required API keys are set.", err=True)
        raise SystemExit(1)
    except ConnectionError as e:
        click.echo(f"Error: Connection failed — {e}", err=True)
        click.echo("  Hint: Check your network connection and API endpoint configuration.", err=True)
        raise SystemExit(1)
    except KeyboardInterrupt:
        click.echo("\nOperation cancelled by user.", err=True)
        raise SystemExit(130)
    except Exception as e:
        click.echo(f"Error: {type(e).__name__}: {e}", err=True)
        if verbose:
            import traceback
            click.echo(traceback.format_exc(), err=True)
        else:
            click.echo("  Run with --verbose for full details.", err=True)
        raise SystemExit(1)


@main.command("agents")
def list_agents() -> None:
    """List all available agents."""
    _ensure_discovery()

    agents = AgentRegistry.list_all()
    if not agents:
        click.echo("No agents registered.")
        return

    click.echo(f"Registered agents ({len(agents)}):\n")
    for name, cls in sorted(agents.items()):
        desc = get_agent_description(name) if name in get_all_descriptions() else ""
        prompt_preview = ""
        if hasattr(cls, "SYSTEM_PROMPT") and cls.SYSTEM_PROMPT:
            prompt_preview = cls.SYSTEM_PROMPT[:80].replace("\n", " ")
        click.echo(f"  {name:25s} {desc}")
        if prompt_preview:
            click.echo(f"  {'':25s} Prompt: {prompt_preview}...")
        click.echo()


@main.group("plugin")
def plugin_group() -> None:
    """Manage plugins (agents and workflows)."""


@plugin_group.command("list")
def plugin_list() -> None:
    """List all registered plugins."""
    _ensure_discovery()

    agents = AgentRegistry.list_all()
    workflows = WorkflowRegistry.list_all()

    click.echo("=== Agent Plugins ===")
    if agents:
        for name in sorted(agents):
            desc = get_agent_description(name) if name in get_all_descriptions() else "(external)"
            click.echo(f"  {name:25s} {desc}")
    else:
        click.echo("  (none)")

    click.echo(f"\n=== Workflow Plugins ({len(workflows)}) ===")
    if workflows:
        for name, cls in sorted(workflows.items()):
            desc = getattr(cls, "description", "") or ""
            click.echo(f"  {name:25s} {desc}")
    else:
        click.echo("  (none)")


@plugin_group.command("info")
@click.argument("name")
def plugin_info(name: str) -> None:
    """Show detailed info about a plugin."""
    _ensure_discovery()

    if AgentRegistry.has(name):
        cls = AgentRegistry.get(name)
        desc = get_agent_description(name) if name in get_all_descriptions() else "(external)"
        click.echo(f"Agent: {name}")
        click.echo(f"  Class: {cls.__module__}.{cls.__qualname__}")
        click.echo(f"  Description: {desc}")
        if hasattr(cls, "SYSTEM_PROMPT"):
            click.echo(f"  System prompt: {cls.SYSTEM_PROMPT[:200]}...")
    elif WorkflowRegistry.has(name):
        cls = WorkflowRegistry.get(name)
        click.echo(f"Workflow: {name}")
        click.echo(f"  Class: {cls.__module__}.{cls.__qualname__}")
        click.echo(f"  Description: {getattr(cls, 'description', '')}")
    else:
        click.echo(f"Plugin '{name}' not found.", err=True)
        raise SystemExit(1)


@main.command("version")
def show_version() -> None:
    """Show NexusCore version."""
    click.echo("NexusCore v8.2.0")


if __name__ == "__main__":
    main()
