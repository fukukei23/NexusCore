import logging
import os
import sys
import threading
import uuid

from fastapi import APIRouter, Depends, HTTPException, status

from ..dependencies.auth import AuthenticatedUser, get_current_user
from ..schemas.error import ErrorResponse
from ..schemas.execute import ExecuteRequest, ExecuteResponse, ExecuteStatusResponse
from ..utils.errors import make_not_found_error

router = APIRouter(tags=["execute"])

# --- project_path 安全性検証（C4: パスインジェクション型IDOR対策・2026-08-05）---
# 機密システムパス（realpath 解決後・前方一致）。配下を指すことを禁ずる。
_FORBIDDEN_PATH_PREFIXES = (
    "/etc",
    "/root",
    "/var/log",
    "/proc",
    "/sys",
    "/dev",
    "/boot",
    "/usr",
    "/sbin",
    "/bin",
    "/lib",
    "/lib64",
)

# パス要素のいずれかとして現れてはならない機密ディレクトリ名（クレデンシャル配置箇所）
_SENSITIVE_DIR_NAMES = frozenset({".ssh", ".gnupg", ".aws"})


def validate_project_path(raw_path: str) -> str:
    """project_path の安全性を検証し、realpath 解決済みの絶対パスを返す。

    - os.path.realpath でシンボリックリンクを解決（/tmp/evil -> /etc の回避）
    - 機密システムパス配下・機密ディレクトリ名を含む場合は ValueError を送出
    - 完全なユーザー別プロジェクト隔離（project_id 経由）は別タスク（M粒度）

    Args:
        raw_path: ユーザー入力の project_path

    Returns:
        検証済み絶対パス（realpath 解決済み）

    Raises:
        ValueError: 機密パス・シンボリックリンク攻撃の疑いがある場合
    """
    resolved = os.path.realpath(raw_path)

    for forbidden in _FORBIDDEN_PATH_PREFIXES:
        if resolved == forbidden or resolved.startswith(forbidden + os.sep):
            raise ValueError(
                f"project_path は機密システムパス（{forbidden}）配下を指せません"
            )

    parts = set(resolved.split(os.sep))
    sensitive_hit = parts & _SENSITIVE_DIR_NAMES
    if sensitive_hit:
        raise ValueError(
            f"project_path に機密ディレクトリ({sorted(sensitive_hit)})を含められません"
        )

    return resolved

# --- パス設定（既存の Flask 実装と同様） ---
try:
    PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
    SRC_PATH = os.path.join(PROJECT_ROOT, "src")

    if PROJECT_ROOT not in sys.path:
        sys.path.insert(0, PROJECT_ROOT)
    if SRC_PATH not in sys.path:
        sys.path.insert(0, SRC_PATH)
except (OSError, ValueError) as exc:
    logging.warning("Failed to configure import paths for API server: %s", exc)

# --- NexusCoreのコンポーネントをインポート ---
from nexuscore.agents.architect_agent import ArchitectAgent
from nexuscore.agents.coder_agent import CoderAgent
from nexuscore.agents.debugger_agent import DebuggerAgent
from nexuscore.agents.guardian_agent import GuardianAgent
from nexuscore.agents.planner_agent import PlannerAgent
from nexuscore.agents.tester_agent import TesterAgent
from nexuscore.core.orchestrator import Orchestrator

try:
    from nexuscore.agents.policy_agent import PolicyAgent
except ImportError:

    class PolicyAgent:  # type: ignore[no-redef]
        def __init__(self, *args, **kwargs):
            pass

        def audit(self, *args, **kwargs):
            return {"result": "APPROVED"}


from nexuscore.agents.knowledge_curator_agent import KnowledgeCuratorAgent
from nexuscore.agents.postmortem_agent import PostmortemAgent
from nexuscore.llm.llm_router import LLMRouter
from nexuscore.services.patch_applier import PatchApplier

# --- グローバル変数 ---
# server.py (deprecated Flask) から移行済み。tasks はこのモジュールで管理。
tasks = {}

llm_router = LLMRouter()

# --- ロギング設定 ---
from nexuscore.utils.log_config import get_logs_dir

logs_dir = get_logs_dir()
log_path = logs_dir / "nexus_api_server.log"

logger = logging.getLogger(__name__)


def run_orchestrator_task(task_id: str, requirement: str, project_path: str, constitution: dict):
    """
    Orchestratorをバックグラウンドで実行するワーカー関数

    既存の Flask 実装と同じロジックを使用。
    """
    logger.info(f"Starting background task: {task_id}")
    tasks[task_id] = {"status": "running", "message": "Initializing agents..."}

    try:
        # --- 1. 近代化されたエージェントの招集 (引数なし) ---
        architect_agent = ArchitectAgent()
        planner_agent = PlannerAgent()
        coder_agent = CoderAgent()
        tester_agent = TesterAgent()
        debugger_agent = DebuggerAgent()
        postmortem_agent = PostmortemAgent()

        # --- 2. 特殊任務エージェントのプロビジョニング (引数あり) ---
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError(
                "A primary API key (e.g., GEMINI_API_KEY or OPENAI_API_KEY) must be set in the .env file."
            )

        def provision_agent(agent_class, task_type: str, **kwargs):
            """エージェントを動的にプロビジョニングするヘルパー関数"""
            model_name = llm_router.task_model_map.get(task_type, llm_router.default_model)
            logger.info(
                f"Provisioning {agent_class.__name__} for '{task_type}' task with model '{model_name}'."
            )
            base_args = {"api_key": api_key, "model": model_name}
            all_args = {**base_args, **kwargs}
            return agent_class(**all_args)

        guardian_agent = provision_agent(GuardianAgent, "review")
        knowledge_curator_agent = provision_agent(KnowledgeCuratorAgent, "general")

        policy_rules_path = os.path.join(PROJECT_ROOT, "config", "policy_rules.json")
        policy_agent = provision_agent(PolicyAgent, "policy", policy_rules_path=policy_rules_path)

        # --- 3. ユーティリティと司令塔 (Orchestrator) の任命 ---
        patch_applier = PatchApplier()

        orchestrator = Orchestrator(
            project_path=project_path,
            constitution=constitution,
            requirement_agent=None,
            architect_agent=architect_agent,
            planner_agent=planner_agent,
            coder_agent=coder_agent,
            tester_agent=tester_agent,
            debugger_agent=debugger_agent,
            guardian_agent=guardian_agent,
            policy_agent=policy_agent,
            postmortem_agent=postmortem_agent,
            knowledge_curator_agent=knowledge_curator_agent,
            patch_applier=patch_applier,
        )

        # --- 4. 開発プロセスの開始 ---
        tasks[task_id]["message"] = "Design phase started."
        orchestrator.design_phase(requirement)

        tasks[task_id]["message"] = "Development cycle started."
        orchestrator.development_cycle({"main_goal": requirement})

        tasks[task_id] = {
            "status": "completed",
            "message": "Development process finished successfully.",
        }
        logger.info(f"Task {task_id} completed successfully.")

    except ValueError as e:
        logger.error(f"Configuration error in task {task_id}: {e}")
        tasks[task_id] = {"status": "error", "message": f"Configuration error: {e}. Check your .env file and API keys."}
    except ConnectionError as e:
        logger.error(f"Connection error in task {task_id}: {e}")
        tasks[task_id] = {"status": "error", "message": f"Connection failed: {e}. Check your network and API endpoints."}
    except ImportError as e:
        logger.error(f"Import error in task {task_id}: {e}")
        tasks[task_id] = {"status": "error", "message": f"Module not found: {e}. Run 'pip install -e .' to install dependencies."}
    except Exception as e:  # noqa: BLE001
        logger.critical(f"An error occurred in task {task_id}: {e}", exc_info=True)
        tasks[task_id] = {"status": "error", "message": f"orchestrator failed: {e}"}


@router.post(
    "/execute",
    response_model=ExecuteResponse,
    summary="Run self-healing job",
    status_code=status.HTTP_202_ACCEPTED,
    responses={
        401: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
async def execute_endpoint(
    payload: ExecuteRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> ExecuteResponse:
    """
    Execute エンドポイント

    指定されたプロジェクトパスに対して self-healing 実行をトリガーし、
    実行IDおよび現在のステータスを返します。

    このエンドポイントは認証済みクライアントからのみ利用可能です。
    （CR-FASTAPI-003 で認証を追加予定）

    Args:
        payload: 実行リクエスト（requirement, project_path, constitution_text）

    Returns:
        ExecuteResponse: タスクIDとステータスURLを含むレスポンス

    Raises:
        HTTPException: バリデーションエラーまたは内部エラー時
    """
    task_id = str(uuid.uuid4())
    try:
        project_path = validate_project_path(payload.project_path)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    constitution = {"description": payload.constitution_text or "Default constitution."}

    # バックグラウンドでタスクを実行
    thread = threading.Thread(
        target=run_orchestrator_task,
        args=(task_id, payload.requirement, project_path, constitution),
    )
    thread.daemon = True
    thread.start()

    logger.info(f"Task {task_id} created for requirement: '{payload.requirement}'")

    return ExecuteResponse(
        message="Task accepted and is running in the background.",
        task_id=task_id,
        status_url=f"/api/v1/status/{task_id}",
    )


@router.get(
    "/status/{task_id}",
    response_model=ExecuteStatusResponse,
    summary="Get task status",
    status_code=status.HTTP_200_OK,
    responses={
        401: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
async def get_task_status(
    task_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> ExecuteStatusResponse:
    """
    Get Task Status エンドポイント

    指定されたタスクIDの現在の状態を返します。
    既存の Flask 実装 (`get_task_status`) と互換性を保つ。

    Args:
        task_id: タスクID（UUID形式）

    Returns:
        ExecuteStatusResponse: タスクの状態情報

    Raises:
        HTTPException: タスクが見つからない場合（404）
    """
    task = tasks.get(task_id)
    if not task:
        raise make_not_found_error("Task", task_id)

    # 既存のFlask実装では、tasks辞書の値がそのまま返される
    # FastAPI版でも同様に、柔軟な構造を許容する
    return ExecuteStatusResponse(**task)
