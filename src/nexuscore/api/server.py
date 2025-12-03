# ==============================================================================
# DEPRECATED:
#   This module previously hosted legacy Flask REST API endpoints.
#   All internal REST APIs (/api/v1/execute, /api/v1/status) have been migrated to FastAPI
#   under src/nexuscore/api/fastapi_app.py and removed in CR-FASTAPI-008.
#   The module is kept only as a stub during the transition period.
#
#   Remaining Flask endpoints:
#   - /api/github/webhook (POST) - Will be migrated in a future CR
#
#   The `tasks` dictionary is kept here for backward compatibility with FastAPI routes
#   that import it. It will be moved to a shared module in a future refactoring.
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

# REMOVED: run_orchestrator_task() function has been removed in CR-FASTAPI-008.
# The FastAPI implementation uses its own run_orchestrator_task() function in src/nexuscore/api/routes/execute.py.

# REMOVED: Flask REST API endpoints /api/v1/execute and /api/v1/status/<task_id> have been removed in CR-FASTAPI-008.
# FastAPI equivalents are available at:
#   - POST /api/v1/execute (see src/nexuscore/api/routes/execute.py)
#   - GET /api/v1/status/{task_id} (see src/nexuscore/api/routes/execute.py)
# All clients MUST use the FastAPI endpoints.

# DEPRECATED: This endpoint is deprecated and will be removed in CR-FASTAPI-008.
# FastAPI equivalent: POST /api/v1/github/webhook (see src/nexuscore/api/routes/github_webhook.py)
# This Flask endpoint is kept only for backward compatibility during migration.
# All new clients MUST use the FastAPI endpoint.
@app.route('/api/github/webhook', methods=['POST'])
def github_webhook_endpoint():
    """
    GitHub Webhook エンドポイント（非推奨）

    このエンドポイントは非推奨です。FastAPI 版の /api/v1/github/webhook を使用してください。
    """
    logger.warning(
        "DEPRECATED endpoint /api/github/webhook called. "
        "Use FastAPI /api/v1/github/webhook instead. "
        "This endpoint will be removed in v0.9.0."
    )
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
