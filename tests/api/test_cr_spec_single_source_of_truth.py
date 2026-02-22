"""
CR ガバナンス定義の Single Source of Truth（SSoT）検証

定義が再び分散した場合に検知するためのテスト。
"""

from pathlib import Path

from nexuscore.governance.cr_spec import (
    ALLOWED_STATUSES,
    COMPLETION_REPORT_SECTIONS,
    README_CR_REQUIRED_FIELDS,
    STATUS_RULES,
)
from tests.api._completion_report_helpers import extract_section_content
from tests.api._readme_cr_helpers import extract_cr_field


def test_completion_report_sections_are_defined_in_cr_spec():
    """
    Completion Report 必須セクションが cr_spec に定義されていることを確認
    （品質ゲートテストが cr_spec を使用していることを間接的に検証）
    """
    # cr_spec に必須セクションが定義されていることを確認
    required_sections = [section.name for section in COMPLETION_REPORT_SECTIONS if section.required]
    assert required_sections, "必須セクションが cr_spec に定義されていません"

    # 必須セクションのリストが空でないことを確認
    assert len(required_sections) >= 3, "必須セクションが少なすぎます（最低3つ以上）"


def test_readme_required_fields_are_defined_in_cr_spec():
    """
    README CR エントリ必須フィールドが cr_spec に定義されていることを確認
    （品質ゲートテストが cr_spec を使用していることを間接的に検証）
    """
    # cr_spec に必須フィールドが定義されていることを確認
    assert README_CR_REQUIRED_FIELDS, "必須フィールドが cr_spec に定義されていません"

    # 必須フィールドのリストに最低限のフィールドが含まれていることを確認
    assert (
        "目的" in README_CR_REQUIRED_FIELDS
    ), "必須フィールド '目的' が cr_spec に定義されていません"
    assert (
        "出力" in README_CR_REQUIRED_FIELDS
    ), "必須フィールド '出力' が cr_spec に定義されていません"


def test_status_rules_are_defined_in_cr_spec():
    """
    CR ステータスルールが cr_spec に定義されていることを確認
    """
    # cr_spec にステータスルールが定義されていることを確認
    assert STATUS_RULES, "ステータスルールが cr_spec に定義されていません"

    # 重要なステータスのルールが定義されていることを確認
    assert "✅ 完了" in STATUS_RULES, "ステータス '✅ 完了' のルールが cr_spec に定義されていません"
    assert "⏸ 保留" in STATUS_RULES, "ステータス '⏸ 保留' のルールが cr_spec に定義されていません"
    assert "❌ 中断" in STATUS_RULES, "ステータス '❌ 中断' のルールが cr_spec に定義されていません"

    # 「✅ 完了」は Completion Report 必須
    assert STATUS_RULES["✅ 完了"][
        "completion_report_required"
    ], "ステータス '✅ 完了' は Completion Report 必須である必要があります"

    # 「⏸ 保留」「❌ 中断」は理由必須
    assert STATUS_RULES["⏸ 保留"][
        "reason_required"
    ], "ステータス '⏸ 保留' は理由必須である必要があります"
    assert STATUS_RULES["❌ 中断"][
        "reason_required"
    ], "ステータス '❌ 中断' は理由必須である必要があります"


def test_allowed_statuses_are_defined_in_cr_spec():
    """
    許容ステータスが cr_spec に定義されていることを確認
    """
    # cr_spec に許容ステータスが定義されていることを確認
    assert ALLOWED_STATUSES, "許容ステータスが cr_spec に定義されていません"

    # 重要なステータスが含まれていることを確認
    assert "✅ 完了" in ALLOWED_STATUSES, "ステータス '✅ 完了' が許容ステータスに含まれていません"
    assert (
        "⏳ 進行中" in ALLOWED_STATUSES
    ), "ステータス '⏳ 進行中' が許容ステータスに含まれていません"


def test_scaffold_generated_completion_report_uses_cr_spec_sections(tmp_path):
    """
    scaffold が生成する Completion Report に cr_spec で定義された必須セクションがすべて含まれることを確認
    """
    # scaffold の generate_completion_report を import（tools/scaffold_cr.py から）
    import sys

    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    from tools.scaffold_cr import generate_completion_report

    # Completion Report を生成
    cr_id = "CR-NEXUS-999"
    title = "Test CR"
    report_content = generate_completion_report(cr_id, title)

    # cr_spec で定義された必須セクションがすべて含まれていることを確認
    required_sections = [section.name for section in COMPLETION_REPORT_SECTIONS if section.required]
    for section_name in required_sections:
        section_content = extract_section_content(report_content, section_name)
        assert section_content is not None, (
            f"scaffold が生成した Completion Report に必須セクション '{section_name}' が含まれていません。"
            f"cr_spec の定義と一致していない可能性があります。"
        )


def test_scaffold_generated_readme_entry_uses_cr_spec_fields(tmp_path):
    """
    scaffold が生成する README エントリに cr_spec で定義された必須フィールドがすべて含まれることを確認
    """
    # scaffold の generate_readme_entry を import（tools/scaffold_cr.py から）
    import sys

    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    from tools.scaffold_cr import generate_readme_entry

    # README エントリを生成
    cr_id = "CR-NEXUS-999"
    title = "Test CR"
    readme_entry = generate_readme_entry(cr_id, title)

    # cr_spec で定義された必須フィールドがすべて含まれていることを確認
    # 注: "完了レポート" はステータスに応じて含まれる/含まれないため、ここでは主要フィールドのみチェック
    core_fields = ["ファイル", "目的", "出力", "ステータス"]
    for field_name in core_fields:
        if field_name not in README_CR_REQUIRED_FIELDS:
            continue  # cr_spec に定義されていない場合はスキップ
        field_value = extract_cr_field(readme_entry, field_name)
        assert field_value is not None, (
            f"scaffold が生成した README エントリに必須フィールド '{field_name}' が含まれていません。"
            f"cr_spec の定義と一致していない可能性があります。"
        )
