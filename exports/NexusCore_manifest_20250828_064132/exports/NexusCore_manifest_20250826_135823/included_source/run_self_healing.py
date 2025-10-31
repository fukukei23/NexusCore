# ==============================================================================
# フォルダ: (プロジェクトルート)
# ファイル名: run_self_healing.py
# メモ: 構造化ログの保存先ディレクトリをOrchestratorに渡すように
#      アップグレードされた最終テストスクリプト。
# ==============================================================================
import os
import sys
import shutil
import subprocess
import logging
from pathlib import Path

VERBOSE = True # 詳細ログの表示/非表示を切り替え

def setup_logging(level=logging.INFO):
    log_format = "%(asctime)s - %(levelname)-8s - %(name)-20s - %(message)s"
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
    logging.basicConfig(level=level, format=log_format)

def main():
    log_level = logging.DEBUG if VERBOSE else logging.INFO
    setup_logging(log_level)
    
    logging.info("--- NexusCore Self-Healing System (Test with Structured Logging) ---")

    try:
        project_root = Path(__file__).resolve().parent
        sandbox_path = project_root / "healing_sandbox"
        
        # (ファイルパスの定義は変更なし)
        # ...
        agent_sources = {
            "orchestrator.py": project_root / "src" / "agents" / "orchestrator.py",
            "debugger_agent.py": project_root / "src" / "agents" / "debugger_agent.py",
            "patch_applier.py": project_root / "src" / "agents" / "patch_applier.py",
            "base_agent.py": project_root / "src" / "agents" / "base_agent.py",
            "fkb_local.json": project_root / "fkb_local.json"
        }
        crm_app_sources = {
            "main.py": project_root / "my-crm-app" / "app" / "main.py",
            "test_main.py": project_root / "my-crm-app" / "tests" / "test_main.py"
        }


        logging.info("Verifying required files...")
        all_sources = {**agent_sources, **crm_app_sources}
        for name, path in all_sources.items():
            if not path.exists():
                raise FileNotFoundError(f"Required file not found: '{path}'")
            logging.debug(f"Found: {path.relative_to(project_root)}")

        logging.info(f"Setting up sandbox environment at: {sandbox_path}")
        if sandbox_path.exists():
            shutil.rmtree(sandbox_path)
        
        # (ディレクトリ作成は変更なし)
        # ...
        (sandbox_path / "app").mkdir(parents=True, exist_ok=True)
        (sandbox_path / "tests").mkdir(exist_ok=True)
        (sandbox_path / "src" / "agents").mkdir(parents=True, exist_ok=True)
        # ★★★★★ ログ保存用ディレクトリを追加 ★★★★★
        (sandbox_path / "logs").mkdir(exist_ok=True)


        # (ファイルコピーは変更なし)
        # ...
        for name, src_path in agent_sources.items():
            dest_folder = (sandbox_path / "src" / "agents") if name.endswith(".py") else sandbox_path
            shutil.copy(src_path, dest_folder / name)
        
        shutil.copy(crm_app_sources["main.py"], sandbox_path / "app" / "main.py")
        shutil.copy(crm_app_sources["test_main.py"], sandbox_path / "tests" / "test_main.py")
        logging.debug("Copied all required files to sandbox.")

        (sandbox_path / "app" / "__init__.py").touch()
        (sandbox_path / "tests" / "__init__.py").touch()
        (sandbox_path / "src" / "__init__.py").touch()
        (sandbox_path / "src" / "agents" / "__init__.py").touch()


        # --- ★★★★★ ここからが最重要修正点 ★★★★★ ---
        runner_script_code = f"""
import sys, logging
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

log_level_str = "{logging.getLevelName(log_level)}"
log_level = logging.getLevelName(log_level_str)
log_format = "%(asctime)s - %(levelname)-8s - %(name)-20s - %(message)s"
logging.basicConfig(level=log_level, format=log_format)

from src.agents.orchestrator import Orchestrator
from src.agents.debugger_agent import DebuggerAgent
from src.agents.patch_applier import PatchApplier

def run():
    logging.info(">> Starting Self-Healing Cycle for CRM App...")
    
    debugger = DebuggerAgent(api_key="dummy_key", model="dummy_model", knowledge_base_path="fkb_local.json")
    patcher = PatchApplier()
    
    # Orchestratorにログ保存先のパスを渡す
    orchestrator = Orchestrator(
        debugger_agent=debugger,
        patch_applier=patcher,
        log_dir="logs", # サンドボックス内のlogsディレクトリを指定
        max_retries=3
    )
    
    orchestrator.self_healing_cycle(
        test_file_path="tests/test_main.py",
        source_file_path="app/main.py"
    )

if __name__ == '__main__':
    run()
"""
        # --- ★★★★★ ここまで ★★★★★ ---
        runner_script_path = sandbox_path / "sandbox_runner.py"
        runner_script_path.write_text(runner_script_code, encoding='utf-8')
        logging.debug("Created sandbox runner script.")

        logging.info("Executing the self-healing cycle for CRM App...")
        result = subprocess.run(
            [sys.executable, "sandbox_runner.py"],
            cwd=sandbox_path,
            capture_output=True, text=True, encoding='utf-8', errors='replace'
        )
        
        print("\\n--- Execution Log ---")
        print(result.stdout)
        if result.stderr:
            print("\\n--- Errors ---")
            print(result.stderr)
        print("---------------------")

        logging.info("Self-healing cycle finished.")
        print(f"\\n[INFO] Structured logs have been saved in '{sandbox_path / 'logs'}'")

    except FileNotFoundError as e:
        logging.critical(f"A required file was not found: {e}")
        sys.exit(1)
    except Exception as e:
        logging.critical(f"An unexpected error occurred: {e}", exc_info=True)
        sys.exit(1)

if __name__ == '__main__':
    main()
