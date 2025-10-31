# ==============================================================================
# フォルダ: src/api
# ファイル名: server.py
# メモ: NexusCoreの機能を外部に公開するためのFlask APIサーバー。
#      Orchestratorの実行をバックグラウンドスレッドで処理する。
# ==============================================================================
import os
import sys
import logging
import threading
import uuid
from flask import Flask, request, jsonify

# --- パス設定 ---
# このファイルがどこから実行されても、srcフォルダ内のモジュールを見つけられるようにする
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# --- NexusCoreのコンポーネントをインポート ---
from src.core.orchestrator import Orchestrator
from src.agents.architect_agent import ArchitectAgent
from src.agents.planner_agent import PlannerAgent
from src.agents.coder_agent import CoderAgent
from src.agents.tester_agent import TesterAgent
from src.agents.debugger_agent import DebuggerAgent
from src.agents.guardian_agent import GuardianAgent
from src.agents.policy_agent import PolicyAgent
from src.agents.postmortem_agent import PostmortemAgent
from src.agents.knowledge_curator_agent import KnowledgeCuratorAgent
from src.utils.config import config

# --- グローバル変数 ---
app = Flask(__name__)
tasks = {} # 実行中のタスクの状態を保存する辞書

# --- ロギング設定 ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)-8s - %(name)-20s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("nexus_api_server.log", mode='w', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

def run_orchestrator_task(task_id: str, requirement: str, project_path: str, constitution: dict):
    """Orchestratorをバックグラウンドで実行するワーカー関数"""
    logger.info(f"Starting background task: {task_id}")
    tasks[task_id] = {"status": "running", "message": "Initializing agents..."}
    
    try:
        # --- AI開発チーム（エージェント群）の招集 ---
        model_name = "gemini-1.5-pro-latest" 
        api_key = config.GEMINI_API_KEY_AGENT_A
        
        if not api_key:
            raise ValueError("GEMINI_API_KEY_AGENT_A is not set in the .env file.")

        architect = ArchitectAgent(api_key=api_key, model=model_name)
        planner = PlannerAgent(api_key=api_key, model=model_name)
        coder = CoderAgent(api_key=api_key, model=model_name)
        tester = TesterAgent(api_key=api_key, model=model_name)
        debugger = DebuggerAgent(api_key=api_key, model=model_name, project_path=project_path)
        guardian = GuardianAgent(api_key=api_key, model=model_name)
        policy_agent = PolicyAgent(api_key=api_key, model=model_name)
        postmortem_agent = PostmortemAgent(api_key=api_key, model=model_name)
        knowledge_curator_agent = KnowledgeCuratorAgent(api_key=api_key, model=model_name)

        # --- 司令塔 (Orchestrator) の任命 ---
        orchestrator = Orchestrator(
            project_path=project_path,
            constitution=constitution,
            architect=architect,
            planner=planner,
            coder=coder,
            tester=tester,
            debugger=debugger,
            guardian=guardian,
            policy_agent=policy_agent,
            postmortem_agent=postmortem_agent,
            knowledge_curator_agent=knowledge_curator_agent
        )

        # --- 開発プロセスの開始 ---
        tasks[task_id]["message"] = "Design phase started."
        orchestrator.design_phase(requirement)
        
        tasks[task_id]["message"] = "Development cycle started."
        orchestrator.development_cycle(requirement)
        
        tasks[task_id] = {"status": "completed", "message": "Development process finished successfully."}
        logger.info(f"Task {task_id} completed successfully.")

    except Exception as e:
        logger.critical(f"An error occurred in task {task_id}: {e}", exc_info=True)
        tasks[task_id] = {"status": "error", "message": str(e)}

@app.route('/api/v1/execute', methods=['POST'])
def execute_task():
    """新しい開発タスクを開始するAPIエンドポイント"""
    data = request.json
    if not data or 'requirement' not in data or 'project_path' not in data:
        return jsonify({"error": "Missing 'requirement' or 'project_path' in request body"}), 400

    task_id = str(uuid.uuid4())
    requirement = data['requirement']
    project_path = os.path.abspath(data['project_path'])
    
    # プロジェクト憲法を定義 (将来的にはリクエストから受け取ることも可能)
    constitution = {
        "description": data.get("constitution_text", "Default constitution: write clean, maintainable code."),
        "quality_gate": {
            "MIN_COVERAGE": 90,
            "MIN_PYLINT_SCORE": 8.0
        }
    }

    # バックグラウンドでOrchestratorを実行
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
    """タスクの現在の状態を返すAPIエンドポイント"""
    task = tasks.get(task_id)
    if not task:
        return jsonify({"error": "Task not found"}), 404
    return jsonify(task)

if __name__ == '__main__':
    logger.info("Starting NexusCore API Server...")
    app.run(host='0.0.0.0', port=5001, debug=True)
