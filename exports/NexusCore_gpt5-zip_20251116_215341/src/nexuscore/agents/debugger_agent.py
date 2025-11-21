# ==============================================================================
# 操作するソフト: VSCode (または任意のテキストエディタ)
# レジストリ/フォルダ: C:\Users\USER\tools\NexusCore\src\nexuscore\agents\
# ファイル名: debugger_agent.py
# 日付: 2025/09/01
#
# 使用方法:
#   このファイルを指定のパスに保存（上書き）してください。
#   あなたの最新の改良ロジックを維持しつつ、構文エラーと未定義メソッドエラーを修正した最終FIX版です。
#
# 改修内容:
#   - あなたが実装した、より堅牢な _find_solution_from_kb を維持。
#   - あなたの意図を汲み、堅牢な相対パス処理を行う _create_diff メソッドを実装。
#   - _generate_fixed_code内の三重引用符が閉じていないSyntaxErrorを修正。
#   - LLMからの応答を抽出し、整形するロジックを _generate_fixed_code に追加。
#   - knowledge_baseのimportパスを、プロジェクトアーキテクチャに合わせて修正。
# ==============================================================================

import os
import json
import re
import logging
from typing import Optional, Dict, Any
import difflib

try:
    from .base_agent import BaseAgent
    # ▼▼▼【Importパス修正】プロジェクトアーキテクチャに合わせて修正▼▼▼
    from database.knowledge_base import knowledge_base
    # ▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲
except ImportError:
    # 開発・テスト用のフォールバック
    knowledge_base = None
    class BaseAgent:
        def __init__(self, *args, **kwargs):
            self.logger = logging.getLogger(self.__class__.__name__)
        def execute_llm_task(self, prompt: str, as_json: bool = False) -> str: return ""
        def _call_llm(self, prompt: str, system_prompt: str, as_json: bool = False) -> str:
            return self.execute_llm_task(prompt, as_json)

class DebuggerAgent(BaseAgent):
    """
    テスト失敗ログを分析し、コードのバグを特定・修正するエージェント。
    中央のナレッジベースと連携し、過去の失敗から学習する。
    """
    SYSTEM_PROMPT = """あなたは、ソフトウェアのデバッグを専門とするAIアシスタントです。あなたの仕事は、失敗したテストのログと関連するソースコードを分析し、バグの根本原因を特定し、それを修正するためのパッチ（unified diff形式）を生成することです。"""

    def __init__(self, knowledge_base_path: Optional[str] = None):
        """
        DebuggerAgentを初期化する。
        """
        super().__init__()
        self.local_knowledge_base = None
        if knowledge_base_path:
            self.logger.info(f"Using local temporary knowledge base: {knowledge_base_path}")
            try:
                with open(knowledge_base_path, 'r', encoding='utf-8') as f:
                    self.local_knowledge_base = json.load(f)
            except Exception:
                self.logger.error(
                    f"Failed to load local knowledge base from {knowledge_base_path}",
                    exc_info=True
                )

    def debug_and_patch(self, error_log: str, files_content: Dict[str, str], project_path: str) -> Dict[str, Any]:
        """
        エラーログとファイル内容からバグを修正し、パッチを返す。
        """
        if not files_content:
            return {"error": "No files provided for debugging."}
            
        # 現状は単一ファイル処理を前提とする
        source_path = next(iter(files_content))
        source_code = files_content[source_path]
        
        solution = self._find_solution_from_kb(error_log)
        
        instruction = "Analyze the error log and source code to identify the root cause of the bug and generate a fix."
        if solution:
            self.logger.info(f"Found a known solution in knowledge base for: {solution.get('error_signature')}")
            instruction = (
                f"A known solution was found: {solution.get('cause')}. "
                f"Apply the following pattern: {json.dumps(solution.get('solution_pattern'), ensure_ascii=False)}"
            )
            
        fixed_code = self._generate_fixed_code(error_log, source_path, source_code, instruction)
        
        if not fixed_code:
            return {"error": "Failed to generate fixed code."}
            
        patch = self._create_diff(source_code, fixed_code, source_path, project_path)
        
        return {"patch": patch, "fixed_code": fixed_code, "solution_used": solution}

    def _find_solution_from_kb(self, error_log: str) -> Optional[Dict[str, Any]]:
        """【あなたの改良案を維持】より安全なナレッジ検索"""
        if self.local_knowledge_base:
            for entry in self.local_knowledge_base:
                if "error_signature" in entry and re.search(entry["error_signature"], error_log or ""):
                    return entry
            return None
            
        if knowledge_base and hasattr(knowledge_base, "find_solution"):
            try:
                return knowledge_base.find_solution(error_log)
            except Exception:
                self.logger.warning("knowledge_base.find_solution failed.", exc_info=True)
                return None
                
        return None

    def _generate_fixed_code(self, error_log: str, source_path: str, source_code: str, instruction: str) -> Optional[str]:
        prompt = f"""
# INSTRUCTION
{instruction}

# FAILED TEST LOG
```
{error_log}
```

# SOURCE CODE TO FIX: {source_path}
```python
{source_code}
"""