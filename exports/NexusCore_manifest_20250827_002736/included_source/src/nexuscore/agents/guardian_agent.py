# ==============================================================================
# ファイル: src/nexuscore/agents/guardian_agent.py
# 目的  : コードの品質/セキュリティ/憲法準拠をレビューし、許可時のみコミット
# 変更点:
#   - Step2: 予算フック on_budget_tick（LLM直前に1行呼ぶ）
#   - Step3: allow_commit (bool) 追加、review-only を実現
#   - Step4: branch_name 追加（feature ブランチでのコミット＝L2対応）
# 後方互換:
#   - 既存の review_and_commit(...) 呼び出しは allow_commit=True 既定で従来どおり
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

    # ガバナンストーン（システムプロンプト）
    SYSTEM_PROMPT = """
あなたはCTO（最高技術責任者）です。
開発チームから提出されたコード、テスト結果、その他の情報を総合的にレビューし、
その変更を承認（APPROVE）するか、修正のために差し戻す（REJECT）かを判断してください。
判断は、プロジェクトの憲法と、提示された技術的証拠に厳密に基づいてください。
"""

    # Orchestrator から注入可能な予算フック（未設定なら何もしない）
    on_budget_tick: Optional[Callable[[str], None]] = None

    def __init__(self, api_key: str, model: str):
        super().__init__(api_key, model)
        try:
            self.vcs = GitController()
        except git.InvalidGitRepositoryError:
            self.vcs = None
            print("⚠️ GuardianAgent: Gitリポジトリが見つからないため、コミット機能は無効です。")

    # -------- 内部: 予算フック呼び出し（安全に無視） -------- #
    def _budget(self, step: str) -> None:
        try:
            if callable(self.on_budget_tick):
                self.on_budget_tick(step)
        except Exception:
            # 予算フックは安全側で握りつぶす
            pass

    # -------- レビューのみ -------- #
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
        self._budget("guardian:review")  # Step2: 予算カウント

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
        # LLM 呼び出し
        review_result_json = self._call_llm(prompt, self.SYSTEM_PROMPT, as_json=True)
        try:
            review_data = json.loads(review_result_json)
        except json.JSONDecodeError:
            print("❌ GuardianAgentのレビュー出力が不正なJSONでした。")
            return {"decision": "REJECT", "reason": "Invalid JSON response from Guardian."}

        # フィールド整形
        review_data.setdefault("decision", "REJECT")
        review_data.setdefault("reason", "理由不明。")
        if review_data["decision"] == "REJECT":
            review_data.setdefault("feedback_for_coder", review_data["reason"])
        return review_data

    # -------- レビュー＋（許可時のみ）コミット -------- #
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
        branch_name が与えられた場合は、そのブランチでコミット（L2: PR前提運用）。
        """
        # まずレビュー
        review_data = self.review(
            code_draft=code_draft,
            test_code=test_code,
            test_result=test_result,
            testimony=testimony,
            constitution=constitution,
            task_description=task_description
        )
        decision = review_data.get("decision", "REJECT")
        if decision != "APPROVE":
            return review_data  # 差し戻し

        # コミット抑止（Step3）
        if not allow_commit:
            review_data["commit"] = "Commit blocked by autonomy policy (review-only)."
            return review_data

        # Git 不可（フォールバック）
        if not self.vcs:
            review_data["commit"] = "Git repository not available."
            return review_data

        # L2: feature ブランチでのコミット（Step4）
        try:
            if branch_name:
                self._prepare_branch(branch_name)
        except Exception as e:
            review_data["commit"] = f"Failed to prepare branch '{branch_name}': {e}"
            return review_data

        # コミット実行
        commit_message = self._generate_commit_message(review_data, changed_files, debug_info)
        commit_hash = self.vcs.commit_changes(changed_files, commit_message)
        review_data["commit"] = commit_hash or "Commit failed or no changes detected."
        return review_data

    # -------- ブランチ準備（-B で作成/更新してチェックアウト） -------- #
    def _prepare_branch(self, branch_name: str) -> None:
        """
        GitPython を使って <branch_name> に -B 相当で移動。
        vcs がブランチ操作を提供していない場合の保険。
        """
        try:
            repo = git.Repo(os.getcwd())
        except Exception as e:
            raise RuntimeError(f"Git repo not found: {e}")
        # 現在の HEAD から強制的にブランチを作り直して移動
        repo.git.checkout("-B", branch_name)

    # -------- Conventional Commits 風コミットメッセージ -------- #
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
