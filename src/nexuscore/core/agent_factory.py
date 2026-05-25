from __future__ import annotations

import logging
from typing import Any

from nexuscore.llm.llm_router import LLMRouter
from nexuscore.plugins.builtin_agents import PARAM_NAME_MAP, register_builtin_agents
from nexuscore.plugins.registry import AgentRegistry
from nexuscore.services.patch_applier import PatchApplier


def assemble_agent_team(project_path: str) -> dict[str, Any]:
    """Build the agent team using AgentRegistry for discovery."""
    logger = logging.getLogger("AgentAssembler")

    # Ensure built-ins are registered
    if not AgentRegistry.list_all():
        register_builtin_agents()
        AgentRegistry.discover()

    llm_router = LLMRouter()

    # Map Orchestrator parameter names to registry entries
    agents: dict[str, Any] = {"llm_router": llm_router}

    for param_name, registry_name in PARAM_NAME_MAP.items():
        if registry_name == "patch_applier":
            agents[param_name] = PatchApplier()
        elif AgentRegistry.has(registry_name):
            agents[param_name] = AgentRegistry.get(registry_name)()
        else:
            logger.warning("Agent '%s' not found in registry, skipping.", registry_name)

    # ContextAgent (not a BaseAgent, so not in registry)
    try:
        from nexuscore.analyzer.context_agent import ContextAgent

        agents["context_agent"] = ContextAgent(project_root=project_path)
    except Exception as e:
        logger.warning("ContextAgent not available, skipping: %s", e)

    logger.info("Agent team assembled via Registry. total=%d (including llm_router).", len(agents))
    return agents
