# ==============================================================================
# 操作するソフト: VSCode (または任意のテキストエディタ)
# レジストリ/フォルダ: C:\Users\USER\tools\NexusCore\
# ファイル名: run_self_heal_test.py
# 日付: 2025/09/02
#
# 使用方法:
#   このファイルを指定のパスに保存（上書き）してください。
#   GuardianAgentの初期化エラー(TypeError)を修正し、テストを実行可能にした最終FIX版です。
#
# 改修内容:
#   - GuardianAgentの初期化時に、他のエージェントと一貫性のあるダミー引数を追加。
# ==============================================================================
import os
import sys
import json
import logging
from pathlib import Path

# --- Python検索パスの設定 ---
PROJECT_ROOT = Path(__file__).parent.resolve()
SRC_PATH = PROJECT_ROOT / "src"
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

# --- 司令塔と、それに必要な全エージェントをインポート ---
from nexuscore.core.orchestrator import Orchestrator
from nexuscore.agents.requirement_agent import RequirementAgent
from nexuscore.agents.architect_agent import ArchitectAgent
from nexuscore.agents.planner_agent import PlannerAgent
from nexuscore.agents.coder_agent import CoderAgent
from nexuscore.agents.tester_agent import TesterAgent
from nexuscore.agents.debugger_agent import DebuggerAgent
from nexuscore.agents.guardian_agent import GuardianAgent
from nexuscore.agents.postmortem_agent import PostmortemAgent
from nexuscore.agents.knowledge_curator_agent import KnowledgeCuratorAgent
from nexuscore.agents.patch_applier import PatchApplier
try:
    from nexuscore.agents.policy_agent import PolicyAgent
except ImportError:
    class PolicyAgent: pass

# --- ロギング設定 ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - %(name)s - %(message)s')

def main():
    """自己修復ループを安全に実証するためのメイン関数。"""
    print("🚀 [INFO] Starting Self-Healing Loop Demonstration (v7).")

    try:
        # --- 1. 憲法(プロジェクトルール)の読み込み ---
        constitution_path = PROJECT_ROOT / "constitution.json"
        constitution = json.load(constitution_path.open("r", encoding="utf-8")) if constitution_path.exists() else {"automation_policy": {"max_llm_calls_per_task": 20}}
        print(f"📜 [INFO] Constitution {'loaded' if constitution_path.exists() else 'created dummy'}.")

        # --- 2. 専門家チーム(エージェント群)の招集 ---
        print("👥 [INFO] Assembling agent team...")
        requirement_agent = RequirementAgent()
        architect_agent = ArchitectAgent()
        planner_agent = PlannerAgent()
        coder_agent = CoderAgent()
        tester_agent = TesterAgent()
        debugger_agent = DebuggerAgent()
        # ▼▼▼【TypeError修正】GuardianAgentの初期化にダミー引数を追加 ▼▼▼
        guardian_agent = GuardianAgent(api_key="dummy", model="dummy")
        # ▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲
        postmortem_agent = PostmortemAgent()
        policy_agent = PolicyAgent()
        knowledge_curator_agent = KnowledgeCuratorAgent(api_key="dummy", model="dummy")
        patch_applier = PatchApplier()
        print("✅ [INFO] All agents instantiated.")

        # --- 3. 司令塔(Orchestrator)の初期化 ---
        orchestrator = Orchestrator(
            project_path=str(PROJECT_ROOT), constitution=constitution,
            requirement_agent=requirement_agent, architect_agent=architect_agent,
            planner_agent=planner_agent, coder_agent=coder_agent,
            tester_agent=tester_agent, debugger_agent=debugger_agent,
            guardian_agent=guardian_agent, policy_agent=policy_agent,
            postmortem_agent=postmortem_agent, knowledge_curator_agent=knowledge_curator_agent,
            patch_applier=patch_applier
        )
        print("🤖 [INFO] Orchestrator initialized successfully.")

    except Exception as e:
        logging.error("Failed during initialization phase.", exc_info=True)
        print(f"🚨 [FATAL] A critical error occurred during setup: {e}")
        return

    # --- 4. テストの実行と失敗の捕捉 ---
    target_test_file = "tests/test_math_utils.py"
    print(f"🩺 [INFO] Running initial test on '{target_test_file}' to detect expected failure...")
    is_success, test_logs = orchestrator.tester_agent.run_tests(test_path=target_test_file)
    if is_success:
        print("✅ [UNEXPECTED] Tests passed unexpectedly. Exiting.")
        return
    print("🐞 [SUCCESS] Bug detected as expected. Initiating self-healing loop...")
    print(f"\n--- Captured Test Failure Log ---\n{test_logs}\n---------------------------------\n")

    # --- 5. 自己修復サイクルの実行 ---
    try:
        related_source_file = "tools/utils/math_utils.py"
        print("🕵️  [INFO] PostmortemAgent is analyzing the failure...")
        analysis_result = orchestrator.postmortem_agent.analyze(test_logs)
        print(f"📝 [INFO] Postmortem analysis complete: {json.dumps(analysis_result, indent=2, ensure_ascii=False)}")

        print("\n👨‍⚕️ [INFO] DebuggerAgent is generating a patch based on the analysis...")
        debug_result = orchestrator.debugger_agent.debug_and_patch(
            error_log=test_logs,
            files_content={related_source_file: Path(related_source_file).read_text(encoding="utf-8")},
            project_path=str(PROJECT_ROOT)
        )
        patch = debug_result.get("patch")
        if not patch:
            print("❌ [ERROR] DebuggerAgent failed to generate a patch. Aborting.")
            return
        print(f"🩹 [INFO] Patch generated successfully.\n--- Generated Patch ---\n{patch}\n-----------------------\n")

        print("🩹 [INFO] PatchApplier is applying the patch...")
        was_applied = orchestrator.patch_applier.apply(patch, project_path=str(PROJECT_ROOT))
        if not was_applied:
            print("❌ [ERROR] Failed to apply the patch. Aborting.")
            return
        print("✅ [INFO] Patch applied successfully.")

        # --- 6. 修正の検証 ---
        print("\n🔬 [INFO] Re-running tests to verify the fix...")
        is_fixed, final_test_logs = orchestrator.tester_agent.run_tests(test_path=target_test_file)
        if is_fixed:
            print("\n🎉 [SUCCESS] All tests passed! The bug has been successfully self-healed.")
        else:
            print(f"\n❌ [FAILURE] Tests still fail after applying the patch.\n--- Final Test Log ---\n{final_test_logs}\n----------------------\n")
            
    except Exception as e:
        logging.error("An error occurred during the self-healing cycle.", exc_info=True)
        print(f"🚨 [FATAL] A critical error occurred: {e}")

if __name__ == "__main__":
    main()
