# ==============================================================================
# ファイル名: run_quality_loop_test.py
# 場所: プロジェクトのルートディレクトリ
# メモ: DebuggerAgentの初期化を最終仕様に合わせた、完成版テストスクリプト。
# ==============================================================================

import os
import shutil
import logging
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

from src.core.orchestrator import Orchestrator
from src.agents.architect_agent import ArchitectAgent
from src.agents.planner_agent import PlannerAgent
from src.agents.coder_agent import CoderAgent
from src.agents.tester_agent import TesterAgent
from src.agents.debugger_agent import DebuggerAgent
from src.agents.guardian_agent import GuardianAgent
from src.agents.policy_agent import PolicyAgent

# --- テスト用の設定 ---
API_KEY = os.environ.get("OPENAI_API_KEY")
MODEL = "gpt-4o"
TEST_PROJECT_PATH = "quality_loop_test_sandbox"

# --- ロギング設定 ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

def setup_test_environment():
    """テスト用のサンドボックス環境を準備する"""
    logger.info(f"Setting up test environment at: ./{TEST_PROJECT_PATH}")
    if os.path.exists(TEST_PROJECT_PATH):
        shutil.rmtree(TEST_PROJECT_PATH)
    
    app_dir = Path(TEST_PROJECT_PATH) / "app"
    tests_dir = Path(TEST_PROJECT_PATH) / "tests"
    app_dir.mkdir(parents=True, exist_ok=True)
    tests_dir.mkdir(exist_ok=True)
    (app_dir / "__init__.py").touch()
    (tests_dir / "__init__.py").touch()
    (app_dir / "main.py").write_text("# Initial application file\n", encoding='utf-8')
    logger.info("Test environment setup complete.")

def run_test():
    """品質改善ループのE2Eテストを実行する"""
    if not API_KEY:
        logger.error("APIキーが見つかりません。.envファイルに 'OPENAI_API_KEY=...' を設定するか、環境変数を確認してください。")
        return
        
    setup_test_environment()

    logger.info("--- Initializing Agents with REAL LLM model ---")
    
    architect = ArchitectAgent(API_KEY, MODEL)
    planner = PlannerAgent(API_KEY, MODEL)
    coder = CoderAgent(API_KEY, MODEL)
    tester = TesterAgent(API_KEY, MODEL)
    # ★ DebuggerAgentにプロジェクトパスを渡すように修正
    debugger = DebuggerAgent(API_KEY, MODEL, knowledge_base_path="fkb_local.json", project_path=TEST_PROJECT_PATH)
    guardian = GuardianAgent(API_KEY, MODEL)
    policy_agent = PolicyAgent(API_KEY, MODEL, policy_rules_path="config/policy_rules.json")

    logger.info(f"--- Initializing Orchestrator (Model: {MODEL}) ---")
    
    orchestrator = Orchestrator(
        project_path=TEST_PROJECT_PATH,
        constitution="Test Constitution: Write clean, documented, and professional code.",
        architect=architect,
        planner=planner,
        coder=coder,
        tester=tester,
        debugger=debugger,
        guardian=guardian,
        policy_agent=policy_agent
    )

    violating_task = {
        "name": "create_user_greeting",
        "module": "main",
        "description": "Create a function 'greet' that takes a name and returns a greeting message. It should be simple."
    }
    
    logger.info("\n" + "="*50)
    logger.info("🚀 STARTING TEST: QUALITY IMPROVEMENT FEEDBACK LOOP")
    logger.info("="*50 + "\n")

    orchestrator.execute_task(violating_task)

    logger.info("\n" + "="*50)
    logger.info("🔬 FINAL VERIFICATION")
    logger.info("="*50)
    
    final_code_path = Path(TEST_PROJECT_PATH) / "app" / "main.py"
    if final_code_path.exists():
        final_code = final_code_path.read_text(encoding='utf-8')
        logger.info(f"Final generated code in {final_code_path}:\n---\n{final_code}\n---")
        
        if "print(" not in final_code and '"""' in final_code:
            logger.info("✅ SUCCESS: Final code appears to have fixed the violations (no 'print', has docstring).")
        else:
            logger.error("❌ FAILURE: Final code still seems to contain policy violations.")
    else:
        logger.error("❌ FAILURE: Final code was not generated.")

if __name__ == "__main__":
    run_test()
