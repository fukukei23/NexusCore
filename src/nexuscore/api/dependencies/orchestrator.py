import logging
import os
from pathlib import Path

from nexuscore.core.agent_factory import assemble_agent_team
from nexuscore.core.orchestrator import Orchestrator

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
    except (OSError, shutil.Error) as copy_error:
        logger.error("Failed to copy knowledge base template: %s", copy_error, exc_info=True)
        return None

    return project_kb_path


def get_orchestrator(project_path: str | None = None, language: str = "ja") -> Orchestrator:
    """
    Generate a new Orchestrator instance for API request (request-scoped).

    エージェント構築は assemble_agent_team() に統一（CLI/webapp/UI 経路と共通化）。
    GuardianAgent の cred 出所は GuardianAgent.__init__ 内の env 読込に集約されており、
    ここでは cred を扱わない（旧 _load_guardian_credentials は廃止）。

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

    # Assemble agent team via shared factory (他3経路と同一パス)
    agents = assemble_agent_team(
        project_path,
        language=language,
        knowledge_base_path=local_kb_path,
    )

    # Default constitution (can be overridden per request if needed)
    constitution = {
        "description": "",
        "quality_gate": {"MIN_COVERAGE": 90, "MIN_PYLINT_SCORE": 8.0},
    }

    # Create Orchestrator instance
    orchestrator = Orchestrator(
        project_path=project_path,
        constitution=constitution,
        **agents,
    )

    return orchestrator
