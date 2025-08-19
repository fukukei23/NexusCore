# ==============================================================================
# フォルダ: src/agents
# ファイル名: debugger_agent.py
# メモ: 【記憶能力強化版】外部から新しい知識を動的に追加するための
#      `add_knowledge`メソッドを実装。
# ==============================================================================
import os
import json
import re
import difflib
import logging
from pathlib import Path
from .base_agent import BaseAgent
# ==============================================================================
# フォルダ: src/agents
# ファイル名: debugger_agent.py
# メモ: 【信頼性向上・最終版】LLMに不確実なパッチを生成させるのをやめ、
#      「修正後の完全なコード」を生成させるようにプロンプトを変更。
#      受け取ったコードから、Python標準のdifflibを用いて、自ら100%正確な
#      パッチを生成するロジックにアップグレード。
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
あなたの仕事は、失敗したテストのエラーログと関連するソースコードを分析し、
エラーの根本原因を特定して、それを修正した後の完全なソースコードを生成することです。
"""

    def __init__(self, api_key: str, model: str, knowledge_base_path: str = "fkb_local.json", project_path: str = "."):
        super().__init__(api_key, model)
        self.knowledge_base_path = knowledge_base_path
        self.project_path = os.path.abspath(project_path)
        self.fkb = self._load_fkb()
        
        if self.fkb:
            self.logger.info(f"{len(self.fkb)} known issues loaded from: {self.knowledge_base_path}")
        else:
            self.logger.warning(f"EMPTY knowledge base. File not found or empty at: {self.knowledge_base_path}")

    def _load_fkb(self) -> list:
        try:
            if os.path.isabs(self.knowledge_base_path) and os.path.exists(self.knowledge_base_path):
                config_path = self.knowledge_base_path
            elif os.path.exists(os.path.join(self.project_path, self.knowledge_base_path)):
                 config_path = os.path.join(self.project_path, self.knowledge_base_path)
            else:
                base_dir = os.path.dirname(os.path.abspath(__file__))
                config_path = os.path.join(base_dir, '..', '..', self.knowledge_base_path)

            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            self.logger.error(f"Failed to load FKB from attempted paths: {e}")
            return []

    def add_knowledge(self, new_entry: dict):
        if isinstance(new_entry, dict) and "error_signature" in new_entry:
            self.fkb.append(new_entry)
            self.logger.info(f"New knowledge for '{new_entry.get('cause', 'N/A')}' added to in-memory FKB.")
        else:
            self.logger.warning(f"Attempted to add malformed knowledge entry: {new_entry}")

    def debug(self, error_log: str, files_context: dict) -> dict | None:
        self.logger.info(f"Debugging error... (log size: {len(error_log)} chars)")

        for entry in self.fkb:
            if re.search(entry["error_signature"], error_log, re.DOTALL | re.IGNORECASE):
                self.logger.info(f"Found known issue: {entry['cause']}")
                
                raw_target_hints = entry.get("target", "source_file")
                if isinstance(raw_target_hints, str):
                    raw_target_hints = [raw_target_hints] 

                target_hints = []
                for hint in raw_target_hints:
                    target_hints.extend([h.strip() for h in hint.split(',')])

                file_to_read_path = None
                found_target_hint = None
                for hint in target_hints:
                    if not hint: continue
                    path = files_context.get(hint)
                    if path and os.path.exists(path):
                        file_to_read_path = path
                        found_target_hint = hint
                        self.logger.info(f"Found target file '{path}' using symbolic hint '{hint}'.")
                        break
                    if not file_to_read_path:
                        for key, file_path_value in files_context.items():
                            normalized_hint = str(Path(hint)).replace("\\", "/")
                            normalized_path_value = str(Path(file_path_value)).replace("\\", "/")
                            if normalized_hint in normalized_path_value:
                                file_to_read_path = file_path_value
                                found_target_hint = key
                                self.logger.info(f"Found target file '{file_to_read_path}' by matching path hint '{hint}' with key '{key}'.")
                                break
                    if file_to_read_path:
                        break

                if not file_to_read_path:
                    self.logger.error(f"None of the target files for reading were found in context using hints: {target_hints}")
                    continue

                try:
                    with open(file_to_read_path, 'r', encoding='utf-8') as f:
                        original_code = f.read()
                    
                    solution = entry["solution_pattern"]
                    
                    if not isinstance(solution, dict):
                        self.logger.warning(f"Malformed solution_pattern in FKB entry for '{entry['cause']}'. Expected a dictionary, but got {type(solution)}. Skipping this solution.")
                        continue

                    if solution.get("type") == "llm_diagnose_and_fix":
                        self.logger.info("Attempting LLM-based diagnosis and fix...")
                        other_files_context = {k: v for k, v in files_context.items() if k != found_target_hint}
                        
                        # ▼▼▼▼▼ ここからが最重要修正点 ▼▼▼▼▼
                        modified_code = self._llm_generate_fixed_code(error_log, original_code, file_to_read_path, solution["instruction"], other_files_context)
                        if modified_code and original_code != modified_code:
                            patch_str = self._create_diff(original_code, modified_code, file_to_read_path)
                            self.logger.info(f"LLM-based fix generated a patch for '{found_target_hint}':\n{patch_str}")
                            return {"patch": patch_str, "target": found_target_hint, "entry": entry}
                        else:
                             self.logger.warning("LLM-based fix did not result in code changes.")
                        # ▲▲▲▲▲ ここまでが最重要修正点 ▲▲▲▲▲
                    else:
                        modified_code = self._apply_solution_pattern(original_code, solution)
                        if modified_code and original_code != modified_code:
                            diff = self._create_diff(original_code, modified_code, file_to_read_path)
                            self.logger.info(f"Generated patch for '{found_target_hint}':\n{diff}")
                            return {"patch": diff, "target": found_target_hint, "entry": entry}
                        else:
                            self.logger.warning(f"Solution pattern did not result in code changes for file: {file_to_read_path}")
                
                except Exception as e:
                    self.logger.error(f"Error applying solution for '{entry['cause']}': {e}", exc_info=True)
                
                return None

        self.logger.warning("No known solution found in FKB for this error.")
        return None

    # ▼▼▼▼▼ メソッド名を変更し、役割を明確化 ▼▼▼▼▼
    def _llm_generate_fixed_code(self, error_log: str, source_code: str, source_path: str, instruction: str, other_files: dict) -> str | None:
        context_str = ""
        source_path_rel = os.path.relpath(source_path, self.project_path)
        source_path_normalized = Path(source_path_rel).as_posix()
        
        for name, path in other_files.items():
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
                rel_path = os.path.relpath(path, self.project_path)
                context_str += f"\n\n--- Context File: {name} ({Path(rel_path).as_posix()}) ---\n```python\n{content}\n```"
            except Exception:
                pass

        # ▼▼▼▼▼ プロンプトを「完全なコード」を要求するように変更 ▼▼▼▼▼
        prompt = f"""
# CONTEXT
You are an expert developer debugging a failed test. Your task is to provide the complete, fixed version of the source code file.

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

# ABSOLUTE OUTPUT RULES
- **Output ONLY the complete and fixed Python code for the file `{source_path_normalized}`.**
- Do NOT include any explanations, apologies, or any text before or after the code block.
- Your output must start with `def` or `import` and be a single, clean block of Python code.
"""
        # ▲▲▲▲▲ プロンプトを「完全なコード」を要求するように変更 ▲▲▲▲▲
        
        fixed_code_raw = self._call_llm(prompt, self.DEBUG_SYSTEM_PROMPT)
        
        # LLMの出力からコードブロックを抽出する堅牢なロジック
        match = re.search(r"```(?:python\n)?(.*)```", fixed_code_raw, re.DOTALL)
        if match:
            return match.group(1).strip()
        
        # コードブロックが見つからない場合、出力がそのままコードであると仮定
        return fixed_code_raw.strip()


    def _apply_solution_pattern(self, code: str, solution: dict) -> str | None:
        # (このメソッドは変更なし)
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
        # (このメソッドは変更なし)
        rel_path = os.path.relpath(filename, self.project_path)
        filename_for_diff = Path(rel_path).as_posix()
        diff = difflib.unified_diff(
            original_code.splitlines(keepends=True),
            modified_code.splitlines(keepends=True),
            fromfile=filename_for_diff,
            tofile=filename_for_diff,
        )
        return "".join(diff)

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
        self.project_path = os.path.abspath(project_path)
        self.fkb = self._load_fkb()
        
        if self.fkb:
            self.logger.info(f"{len(self.fkb)} known issues loaded from: {self.knowledge_base_path}")
        else:
            self.logger.warning(f"EMPTY knowledge base. File not found or empty at: {self.knowledge_base_path}")

    def _load_fkb(self) -> list:
        try:
            if os.path.isabs(self.knowledge_base_path) and os.path.exists(self.knowledge_base_path):
                config_path = self.knowledge_base_path
            elif os.path.exists(os.path.join(self.project_path, self.knowledge_base_path)):
                 config_path = os.path.join(self.project_path, self.knowledge_base_path)
            else:
                base_dir = os.path.dirname(os.path.abspath(__file__))
                config_path = os.path.join(base_dir, '..', '..', self.knowledge_base_path)

            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            self.logger.error(f"Failed to load FKB from attempted paths: {e}")
            return []

    # ▼▼▼▼▼ ここからが最重要修正点 ▼▼▼▼▼
    def add_knowledge(self, new_entry: dict):
        """新しい知識エントリをメモリ内のFKBに動的に追加する。"""
        if isinstance(new_entry, dict) and "error_signature" in new_entry:
            self.fkb.append(new_entry)
            self.logger.info(f"New knowledge for '{new_entry.get('cause', 'N/A')}' added to in-memory FKB.")
        else:
            self.logger.warning(f"Attempted to add malformed knowledge entry: {new_entry}")
    # ▲▲▲▲▲ ここまでが最重要修正点 ▲▲▲▲▲

    def debug(self, error_log: str, files_context: dict) -> dict | None:
        self.logger.info(f"Debugging error... (log size: {len(error_log)} chars)")

        for entry in self.fkb:
            if re.search(entry["error_signature"], error_log, re.DOTALL | re.IGNORECASE):
                self.logger.info(f"Found known issue: {entry['cause']}")
                
                raw_target_hints = entry.get("target", "source_file")
                if isinstance(raw_target_hints, str):
                    raw_target_hints = [raw_target_hints] 

                target_hints = []
                for hint in raw_target_hints:
                    target_hints.extend([h.strip() for h in hint.split(',')])

                file_to_read_path = None
                found_target_hint = None
                for hint in target_hints:
                    if not hint: continue

                    path = files_context.get(hint)
                    if path and os.path.exists(path):
                        file_to_read_path = path
                        found_target_hint = hint
                        self.logger.info(f"Found target file '{path}' using symbolic hint '{hint}'.")
                        break

                    if not file_to_read_path:
                        for key, file_path_value in files_context.items():
                            normalized_hint = str(Path(hint)).replace("\\", "/")
                            normalized_path_value = str(Path(file_path_value)).replace("\\", "/")
                            
                            if normalized_hint in normalized_path_value:
                                file_to_read_path = file_path_value
                                found_target_hint = key
                                self.logger.info(f"Found target file '{file_to_read_path}' by matching path hint '{hint}' with key '{key}'.")
                                break
                    
                    if file_to_read_path:
                        break

                if not file_to_read_path:
                    self.logger.error(f"None of the target files for reading were found in context using hints: {target_hints}")
                    continue

                try:
                    with open(file_to_read_path, 'r', encoding='utf-8') as f:
                        original_code = f.read()
                    
                    solution = entry["solution_pattern"]
                    
                    if not isinstance(solution, dict):
                        self.logger.warning(f"Malformed solution_pattern in FKB entry for '{entry['cause']}'. Expected a dictionary, but got {type(solution)}. Skipping this solution.")
                        continue

                    if solution.get("type") == "llm_diagnose_and_fix":
                        self.logger.info("Attempting LLM-based diagnosis and fix...")
                        other_files_context = {k: v for k, v in files_context.items() if k != found_target_hint}
                        patch_str = self._llm_generate_patch(error_log, original_code, file_to_read_path, solution["instruction"], other_files_context)
                        if patch_str:
                            return {"patch": patch_str, "target": found_target_hint, "entry": entry}
                    else:
                        modified_code = self._apply_solution_pattern(original_code, solution)
                        if modified_code and original_code != modified_code:
                            diff = self._create_diff(original_code, modified_code, file_to_read_path)
                            self.logger.info(f"Generated patch for '{found_target_hint}':\n{diff}")
                            return {"patch": diff, "target": found_target_hint, "entry": entry}
                        else:
                            self.logger.warning(f"Solution pattern did not result in code changes for file: {file_to_read_path}")
                
                except Exception as e:
                    self.logger.error(f"Error applying solution for '{entry['cause']}': {e}", exc_info=True)
                
                return None

        self.logger.warning("No known solution found in FKB for this error.")
        return None

    def _llm_generate_patch(self, error_log: str, source_code: str, source_path: str, instruction: str, other_files: dict) -> str | None:
        # (このメソッドは変更なし)
        context_str = ""
        source_path_rel = os.path.relpath(source_path, self.project_path)
        source_path_normalized = Path(source_path_rel).as_posix()
        
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
        
        if "```" in patch:
            match = re.search(r"```(?:diff\n)?((?:.|\n)*?)```", patch, re.DOTALL)
            if match:
                patch_content = match.group(1).strip()
                patch = patch_content + "\n"
        
        if patch and patch.startswith("---") and "+++" in patch and "@@" in patch:
            self.logger.info(f"LLM generated a valid-looking patch:\n{patch}")
            return patch
            
        self.logger.warning(f"LLM did not generate a valid patch. Output:\n{patch}")
        return None

    def _apply_solution_pattern(self, code: str, solution: dict) -> str | None:
        # (このメソッドは変更なし)
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
        # (このメソッドは変更なし)
        rel_path = os.path.relpath(filename, self.project_path)
        filename_for_diff = Path(rel_path).as_posix()
        diff = difflib.unified_diff(
            original_code.splitlines(keepends=True),
            modified_code.splitlines(keepends=True),
            fromfile=filename_for_diff,
            tofile=filename_for_diff,
        )
        return "".join(diff)
