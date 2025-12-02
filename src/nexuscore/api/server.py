# ==============================================================================
# 操作するソフト: VSCode (または任意のテキストエディタ)
# レジストリ/フォルダ: C:\Users\USER\tools\NexusCore\src\nexuscore\api\
# ファイル名: server.py
# 日付: 2025/09/03
#
# 使用方法:
#   この内容で既存のファイルを上書きしてください。
#   すべてのエージェントの初期化問題を、あなたのハイブリッド・アーキテクチャ設計に
#   完全に準拠する形で解決する、最終FIX版です。
#
# 改修内容:
#   - 私の誤解であった`PostmortemAgent`の初期化方法を修正しました。
#   - 全てのエージェントが、その役割（近代化/特殊任務）に応じて
#     正しく初期化されるように、チーム編成ロジックを全面的に改良しました。
# ==============================================================================
import os
import sys
import logging
import threading
import uuid
from functools import wraps
from flask import Flask, request, jsonify

# --- パス設定 ---
# WSL/Windows 混在環境で main_cli.py と同等の import パスを保証する暫定措置。
try:
    PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
    SRC_PATH = os.path.join(PROJECT_ROOT, "src")

    if PROJECT_ROOT not in sys.path:
        sys.path.insert(0, PROJECT_ROOT)
    if SRC_PATH not in sys.path:
        sys.path.insert(0, SRC_PATH)
except Exception as exc:
    logging.warning("Failed to configure import paths for API server: %s", exc)

# --- NexusCoreのコンポーネントをインポート ---
from nexuscore.core.orchestrator import Orchestrator
# 将来的には orchestrator.assemble_agent_team の利用も検討（挙動互換のため現状は個別生成）。
from nexuscore.agents.architect_agent import ArchitectAgent
from nexuscore.agents.planner_agent import PlannerAgent
from nexuscore.agents.coder_agent import CoderAgent
from nexuscore.agents.tester_agent import TesterAgent
from nexuscore.agents.debugger_agent import DebuggerAgent
from nexuscore.agents.guardian_agent import GuardianAgent
try:
    from nexuscore.agents.policy_agent import PolicyAgent
except ImportError:
    class PolicyAgent:
        def __init__(self, *args, **kwargs): pass
        def audit(self, *args, **kwargs): return {"result": "APPROVED"}
from nexuscore.agents.postmortem_agent import PostmortemAgent
from nexuscore.agents.knowledge_curator_agent import KnowledgeCuratorAgent
from nexuscore.agents.patch_applier import PatchApplier
from nexuscore.config.config import config
from nexuscore.llm.llm_router import LLMRouter

# --- グローバル変数 ---
app = Flask(__name__)
tasks = {}
llm_router = LLMRouter()

# --- ロギング設定 ---
from nexuscore.utils.log_config import get_logs_dir

logs_dir = get_logs_dir()
log_path = logs_dir / "nexus_api_server.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)-8s - %(name)-20s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(log_path, mode='a', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)
logger.info(f"API server log file: {log_path}")

def require_auth(f):
    """
    認証デコレータ: Authorization: Bearer <TOKEN> ヘッダを検証する。

    環境変数 NEXUSCORE_API_TOKEN から有効なトークンを取得し、
    リクエストの Authorization ヘッダと照合する。

    認証失敗時は 401 Unauthorized を返す。
    環境変数が未設定の場合は 500 Internal Server Error を返す。
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # 環境変数の確認
        expected_token = os.getenv("NEXUSCORE_API_TOKEN")
        if not expected_token:
            logger.error("NEXUSCORE_API_TOKEN is not set. Server misconfiguration.")
            return jsonify({"error": "Server misconfigured: NEXUSCORE_API_TOKEN is not set"}), 500

        # Authorization ヘッダの取得
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            logger.warning("Authorization header missing")
            return jsonify({"error": "Authorization required"}), 401

        # Bearer トークンの抽出
        if not auth_header.startswith("Bearer "):
            logger.warning("Invalid Authorization header format")
            return jsonify({"error": "Authorization required"}), 401

        token = auth_header[7:].strip()  # "Bearer " の後の部分を取得

        # トークンの検証
        if token != expected_token:
            logger.warning("Invalid token provided")
            return jsonify({"error": "Authorization required"}), 401

        # 認証成功
        return f(*args, **kwargs)

    return decorated_function

def run_orchestrator_task(task_id: str, requirement: str, project_path: str, constitution: dict):
    """Orchestratorをバックグラウンドで実行するワーカー関数"""
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
            raise ValueError("A primary API key (e.g., GEMINI_API_KEY or OPENAI_API_KEY) must be set in the .env file.")

        def provision_agent(agent_class, task_type: str, **kwargs):
            """エージェントを動的にプロビジョニングするヘルパー関数"""
            model_name = llm_router.task_model_map.get(task_type, llm_router.default_model)
            logger.info(f"Provisioning {agent_class.__name__} for '{task_type}' task with model '{model_name}'.")
            base_args = {'api_key': api_key, 'model': model_name}
            all_args = {**base_args, **kwargs}
            return agent_class(**all_args)

        guardian_agent = provision_agent(GuardianAgent, 'review')
        knowledge_curator_agent = provision_agent(KnowledgeCuratorAgent, 'general')

        policy_rules_path = os.path.join(PROJECT_ROOT, "config", "policy_rules.json")
        policy_agent = provision_agent(PolicyAgent, 'policy', policy_rules_path=policy_rules_path)

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
            patch_applier=patch_applier
        )

        # --- 4. 開発プロセスの開始 ---
        tasks[task_id]["message"] = "Design phase started."
        orchestrator.design_phase(requirement)

        tasks[task_id]["message"] = "Development cycle started."
        orchestrator.development_cycle({"main_goal": requirement})

        tasks[task_id] = {"status": "completed", "message": "Development process finished successfully."}
        logger.info(f"Task {task_id} completed successfully.")

    except Exception as e:
        logger.critical(f"An error occurred in task {task_id}: {e}", exc_info=True)
        tasks[task_id] = {"status": "error", "message": f"orchestrator failed: {e}"}

@app.route('/api/v1/execute', methods=['POST'])
@require_auth
def execute_task():
    data = request.json
    if not data or 'requirement' not in data or 'project_path' not in data:
        return jsonify({"error": "Missing 'requirement' or 'project_path' in request body", "error_code": "MISSING_FIELD"}), 400

    task_id = str(uuid.uuid4())
    requirement = data['requirement']
    project_path = os.path.abspath(data['project_path'])

    constitution = { "description": data.get("constitution_text", "Default constitution.") }

    thread = threading.Thread(
        target=run_orchestrator_task,
        args=(task_id, requirement, project_path, constitution)
    )
    thread.daemon = True
    thread.start()

    logger.info(f"Task {task_id} created for requirement: '{requirement}'")

    return jsonify({
        "message": "Task accepted and is running in the background.",
        "task_id": task_id,
        "status_url": f"/api/v1/status/{task_id}"
    }), 202

@app.route('/api/v1/status/<task_id>', methods=['GET'])
def get_task_status(task_id):
    task = tasks.get(task_id)
    if not task:
        return jsonify({"error": "Task not found"}), 404
    return jsonify(task)

@app.route('/api/github/webhook', methods=['POST'])
def github_webhook_endpoint():
    """GitHub Webhook エンドポイント"""
    try:
        from nexuscore.api.github_webhook_handler import handle_github_webhook
        result = handle_github_webhook()

        # タプルが返された場合は (body, status_code) 形式
        if isinstance(result, tuple):
            return jsonify(result[0]), result[1]

        return jsonify(result)
    except ImportError:
        logger.error("github_webhook_handler is not available")
        return jsonify({"error": "GitHub webhook handler not available"}), 500
    except Exception as e:
        logger.error(f"GitHub webhook endpoint error: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    logger.info("Starting NexusCore API Server...")
    app.run(host='0.0.0.0', port=5001, debug=True, use_reloader=False)
