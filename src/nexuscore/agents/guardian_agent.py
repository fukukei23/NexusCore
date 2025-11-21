# ==============================================================================
# 操作するソフト: VSCode (または任意のテキストエディタ)
# フォルダ: src/nexuscore/agents/
# ファイル名: guardian_agent.py
# 日付: 2025/09/03
#
# 使用方法:
#   この内容で既存のファイルを上書きしてください。
#   BaseAgentの近代化された__init__契約に準拠させるための修正です。
#
# 改修内容:
#   - super().__init__()を、引数なしで呼び出すように修正しました。
#   - 受け取ったmodel名は、自身の属性として保持するようにしました。
# ==============================================================================

from __future__ import annotations

import os
import json
import git
from typing import Any, Dict, Optional, Callable, List

from .base_agent import BaseAgent
from nexuscore.utils.vcs import GitController

class GuardianAgent(BaseAgent):
    """
    コードの品質、セキュリティ、プロジェクト憲法への準拠をレビューし、
    承認時のみ Git に記録する CTO エージェント。
    """
    SYSTEM_PROMPT = """
あなたはCTO（最高技術責任者）です。
開発チームから提出されたコード、テスト結果、その他の情報を総合的にレビューし、
その変更を承認（APPROVE）するか、修正のために差し戻す（REJECT）かを判断してください。
判断は、プロジェクトの憲法と、提示された技術的証拠に厳密に基づいてください。
"""
    on_budget_tick: Optional[Callable[[str], None]] = None

    # ▼▼▼【最重要修正点】ここから▼▼▼
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        """
        api_key/model はオプション扱い。未指定でも BaseAgent のルーター経由でスタブ/実コールが走る。
        実運用で専用モデルを強制したい場合は model を明示する。
        """
        super().__init__()  # 引数なしで呼び出すのが正しい作法
        self.model = model or ""  # model名は自身の属性として保持
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY", "")
        # ▲▲▲【最重要修正点】ここまで▲▲▲
        try:
            self.vcs = GitController()
        except git.InvalidGitRepositoryError:
            self.vcs = None
            print("⚠️ GuardianAgent: Gitリポジトリが見つからないため、コミット機能は無効です。")

    def _budget(self, step: str) -> None:
        try:
            if callable(self.on_budget_tick):
                self.on_budget_tick(step)
        except Exception:
            pass

    def review(
        self,
        code_draft: str,
        test_code: str,
        test_result: str,
        testimony: str,
        constitution: str,
        task_description: str
    ) -> Dict[str, Any]:
        """
        コードと証跡をレビューして JSON を返す（コミットはしない）
        """
        self._budget("guardian:review")

        prompt = f"""
# レビュー対象の情報
- **プロジェクト憲法**: {constitution}
- **元のタスク**: {task_description}
- **提出コード**:
```python
{code_draft}
```
- **テストコード**:
```python
{test_code}
```
- **テスト結果**:
```
{test_result}
```
- **開発者の証言**: {testimony}

# あなたへの指示
上記の情報に基づき、このコード変更を承認するかを判断してください。

# 出力要件
必ず decision (APPROVEまたはREJECT) と reason (判断理由) を含むJSON形式で出力してください。
REJECTする場合、feedback_for_coder キーに具体的な修正指示を含めてください。
"""
        review_result_json = self.execute_llm_task(prompt, as_json=True)
        try:
            review_data = json.loads(review_result_json)
        except json.JSONDecodeError:
            print("❌ GuardianAgentのレビュー出力が不正なJSONでした。")
            return {"decision": "REJECT", "reason": "Invalid JSON response from Guardian."}

        review_data.setdefault("decision", "REJECT")
        review_data.setdefault("reason", "理由不明。")
        if review_data["decision"] == "REJECT":
            review_data.setdefault("feedback_for_coder", review_data["reason"])
        return review_data

    def review_and_commit(
        self,
        code_draft: str,
        test_code: str,
        test_result: str,
        testimony: str,
        constitution: str,
        task_description: str,
        changed_files: List[str],
        debug_info: Optional[Dict[str, Any]] = None,
        *,
        allow_commit: bool = True,
        branch_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        レビューし、APPROVE かつ allow_commit=True の場合のみコミットする。
        """
        review_data = self.review(
            code_draft=code_draft,
            test_code=test_code,
            test_result=test_result,
            testimony=testimony,
            constitution=constitution,
            task_description=task_description
        )
        decision = review_data.get("decision", "REJECTT")
        if decision != "APPROVE":
            return review_data

        if not allow_commit:
            review_data["commit"] = "Commit blocked by autonomy policy (review-only)."
            return review_data

        if not self.vcs:
            review_data["commit"] = "Git repository not available."
            return review_data

        try:
            if branch_name:
                self._prepare_branch(branch_name)
        except Exception as e:
            review_data["commit"] = f"Failed to prepare branch '{branch_name}': {e}"
            return review_data

        commit_message = self._generate_commit_message(review_data, changed_files, debug_info)
        commit_hash = self.vcs.commit_changes(changed_files, commit_message)
        review_data["commit"] = commit_hash or "Commit failed or no changes detected."
        return review_data

    def _prepare_branch(self, branch_name: str) -> None:
        """
        GitPython を使って <branch_name> に -B 相当で移動。
        """
        try:
            repo = git.Repo(os.getcwd())
        except Exception as e:
            raise RuntimeError(f"Git repo not found: {e}")
        repo.git.checkout("-B", branch_name)

    def _generate_commit_message(self, review_data: dict, changed_files: list, debug_info: dict = None) -> str:
        scope = "auto"
        body = f"Reviewed by: GuardianAgent (Model: {self.model})\n"
        body += f"Reason for approval: {review_data.get('reason', 'N/A')}\n"

        if debug_info:
            commit_type = "fix"
            header = f"{commit_type}({scope}): Self-healed by DebuggerAgent"
            body += f"\n[DEBUGGER ACTIVITY]\n"
            body += f"Error Signature: {debug_info.get('error_signature', 'N/A')}\n"
            solution_type = debug_info.get('solution_pattern', {}).get('type', 'N/A')
            body += f"Applied Solution Type: {solution_type}\n"
        else:
            commit_type = "feat"
            header = f"{commit_type}({scope}): Implemented new functionality via CoderAgent"

        return f"{header}\n\n{body}"
