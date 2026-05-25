from __future__ import annotations

from nexuscore.agents.architect_agent import ArchitectAgent
from nexuscore.agents.base_agent import BaseAgent
from nexuscore.agents.coder_agent import CoderAgent
from nexuscore.agents.constitutional_council_agent import ConstitutionalCouncilAgent
from nexuscore.agents.debugger_agent import DebuggerAgent
from nexuscore.agents.guardian_agent import GuardianAgent
from nexuscore.agents.knowledge_curator_agent import KnowledgeCuratorAgent
from nexuscore.agents.mutation_tester_agent import MutationTesterAgent
from nexuscore.agents.planner_agent import PlannerAgent
from nexuscore.agents.policy_agent import PolicyAgent
from nexuscore.agents.postmortem_agent import PostmortemAgent
from nexuscore.agents.requirement_agent import RequirementAgent
from nexuscore.agents.tester_agent import TesterAgent
from nexuscore.plugins.registry import AgentRegistry

# Agent name → (class, description)
_BUILTIN_AGENTS: dict[str, tuple[type[BaseAgent], str]] = {
    "architect": (ArchitectAgent, "Architecture design"),
    "coder": (CoderAgent, "Code generation"),
    "constitutional_council": (ConstitutionalCouncilAgent, "Governance & decision-making"),
    "debugger": (DebuggerAgent, "Error fixing & debugging"),
    "guardian": (GuardianAgent, "Multi-layer quality gate"),
    "knowledge_curator": (KnowledgeCuratorAgent, "Knowledge management"),
    "mutation_tester": (MutationTesterAgent, "Test suite strength measurement"),
    "planner": (PlannerAgent, "Implementation planning"),
    "policy": (PolicyAgent, "Policy enforcement"),
    "postmortem": (PostmortemAgent, "Failure analysis & post-verification"),
    "requirement": (RequirementAgent, "Requirements analysis & specification"),
    "tester": (TesterAgent, "Automated test generation"),
}

# Map from agent parameter name in Orchestrator → registry name
PARAM_NAME_MAP: dict[str, str] = {
    "requirement_agent": "requirement",
    "architect_agent": "architect",
    "planner_agent": "planner",
    "coder_agent": "coder",
    "tester_agent": "tester",
    "debugger_agent": "debugger",
    "guardian_agent": "guardian",
    "policy_agent": "policy",
    "postmortem_agent": "postmortem",
    "knowledge_curator_agent": "knowledge_curator",
    "constitutional_council_agent": "constitutional_council",
    "patch_applier_agent": "patch_applier",
}

_AGENT_DESCRIPTIONS: dict[str, str] = {}


def register_builtin_agents() -> None:
    """Register all built-in agents into the global AgentRegistry."""
    for name, (cls, desc) in _BUILTIN_AGENTS.items():
        AgentRegistry.register(name, cls)
        _AGENT_DESCRIPTIONS[name] = desc


def get_agent_description(name: str) -> str:
    return _AGENT_DESCRIPTIONS.get(name, "")


def get_all_descriptions() -> dict[str, str]:
    return _AGENT_DESCRIPTIONS.copy()
