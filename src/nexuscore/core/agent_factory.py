"""Agent team assembly factory for NexusCore Orchestrator."""

from __future__ import annotations

import logging
import os
from typing import Any

from nexuscore.agents.architect_agent import ArchitectAgent
from nexuscore.agents.coder_agent import CoderAgent
from nexuscore.agents.debugger_agent import DebuggerAgent
from nexuscore.agents.guardian_agent import GuardianAgent
from nexuscore.agents.knowledge_curator_agent import KnowledgeCuratorAgent
from nexuscore.agents.planner_agent import PlannerAgent
from nexuscore.agents.policy_agent import PolicyAgent
from nexuscore.agents.postmortem_agent import PostmortemAgent
from nexuscore.agents.requirement_agent import RequirementAgent
from nexuscore.agents.tester_agent import TesterAgent
from nexuscore.llm.llm_router import LLMRouter
from nexuscore.services.patch_applier import PatchApplier


def assemble_agent_team(project_path: str) -> dict[str, Any]:
    """Build the default agent team and LLMRouter for the Orchestrator."""
    logger = logging.getLogger("AgentAssembler")
    logger.info("Assembling agent team for NexusCore Orchestrator v8.2...")

    llm_router = LLMRouter()

    requirement_agent = RequirementAgent()
    architect_agent = ArchitectAgent()
    planner_agent = PlannerAgent()
    coder_agent = CoderAgent()
    tester_agent = TesterAgent()
    debugger_agent = DebuggerAgent()
    guardian_agent = GuardianAgent()
    policy_agent = PolicyAgent()
    postmortem_agent = PostmortemAgent()
    curator_api_key = os.getenv("GLM_API_KEY", "")
    curator_model = os.getenv("NEXUS_TASK_MODEL_KNOWLEDGE", "glm-4-plus")

    if not curator_api_key:
        raise RuntimeError(
            "KnowledgeCuratorAgent requires GLM_API_KEY. Set it in the environment before assembling agent team."
        )

    knowledge_curator_agent = KnowledgeCuratorAgent(
        api_key=curator_api_key,
        model=curator_model,
    )
    patch_applier_agent = PatchApplier()

    agents: dict[str, Any] = {
        "requirement_agent": requirement_agent,
        "architect_agent": architect_agent,
        "planner_agent": planner_agent,
        "coder_agent": coder_agent,
        "tester_agent": tester_agent,
        "debugger_agent": debugger_agent,
        "guardian_agent": guardian_agent,
        "policy_agent": policy_agent,
        "postmortem_agent": postmortem_agent,
        "knowledge_curator_agent": knowledge_curator_agent,
        "patch_applier_agent": patch_applier_agent,
        "llm_router": llm_router,
    }

    logger.info(f"Agent team assembled. total={len(agents)} (including llm_router).")
    return agents
