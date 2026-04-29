# ==============================================================================
# フォルダ: src/agents
# ファイル名: knowledge_curator_agent.py
# メモ: 【情報伝達修正版】検証プロセスにおいて、PostmortemAgentが分析した
#      のと同一の「生のエラーログ」をDebuggerAgentに引き継ぐように修正。
# ==============================================================================
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

    def validate_fkb_suggestion(
        self,
        suggestion: dict,
        original_project_path: str,
        failed_test_path: str,
        related_source_path: str,
        # ▼▼▼▼▼ 【最重要修正点】生のテスト失敗ログを追加 ▼▼▼▼▼
        original_test_output: str,
        # ▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲
    ) -> bool:
        """
        提案されたFKBエントリを一時的なサンドボックス環境で検証する。
        """
        self.logger.info(f"Starting validation for FKB suggestion: {suggestion.get('id', 'N/A')}")

        with tempfile.TemporaryDirectory(prefix="k_curator_") as sandbox_path:
            try:
                # 1. プロジェクトの関連ファイルのみをサンドボックスにコピー
                self.logger.debug(f"Creating minimal sandbox at: {sandbox_path}")

                # 必要なディレクトリ構造を作成
                Path(
                    sandbox_path,
                    os.path.dirname(os.path.relpath(related_source_path, original_project_path)),
                ).mkdir(parents=True, exist_ok=True)
                Path(
                    sandbox_path,
                    os.path.dirname(os.path.relpath(failed_test_path, original_project_path)),
                ).mkdir(parents=True, exist_ok=True)

                # 関連ファイルのみをコピー
                shutil.copy(
                    related_source_path,
                    os.path.join(
                        sandbox_path, os.path.relpath(related_source_path, original_project_path)
                    ),
                )
                shutil.copy(
                    failed_test_path,
                    os.path.join(
                        sandbox_path, os.path.relpath(failed_test_path, original_project_path)
                    ),
                )

                # __init__.pyを作成
                for dirpath, _, _ in os.walk(sandbox_path):
                    Path(dirpath, "__init__.py").touch()

                # 2. 一時的なFKBを作成
                temp_fkb_path = os.path.join(sandbox_path, "temp_fkb.json")
                with open(temp_fkb_path, "w", encoding="utf-8") as f:
                    json.dump([suggestion], f, ensure_ascii=False, indent=2)
                self.logger.debug("Created temporary FKB with new suggestion.")

                # 3. サンドボックス内でDebuggerAgentを初期化
                debugger = DebuggerAgent(knowledge_base_path=temp_fkb_path)
                patcher = PatchApplier()

                # 4. 自己修復を試行（LLM診断で得たパッチを適用）
                source_rel = os.path.relpath(related_source_path, original_project_path)
                test_rel = os.path.relpath(failed_test_path, original_project_path)
                sandbox_source_path = os.path.join(sandbox_path, source_rel)
                sandbox_test_path = os.path.join(sandbox_path, test_rel)

                files_content = {}
                try:
                    with open(sandbox_source_path, encoding="utf-8") as src_file:
                        files_content[sandbox_source_path] = src_file.read()
                except FileNotFoundError:
                    self.logger.warning("Source file missing in sandbox: %s", sandbox_source_path)
                try:
                    with open(sandbox_test_path, encoding="utf-8") as test_file:
                        files_content[sandbox_test_path] = test_file.read()
                except FileNotFoundError:
                    self.logger.warning("Test file missing in sandbox: %s", sandbox_test_path)

                if not files_content:
                    self.logger.error(
                        "No files available for debugging in sandbox. Aborting validation."
                    )
                    return False

                debug_result = debugger.debug_and_patch(
                    error_log=original_test_output,
                    files_content=files_content,
                    project_path=sandbox_path,
                )

                if not (debug_result and debug_result.get("patch")):
                    self.logger.warning(
                        "Validation failed: Debugger did not generate a patch with the new knowledge."
                    )
                    return False

                # 5. パッチを適用し、テストが成功するか確認
                was_applied = patcher.apply(debug_result["patch"], sandbox_path)
                if not was_applied:
                    self.logger.warning("Validation failed: Generated patch could not be applied.")
                    return False

                tests_passed, _ = self._run_tests_in_sandbox(
                    sandbox_path, os.path.relpath(failed_test_path, original_project_path)
                )
                if tests_passed:
                    self.logger.info(
                        "✅ Validation successful! The new knowledge correctly fixed the bug."
                    )
                    return True
                else:
                    self.logger.warning(
                        "Validation failed: Tests still fail after applying the patch."
                    )
                    return False

            except Exception as e:
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
