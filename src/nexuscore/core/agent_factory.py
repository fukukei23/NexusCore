from __future__ import annotations

import logging
from typing import Any

from nexuscore.llm.llm_router import LLMRouter
from nexuscore.plugins.builtin_agents import PARAM_NAME_MAP, register_builtin_agents
from nexuscore.plugins.registry import AgentRegistry
from nexuscore.services.patch_applier import PatchApplier


def assemble_agent_team(
    project_path: str,
    language: str = "ja",
    knowledge_base_path: str | None = None,
) -> dict[str, Any]:
    """Build the agent team using AgentRegistry for discovery.

    Args:
        project_path: Target project root path.
        language: Language for RequirementAgent ("ja" or "en").
        knowledge_base_path: Optional local KB path for DebuggerAgent
            (API request-scoped でプロジェクト固有 KB を使用する場合に指定)。
    """
    logger = logging.getLogger("AgentAssembler")

    # Ensure built-ins are registered
    if not AgentRegistry.list_all():
        register_builtin_agents()
        AgentRegistry.discover()

    llm_router = LLMRouter()

    # Map Orchestrator parameter names to registry entries
    agents: dict[str, Any] = {"llm_router": llm_router}

    for param_name, registry_name in PARAM_NAME_MAP.items():
        if AgentRegistry.has(registry_name):
            agents[param_name] = AgentRegistry.get(registry_name)()
        else:
            logger.warning("Agent '%s' not found in registry, skipping.", registry_name)

    # language を RequirementAgent に伝搬（デフォルト "ja"、get_orchestrator 経由で上書き可）
    if AgentRegistry.has("requirement"):
        agents["requirement_agent"] = AgentRegistry.get("requirement")(language=language)

    # knowledge_base_path を DebuggerAgent に伝搬（プロジェクト固有 KB）
    if knowledge_base_path is not None and AgentRegistry.has("debugger"):
        agents["debugger_agent"] = AgentRegistry.get("debugger")(
            knowledge_base_path=knowledge_base_path
        )

    # PatchApplier is a service, not a BaseAgent
    agents["patch_applier_agent"] = PatchApplier()

    # ContextAgent (not a BaseAgent, so not in registry)
    try:
        from nexuscore.analyzer.context_agent import ContextAgent

        agents["context_agent"] = ContextAgent(project_root=project_path)
    except Exception as e:  # noqa: BLE001 — optional agent, skip if unavailable
        logger.warning("ContextAgent not available, skipping: %s", e)

    logger.info("Agent team assembled via Registry. total=%d (including llm_router).", len(agents))
    return agents
