"""
完了した CR の Completion Report ファイルの存在チェック

docs/api/README.md でステータスが「✅ 完了」になっている CR-ID について、
対応する docs/api/<CR-ID>_COMPLETION_REPORT.md が必ず存在することを検証する。
"""

from pathlib import Path

from tests.api._readme_cr_helpers import extract_completed_cr_ids

# プロジェクトルートのパス
PROJECT_ROOT = Path(__file__).parent.parent.parent
README_PATH = PROJECT_ROOT / "docs" / "api" / "README.md"
DOCS_API_DIR = PROJECT_ROOT / "docs" / "api"


def test_completion_reports_exist_for_completed_crs():
    """
    docs/api/README.md で「✅ 完了」となっている CR について、
    対応する Completion Report ファイルが存在することを検証
    """
    # README を読み込む
    assert README_PATH.exists(), f"README file not found: {README_PATH}"
    readme_content = README_PATH.read_text(encoding="utf-8")

    # 完了した CR-ID を抽出
    completed_cr_ids = extract_completed_cr_ids(readme_content)
    assert completed_cr_ids, "No completed CRs found in README"

    # 各 CR-ID について Completion Report ファイルが存在することを確認
    missing_files = []
    for cr_id in completed_cr_ids:
        filename = f"{cr_id}_COMPLETION_REPORT.md"
        file_path = DOCS_API_DIR / filename
        if not file_path.exists():
            missing_files.append((cr_id, filename, file_path))

    assert not missing_files, (
        "Completion report files for completed CRs do not exist:\n"
        + "\n".join(
            f"  - CR-ID: {cr_id}\n    Expected file: {filename}\n    Expected path: {file_path}"
            for cr_id, filename, file_path in missing_files
        )
        + f"\n\nExpected location: {DOCS_API_DIR}"
    )
