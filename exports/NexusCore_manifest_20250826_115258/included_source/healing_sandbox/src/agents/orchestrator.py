# ==============================================================================
# フォルダ: src/agents
# ファイル名: orchestrator.py
# メモ: 構造化ロギング(Markdown/JSONL)の能力をMixinとして追加した、
#      最終形態のOrchestratorアーキテクチャ。
# ==============================================================================
import subprocess
import logging
import os
import sys
import json
from datetime import datetime
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, ClassVar

if TYPE_CHECKING:
    from .debugger_agent import DebuggerAgent
    from .patch_applier import PatchApplier

# --- Mixin 1: 構造化ロギングの「能力」 ---
class StructuredLoggingMixin:
    """
    AIの思考と行動を人間と機械の両方が読める形式で記録するMixin。
    - .md: 人間向けの監査ログ（業務日報）
    - .jsonl: 機械学習向けの学習データ
    """
    log_dir: str
    logger: logging.Logger
    
    def _log_to_files(self, md_content: str, json_data: dict):
        """MarkdownとJSONLファイルに追記する内部ヘルパー"""
        try:
            # Markdown Log
            with open(os.path.join(self.log_dir, "run_log.md"), "a", encoding="utf-8") as f:
                f.write(md_content + "\n")
            
            # JSONL Log
            with open(os.path.join(self.log_dir, "run_data.jsonl"), "a", encoding="utf-8") as f:
                # すべてのJSONログにタイムスタンプとイベントタイプを追加
                log_entry = {
                    "timestamp": datetime.now().isoformat(),
                    **json_data
                }
                f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
        except Exception as e:
            self.logger.error(f"Failed to write to structured log files: {e}")

    def log_cycle_start(self, test_file: str, source_file: str):
        md = f"# Self-Healing Cycle Start: {os.path.basename(test_file)}\n\n"
        md += f"- **Timestamp**: {datetime.now().isoformat()}\n"
        md += f"- **Test File**: `{test_file}`\n"
        md += f"- **Source File**: `{source_file}`\n"
        js = {"event": "cycle_start", "test_file": test_file, "source_file": source_file}
        self._log_to_files(md, js)

    def log_test_failure(self, attempt: int, test_output: str):
        md = f"\n---\n\n## 🔴 Attempt {attempt}: Test Failed\n\n"
        md += "```text\n" + test_output + "\n```"
        js = {"event": "test_failure", "attempt": attempt, "test_output": test_output}
        self._log_to_files(md, js)

    def log_patch_generation(self, patch: str, target: str, fkb_entry: dict):
        md = f"\n### 🧠 Diagnosis & Patch Generation\n\n"
        md += f"- **Cause Found**: {fkb_entry.get('cause', 'N/A')}\n"
        md += f"- **Target File**: `{target}`\n"
        md += "```diff\n" + patch + "\n```"
        js = {"event": "patch_generated", "patch": patch, "target": target, "fkb_entry": fkb_entry}
        self._log_to_files(md, js)

    def log_patch_application(self, success: bool, file_path: str):
        if success:
            md = f"\n- **Result**: ✅ Patch successfully applied to `{os.path.basename(file_path)}`."
            js = {"event": "patch_applied", "status": "success", "file_path": file_path}
        else:
            md = f"\n- **Result**: ❌ Patch application FAILED for `{os.path.basename(file_path)}`."
            js = {"event": "patch_applied", "status": "failed", "file_path": file_path}
        self._log_to_files(md, js)
    
    def log_cycle_end(self, success: bool, attempts: int):
        if success:
            md = f"\n---\n\n## ✅ Self-Healing Cycle Succeeded\n\n- **Total Attempts**: {attempts}"
            js = {"event": "cycle_end", "status": "success", "attempts": attempts}
        else:
            md = f"\n---\n\n## ❌ Self-Healing Cycle Failed\n\n- **Total Attempts**: {attempts}"
            js = {"event": "cycle_end", "status": "failed", "attempts": attempts}
        self._log_to_files(md, js)

# --- Mixin 2: 自己修復のロジック ---
class SelfHealingMixin:
    """自己修復サイクルという「能力」を提供するMixin"""
    logger: logging.Logger
    debugger_agent: 'DebuggerAgent'
    patch_applier: 'PatchApplier'
    max_retries: int
    # 構造化ロギングMixinのメソッドを呼び出すことを型ヒントで示す
    log_cycle_start: callable
    log_test_failure: callable
    log_patch_generation: callable
    log_patch_application: callable
    log_cycle_end: callable

    def run_tests(self, test_path: str) -> tuple[bool, str]:
        # (実装は変更なし)
        # ...
        self.logger.info(f"Running tests for: {test_path}")
        if not os.path.exists(test_path):
            self.logger.error(f"Test path does not exist: {test_path}")
            return False, f"Test path does not exist: {test_path}"
        try:
            process = subprocess.run(
                [sys.executable, '-m', 'pytest', test_path, '--tb=short'],
                capture_output=True, text=True, encoding='utf-8', errors='replace'
            )
            output = process.stdout + process.stderr
            if process.returncode != 0:
                self.logger.warning(f"Tests failed (Exit Code: {process.returncode}).")
                self.logger.debug(f"Full test output:\n{output}")
            else:
                self.logger.info("All tests passed.")
            return process.returncode == 0, output
        except Exception as e:
            self.logger.error(f"An exception occurred while running tests: {e}", exc_info=True)
            return False, str(e)


    def self_healing_cycle(self, test_file_path: str, source_file_path: str):
        self.logger.info(f"Starting self-healing cycle for test: '{os.path.basename(test_file_path)}'")
        self.log_cycle_start(test_file_path, source_file_path)
        
        for attempt in range(1, self.max_retries + 1):
            self.logger.info(f"--- Attempt {attempt}/{self.max_retries} ---")
            
            tests_passed, test_output = self.run_tests(test_file_path)

            if tests_passed:
                self.logger.info("Self-healing successful!")
                self.log_cycle_end(success=True, attempts=attempt)
                print("\n[SUCCESS] The code was successfully repaired! All tests passed.")
                return

            self.logger.warning("Tests failed. Initiating debugging process.")
            self.log_test_failure(attempt, test_output)
            
            files_context = {"source_file": source_file_path, "test_file": test_file_path}
            debug_result = self.debugger_agent.debug(error_log=test_output, files_context=files_context)

            if debug_result and debug_result.get("patch"):
                patch, target_hint, entry = debug_result["patch"], debug_result["target"], debug_result["entry"]
                self.log_patch_generation(patch, target_hint, entry)
                
                file_to_patch = files_context.get(target_hint)
                
                if not file_to_patch:
                    self.logger.error(f"Invalid target hint from DebuggerAgent: '{target_hint}'. Aborting.")
                    break

                self.logger.info(f"Applying patch for '{target_hint}' to '{os.path.basename(file_to_patch)}'...")
                was_applied = self.patch_applier.apply(patch, file_to_patch)
                self.log_patch_application(was_applied, file_to_patch)

                if not was_applied:
                    self.logger.error("PatchApplier failed. Aborting cycle.")
                    break
            else:
                self.logger.warning("DebuggerAgent did not return a patch. Aborting cycle.")
                break
        else: # forループがbreakされずに完了した場合
            attempt += 1 # 最後の試行回数を反映
        
        self.logger.error(f"Self-healing cycle failed after {attempt -1} attempts.")
        self.log_cycle_end(success=False, attempts=attempt - 1)
        print("\n[FAILED] The code could not be repaired.")

# --- 本体: 複数の能力(Mixin)を統合したOrchestrator ---
@dataclass
class Orchestrator(SelfHealingMixin, StructuredLoggingMixin):
    """
    NexusCoreの司令塔。
    @dataclassで構成部品を定義し、Mixinで能力を獲得する。
    """
    # 構成部品
    debugger_agent: 'DebuggerAgent'
    patch_applier: 'PatchApplier'
    log_dir: str # ログの保存先ディレクトリ
    max_retries: int = 3
    
    # 初期化後に設定される属性
    logger: logging.Logger = field(init=False)

    def __post_init__(self):
        """@dataclassの初期化後に呼ばれるメソッド"""
        self.logger = logging.getLogger(self.__class__.__name__)
        # ログディレクトリが存在しない場合は作成
        os.makedirs(self.log_dir, exist_ok=True)
        self.logger.info(f"Orchestrator initialized. Logging to '{self.log_dir}'.")
        self.logger.debug(f"  - Debugger: {self.debugger_agent.__class__.__name__}")
        self.logger.debug(f"  - Patcher: {self.patch_applier.__class__.__name__}")
