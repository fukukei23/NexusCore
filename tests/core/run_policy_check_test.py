# ==============================================================================
# ファイル名: run_policy_check_test.py (修正版)
# 場所: プロジェクトのルートディレクトリ
# メモ: PolicyAgentが開発サイクルに正しく組み込まれ、ポリシー違反を
#      検知・ブロックできるかを検証するためのE2Eテストスクリプト。
#      << 修正点 >>
#      - __init__.py をテスト用サンドボックスに自動生成し、
#        pytestのモジュール解決エラーを修正。
# ==============================================================================

import logging
import os
import shutil
from pathlib import Path  # pathlibをインポート

from src.agents.architect_agent import ArchitectAgent
from src.agents.coder_agent import CoderAgent
from src.agents.debugger_agent import DebuggerAgent
from src.agents.guardian_agent import GuardianAgent
from src.agents.planner_agent import PlannerAgent
from src.agents.policy_agent import PolicyAgent
from src.agents.tester_agent import TesterAgent

# --- プロジェクトのコアコンポーネントをインポート ---
from src.core.orchestrator import Orchestrator

# --- テスト用の設定 ---
TEST_PROJECT_PATH = "policy_test_sandbox"
API_KEY = "dummy_key_for_testing"
MODEL = "dummy"

# --- ロギング設定 ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


def setup_test_environment():
    """テスト用のサンドボックス環境を準備する"""
    logger.info(f"Setting up test environment at: ./{TEST_PROJECT_PATH}")
    if os.path.exists(TEST_PROJECT_PATH):
        shutil.rmtree(TEST_PROJECT_PATH)

    # --- ★★★★★ ここからが最重要修正点 ★★★★★ ---
    # 各ディレクトリを作成し、同時に__init__.pyファイルも作成する
    app_dir = Path(TEST_PROJECT_PATH) / "app"
    tests_dir = Path(TEST_PROJECT_PATH) / "tests"

    app_dir.mkdir(parents=True, exist_ok=True)
    tests_dir.mkdir(exist_ok=True)

    # __init__.py を作成して、ディレクトリをPythonパッケージとして認識させる
    (app_dir / "__init__.py").touch()
    (tests_dir / "__init__.py").touch()

    # ダミーの初期ファイルを作成
    (app_dir / "main.py").write_text("# Initial application file\n", encoding="utf-8")
    (tests_dir / "test_main.py").write_text("# Initial test file\n", encoding="utf-8")
    # --- ★★★★★ ここまでが最重要修正点 ★★★★★ ---

    logger.info("Test environment setup complete with package markers (__init__.py).")


def run_test():
    """PolicyAgentの統合テストを実行する"""
    setup_test_environment()

    logger.info("--- Initializing Agents ---")

    # 各エージェントを初期化
    architect = ArchitectAgent(API_KEY, MODEL)
    planner = PlannerAgent(API_KEY, MODEL)
    coder = CoderAgent(API_KEY, MODEL)
    tester = TesterAgent(API_KEY, MODEL)
    debugger = DebuggerAgent(API_KEY, MODEL, knowledge_base_path="fkb_local.json")
    guardian = GuardianAgent(API_KEY, MODEL)
    policy_agent = PolicyAgent(API_KEY, MODEL, policy_rules_path="config/policy_rules.json")

    logger.info("--- Initializing Orchestrator with PolicyAgent ---")

    orchestrator = Orchestrator(
        project_path=TEST_PROJECT_PATH,
        constitution="Test Constitution: Behave ethically.",
        architect=architect,
        planner=planner,
        coder=coder,
        tester=tester,
        debugger=debugger,
        guardian=guardian,
        policy_agent=policy_agent,
    )

    policy_violating_task = {
        "name": "create_debug_greeting",
        "module": "main",
        "description": "Create a function 'debug_greet' that takes a name and prints a greeting message to the console.",
    }

    logger.info("\n" + "=" * 50)
    logger.info("🚀 STARTING TEST: EXECUTING A POLICY-VIOLATING TASK")
    logger.info(f"TASK: {policy_violating_task['description']}")
    logger.info("=" * 50 + "\n")

    # 1. CoderAgentに違反コードを生成させる (Simulated)
    logger.info("--- 1. CoderAgent Phase (Simulated) ---")
    violating_code = "def debug_greet(name):\n    print(f'Hello, {name}!')\n"
    source_file_path = os.path.join(TEST_PROJECT_PATH, "app/main.py")
    with open(source_file_path, "w", encoding="utf-8") as f:
        f.write(violating_code)
    logger.info(f"CoderAgent generated violating code:\n---\n{violating_code}\n---")

    # 2. TesterAgentにテストを生成させる (Simulated)
    logger.info("--- 2. TesterAgent Phase (Simulated) ---")
    test_code = "from app.main import debug_greet\n\ndef test_debug_greet(capsys):\n    debug_greet('World')\n    captured = capsys.readouterr()\n    assert captured.out == 'Hello, World!\\n'"
    test_file_path = os.path.join(TEST_PROJECT_PATH, "tests/test_main.py")
    with open(test_file_path, "w", encoding="utf-8") as f:
        f.write(test_code)
    logger.info("TesterAgent generated corresponding tests.")

    # 3. テスト実行サイクル (Actual)
    logger.info("--- 3. Test Execution Cycle (Actual) ---")
    tests_passed, _ = orchestrator.run_tests(test_file_path)
    if not tests_passed:
        logger.error("Tests failed unexpectedly even after the fix. There might be another issue.")
        return
    logger.info("✅ Tests passed successfully.")

    # 4. PolicyAgentによる監査の実行 (Actual)
    logger.info("--- 3.5. PolicyAgent Audit Phase (Actual) ---")
    files_for_audit = [
        {"path": "app/main.py", "content": violating_code},
        {"path": "tests/test_main.py", "content": test_code},
    ]
    policy_result = orchestrator.policy_agent.audit(files_for_audit)

    # 5. 結果の検証
    logger.info("\n" + "=" * 50)
    logger.info("🔬 TEST RESULT VERIFICATION")
    logger.info("=" * 50)

    if policy_result.get("result") == "REJECTED":
        logger.info("✅ SUCCESS: PolicyAgent correctly REJECTED the code.")
        violations = policy_result.get("violations", [])
        logger.info(f"Found {len(violations)} violation(s):")
        for v in violations:
            logger.info(f"  - {v}")

        found_lint_violation = any(v.get("policy_id") == "POLICY_LINT_001" for v in violations)
        if found_lint_violation:
            logger.info("✅ SUCCESS: The correct policy (POLICY_LINT_001) was triggered.")
        else:
            logger.error(
                "❌ FAILURE: The code was rejected, but not for the expected reason (POLICY_LINT_001)."
            )
    else:
        logger.error("❌ FAILURE: PolicyAgent INCORRECTLY approved the code with violations.")

    logger.info("\n--- Test Finished ---")


if __name__ == "__main__":
    run_test()
