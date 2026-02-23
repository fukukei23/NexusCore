"""
Completion Report 品質ゲート（必須セクション検証）

docs/api/README.md でステータスが「✅ 完了」になっている CR-ID について、
対応する Completion Report ファイルが必須セクション（見出し）を含んでいることを検証する。
"""

import re
from pathlib import Path

from tests.api._readme_cr_helpers import extract_completed_cr_ids

# プロジェクトルートのパス
PROJECT_ROOT = Path(__file__).parent.parent.parent
README_PATH = PROJECT_ROOT / "docs" / "api" / "README.md"
DOCS_API_DIR = PROJECT_ROOT / "docs" / "api"

from nexuscore.governance.cr_spec import COMPLETION_REPORT_SECTIONS

# 必須セクションのリスト（cr_spec から取得）
REQUIRED_SECTIONS = [section.name for section in COMPLETION_REPORT_SECTIONS if section.required]


def check_required_sections(report_content: str, required_sections: list[str]) -> list[str]:
    """
    Completion Report の内容に必須セクションの見出しが含まれているかチェック

    Args:
        report_content: Completion Report の内容
        required_sections: 必須セクション名のリスト

    Returns:
        欠落しているセクション名のリスト
    """
    missing_sections = []

    for section_name in required_sections:
        # 見出しレベル ## または ### を許容し、行頭アンカーで検索
        # 例: "## 実装日時" や "### 実装日時" にマッチ
        # 余計な装飾（:, -, 全角スペース）も許容するため、\s* を使用
        pattern = rf"^\s*#{{2,3}}\s*{re.escape(section_name)}\b"
        if not re.search(pattern, report_content, re.MULTILINE):
            missing_sections.append(section_name)

    return missing_sections


def test_completion_reports_have_required_sections():
    """
    docs/api/README.md で「✅ 完了」となっている CR について、
    対応する Completion Report が必須セクション（見出し）を含んでいることを検証
    """
    # README を読み込む
    assert README_PATH.exists(), f"README file not found: {README_PATH}"
    readme_content = README_PATH.read_text(encoding="utf-8")

    # 完了した CR-ID を抽出
    completed_cr_ids = extract_completed_cr_ids(readme_content)
    assert completed_cr_ids, "No completed CRs found in README"

    # 各 CR-ID について Completion Report の必須セクションを確認
    failures = []
    for cr_id in completed_cr_ids:
        filename = f"{cr_id}_COMPLETION_REPORT.md"
        file_path = DOCS_API_DIR / filename

        # ファイルが存在することは 041 のテストで確認済みだが、念のため確認
        if not file_path.exists():
            failures.append(
                {
                    "cr_id": cr_id,
                    "file_path": file_path,
                    "missing_sections": ["FILE_NOT_FOUND"],
                }
            )
            continue

        # ファイル内容を読み込む
        report_content = file_path.read_text(encoding="utf-8")

        # 必須セクションの存在をチェック
        missing_sections = check_required_sections(report_content, REQUIRED_SECTIONS)
        if missing_sections:
            failures.append(
                {
                    "cr_id": cr_id,
                    "file_path": file_path,
                    "missing_sections": missing_sections,
                }
            )

    assert not failures, "Completion reports missing required sections:\n" + "\n".join(
        f"  - CR-ID: {f['cr_id']}\n"
        f"    File: {f['file_path']}\n"
        f"    Missing sections: {', '.join(f['missing_sections'])}"
        for f in failures
    )
