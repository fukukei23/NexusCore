"""
Completion Report 内容品質ゲート（中身の妥当性検証）

docs/api/README.md でステータスが「✅ 完了」になっている CR-ID について、
対応する Completion Report ファイルの各セクションに実質的な内容が含まれていることを検証する。
"""

from pathlib import Path

from tests.api._completion_report_helpers import (
    contains_evidence,
    contains_file_paths,
    contains_step_markers,
    extract_section_content,
    is_effectively_empty_text,
)
from tests.api._readme_cr_helpers import extract_completed_cr_ids

# プロジェクトルートのパス
PROJECT_ROOT = Path(__file__).parent.parent.parent
README_PATH = PROJECT_ROOT / "docs" / "api" / "README.md"
DOCS_API_DIR = PROJECT_ROOT / "docs" / "api"

from nexuscore.governance.cr_spec import COMPLETION_REPORT_SECTIONS

# 必須セクションのリスト（cr_spec から取得）
REQUIRED_SECTIONS = [section.name for section in COMPLETION_REPORT_SECTIONS if section.required]


def check_section_not_empty(report_content: str, section_name: str) -> tuple[bool, str]:
    """
    セクションが空でないかチェック

    Args:
        report_content: Completion Report の内容
        section_name: セクション名

    Returns:
        (is_valid, error_message) のタプル
    """
    content = extract_section_content(report_content, section_name)
    if content is None:
        return False, "セクションが見つからない"

    if is_effectively_empty_text(content):
        return False, "セクションが実質的に空（空行のみ、プレースホルダ、またはMarkdown記号のみ）"

    return True, ""


def check_implementation_steps(report_content: str) -> tuple[bool, str]:
    """
    実装ステップに Step が含まれているかチェック

    Args:
        report_content: Completion Report の内容

    Returns:
        (is_valid, error_message) のタプル
    """
    content = extract_section_content(report_content, "実装ステップ")
    if content is None:
        return False, "実装ステップセクションが見つからない"

    if not contains_step_markers(content):
        return False, "Step が1つも見つからない"

    return True, ""


def check_file_list(report_content: str) -> tuple[bool, str]:
    """
    変更ファイル一覧にファイルパスが含まれているかチェック

    Args:
        report_content: Completion Report の内容

    Returns:
        (is_valid, error_message) のタプル
    """
    content = extract_section_content(report_content, "変更ファイル一覧")
    if content is None:
        return False, "変更ファイル一覧セクションが見つからない"

    if not contains_file_paths(content):
        return False, "ファイルパス表記が見つからない"

    return True, ""


def check_validation_result(report_content: str) -> tuple[bool, str]:
    """
    動作確認結果に実行コマンドや結果が含まれているかチェック

    Args:
        report_content: Completion Report の内容

    Returns:
        (is_valid, error_message) のタプル
    """
    content = extract_section_content(report_content, "動作確認結果")
    if content is None:
        return False, "動作確認結果セクションが見つからない"

    if not contains_evidence(content):
        return False, "実行コマンドまたは結果の記述が見つからない"

    return True, ""


def test_completion_reports_have_content_quality():
    """
    docs/api/README.md で「✅ 完了」となっている CR について、
    対応する Completion Report の各セクションに実質的な内容が含まれていることを検証
    """
    # README を読み込む
    assert README_PATH.exists(), f"README file not found: {README_PATH}"
    readme_content = README_PATH.read_text(encoding="utf-8")

    # 完了した CR-ID を抽出
    completed_cr_ids = extract_completed_cr_ids(readme_content)
    assert completed_cr_ids, "No completed CRs found in README"

    # 各 CR-ID について Completion Report の内容品質を確認
    failures = []
    for cr_id in completed_cr_ids:
        filename = f"{cr_id}_COMPLETION_REPORT.md"
        file_path = DOCS_API_DIR / filename

        if not file_path.exists():
            failures.append(
                {
                    "cr_id": cr_id,
                    "file_path": file_path,
                    "issues": [{"section": "FILE", "reason": "ファイルが見つからない"}],
                }
            )
            continue

        # ファイル内容を読み込む
        report_content = file_path.read_text(encoding="utf-8")

        issues = []

        # 1. 必須セクションが空でないかチェック
        for section_name in REQUIRED_SECTIONS:
            is_valid, error_msg = check_section_not_empty(report_content, section_name)
            if not is_valid:
                issues.append({"section": section_name, "reason": error_msg})

    # 2. 各セクションの品質要件をチェック（cr_spec の定義に基づく）
    for section_def in COMPLETION_REPORT_SECTIONS:
        if not section_def.required:
            continue

        section_content = extract_section_content(report_content, section_def.name)
        if section_content is None:
            issues.append({"section": section_def.name, "reason": "セクションが見つからない"})
            continue

        # min_steps_required チェック
        if section_def.min_steps_required > 0:
            if section_def.name == "実装ステップ":
                is_valid, error_msg = check_implementation_steps(report_content)
                if not is_valid:
                    issues.append({"section": section_def.name, "reason": error_msg})

        # requires_file_paths チェック
        if section_def.requires_file_paths:
            if section_def.name == "変更ファイル一覧":
                is_valid, error_msg = check_file_list(report_content)
                if not is_valid:
                    issues.append({"section": section_def.name, "reason": error_msg})

        # evidence_required チェック
        if section_def.evidence_required:
            if section_def.name == "動作確認結果":
                is_valid, error_msg = check_validation_result(report_content)
                if not is_valid:
                    issues.append({"section": section_def.name, "reason": error_msg})

        if issues:
            failures.append({"cr_id": cr_id, "file_path": file_path, "issues": issues})

    assert not failures, "Completion reports with content quality issues:\n" + "\n".join(
        f"  - CR-ID: {f['cr_id']}\n"
        f"    File: {f['file_path']}\n"
        + "\n".join(f"    ✗ {issue['section']}: {issue['reason']}" for issue in f["issues"])
        for f in failures
    )
