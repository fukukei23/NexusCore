"""
Quality gate execution and code review helpers for GuardianAgent.
"""

from __future__ import annotations

import json
from typing import Any

from nexuscore.config.constitution_loader import get_constitution
from nexuscore.utils.code_analyzer import QualityReport, analyze_code_quality

from ..mutation_tester_agent import MutationReport, MutationTesterAgent

try:
    from nexuscore.guard.guardian_auto_reviewer import (
        GuardianAutoReviewer,
        ReviewDecision,
        ReviewResult,
    )
except ImportError:
    GuardianAutoReviewer = None  # type: ignore[assignment,misc]
    ReviewDecision = None  # type: ignore[assignment,misc]
    ReviewResult = None  # type: ignore[assignment,misc]


def run_quality_gates(
    source_path: str,
    test_path: str,
    project_root: str | None = None,
    constitution: dict[str, Any] | None = None,
    logger: Any = None,
) -> dict[str, Any]:
    if constitution is None:
        constitution = get_constitution()

    violations: list[str] = []

    try:
        tier1_report: QualityReport = analyze_code_quality(
            source_path=source_path,
            test_path=test_path,
            constitution=constitution,
            project_root=project_root or "",
        )
    except Exception as e:
        if logger:
            logger.error(f"Tier 1 quality gate failed: {e}", exc_info=True)
        tier1_report = None  # type: ignore[assignment]
        violations.append(f"Tier 1実行エラー: {e}")

    try:
        mutation_agent = MutationTesterAgent()
        tier2_report: MutationReport = mutation_agent.run_mutation_testing(
            source_path=source_path,
            test_path=test_path,
            constitution=constitution,
            timeout_per_test=10,
        )
    except Exception as e:
        if logger:
            logger.error(f"Tier 2 quality gate failed: {e}", exc_info=True)
        tier2_report = None  # type: ignore[assignment]
        violations.append(f"Tier 2実行エラー: {e}")

    overall_passed = True
    if tier1_report and not tier1_report.passed:
        overall_passed = False
        violations.extend(tier1_report.violations)
    if tier2_report and not tier2_report.passed:
        overall_passed = False
        violations.append(
            f"Tier 2不合格: ミューテーションスコア {tier2_report.mutation_score:.1f}% "
            f"(最低基準: {constitution.get('quality_gates', {}).get('tier2', {}).get('mutation_score_min', 80)}%)"
        )

    return {
        "tier1": tier1_report,
        "tier2": tier2_report,
        "overall_passed": overall_passed,
        "violations": violations,
    }


def format_quality_gates_summary(quality_gates_result: dict[str, Any]) -> str:
    summary = "✅ 全ての品質ゲートに合格しました。\n\n"

    tier1 = quality_gates_result.get("tier1")
    if tier1:
        summary += "**Tier 1: コード品質**\n"
        summary += f"- カバレッジ: {tier1.coverage_percentage:.1f}% {'✅' if tier1.coverage_passed else '❌'}\n"
        summary += f"- Pylint: {tier1.pylint_score:.1f}/10 {'✅' if tier1.pylint_passed else '❌'}\n"
        summary += f"- MyPy: {'✅' if tier1.mypy_passed else '❌'}\n"
        summary += f"- Bandit: {'✅' if tier1.bandit_passed else '❌'}\n"
        if tier1.security_issues:
            summary += f"  - セキュリティ問題: {len(tier1.security_issues)}件\n"

    tier2 = quality_gates_result.get("tier2")
    if tier2:
        summary += "\n**Tier 2: テスト品質**\n"
        summary += f"- ミューテーションスコア: {tier2.mutation_score:.1f}% {'✅' if tier2.passed else '❌'}\n"
        summary += f"- 検出率: {tier2.killed}/{tier2.total_mutants} mutants killed\n"
        if tier2.survived_mutants:
            summary += f"  - 生き残ったmutant: {len(tier2.survived_mutants)}個\n"

    return summary


def review_code(
    execute_llm_fn: Any,
    code_draft: str,
    test_code: str,
    test_result: str,
    testimony: str,
    constitution: str,
    task_description: str,
) -> dict[str, Any]:
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
    review_result_json = execute_llm_fn(prompt, as_json=True)
    try:
        review_data = json.loads(review_result_json)
    except json.JSONDecodeError:
        return {"decision": "REJECT", "reason": "Invalid JSON response from Guardian."}

    review_data.setdefault("decision", "REJECT")
    review_data.setdefault("reason", "理由不明。")
    if review_data["decision"] == "REJECT":
        review_data.setdefault("feedback_for_coder", review_data["reason"])
    return review_data


def review_with_quality_gates(
    execute_llm_fn: Any,
    source_path: str,
    test_path: str,
    code_draft: str,
    test_code: str,
    test_result: str,
    testimony: str,
    constitution_dict: dict[str, Any],
    task_description: str,
    project_root: str | None = None,
    logger: Any = None,
) -> dict[str, Any]:
    quality_gates_result = run_quality_gates(
        source_path, test_path, project_root, constitution_dict, logger=logger,
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

    constitution_str = json.dumps(constitution_dict, indent=2, ensure_ascii=False)
    quality_summary = format_quality_gates_summary(quality_gates_result)

    prompt = f"""
# レビュー対象の情報
- **プロジェクト憲法**: {constitution_str}
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

# 品質ゲート結果
{quality_summary}

# あなたへの指示
上記の情報に基づき、このコード変更を承認するかを判断してください。
品質ゲートは**既に合格**しています。あなたは技術的判断（設計、可読性、保守性など）に集中してください。

# 出力要件
必ず decision (APPROVEまたはREJECT) と reason (判断理由) を含むJSON形式で出力してください。
REJECTする場合、feedback_for_coder キーに具体的な修正指示を含めてください。
"""
    review_result_json = execute_llm_fn(prompt, as_json=True)
    try:
        review_data = json.loads(review_result_json)
    except json.JSONDecodeError:
        return {
            "decision": "REJECT",
            "reason": "Invalid JSON response from Guardian.",
            "quality_gates": quality_gates_result,
        }

    review_data.setdefault("decision", "REJECT")
    review_data.setdefault("reason", "理由不明。")
    if review_data["decision"] == "REJECT":
        review_data.setdefault("feedback_for_coder", review_data["reason"])

    review_data["quality_gates"] = quality_gates_result
    return review_data


def summarize_diff_for_llm(diff_text: str) -> str:
    lines = diff_text.splitlines()
    file_count = sum(1 for line in lines if line.startswith("+++"))
    hunk_count = sum(1 for line in lines if line.startswith("@@"))

    preview_lines = lines[:50]
    if len(lines) > 50:
        preview_lines.append(f"... (残り {len(lines) - 50} 行)")

    return f"""
変更ファイル数: {file_count}
変更ブロック数: {hunk_count}

Diff プレビュー:
{chr(10).join(preview_lines)}
"""


def review_with_llm(
    execute_llm_fn: Any,
    diff_summary: str,
    auto_review: dict[str, Any] | None = None,
    logger: Any = None,
) -> dict[str, Any]:
    auto_review_text = ""
    if auto_review:
        auto_review_text = f"""
自動レビュー結果:
- 決定: {auto_review.get('decision', 'N/A')}
- 問題数: {auto_review.get('issue_count', 0)}
- 要約:
{auto_review.get('summary', 'N/A')}
"""

    prompt = f"""
以下のコード変更をレビューしてください。

{diff_summary}

{auto_review_text}

# 出力要件
必ず decision (APPROVE / REJECT / MANUAL_REVIEW) と reason (判断理由) を含むJSON形式で出力してください。
"""

    try:
        review_result_json = execute_llm_fn(prompt, as_json=True)
        review_data = json.loads(review_result_json)
        review_data.setdefault("decision", "APPROVE")
        review_data.setdefault("reason", "理由なし")
        return review_data
    except Exception as e:
        if logger:
            logger.error(f"LLM review failed: {e}", exc_info=True)
        return {"decision": "MANUAL_REVIEW", "reason": f"LLM レビューエラー: {e}"}


def review_unified_diff(
    execute_llm_fn: Any,
    diff_text: str,
    project_name: str = "nexuscore",
    logger: Any = None,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "decision": "APPROVE",
        "reason": "",
        "auto_review": None,
    }

    if GuardianAutoReviewer is not None:
        try:
            reviewer = GuardianAutoReviewer(project_name=project_name)
            auto_result: ReviewResult = reviewer.review_unified_diff(diff_text)

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
            if logger:
                logger.warning(f"GuardianAutoReviewer failed: {e}")

    if result["decision"] != "REJECT":
        diff_summary = summarize_diff_for_llm(diff_text)
        llm_review = review_with_llm(
            execute_llm_fn, diff_summary, result.get("auto_review"), logger=logger,
        )

        llm_decision = llm_review.get("decision", "APPROVE")
        if llm_decision == "REJECT":
            result["decision"] = "REJECT"
            result["reason"] = llm_review.get("reason", "LLM レビューで拒否されました")
        elif result["decision"] == "MANUAL_REVIEW" or llm_decision == "MANUAL_REVIEW":
            result["decision"] = "MANUAL_REVIEW"
            if not result["reason"]:
                result["reason"] = llm_review.get("reason", "人間レビューが必要です")

    return result
