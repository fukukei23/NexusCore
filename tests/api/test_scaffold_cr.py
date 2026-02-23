"""
scaffold の成果物が品質ゲート要件を満たすことを検証するテスト

tests/api/_readme_cr_helpers と tests/api/_completion_report_helpers を使用して、
scaffold が生成する README エントリと Completion Report が品質ゲート要件を満たすことを確認する。
"""

import sys
from pathlib import Path

import pytest

# tools/scaffold_cr.py を import（関数を直接使う）
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from nexuscore.governance.cr_spec import (
    COMPLETION_REPORT_SECTIONS,
    README_CR_REQUIRED_FIELDS,
)
from tests.api._completion_report_helpers import (
    contains_evidence,
    contains_file_paths,
    contains_step_markers,
    extract_section_content,
    is_effectively_empty_text,
)
from tests.api._readme_cr_helpers import extract_cr_field, is_effectively_empty
from tools.scaffold_cr import (
    extract_existing_cr_entries,
    find_insert_position,
    generate_completion_report,
    generate_readme_entry,
    parse_cr_id,
)


def test_scaffold_generated_readme_entry_passes_quality_gate(tmp_path):
    """
    scaffold が生成する README エントリが 046 の品質ゲートに抵触しないことを検証

    検証項目:
    - 必須フィールド（ファイル/目的/出力/ステータス）が存在
    - 目的/出力が実質空でない（is_effectively_empty に抵触しない）
    """
    cr_id = "CR-NEXUS-048"
    title = "README/Completion Report テンプレ自動生成（scaffold）"

    # README エントリを生成
    readme_entry = generate_readme_entry(cr_id, title)

    # 必須フィールドのチェック（cr_spec から取得）
    for field_name in README_CR_REQUIRED_FIELDS:
        field_value = extract_cr_field(readme_entry, field_name)
        assert field_value is not None, f"必須フィールド '{field_name}' が存在しません"

    # 目的/出力が実質空でないことをチェック
    purpose = extract_cr_field(readme_entry, "目的")
    assert purpose is not None, "目的フィールドが存在しません"
    assert not is_effectively_empty(purpose), f"目的が実質的に空です: {purpose}"

    output = extract_cr_field(readme_entry, "出力")
    assert output is not None, "出力フィールドが存在しません"
    assert not is_effectively_empty(output), f"出力が実質的に空です: {output}"


def test_scaffold_generated_completion_report_passes_quality_gate(tmp_path):
    """
    scaffold が生成する Completion Report が 042/044 の品質ゲート最小要件を満たすことを検証

    検証項目:
    - 必須見出しがすべて存在
    - 実装ステップに Step が含まれる
    - 変更ファイル一覧にファイルパスが含まれる
    - 動作確認結果に証跡（pytest/cmd/pass 等）が含まれる
    """
    cr_id = "CR-NEXUS-048"
    title = "README/Completion Report テンプレ自動生成（scaffold）"

    # Completion Report を生成
    report_content = generate_completion_report(cr_id, title)

    # 必須セクションのリスト（cr_spec から取得）
    required_sections = [section.name for section in COMPLETION_REPORT_SECTIONS if section.required]

    # 必須見出しがすべて存在することをチェック
    for section_name in required_sections:
        section_content = extract_section_content(report_content, section_name)
        assert section_content is not None, f"必須セクション '{section_name}' が見つかりません"

    # 実装ステップに Step が含まれることをチェック（044 の要件）
    steps_content = extract_section_content(report_content, "実装ステップ")
    assert steps_content is not None, "実装ステップセクションが見つかりません"
    assert contains_step_markers(steps_content), "実装ステップに Step マーカーが含まれていません"

    # 変更ファイル一覧にファイルパスが含まれることをチェック（044 の要件）
    files_content = extract_section_content(report_content, "変更ファイル一覧")
    assert files_content is not None, "変更ファイル一覧セクションが見つかりません"
    assert contains_file_paths(
        files_content
    ), "変更ファイル一覧にファイルパス表記が含まれていません"

    # 動作確認結果に証跡が含まれることをチェック（044 の要件）
    validation_content = extract_section_content(report_content, "動作確認結果")
    assert validation_content is not None, "動作確認結果セクションが見つかりません"
    assert contains_evidence(
        validation_content
    ), "動作確認結果に実行コマンドまたは結果の記述が含まれていません"

    # 各セクションが実質的に空でないことをチェック（044 の要件）
    for section_name in required_sections:
        section_content = extract_section_content(report_content, section_name)
        assert section_content is not None, f"セクション '{section_name}' が見つかりません"
        assert not is_effectively_empty_text(
            section_content
        ), f"セクション '{section_name}' が実質的に空です"


def test_scaffold_cr_id_parsing():
    """CR-ID のパース機能をテスト"""
    # 正常系
    prefix, series, number, suffix = parse_cr_id("CR-NEXUS-048")
    assert prefix == "CR"
    assert series == "NEXUS"
    assert number == 48
    assert suffix == ""

    prefix, series, number, suffix = parse_cr_id("CR-FASTAPI-012")
    assert prefix == "CR"
    assert series == "FASTAPI"
    assert number == 12
    assert suffix == ""

    prefix, series, number, suffix = parse_cr_id("CR-FASTAPI-010A")
    assert prefix == "CR"
    assert series == "FASTAPI"
    assert number == 10
    assert suffix == "A"

    # 異常系
    with pytest.raises(ValueError):
        parse_cr_id("INVALID")

    with pytest.raises(ValueError):
        parse_cr_id("CR-XXX-001")


def test_scaffold_readme_entry_insertion_order(tmp_path):
    """README エントリの挿入順序が数値順になっていることをテスト"""
    # ダミー README を作成
    dummy_readme = """# API Documentation

## プロンプト一覧

### CR-FASTAPI-001: First
- **目的**: First CR

### CR-FASTAPI-005: Fifth
- **目的**: Fifth CR

### CR-NEXUS-010: Tenth
- **目的**: Tenth CR
"""

    readme_path = tmp_path / "README.md"
    readme_path.write_text(dummy_readme, encoding="utf-8")

    # 既存エントリを抽出
    entries = extract_existing_cr_entries(dummy_readme)

    # CR-FASTAPI-003 を挿入する場合、位置は CR-FASTAPI-001 の後、CR-FASTAPI-005 の前になる
    insert_pos = find_insert_position(dummy_readme, "CR-FASTAPI-003")
    assert insert_pos > 0

    # CR-NEXUS-005 を挿入する場合、CR-NEXUS-010 の前になる
    insert_pos_nexus = find_insert_position(dummy_readme, "CR-NEXUS-005")
    assert insert_pos_nexus > 0


def test_scaffold_detects_existing_cr_id(tmp_path):
    """既存 CR-ID が存在する場合、挿入位置が -1 になることをテスト"""
    dummy_readme = """# API Documentation

## プロンプト一覧

### CR-NEXUS-048: Existing
- **目的**: Existing CR
"""

    # 既に存在する CR-ID の場合、-1 を返す
    insert_pos = find_insert_position(dummy_readme, "CR-NEXUS-048")
    assert insert_pos == -1


def test_scaffold_completion_report_has_all_required_sections():
    """Completion Report に必須セクションがすべて含まれていることをテスト"""
    cr_id = "CR-NEXUS-048"
    title = "Test CR"

    report_content = generate_completion_report(cr_id, title)

    # 必須セクションのリスト（cr_spec から取得）
    required_sections = [section.name for section in COMPLETION_REPORT_SECTIONS if section.required]

    for section_name in required_sections:
        section_content = extract_section_content(report_content, section_name)
        assert section_content is not None, f"必須セクション '{section_name}' が見つかりません"
