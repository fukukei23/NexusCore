"""
Orchestrator Dependency Injection for FastAPI (CR-NEXUS-029).

Provides request-scoped Orchestrator instance generation for API endpoints.
"""

import logging
import os
from pathlib import Path

from nexuscore.agents.architect_agent import ArchitectAgent
from nexuscore.agents.coder_agent import CoderAgent
from nexuscore.agents.debugger_agent import DebuggerAgent
from nexuscore.agents.guardian_agent import GuardianAgent
from nexuscore.agents.knowledge_curator_agent import KnowledgeCuratorAgent
from nexuscore.services.patch_applier import PatchApplier
from nexuscore.agents.planner_agent import PlannerAgent
from nexuscore.agents.policy_agent import PolicyAgent
from nexuscore.agents.postmortem_agent import PostmortemAgent
from nexuscore.agents.requirement_agent import RequirementAgent
from nexuscore.agents.tester_agent import TesterAgent
from nexuscore.core.orchestrator import Orchestrator
from nexuscore.llm.llm_router import LLMRouter

logger = logging.getLogger(__name__)


def _prepare_local_knowledge_base(project_path: str, project_root: str) -> str | None:
    """
    Ensure each project has its own writable knowledge base copy.

    Args:
        project_path: Target project path
        project_root: NexusCore project root directory

    Returns:
        Path to knowledge base file, or None if unavailable
    """
    import shutil

    template_path = os.path.join(project_root, "fkb_local.json")
    project_kb_path = os.path.join(project_path, "fkb_local.json")

    if not os.path.exists(template_path):
        logger.warning("Global knowledge base template not found at %s", template_path)
        return None

    if os.path.exists(project_kb_path):
        return project_kb_path

    try:
        shutil.copy(template_path, project_kb_path)
        logger.info("Copied fkb_local.json template into project directory.")
    except Exception as copy_error:
        logger.error("Failed to copy knowledge base template: %s", copy_error, exc_info=True)
        return None

    return project_kb_path


def _load_guardian_credentials() -> tuple[str, str]:
    """
    Load Guardian agent credentials from environment.

    Returns:
        Tuple of (api_key, model)
    """
    api_key = os.getenv("GUARDIAN_API_KEY", "")
    model = os.getenv("GUARDIAN_MODEL", "")
    return api_key, model


def get_orchestrator(project_path: str | None = None, language: str = "ja") -> Orchestrator:
    """
    Generate a new Orchestrator instance for API request (request-scoped).

    This function creates a fresh Orchestrator instance with all required agents
    initialized. Each API request gets its own Orchestrator instance to avoid
    state leakage and race conditions.

    Args:
        project_path: Project directory path (must exist and be writable)
        language: Language for RequirementAgent ("ja" or "en")

    Returns:
        Orchestrator instance ready for use

    Raises:
        ValueError: If project_path is invalid
        RuntimeError: If agent initialization fails
    """
    # Resolve project root (NexusCore root directory)
    # Assume we're in src/nexuscore/api/deps/orchestrator.py
    current_file = Path(__file__).resolve()
    project_root = current_file.parents[4]  # Go up to NexusCore root

    # Get project path from environment or use default
    if project_path is None:
        project_path = os.getenv(
            "NEXUSCORE_PROJECT_PATH", str(project_root / ".nexus" / "api_runs")
        )

    # Ensure project path exists
    project_path = os.path.abspath(project_path)
    os.makedirs(project_path, exist_ok=True)

    # Prepare knowledge base
    local_kb_path = _prepare_local_knowledge_base(project_path, str(project_root))

    # Load guardian credentials
    guardian_api_key, guardian_model = _load_guardian_credentials()

    # Initialize all agents
    requirement_agent = RequirementAgent(language=language, use_ui=False)
    architect = ArchitectAgent()
    planner = PlannerAgent()
    coder = CoderAgent()
    tester = TesterAgent()
    debugger = DebuggerAgent(knowledge_base_path=local_kb_path)
    guardian = GuardianAgent(api_key=guardian_api_key, model=guardian_model)
    policy_agent = PolicyAgent(
        policy_rules_path=os.path.join(str(project_root), "config", "policy_rules.json")
    )
    postmortem_agent = PostmortemAgent()
    knowledge_curator_agent = KnowledgeCuratorAgent(api_key=guardian_api_key, model=guardian_model)
    patch_applier = PatchApplier()
    llm_router = LLMRouter()

    # Default constitution (can be overridden per request if needed)
    constitution = {
        "description": "",
        "quality_gate": {"MIN_COVERAGE": 90, "MIN_PYLINT_SCORE": 8.0},
    }

    # Create Orchestrator instance
    orchestrator = Orchestrator(
        project_path=project_path,
        constitution=constitution,
        requirement_agent=requirement_agent,
        architect_agent=architect,
        planner_agent=planner,
        coder_agent=coder,
        tester_agent=tester,
        debugger_agent=debugger,
        guardian_agent=guardian,
        policy_agent=policy_agent,
        postmortem_agent=postmortem_agent,
        knowledge_curator_agent=knowledge_curator_agent,
        patch_applier_agent=patch_applier,
        llm_router=llm_router,
    )

    return orchestrator
