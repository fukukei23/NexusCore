# ==============================================================================
# フォルダ: src/agents
# ファイル名: debugger_agent.py
# メモ: 生成するパッチのファイルパスをOS非依存の相対パス形式に正規化し、
#      PatchApplierとの連携をより堅牢にした最終形態。
# ==============================================================================
import os
import json
import re
import difflib
import logging
from pathlib import Path
from .base_agent import BaseAgent

class DebuggerAgent(BaseAgent):
    DEBUG_SYSTEM_PROMPT = """
あなたは、熟練のソフトウェア開発者であり、デバッグの達人です。
あなたの仕事は、失敗したテストのエラーログ、関連するソースコード、そしてテストコードを分析し、
エラーの根本原因を特定して、それを修正するためのunified diff形式のパッチを生成することです。
パッチは正確で、必要最小限の変更に留めてください。
"""

    def __init__(self, api_key: str, model: str, knowledge_base_path: str = "fkb_local.json", project_path: str = "."):
        super().__init__(api_key, model)
        self.knowledge_base_path = knowledge_base_path
        self.fkb = self._load_fkb()
        # ★ プロジェクトルートのパスを保持
        self.project_path = os.path.abspath(project_path)
        
        if self.fkb:
            self.logger.info(f"{len(self.fkb)} known issues loaded from: {self.knowledge_base_path}")
        else:
            self.logger.warning(f"EMPTY knowledge base. File not found or empty at: {self.knowledge_base_path}")

    def _load_fkb(self) -> list:
        try:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            config_path = os.path.join(base_dir, '..', '..', self.knowledge_base_path)
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            self.logger.error(f"Failed to load FKB from '{config_path}': {e}")
            return []

    def debug(self, error_log: str, files_context: dict) -> dict | None:
        self.logger.info(f"Debugging error... (log size: {len(error_log)} chars)")

        for entry in self.fkb:
            if re.search(entry["error_signature"], error_log, re.DOTALL | re.IGNORECASE):
                self.logger.info(f"Found known issue: {entry['cause']}")
                
                target_hint = entry.get("target", "source_file")
                file_to_read_path = files_context.get(target_hint)
                
                if not file_to_read_path or not os.path.exists(file_to_read_path):
                    self.logger.error(f"Target file for reading not found in context: {target_hint}")
                    continue

                try:
                    with open(file_to_read_path, 'r', encoding='utf-8') as f:
                        original_code = f.read()
                    
                    solution = entry["solution_pattern"]
                    if solution.get("type") == "llm_diagnose_and_fix":
                        self.logger.info("Attempting LLM-based diagnosis and fix...")
                        other_files_context = {k: v for k, v in files_context.items() if k != target_hint}
                        patch_str = self._llm_generate_patch(error_log, original_code, file_to_read_path, solution["instruction"], other_files_context)
                        if patch_str:
                            return {"patch": patch_str, "target": target_hint, "entry": entry}
                    else:
                        modified_code = self._apply_solution_pattern(original_code, solution)
                        if modified_code and original_code != modified_code:
                            diff = self._create_diff(original_code, modified_code, file_to_read_path)
                            self.logger.info(f"Generated patch for '{target_hint}':\n{diff}")
                            return {"patch": diff, "target": target_hint, "entry": entry}
                        else:
                            self.logger.warning(f"Solution pattern did not result in code changes for file: {file_to_read_path}")
                
                except Exception as e:
                    self.logger.error(f"Error applying solution for '{entry['cause']}': {e}", exc_info=True)
                
                return None

        self.logger.warning("No known solution found in FKB for this error.")
        return None

    def _llm_generate_patch(self, error_log: str, source_code: str, source_path: str, instruction: str, other_files: dict) -> str | None:
        context_str = ""
        # ★ 相対パスに変換
        source_path_rel = os.path.relpath(source_path, self.project_path)
        source_path_normalized = Path(source_path_rel).as_posix() # /区切りに正規化
        
        for name, path in other_files.items():
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
                rel_path = os.path.relpath(path, self.project_path)
                context_str += f"\n\n--- Context File: {name} ({Path(rel_path).as_posix()}) ---\n```python\n{content}\n```"
            except Exception:
                pass

        prompt = f"""
# CONTEXT
You are an expert developer debugging a failed test. Your task is to generate a patch file to fix the bug.

# INSTRUCTION
{instruction}

# FAILED TEST LOG
```
{error_log}
```

# SOURCE CODE TO FIX: {source_path_normalized}
```python
{source_code}
```
{context_str}

# ANALYSIS & DEBUGGING STRATEGY
1.  Analyze the error log and the source code. The test is failing. This often means the function's output does not match the test's expectation.
2.  Identify the root cause. A very common bug pattern is a function using `print()` to display a result, when the test expects a `return` statement to capture the output.
3.  Formulate the simplest, most correct fix. If the issue is `print` vs `return`, the best fix is to **replace** the `print()` statement with a `return` statement. Do not add a `return` statement while keeping the `print()`. This is a crucial best practice.
4.  Generate the patch. Create a concise, correct patch in the **unified diff format**.

# ABSOLUTE OUTPUT RULES
- **Output ONLY the patch content.**
- Start the patch with `--- {source_path_normalized}` and `+++ {source_path_normalized}`.
- Do NOT include any explanations, apologies, or any text before or after the patch content.
- The output must be a valid unified diff that can be applied by the `patch` command.
- Ensure the patched code is syntactically correct Python.
"""
        patch = self._call_llm(prompt, self.DEBUG_SYSTEM_PROMPT)
        
        # === ★★★★★ パッチ書式を完璧にする最終修正 ★★★★★ ===
        if "```" in patch:
            match = re.search(r"```(?:diff\n)?((?:.|\n)*?)```", patch, re.DOTALL)
            if match:
                # 抽出した内容の先頭と末尾の空白のみを削除し、末尾に改行を1つだけ保証する
                patch_content = match.group(1).strip()
                patch = patch_content + "\n"
        
        if patch and patch.startswith("---") and "+++" in patch and "@@" in patch:
            self.logger.info(f"LLM generated a valid-looking patch:\n{patch}")
            return patch
            
        self.logger.warning(f"LLM did not generate a valid patch. Output:\n{patch}")
        return None

    def _apply_solution_pattern(self, code: str, solution: dict) -> str | None:
        # (変更なし)
        solution_type = solution.get("type")
        if solution_type == "regex_replace":
            search_pattern = solution["search"]
            replace_template = solution["replace"]
            replace_template = re.sub(r'\$(\d)', r'\\\1', replace_template)
            return re.sub(search_pattern, replace_template, code, flags=re.DOTALL)
        elif solution_type == "add_import":
            import_statement = solution["import"]
            if import_statement not in code:
                return f"{import_statement}\n{code}"
            return code
        elif solution_type == "regex_replace_with_import":
            import_statement = solution["import_statement"]
            modified_code = code
            if not re.search(fr"^\s*import\s+{re.escape(import_statement.split(' ')[1])}", code, re.MULTILINE):
                 if import_statement not in modified_code:
                    modified_code = f"{import_statement}\n{modified_code}"
            search_pattern = solution["search"]
            replace_template = solution["replace"]
            replace_template = re.sub(r'\$(\d)', r'\\\1', replace_template)
            return re.sub(search_pattern, replace_template, modified_code, flags=re.DOTALL)
        return None

    def _create_diff(self, original_code: str, modified_code: str, filename: str) -> str:
        # ★ 相対パスに変換
        rel_path = os.path.relpath(filename, self.project_path)
        filename_for_diff = Path(rel_path).as_posix() # /区切りに正規化
        diff = difflib.unified_diff(
            original_code.splitlines(keepends=True),
            modified_code.splitlines(keepends=True),
            fromfile=filename_for_diff,
            tofile=filename_for_diff,
        )
        return "".join(diff)
