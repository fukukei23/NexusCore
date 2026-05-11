"""
Enhanced review execution logic for GuardianAgent.

Handles the quality-gates-passed LLM review flow — building the prompt,
calling the LLM, and parsing the JSON response.
"""

from __future__ import annotations

import json
from typing import Any, Callable


def execute_quality_gated_review(
    execute_llm_fn: Callable[..., str],
    *,
    code_draft: str,
    test_code: str,
    test_result: str,
    testimony: str,
    constitution_dict: dict[str, Any],
    task_description: str,
    quality_gates_result: dict[str, Any],
    quality_summary: str,
) -> dict[str, Any]:
    """Run an LLM review after quality gates have passed.

    Args:
        execute_llm_fn: ``execute_llm_task`` bound method or equivalent.
        quality_gates_result: Result from ``run_quality_gates``.
        quality_summary: Human-readable summary of the gates result.

    Returns:
        Review result dictionary with keys: decision, reason,
        feedback_for_coder (if REJECT), quality_gates.
    """
    constitution_str = json.dumps(constitution_dict, indent=2, ensure_ascii=False)

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
