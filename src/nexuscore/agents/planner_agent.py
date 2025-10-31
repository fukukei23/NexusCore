# ==============================================================================
# 操作するソフト: VSCode (または任意のテキストエディタ)
# レジストリ/フォルダ: C:\Users\USER\tools\NexusCore\src\nexuscore\agents\
# ファイル名: planner_agent.py
# 日付: 2025/09/02
#
# 使用方法:
#   このファイルを指定のパスに保存（上書き）してください。
#   `Tuple`が未定義であるというPylanceのエラーを解決します。
#
# 改修内容:
#   - `typing`モジュールから`Tuple`をインポートする文を追加しました。
# ==============================================================================

from __future__ import annotations
import os
import json
import logging
from typing import List, Dict, Any, Optional, Callable, Tuple # Tupleをインポート
from pathlib import Path

try:
    from .base_agent import BaseAgent
    from ..utils.json_sanitizer import sanitize_json_like
except ImportError:
    # --- フォールバック定義 ---
    def sanitize_json_like(payload: Any) -> Any: return payload
    class BaseAgent:
        def __init__(self, *args, **kwargs):
            self.logger = logging.getLogger(self.__class__.__name__)
            print("警告: BaseAgentが見つかりません。（フォールバック）")
        def execute_llm_task(self, prompt: str, as_json: bool = False) -> str: return "[]"
        def _call_llm(self, prompt: str, system_prompt: str, as_json: bool = False) -> str:
            return self.execute_llm_task(prompt, as_json)

class PlannerAgent(BaseAgent):
    """
    与えられた要件とファイルコンテキストに基づき、
    実装計画を詳細なタスクリストに分解するエージェント。
    """
    SYSTEM_PROMPT = """
あなたは、複雑なソフトウェア要件を、実行可能なタスクの順序付きリストに分解することを専門とする、経験豊富なソフトウェアアーキテクトです。
あなたの仕事は、ユーザーの要求と既存のコードを分析し、開発者が従うべき明確で具体的な実装計画を作成することです。
各タスクは、単一のファイルに対する単一の責任を持つ、可能な限り最小の単位でなければなりません。
"""

    def __init__(self):
        """
        PlannerAgentを初期化する。
        """
        super().__init__()

    def generate_plan(self, user_requirement: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        ユーザー要求とコンテキストから実装計画を生成する。
        """
        file_context_str = self._get_file_context(context.get("project_path", ".")) if context else ""

        prompt = f"""
# あなたへの指示
以下のユーザー要件と、関連する既存のファイルコンテキストを分析し、実装計画をJSON形式で生成してください。

# ユーザー要件
{user_requirement}

# 関連ファイルコンテキスト
{file_context_str}

# 出力要件
- 出力は、`functions_to_implement` というキーを持つ単一のJSONオブジェクトでなければなりません。
- `functions_to_implement` の値は、実装すべき機能のリスト（配列）です。
- 各機能は、以下のキーを持つJSONオブジェクトです:
  - `name`: 関数名 (snake_case)
  - `description`: 機能の短い説明
  - `args`: 引数のリスト (例: `["arg1: str", "arg2: int"]`)
  - `returns`: 戻り値の型 (例: `"str"`, `"List[Dict]"`, `"None"`)
  - `dependencies`: 依存する他の関数やモジュールのリスト
  - `tests`: この機能を検証するためのテストケースのリスト（文字列）
  - `acceptance_criteria`: 受け入れ基準のリスト（文字列）
  - `priority`: 優先度 (例: "P0", "P1", "P2")
- 説明や追加のテキストは一切含めないでください。
"""
        response_str = self.execute_llm_task(prompt, as_json=True)
        try:
            sanitized = sanitize_json_like(response_str)
            if self._is_plan_valid(sanitized):
                return sanitized
            else:
                self.logger.warning(f"Generated plan is invalid or empty. Raw response: {response_str}")
                return self._fallback_plan(user_requirement, context)
        except Exception:
            self.logger.error(f"Failed to decode or validate JSON plan. Raw response: {response_str}", exc_info=True)
            return self._fallback_plan(user_requirement, context)

    def _get_file_context(self, project_path: str, max_files: int = 15) -> str:
        """
        プロジェクト内のファイル構造を分析し、LLMに与えるコンテキストを生成する。
        """
        filepaths = []
        for root, _, files in os.walk(project_path):
            if any(d in root for d in [".git", "__pycache__", ".venv", "node_modules"]):
                continue
            for file in files:
                if file.endswith(('.py', '.js', '.ts', '.html', '.css', '.md', '.json', 'Dockerfile', 'pyproject.toml')):
                    filepaths.append(os.path.relpath(os.path.join(root, file), project_path))

        if not filepaths:
            return "プロジェクトにファイルが見つかりません。"
        
        if len(filepaths) > max_files:
            filepaths = sorted(filepaths, key=lambda p: (p.count('/'), len(p)))[:max_files]
            context = "関連ファイル (一部抜粋):\n" + "\n".join(f"- {fp}" for fp in filepaths)
        else:
            context = "関連ファイル:\n" + "\n".join(f"- {fp}" for fp in filepaths)
        return context

    def _is_plan_valid(self, plan: Any) -> bool:
        if not isinstance(plan, dict): return False
        f = plan.get("functions_to_implement")
        return isinstance(f, list) and len(f) > 0

    def _fallback_plan(self, user_requirement: str, context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        name = self._to_snake_case(user_requirement)[:32] or "planned_function"
        return {
            "functions_to_implement": [{
                "name": name,
                "description": f"Auto-generated stub for: {user_requirement[:80]}",
                "args": [],
                "returns": "None",
                "dependencies": [],
                "tests": ["Should run without exceptions.", "Smoke import succeeds."],
                "acceptance_criteria": ["Code compiles and minimal flow executes."],
                "priority": "P2",
            }]
        }

    @staticmethod
    def _to_snake_case(s: str) -> str:
        import re
        s = s.strip()
        s = re.sub(r"[^\w]+", "_", s)
        s = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s)
        s = s.replace("__", "_").strip("_")
        return s.lower()
