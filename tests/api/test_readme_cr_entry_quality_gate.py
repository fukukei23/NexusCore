"""
README CR エントリ品質ゲート（項目欠落・フォーマットぶれ検証）

docs/api/README.md の CR エントリに対して、必須項目が存在し、かつ実質的に空でないことを検証する。
"""

from pathlib import Path

import pytest

from tests.api._readme_cr_helpers import (
    extract_cr_blocks,
    extract_cr_field,
    extract_cr_status,
    is_effectively_empty,
)

# プロジェクトルートのパス
PROJECT_ROOT = Path(__file__).parent.parent.parent
README_PATH = PROJECT_ROOT / "docs" / "api" / "README.md"

from nexuscore.governance.cr_spec import README_CR_REQUIRED_FIELDS

# 全 CR ブロックで必須のフィールド（cr_spec から取得）
# 注: "ファイル" と "ステータス" は test_readme_cr_status_quality_gate で検証されるため、
# ここでは "目的" と "出力" のみをチェック（046 の要件に合わせる）
REQUIRED_FIELDS = [field for field in README_CR_REQUIRED_FIELDS if field in ("目的", "出力")]


def test_readme_cr_blocks_have_required_fields():
    """
    Rule E: すべての CR ブロックに 目的 と 出力 が存在し、かつ実質的に空でないことを検証
    """
    assert README_PATH.exists(), f"README file not found: {README_PATH}"
    readme_content = README_PATH.read_text(encoding="utf-8")

    blocks = extract_cr_blocks(readme_content)
    assert blocks, "No CR blocks found in README"

    failures = []
    for block in blocks:
        cr_id = block["cr_id"]
        block_text = block["block_text"]

        for field_name in REQUIRED_FIELDS:
            field_value = extract_cr_field(block_text, field_name)

            if field_value is None:
                failures.append(
                    {
                        "cr_id": cr_id,
                        "field": field_name,
                        "reason": f"フィールド '{field_name}' が存在しない",
                    }
                )
            elif is_effectively_empty(field_value):
                failures.append(
                    {
                        "cr_id": cr_id,
                        "field": field_name,
                        "reason": f"フィールド '{field_name}' が実質的に空（プレースホルダまたは空文字）",
                        "value": field_value[:50] if len(field_value) > 50 else field_value,
                    }
                )

    assert not failures, (
        f"CR blocks missing required fields or fields are empty:\n"
        + "\n".join(
            f"  - CR-ID: {f['cr_id']}\n"
            f"    Field: {f['field']}\n"
            f"    Reason: {f['reason']}"
            + (f"\n    Value: {f['value']}" if "value" in f else "")
            for f in failures
        )
    )


def test_completed_cr_blocks_have_completion_report_field():
    """
    Rule E: ステータス == "✅ 完了" の CR ブロックに 完了レポート が存在し、かつ実質的に空でないことを検証
    """
    assert README_PATH.exists(), f"README file not found: {README_PATH}"
    readme_content = README_PATH.read_text(encoding="utf-8")

    blocks = extract_cr_blocks(readme_content)
    assert blocks, "No CR blocks found in README"

    failures = []
    for block in blocks:
        cr_id = block["cr_id"]
        block_text = block["block_text"]

        status = extract_cr_status(block_text)
        if status == "✅ 完了":
            completion_report_value = extract_cr_field(block_text, "完了レポート")

            if completion_report_value is None:
                failures.append(
                    {
                        "cr_id": cr_id,
                        "reason": "ステータスが ✅ 完了 だが '完了レポート' フィールドが存在しない",
                    }
                )
            elif is_effectively_empty(completion_report_value):
                failures.append(
                    {
                        "cr_id": cr_id,
                        "reason": "ステータスが ✅ 完了 だが '完了レポート' フィールドが実質的に空（プレースホルダまたは空文字）",
                        "value": completion_report_value[:50]
                        if len(completion_report_value) > 50
                        else completion_report_value,
                    }
                )

    assert not failures, (
        f"Completed CR blocks missing completion report field:\n"
        + "\n".join(
            f"  - CR-ID: {f['cr_id']}\n    Reason: {f['reason']}"
            + (f"\n    Value: {f['value']}" if "value" in f else "")
            for f in failures
        )
    )

