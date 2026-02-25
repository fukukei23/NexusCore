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

import json
import logging
import os
from typing import Any

try:
    from ..utils.json_sanitizer import sanitize_json_like
    from .base_agent import BaseAgent
except ImportError:
    # --- フォールバック定義 ---
    def sanitize_json_like(payload: Any) -> Any:  # type: ignore[misc]
        return payload

    class BaseAgent:  # type: ignore[no-redef]
        def __init__(self, *args, **kwargs):
            self.logger = logging.getLogger(self.__class__.__name__)
            print("警告: BaseAgentが見つかりません。（フォールバック）")

        def execute_llm_task(self, prompt: str, as_json: bool = False) -> str:
            return "[]"

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

    def generate_plan(
        self, user_requirement: str, context: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """
        ユーザー要求とコンテキストから実装計画を生成する。
        """
        file_context_str = (
            self._get_file_context(context.get("project_path", ".")) if context else ""
        )

        prompt = f"""
# 指示
あなたは熟練したソフトウェア設計者です。以下の要件・制約・既存構造を踏まえ、
最低でも3件の実装タスクを含むJSON計画を必ず生成してください。

# プロジェクト要件（ユーザー入力をそのまま記載）
{user_requirement}

# 制約と期待されるアウトプット
- すべてのタスクは CLI ベースの ToDo アプリに直接関係すること。
- 永続化・エラー処理・テスト・ドキュメント等も必要であればタスクに含める。
- それぞれのタスクは単一責任・単一ファイルを原則とし、依存関係を明示する。
- ~~UI~~ のような不要要素は含めない。

# 参考となる既存ファイル一覧
{file_context_str}

# 出力フォーマット（STRICT JSON）
{{
  "functions_to_implement": [
    {{
      "name": "snake_case_function_name",
      "description": "短い説明",
      "args": ["arg_name: type"],
      "returns": "type",
      "dependencies": ["other_function"],
      "tests": ["テスト内容"],
      "acceptance_criteria": ["条件1", "条件2"],
      "priority": "P0 | P1 | P2"
    }}
  ]
}}

必ず上記スキーマ通りのJSONのみを返してください。追加の文章やコードフェンスは禁止です。
"""
        response_str = self.execute_llm_task(prompt, as_json=True)
        llm_mode = getattr(getattr(self, "llm_router", None), "last_mode", "real")
        if llm_mode != "real":
            self.logger.warning(
                f"PlannerAgent detected router mode='{llm_mode}'. Falling back to heuristic plan."
            )
            return self._fallback_plan(user_requirement, context)
        try:
            parsed = json.loads(response_str)
            if isinstance(parsed, dict):
                mode = str(parsed.get("mode", "")).lower()
                if "stub" in mode or "fallback" in mode:
                    self.logger.warning(
                        "PlannerAgent detected stub response (%s); using fallback plan.", mode
                    )
                    return self._fallback_plan(user_requirement, context)
            sanitized = sanitize_json_like(parsed)
            if not self._is_plan_valid(sanitized):
                self.logger.warning(
                    f"Generated plan is invalid or empty. Raw response: {response_str}"
                )
                return self._fallback_plan(user_requirement, context)
            if len(sanitized.get("functions_to_implement", [])) < 3:  # type: ignore[union-attr]
                self.logger.info("Plan contained fewer than 3 tasks; merging with fallback tasks.")
                fb = self._fallback_plan(user_requirement, context)
                existing = sanitized["functions_to_implement"]  # type: ignore[call-overload]
                names = {entry["name"] for entry in existing}
                for fb_task in fb["functions_to_implement"]:
                    if fb_task["name"] not in names:
                        existing.append(fb_task)
                sanitized["functions_to_implement"] = existing  # type: ignore[call-overload]
            return sanitized  # type: ignore[return-value]
        except Exception:
            self.logger.error(
                f"Failed to decode or validate JSON plan. Raw response: {response_str}",
                exc_info=True,
            )
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
                if file.endswith(
                    (
                        ".py",
                        ".js",
                        ".ts",
                        ".html",
                        ".css",
                        ".md",
                        ".json",
                        "Dockerfile",
                        "pyproject.toml",
                    )
                ):
                    filepaths.append(os.path.relpath(os.path.join(root, file), project_path))

        if not filepaths:
            return "プロジェクトにファイルが見つかりません。"

        if len(filepaths) > max_files:
            filepaths = sorted(filepaths, key=lambda p: (p.count("/"), len(p)))[:max_files]
            context = "関連ファイル (一部抜粋):\n" + "\n".join(f"- {fp}" for fp in filepaths)
        else:
            context = "関連ファイル:\n" + "\n".join(f"- {fp}" for fp in filepaths)
        return context

    def _is_plan_valid(self, plan: Any) -> bool:
        if not isinstance(plan, dict):
            return False
        f = plan.get("functions_to_implement")
        return isinstance(f, list) and len(f) > 0

    def _fallback_plan(
        self, user_requirement: str, context: dict[str, Any] | None
    ) -> dict[str, Any]:
        base_name = self._to_snake_case(user_requirement) or "planned_function"
        core_steps = [
            ("spec_analysis", "要件をJSON仕様にまとめ、主要エンティティとユースケースを洗い出す"),
            (
                "core_implementation",
                "アプリケーションの主要コマンド/機能を実装し、エラー処理を整備する",
            ),
            ("testing_and_docs", "pytest用のテストとREADME/使用手順を整備する"),
        ]

        functions: list[dict[str, Any]] = []
        for idx, (suffix, description) in enumerate(core_steps, start=1):
            functions.append(
                {
                    "name": f"{base_name}_{suffix}",
                    "description": f"{description}（要求: {user_requirement[:60]}...）",
                    "args": [],
                    "returns": "None",
                    "dependencies": [] if idx == 1 else [functions[idx - 2]["name"]],
                    "tests": ["pytest が成功すること", "主要フローで例外が発生しないこと"],
                    "acceptance_criteria": [
                        "要件で述べられたユースケースがCLI経由で実行できること",
                        "主要コマンドに対するドキュメントが整備されていること",
                    ],
                    "priority": "P1" if idx == 1 else ("P0" if idx == 2 else "P2"),
                }
            )

        return {"functions_to_implement": functions}

    @staticmethod
    def _to_snake_case(s: str) -> str:
        import re

        s = s.strip()
        s = re.sub(r"[^\w]+", "_", s)
        s = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s)
        s = s.replace("__", "_").strip("_")
        return s.lower()
