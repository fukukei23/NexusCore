# ==============================================================================
# フォルダ: (プロジェクトルート)
# ファイル名: run_quality_gate_test.py
# メモ: Orchestratorに実装された「品質ゲート」が正しく機能するかを
#      検証するためのE2Eテストスクリプト。【ImportError修正版】
# ==============================================================================

import logging
import os
import shutil
from pathlib import Path

from dotenv import load_dotenv

# .envファイルから環境変数を読み込む
load_dotenv()

# --- プロジェクトのコアコンポーネントをインポート ---
# スクリプトがルートにあるため、パス設定は不要
# ▼▼▼▼▼ ここからが最重要修正点 ▼▼▼▼▼
# 各エージェントを、それぞれのファイル(モジュール)から直接インポートするように修正
from src.agents.architect_agent import ArchitectAgent
from src.agents.coder_agent import CoderAgent
from src.agents.debugger_agent import DebuggerAgent
from src.agents.guardian_agent import GuardianAgent
from src.agents.knowledge_curator_agent import KnowledgeCuratorAgent
from src.agents.planner_agent import PlannerAgent
from src.agents.policy_agent import PolicyAgent
from src.agents.postmortem_agent import PostmortemAgent
from src.agents.tester_agent import TesterAgent
from src.core.orchestrator import Orchestrator

# ▲▲▲▲▲ ここまでが最重要修正点 ▲▲▲▲▲
from src.utils.config import config

# --- テスト用の設定 ---
# 環境変数からAPIキーとモデルを取得、なければデフォルト値を使用
API_KEY = config.GEMINI_API_KEY_AGENT_A
MODEL = "gemini-1.5-pro-latest"
TEST_PROJECT_PATH = "quality_gate_test_sandbox"

# --- ロギング設定 ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("quality_gate_test_run.log", mode="w", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)


def setup_test_environment():
    """テスト用のサンドボックス環境を準備する"""
    logger.info(f"Setting up test environment at: ./{TEST_PROJECT_PATH}")
    if os.path.exists(TEST_PROJECT_PATH):
        shutil.rmtree(TEST_PROJECT_PATH)
    os.makedirs(TEST_PROJECT_PATH)

    # ダミーのfkb_local.jsonを作成
    Path(TEST_PROJECT_PATH, "fkb_local.json").write_text("[]", encoding="utf-8")

    # ダミーのpolicy_rules.jsonを作成
    config_dir = Path(TEST_PROJECT_PATH, "config")
    config_dir.mkdir()
    Path(config_dir, "policy_rules.json").write_text("[]", encoding="utf-8")

    # pytest-covのための設定ファイルを作成
    pyproject_toml_content = """
[tool.pytest.ini_options]
pythonpath = ["."]
addopts = "--cov=app --cov-report=term-missing"

[tool.coverage.run]
source = ["app"]

[tool.coverage.report]
fail_under = 0  # テスト自体はカバレッジで失敗させない
show_missing = true
"""
    Path(TEST_PROJECT_PATH, "pyproject.toml").write_text(pyproject_toml_content, encoding="utf-8")


def main():
    """品質ゲートのテストを実行するメイン関数"""
    if not API_KEY:
        logger.error("GEMINI_API_KEY_AGENT_A is not set in the .env file. Aborting test.")
        return

    setup_test_environment()

    try:
        # --- 憲法 (品質基準を含む) ---
        constitution = {
            "description": "This is a test constitution for the quality gate.",
            "quality_gate": {"MIN_COVERAGE": 90, "MIN_PYLINT_SCORE": 8.0},
        }

        # --- AIエージェントの初期化 ---
        project_abs_path = os.path.abspath(TEST_PROJECT_PATH)
        architect = ArchitectAgent(api_key=API_KEY, model=MODEL)
        planner = PlannerAgent(api_key=API_KEY, model=MODEL)
        coder = CoderAgent(api_key=API_KEY, model=MODEL)
        tester = TesterAgent(api_key=API_KEY, model=MODEL)
        debugger = DebuggerAgent(api_key=API_KEY, model=MODEL, project_path=project_abs_path)
        guardian = GuardianAgent(api_key=API_KEY, model=MODEL)
        policy_agent = PolicyAgent(
            api_key=API_KEY,
            model=MODEL,
            policy_rules_path=f"{TEST_PROJECT_PATH}/config/policy_rules.json",
        )
        postmortem_agent = PostmortemAgent(api_key=API_KEY, model=MODEL)
        knowledge_curator_agent = KnowledgeCuratorAgent()

        # --- Orchestratorの初期化 ---
        orchestrator = Orchestrator(
            project_path=project_abs_path,
            constitution=constitution,
            architect=architect,
            planner=planner,
            coder=coder,
            tester=tester,
            debugger=debugger,
            guardian=guardian,
            policy_agent=policy_agent,
            postmortem_agent=postmortem_agent,
            knowledge_curator_agent=knowledge_curator_agent,
        )

        # --- テストシナリオの定義 ---
        # このタスクはシンプルなので、AIは最初ドキュメントなしのコードを生成しやすい
        task_to_execute = {
            "name": "add_two_numbers",
            "module": "calculator",
            "description": "Create a function 'add' that takes two integers 'a' and 'b' and returns their sum.",
        }

        logger.info("\n" + "=" * 50)
        logger.info("🚀 STARTING TEST: QUALITY GATE FEEDBACK LOOP")
        logger.info("=" * 50 + "\n")

        # 設計フェーズをスキップし、開発サイクルのみを実行
        orchestrator.execute_task(task_to_execute)

        # --- 結果の検証 ---
        logger.info("\n" + "=" * 50)
        logger.info("🔬 FINAL VERIFICATION")
        logger.info("=" * 50)

        final_code_path = Path(TEST_PROJECT_PATH) / "app" / "calculator.py"
        log_file_path = Path("quality_gate_test_run.log")

        test_passed = True

        # 1. 最終的なコードが存在するか
        if final_code_path.exists():
            final_code = final_code_path.read_text(encoding="utf-8")
            logger.info(f"Final generated code in {final_code_path}:\n---\n{final_code}\n---")
            # 2. 最終コードにdocstringが含まれているか（品質改善の結果）
            if '"""' not in final_code and "'''" not in final_code:
                logger.error("VERIFICATION FAILED: Final code does not contain a docstring.")
                test_passed = False
            else:
                logger.info("✅ VERIFICATION PASSED: Final code contains a docstring.")
        else:
            logger.error(
                f"VERIFICATION FAILED: Final code file '{final_code_path}' was not generated."
            )
            test_passed = False

        # 3. ログに品質ゲート違反の記録があるか
        if log_file_path.exists():
            log_content = log_file_path.read_text(encoding="utf-8")
            if "QUALITY GATE VIOLATION" in log_content:
                logger.info(
                    "✅ VERIFICATION PASSED: 'QUALITY GATE VIOLATION' found in logs, indicating the gate was triggered."
                )
            else:
                logger.error(
                    "VERIFICATION FAILED: 'QUALITY GATE VIOLATION' not found in logs. The quality gate may not have been triggered."
                )
                test_passed = False
        else:
            logger.error("VERIFICATION FAILED: Log file not found.")
            test_passed = False

        logger.info("\n" + "-" * 20)
        if test_passed:
            logger.info("🎉🎉🎉 OVERALL TEST RESULT: PASSED 🎉🎉🎉")
        else:
            logger.error("😭😭😭 OVERALL TEST RESULT: FAILED 😭😭😭")
        logger.info("-" * 20)

    except Exception as e:
        logger.critical(f"An unexpected error occurred during the test run: {e}", exc_info=True)
    finally:
        # クリーンアップ
        # logger.info("Cleaning up test environment...")
        # if os.path.exists(TEST_PROJECT_PATH):
        #     shutil.rmtree(TEST_PROJECT_PATH)
        pass  # ログを確認できるよう、サンドボックスは残す


if __name__ == "__main__":
    main()
