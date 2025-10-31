# ==============================================================================
# 操作するソフト: VSCode (または任意のテキストエディタ)
# フォルダ: src/nexuscore/agents/
# ファイル名: debugger_agent.py
# バージョン: 3.0 (データベース対応・最終版)
#
# メモ:
# これは、「ステートストア」と「ナレッジベース」の導入に伴い、
# データベース中心のアーキテクチャに完全に対応したDebuggerAgentです。
#
# 【主な改良点】
# 1. KnowledgeBase(PostgreSQL)への標準対応:
#    - デフォルトで、中央の`knowledge_base`モジュール(PostgreSQL)から
#      知識を検索するようになりました。これにより、常に最新の学習結果を
#      利用してデバッグを行います。
# 2. Curatorの検証プロセスへの後方互換性:
#    - `__init__`時に、従来の`knowledge_base_path`引数が渡された場合
#      (KnowledgeCuratorAgentによる検証時)、その一時的なJSONファイルから
#      知識を読み込むようになっています。
#    - これにより、既存の`knowledge_curator_agent.py`のロジックを
#      一切変更することなく、新しいアーキテクチャと連携できます。
# 3. 知識の動的追加:
#    - Orchestratorが`add_knowledge`メソッドを呼び出すことで、
#      実行中のDebuggerAgentに新しい知識を動的に「教える」ことができます。
# ==============================================================================
import json
import re
import logging
import os
import difflib
from pathlib import Path
from typing import List, Dict, Any, Optional

from .base_agent import BaseAgent
from .patch_applier import PatchApplier

# --- データベースモジュールをインポート ---
from nexuscore.database.knowledge_base import knowledge_base

class DebuggerAgent(BaseAgent):
    SYSTEM_PROMPT = """
あなたは、熟練のソフトウェア開発者であり、デバッグの達人です。
あなたの仕事は、失敗したテストのエラーログと関連するソースコードを分析し、
エラーの根本原因を特定して、それを修正した後の完全なソースコードを生成することです。
"""

    def __init__(
        self,
        api_key: str,
        model: str,
        project_path: str,
        # ★改良点: knowledge_base_pathはオプショナルになり、下位互換性のためにのみ使用
        knowledge_base_path: Optional[str] = None
    ):
        super().__init__(api_key, model) # BaseAgentの初期化
        self.project_path = os.path.abspath(project_path)
        self.patcher = PatchApplier()
        self.in_memory_knowledge: List[Dict] = []

        # ★★★★★ ここからがアーキテクチャ更新の核心 ★★★★★
        if knowledge_base_path:
            # Curatorによる検証モード: 指定された一時ファイルから知識を読み込む
            self.logger.info(f"DebuggerAgent is in VALIDATION MODE, using temporary FKB: {knowledge_base_path}")
            try:
                with open(knowledge_base_path, 'r', encoding='utf-8') as f:
                    self.in_memory_knowledge = json.load(f)
            except (IOError, json.JSONDecodeError) as e:
                self.logger.error(f"Failed to load temporary FKB for validation: {e}")
        else:
            # 通常モード: 中央のPostgreSQLデータベースを参照する (直接の参照はfind_solution内で行う)
            self.logger.info("DebuggerAgent is in NORMAL MODE, using central PostgreSQL KnowledgeBase.")
        # ★★★★★ ここまで ★★★★★


    def add_knowledge(self, new_knowledge: dict):
        """
        Orchestratorから呼び出され、実行中に新しい知識を動的に追加する。
        これにより、学習サイクルが成功した直後に、その知識を即座に利用できる。
        """
        if new_knowledge and isinstance(new_knowledge, dict):
            self.logger.info(f"Dynamically adding new knowledge: {new_knowledge.get('error_signature')}")
            # 重複を避ける
            if not any(e.get('error_signature') == new_knowledge.get('error_signature') for e in self.in_memory_knowledge):
                self.in_memory_knowledge.append(new_knowledge)


    def debug(self, error_log: str, files_context: Dict[str, str]) -> Dict[str, Any]:
        """エラーログを分析し、修正パッチを生成する"""
        self.logger.info("Starting debug process...")

        # 1. まず、インメモリの知識(Curatorからの検証知識 or 動的追加された知識)を検索
        solution = self._find_solution_in_list(error_log, self.in_memory_knowledge)

        # 2. インメモリで見つからなければ、中央のDB(PostgreSQL)を検索
        if not solution:
            self.logger.info("No solution in memory, querying central KnowledgeBase...")
            solution = knowledge_base.find_solution(error_log)

        if not solution:
            self.logger.warning("No applicable solution found in any knowledge source.")
            return {"status": "no_solution_found"}

        self.logger.info(f"Found matching solution with signature: {solution['error_signature']}")
        
        # 3. 解決策のパターンに応じて処理を実行
        solution_pattern = solution.get("solution_pattern", {})
        solution_type = solution_pattern.get("type")

        if solution_type == "llm_diagnose_and_fix":
            return self._handle_llm_fix(solution, error_log, files_context)
        else:
            self.logger.error(f"Unknown or unsupported solution type: {solution_type}")
            return {"status": "unknown_solution_type"}

    def _find_solution_in_list(self, error_log: str, knowledge_list: List[Dict]) -> Optional[Dict]:
        """与えられたリストの中から解決策を探すヘルパー関数"""
        for entry in knowledge_list:
            pattern = entry.get("error_signature")
            if pattern:
                try:
                    if re.search(pattern, error_log):
                        return entry
                except re.error as e:
                    self.logger.warning(f"Invalid regex in in-memory knowledge: {pattern} ({e})")
                    continue
        return None

    def _handle_llm_fix(self, solution: dict, error_log: str, files_context: Dict[str, str]) -> Dict[str, Any]:
        """LLMに修正後の完全なコードを生成させ、そこからパッチを作成する"""
        self.logger.info("Delegating to LLM for full code generation based on FKB instruction.")
        
        instruction = solution.get("solution_pattern", {}).get("instruction", "")
        target_hint = solution.get("target", "source_file") # デフォルトはsource_file
        
        target_file_path = files_context.get(target_hint)
        if not target_file_path or not os.path.exists(target_file_path):
             self.logger.error(f"Target file for hint '{target_hint}' not found in context.")
             return {"status": "target_file_not_found"}

        try:
            with open(target_file_path, 'r', encoding='utf-8') as f:
                original_code = f.read()
        except IOError as e:
            self.logger.error(f"Failed to read target file {target_file_path}: {e}")
            return {"status": "file_read_error"}

        other_files_context = {k: v for k, v in files_context.items() if k != target_hint}
        
        modified_code = self._llm_generate_fixed_code(error_log, original_code, target_file_path, instruction, other_files_context)

        if modified_code and original_code != modified_code:
            patch_str = self._create_diff(original_code, modified_code, target_file_path)
            self.logger.info(f"LLM-based fix generated a patch for '{target_hint}':\n{patch_str}")
            return {"status": "patch_generated", "patch": patch_str, "target": target_hint}
        else:
            self.logger.warning("LLM-based fix did not result in code changes.")
            return {"status": "no_change"}

    def _llm_generate_fixed_code(self, error_log: str, source_code: str, source_path: str, instruction: str, other_files: dict) -> str | None:
        """LLMに修正後の完全なコードを生成させる"""
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
        
        try:
            fixed_code_raw = self.execute_llm_task(prompt)
            
            match = re.search(r"```(?:python\n)?(.*)```", fixed_code_raw, re.DOTALL)
            if match:
                return match.group(1).strip()
            
            return fixed_code_raw.strip()
        except Exception as e:
            self.logger.error(f"An unexpected error occurred during LLM code generation: {e}", exc_info=True)
            return None

    def _create_diff(self, original_code: str, modified_code: str, filename: str) -> str:
        rel_path = os.path.relpath(filename, self.project_path)
        filename_for_diff = Path(rel_path).as_posix()
        diff = difflib.unified_diff(
            original_code.splitlines(keepends=True),
            modified_code.splitlines(keepends=True),
            fromfile=filename_for_diff,
            tofile=filename_for_diff,
        )
        return "".join(diff)
