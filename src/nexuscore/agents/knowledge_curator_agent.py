import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from .base_agent import BaseAgent
from .debugger_agent import DebuggerAgent
from nexuscore.services.patch_applier import PatchApplier


class KnowledgeCuratorAgent(BaseAgent):
    SYSTEM_PROMPT: str = (
        "You are a Knowledge Curator agent. "
        "Your role is to validate and manage knowledge base entries for the NexusCore system."
    )

    def __init__(self):
        super().__init__()

    @staticmethod
    def _setup_sandbox(sandbox_path: str, original_project_path: str,
                       related_source_path: str, failed_test_path: str) -> None:
        """サンドボックスに必要なディレクトリ構造とファイルをコピーする。"""
        source_rel = os.path.relpath(related_source_path, original_project_path)
        test_rel = os.path.relpath(failed_test_path, original_project_path)

        Path(sandbox_path, os.path.dirname(source_rel)).mkdir(parents=True, exist_ok=True)
        Path(sandbox_path, os.path.dirname(test_rel)).mkdir(parents=True, exist_ok=True)

        shutil.copy(related_source_path, os.path.join(sandbox_path, source_rel))
        shutil.copy(failed_test_path, os.path.join(sandbox_path, test_rel))

        for dirpath, _, _ in os.walk(sandbox_path):
            Path(dirpath, "__init__.py").touch()

    def validate_fkb_suggestion(
        self,
        suggestion: dict,
        original_project_path: str,
        failed_test_path: str,
        related_source_path: str,
        original_test_output: str,
    ) -> bool:
        """提案されたFKBエントリを一時的なサンドボックス環境で検証する。"""
        self.logger.info(f"Starting validation for FKB suggestion: {suggestion.get('id', 'N/A')}")

        with tempfile.TemporaryDirectory(prefix="k_curator_") as sandbox_path:
            try:
                self._setup_sandbox(sandbox_path, original_project_path, related_source_path, failed_test_path)
                self.logger.debug(f"Created minimal sandbox at: {sandbox_path}")

                # 一時的なFKBを作成
                temp_fkb_path = os.path.join(sandbox_path, "temp_fkb.json")
                with open(temp_fkb_path, "w", encoding="utf-8") as f:
                    json.dump([suggestion], f, ensure_ascii=False, indent=2)

                # サンドボックス内でDebuggerAgentを初期化して自己修復を試行
                debugger = DebuggerAgent(knowledge_base_path=temp_fkb_path)
                patcher = PatchApplier()

                source_rel = os.path.relpath(related_source_path, original_project_path)
                test_rel = os.path.relpath(failed_test_path, original_project_path)
                sandbox_source = os.path.join(sandbox_path, source_rel)
                sandbox_test = os.path.join(sandbox_path, test_rel)

                files_content = {}
                for path, label in [(sandbox_source, "Source"), (sandbox_test, "Test")]:
                    try:
                        with open(path, encoding="utf-8") as f:
                            files_content[path] = f.read()
                    except FileNotFoundError:
                        self.logger.warning(f"{label} file missing in sandbox: %s", path)

                if not files_content:
                    self.logger.error("No files available for debugging in sandbox. Aborting validation.")
                    return False

                debug_result = debugger.debug_and_patch(
                    error_log=original_test_output, files_content=files_content, project_path=sandbox_path,
                )
                if not (debug_result and debug_result.get("patch")):
                    self.logger.warning("Validation failed: Debugger did not generate a patch with the new knowledge.")
                    return False

                if not patcher.apply(debug_result["patch"], sandbox_path):
                    self.logger.warning("Validation failed: Generated patch could not be applied.")
                    return False

                tests_passed, _ = self._run_tests_in_sandbox(sandbox_path, test_rel)
                if tests_passed:
                    self.logger.info("Validation successful! The new knowledge correctly fixed the bug.")
                    return True
                self.logger.warning("Validation failed: Tests still fail after applying the patch.")
                return False

            except Exception as e:  # noqa: BLE001
                self.logger.error(f"An error occurred during validation: {e}", exc_info=True)
                return False

    def _run_tests_in_sandbox(self, sandbox_path: str, test_file_rel_path: str) -> tuple[bool, str]:
        """サンドボックス内でpytestを実行する"""
        result = subprocess.run(
            [sys.executable, "-m", "pytest", test_file_rel_path],
            cwd=sandbox_path,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        output = result.stdout + "\n" + result.stderr
        return result.returncode == 0, output
