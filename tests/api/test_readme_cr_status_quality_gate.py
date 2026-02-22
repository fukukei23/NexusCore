"""
README CR ステータス品質ゲート（状態機械・整合性検証）

docs/api/README.md の CR エントリに対して、ステータスの正当性を機械的に検証する。
"""

from pathlib import Path

import pytest

from tests.api._readme_cr_helpers import extract_cr_blocks, extract_cr_reason, extract_cr_status

# プロジェクトルートのパス
PROJECT_ROOT = Path(__file__).parent.parent.parent
README_PATH = PROJECT_ROOT / "docs" / "api" / "README.md"
DOCS_API_DIR = PROJECT_ROOT / "docs" / "api"

from nexuscore.governance.cr_spec import ALLOWED_STATUSES, STATUS_RULES

# 許容されるステータスの集合（cr_spec から取得）
ALLOWED_STATUSES_SET = set(ALLOWED_STATUSES)


def test_readme_all_crs_have_status():
    """
    Rule A: すべての CR ブロックにステータスが必ず存在することを検証
    """
    assert README_PATH.exists(), f"README file not found: {README_PATH}"
    readme_content = README_PATH.read_text(encoding="utf-8")

    blocks = extract_cr_blocks(readme_content)
    assert blocks, "No CR blocks found in README"

    failures = []
    for block in blocks:
        cr_id = block["cr_id"]
        status = extract_cr_status(block["block_text"])

        if status is None:
            failures.append({"cr_id": cr_id, "reason": "ステータスが記載されていない"})

    assert not failures, (
        f"CR blocks missing status:\n"
        + "\n".join(f"  - CR-ID: {f['cr_id']}\n    Reason: {f['reason']}" for f in failures)
    )


def test_readme_cr_statuses_are_valid():
    """
    すべての CR ステータスが許容値の集合に含まれることを検証
    """
    assert README_PATH.exists(), f"README file not found: {README_PATH}"
    readme_content = README_PATH.read_text(encoding="utf-8")

    blocks = extract_cr_blocks(readme_content)
    assert blocks, "No CR blocks found in README"

    failures = []
    for block in blocks:
        cr_id = block["cr_id"]
        status = extract_cr_status(block["block_text"])

        if status is None:
            continue  # ステータス未記載は test_readme_all_crs_have_status で検出

        if status not in ALLOWED_STATUSES_SET:
            failures.append(
                {
                    "cr_id": cr_id,
                    "status": status,
                    "reason": f"許容されていないステータス: {status}",
                }
            )

    assert not failures, (
        f"CR blocks with invalid status:\n"
        + "\n".join(
            f"  - CR-ID: {f['cr_id']}\n    Status: {f['status']}\n    Reason: {f['reason']}"
            for f in failures
        )
        + f"\n\n許容されるステータス: {', '.join(ALLOWED_STATUSES)}"
    )


def test_completed_crs_have_completion_reports():
    """
    Rule B: ✅ 完了の CR は Completion Report が存在することを検証
    """
    assert README_PATH.exists(), f"README file not found: {README_PATH}"
    readme_content = README_PATH.read_text(encoding="utf-8")

    blocks = extract_cr_blocks(readme_content)
    assert blocks, "No CR blocks found in README"

    failures = []
    for block in blocks:
        cr_id = block["cr_id"]
        status = extract_cr_status(block["block_text"])

        # cr_spec の STATUS_RULES に基づいて Completion Report 必須をチェック
        status_rule = STATUS_RULES.get(status, {})
        if status_rule.get("completion_report_required", False):
            filename = f"{cr_id}_COMPLETION_REPORT.md"
            file_path = DOCS_API_DIR / filename
            if not file_path.exists():
                failures.append(
                    {
                        "cr_id": cr_id,
                        "file_path": file_path,
                        "reason": "Completion Report が存在しない",
                    }
                )

    assert not failures, (
        f"Completed CRs missing completion reports:\n"
        + "\n".join(
            f"  - CR-ID: {f['cr_id']}\n    Expected file: {f['file_path']}\n    Reason: {f['reason']}"
            for f in failures
        )
    )


def test_paused_or_aborted_crs_have_reason():
    """
    Rule C & D: ⏸ 保留 または ❌ 中断 の CR は理由が必須であることを検証
    """
    assert README_PATH.exists(), f"README file not found: {README_PATH}"
    readme_content = README_PATH.read_text(encoding="utf-8")

    blocks = extract_cr_blocks(readme_content)
    assert blocks, "No CR blocks found in README"

    failures = []
    for block in blocks:
        cr_id = block["cr_id"]
        status = extract_cr_status(block["block_text"])

        # cr_spec の STATUS_RULES に基づいて理由必須をチェック
        status_rule = STATUS_RULES.get(status, {})
        if status_rule.get("reason_required", False):
            reason = extract_cr_reason(block["block_text"])
            if reason is None:
                failures.append(
                    {
                        "cr_id": cr_id,
                        "status": status,
                        "reason": f"ステータスが {status} だが理由が記載されていない",
                    }
                )

    assert not failures, (
        f"Paused or aborted CRs missing reason:\n"
        + "\n".join(
            f"  - CR-ID: {f['cr_id']}\n    Status: {f['status']}\n    Reason: {f['reason']}"
            for f in failures
        )
        + "\n\n保留/中断の CR には必ず理由を記載してください（- **理由**: ...）"
    )

