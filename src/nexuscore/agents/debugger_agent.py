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

import difflib
import json
import logging
import os
import re
import sys
from typing import Any

try:
    from .base_agent import BaseAgent
except ImportError:
    BaseAgent = None  # type: ignore[misc, assignment]

# knowledge_base: プロジェクトルートの database/knowledge_base を参照。CWD に依存しないようリトライする。
knowledge_base = None


def _find_project_root_for_database() -> str | None:
    """database/knowledge_base.py が存在するディレクトリ（プロジェクトルート）を探す。"""
    env_root = os.getenv("NEXUS_PROJECT_ROOT")
    if env_root and os.path.isdir(env_root):
        kb_path = os.path.join(env_root, "database", "knowledge_base.py")
        if os.path.isfile(kb_path):
            return env_root
    try:
        current = os.path.dirname(os.path.abspath(__file__))
        for _ in range(6):
            kb_path = os.path.join(current, "database", "knowledge_base.py")
            if os.path.isfile(kb_path):
                return current
            parent = os.path.dirname(current)
            if parent == current:
                break
            current = parent
    except Exception:
        pass
    return None


try:
    from database.knowledge_base import knowledge_base  # type: ignore[assignment]
except ImportError:
    _root = _find_project_root_for_database()
    if _root and _root not in sys.path:
        sys.path.insert(0, _root)
    try:
        from database.knowledge_base import knowledge_base  # type: ignore[assignment]
    except ImportError:
        pass

if BaseAgent is None:

    class BaseAgent:  # type: ignore[no-redef]
        def __init__(self, *args, **kwargs):
            self.logger = logging.getLogger(self.__class__.__name__)

        def execute_llm_task(self, prompt: str, as_json: bool = False) -> str:
            return ""

        def _call_llm(self, prompt: str, system_prompt: str, as_json: bool = False) -> str:
            return self.execute_llm_task(prompt, as_json)


class DebuggerAgent(BaseAgent):
    """
    テスト失敗ログを分析し、コードのバグを特定・修正するエージェント。
    中央のナレッジベースと連携し、過去の失敗から学習する。
    """

    total_pr_attempts: int = 0
    successful_prs: int = 0

    SYSTEM_PROMPT = """あなたは、ソフトウェアのデバッグを専門とするAIアシスタントです。あなたの仕事は、失敗したテストのログと関連するソースコードを分析し、バグの根本原因を特定し、それを修正するためのパッチ（unified diff形式）を生成することです。"""

    def __init__(self, knowledge_base_path: str | None = None):
        """
        DebuggerAgentを初期化する。
        """
        super().__init__()
        self.local_knowledge_base = None
        if knowledge_base_path:
            self.logger.info(f"Using local temporary knowledge base: {knowledge_base_path}")
            try:
                with open(knowledge_base_path, encoding="utf-8") as f:
                    self.local_knowledge_base = json.load(f)
            except Exception:
                self.logger.error(
                    f"Failed to load local knowledge base from {knowledge_base_path}", exc_info=True
                )

    def debug_and_patch(
        self, error_log: str, files_content: dict[str, str], project_path: str
    ) -> dict[str, Any]:
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
            self.logger.info(
                f"Found a known solution in knowledge base for: {solution.get('error_signature')}"
            )
            instruction = (
                f"A known solution was found: {solution.get('cause')}. "
                f"Apply the following pattern: {json.dumps(solution.get('solution_pattern'), ensure_ascii=False)}"
            )

        fixed_code = self._generate_fixed_code(error_log, source_path, source_code, instruction)

        if not fixed_code:
            return {"error": "Failed to generate fixed code."}

        patch = self._create_diff(source_code, fixed_code, source_path, project_path)

        return {"patch": patch, "fixed_code": fixed_code, "solution_used": solution}

    def _find_solution_from_kb(self, error_log: str) -> dict[str, Any] | None:
        """【あなたの改良案を維持】より安全なナレッジ検索"""
        if self.local_knowledge_base:
            for entry in self.local_knowledge_base:
                if "error_signature" in entry and re.search(
                    entry["error_signature"], error_log or ""
                ):
                    return entry
            return None

        if knowledge_base and hasattr(knowledge_base, "find_solution"):
            try:
                return knowledge_base.find_solution(error_log)
            except Exception:
                self.logger.warning("knowledge_base.find_solution failed.", exc_info=True)
                return None

        return None

    def _generate_fixed_code(
        self, error_log: str, source_path: str, source_code: str, instruction: str
    ) -> str | None:
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
```
"""
        try:
            response = self.execute_llm_task(prompt, as_json=False)
        except Exception as e:
            self.logger.error(f"execute_llm_task failed: {e}", exc_info=True)
            return None

        if not response:
            return None

        sanitized = response.strip()
        if sanitized.startswith("```"):
            sanitized = sanitized.strip("`")
            if sanitized.lower().startswith("diff"):
                sanitized = sanitized[4:].strip()
            elif sanitized.lower().startswith("python"):
                sanitized = sanitized[6:].strip()
        return sanitized or None

    def _create_diff(self, original: str, fixed: str, source_path: str, project_path: str) -> str:
        """
        Unified diff を生成。プロジェクトルートからの相対パスを利用する。
        """
        try:
            rel_path = os.path.relpath(source_path, project_path)
        except Exception:
            rel_path = source_path

        original_lines = original.splitlines(keepends=True)
        fixed_lines = fixed.splitlines(keepends=True)
        diff = difflib.unified_diff(
            original_lines,
            fixed_lines,
            fromfile=f"a/{rel_path}",
            tofile=f"b/{rel_path}",
        )
        return "".join(diff)


    def auto_generate_pr(
        self,
        error_log: str,
        files_content: dict[str, str],
        project_path: str,
        repo_full_name: str,
        base_branch: str,
        fix_branch: str,
        github_token: str,
    ) -> dict[str, Any]:
        """
        エラーログからパッチを生成し、GitHub PR を自動作成するフルフロー。

        フロー:
          1. debug_and_patch() でパッチ・修正コードを生成
          2. GitHubPRCreator.create_fix_pr() でブランチ作成→コミット→PR作成

        Returns:
            成功: {"status": "created", "pr_number": int, "pr_url": str, "branch": str}
            失敗: {"status": "error", "error": str}
        """
        from nexuscore.agents.github_pr_creator import GitHubPRCreator

        DebuggerAgent.total_pr_attempts += 1

        result = self.debug_and_patch(error_log, files_content, project_path)
        if "error" in result:
            return {"status": "error", "error": result["error"]}

        fixed_code = result.get("fixed_code")
        if not fixed_code:
            return {"status": "error", "error": "No fixed code generated."}

        source_path = next(iter(files_content))
        original_code = files_content[source_path]
        if fixed_code.strip() == original_code.strip():
            return {"status": "skipped", "reason": "no_changes"}

        error_summary = (error_log or "")[:120].replace("\n", " ")

        try:
            creator = GitHubPRCreator(token=github_token)
            pr_result = creator.create_fix_pr(
                repo_full_name=repo_full_name,
                file_path=source_path,
                fixed_content=fixed_code,
                base_branch=base_branch,
                fix_branch=fix_branch,
                error_summary=error_summary,
                original_content=original_code,
            )
            if pr_result.get("status") == "created":
                DebuggerAgent.successful_prs += 1
            return pr_result
        except Exception as e:
            self.logger.error("PR creation failed: %s", e, exc_info=True)
            return {"status": "error", "error": str(e)}
