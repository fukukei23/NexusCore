from __future__ import annotations

import json
import os
from collections.abc import Callable
from typing import Any

import git

from .base_agent import BaseAgent
from ._guardian_helpers.commit_workflow import execute_commit_workflow
from ._guardian_helpers.diff_summary import generate_diff_summary
from ._guardian_helpers.git_operations import generate_commit_message, prepare_branch
from ._guardian_helpers.quality_gates import (
    format_quality_gates_summary,
    review_code as _review_code_standalone,
    run_quality_gates,
    review_with_llm,
    summarize_diff_for_llm,
)
from ._guardian_helpers.review_executor import execute_quality_gated_review
from nexuscore.config.constitution_loader import get_constitution
from nexuscore.utils.vcs import GitController

try:
    from nexuscore.guard.guardian_auto_reviewer import GuardianAutoReviewer, ReviewDecision, ReviewResult
except ImportError:
    GuardianAutoReviewer = None
    ReviewDecision = None
    ReviewResult = None


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
    on_budget_tick: Callable[[str], None] | None = None

    def __init__(self, api_key: str | None = None, model: str | None = None):
        super().__init__()
        self.model = model or ""
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY", "")
        try:
            self.vcs = GitController()
        except git.InvalidGitRepositoryError:
            self.vcs = None
            self.logger.warning("GuardianAgent: Gitリポジトリが見つからないため、コミット機能は無効です。")

    def _budget(self, step: str) -> None:
        try:
            if callable(self.on_budget_tick):
                self.on_budget_tick(step)
        except Exception:
            pass

    def _run_quality_gates(
        self,
        source_path: str,
        test_path: str,
        project_root: str | None = None,
        constitution: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        self._budget("guardian:quality_gates")
        return run_quality_gates(
            source_path, test_path, project_root, constitution, logger=self.logger,
        )

    def review(
        self,
        code_draft: str,
        test_code: str,
        test_result: str,
        testimony: str,
        constitution: str,
        task_description: str,
    ) -> dict[str, Any]:
        self._budget("guardian:review")
        return _review_code_standalone(
            execute_llm_fn=self.execute_llm_task,
            code_draft=code_draft,
            test_code=test_code,
            test_result=test_result,
            testimony=testimony,
            constitution=constitution,
            task_description=task_description,
        )

    def review_with_quality_gates(
        self,
        source_path: str,
        test_path: str,
        code_draft: str,
        test_code: str,
        test_result: str,
        testimony: str,
        constitution_dict: dict[str, Any],
        task_description: str,
        project_root: str | None = None,
    ) -> dict[str, Any]:
        self._budget("guardian:review_with_quality_gates")

        quality_gates_result = self._run_quality_gates(
            source_path=source_path,
            test_path=test_path,
            project_root=project_root,
            constitution=constitution_dict,
        )

        if not quality_gates_result["overall_passed"]:
            feedback = "品質ゲートで以下の違反が検出されました:\n"
            for violation in quality_gates_result["violations"]:
                feedback += f"- {violation}\n"

            if quality_gates_result["tier1"] and quality_gates_result["tier1"].feedback:
                feedback += f"\n【Tier 1フィードバック】\n{quality_gates_result['tier1'].feedback}\n"
            if quality_gates_result["tier2"] and quality_gates_result["tier2"].feedback:
                feedback += f"\n【Tier 2フィードバック】\n{quality_gates_result['tier2'].feedback}\n"

            return {
                "decision": "REJECT",
                "reason": "品質ゲート不合格",
                "feedback_for_coder": feedback,
                "quality_gates": quality_gates_result,
            }

        quality_summary = self._format_quality_gates_summary(quality_gates_result)

        return execute_quality_gated_review(
            self.execute_llm_task,
            code_draft=code_draft,
            test_code=test_code,
            test_result=test_result,
            testimony=testimony,
            constitution_dict=constitution_dict,
            task_description=task_description,
            quality_gates_result=quality_gates_result,
            quality_summary=quality_summary,
        )

    def review_and_commit(
        self,
        code_draft: str,
        test_code: str,
        test_result: str,
        testimony: str,
        constitution: str,
        task_description: str,
        changed_files: list[str],
        debug_info: dict[str, Any] | None = None,
        *,
        allow_commit: bool = True,
        branch_name: str | None = None,
        enable_quality_gates: bool = False,
        source_path: str | None = None,
        test_path: str | None = None,
        project_root: str | None = None,
    ) -> dict[str, Any]:
        # --- 1. Review ---
        if enable_quality_gates:
            if not source_path or not test_path:
                return {
                    "decision": "REJECT",
                    "reason": "品質ゲート有効時は source_path と test_path が必須です",
                    "feedback_for_coder": "source_path と test_path を指定してください",
                }

            try:
                constitution_dict = (
                    json.loads(constitution) if isinstance(constitution, str) else constitution
                )
            except json.JSONDecodeError:
                constitution_dict = get_constitution()

            review_data = self.review_with_quality_gates(
                source_path=source_path,
                test_path=test_path,
                code_draft=code_draft,
                test_code=test_code,
                test_result=test_result,
                testimony=testimony,
                constitution_dict=constitution_dict,
                task_description=task_description,
                project_root=project_root,
            )
        else:
            review_data = self.review(
                code_draft=code_draft,
                test_code=test_code,
                test_result=test_result,
                testimony=testimony,
                constitution=constitution,
                task_description=task_description,
            )

        # --- 2. Gate: reject / review-only ---
        if review_data.get("decision") != "APPROVE":
            return review_data

        if not allow_commit:
            review_data["commit"] = "Commit blocked by autonomy policy (review-only)."
            return review_data

        # --- 3. Commit ---
        return execute_commit_workflow(
            review_data,
            changed_files=changed_files,
            vcs=self.vcs,
            model=self.model,
            debug_info=debug_info,
            branch_name=branch_name,
        )

    def review_unified_diff(
        self,
        diff_text: str,
        project_name: str = "nexuscore",
    ) -> dict[str, Any]:
        self._budget("guardian:review_diff")

        result: dict[str, Any] = {
            "decision": "APPROVE",
            "reason": "",
            "auto_review": None,
        }

        if GuardianAutoReviewer is not None:
            try:
                reviewer = GuardianAutoReviewer(project_name=project_name)
                auto_result = reviewer.review_unified_diff(diff_text)

                result["auto_review"] = {
                    "decision": auto_result.decision.value,
                    "summary": auto_result.summary(),
                    "has_errors": auto_result.has_errors,
                    "has_warnings": auto_result.has_warnings,
                    "issue_count": len(auto_result.issues),
                }

                if auto_result.decision == ReviewDecision.REJECT:
                    result["decision"] = "REJECT"
                    result["reason"] = f"自動レビューで拒否されました:\n{auto_result.summary()}"
                    return result

                if auto_result.decision == ReviewDecision.MANUAL_REVIEW:
                    result["decision"] = "MANUAL_REVIEW"
                    result["reason"] = f"自動レビューで警告が検出されました:\n{auto_result.summary()}"

            except Exception as e:
                result["auto_review"] = {"error": str(e)}
                self.logger.warning(f"GuardianAutoReviewer failed: {e}")

        if result["decision"] != "REJECT":
            diff_summary = self._summarize_diff_for_llm(diff_text)
            llm_review = self._review_with_llm(diff_summary, result.get("auto_review"))

            llm_decision = llm_review.get("decision", "APPROVE")
            if llm_decision == "REJECT":
                result["decision"] = "REJECT"
                result["reason"] = llm_review.get("reason", "LLM レビューで拒否されました")
            elif result["decision"] == "MANUAL_REVIEW" or llm_decision == "MANUAL_REVIEW":
                result["decision"] = "MANUAL_REVIEW"
                if not result["reason"]:
                    result["reason"] = llm_review.get("reason", "人間レビューが必要です")

        return result

    def generate_diff_summary(
        self,
        before_code: str | None = None,
        after_code: str | None = None,
        file_diffs: dict[str, dict[str, str]] | None = None,
        semantic_diffs: dict[str, dict[str, Any]] | None = None,
        model: str = "gpt-4.1",
    ) -> str | dict[str, str]:
        self._budget("guardian:diff_summary")
        return generate_diff_summary(
            execute_llm_fn=self.execute_llm_task,
            before_code=before_code,
            after_code=after_code,
            file_diffs=file_diffs,
            semantic_diffs=semantic_diffs,
            model=model,
            logger=self.logger,
        )

    # -- Backward-compatible wrappers for tests --

    def _format_quality_gates_summary(self, quality_gates_result: dict[str, Any]) -> str:
        return format_quality_gates_summary(quality_gates_result)

    def _summarize_diff_for_llm(self, diff_text: str) -> str:
        return summarize_diff_for_llm(diff_text)

    def _review_with_llm(
        self,
        diff_summary: str,
        auto_review: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return review_with_llm(
            self.execute_llm_task, diff_summary, auto_review, logger=self.logger,
        )

    def _generate_commit_message(
        self, review_data: dict, changed_files: list, debug_info: dict | None = None,
    ) -> str:
        return generate_commit_message(review_data, changed_files, self.model, debug_info)

    def _prepare_branch(self, branch_name: str) -> None:
        prepare_branch(branch_name)
