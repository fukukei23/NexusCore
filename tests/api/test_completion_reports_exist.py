"""
README に記載されている Completion Report ファイルの存在チェック

docs/api/README.md に列挙されている *_COMPLETION_REPORT.md リンク先ファイルが
実際に docs/api/ 配下に存在することを検証する。
"""

import re
from pathlib import Path

# プロジェクトルートのパス
PROJECT_ROOT = Path(__file__).parent.parent.parent
README_PATH = PROJECT_ROOT / "docs" / "api" / "README.md"
DOCS_API_DIR = PROJECT_ROOT / "docs" / "api"


def extract_completion_report_links(readme_content: str) -> list[str]:
    """
    README から *_COMPLETION_REPORT.md への相対リンクを抽出する

    Args:
        readme_content: README の内容

    Returns:
        抽出されたリンク先ファイル名のリスト（例: ["CR-FASTAPI-001_COMPLETION_REPORT.md"]）
    """
    # パターン: [リンクテキスト](./CR-XXX_COMPLETION_REPORT.md) または [リンクテキスト](CR-XXX_COMPLETION_REPORT.md)
    pattern = r"\[[^\]]+\]\(\.?/?([A-Z0-9_-]+_COMPLETION_REPORT\.md)\)"
    matches = re.findall(pattern, readme_content)
    return matches


def test_completion_reports_from_readme_exist():
    """
    docs/api/README.md に記載されている Completion Report リンク先ファイルが存在することを検証
    """
    # README を読み込む
    assert README_PATH.exists(), f"README file not found: {README_PATH}"
    readme_content = README_PATH.read_text(encoding="utf-8")

    # リンクを抽出
    linked_files = extract_completion_report_links(readme_content)
    assert linked_files, "No completion report links found in README"

    # 各ファイルが存在することを確認
    missing_files = []
    for filename in linked_files:
        file_path = DOCS_API_DIR / filename
        if not file_path.exists():
            missing_files.append(filename)

    assert not missing_files, (
        "Completion report files referenced in README do not exist:\n"
        + "\n".join(f"  - {f}" for f in missing_files)
        + f"\n\nExpected location: {DOCS_API_DIR}"
    )


def test_completion_report_links_format():
    """
    README 内の Completion Report リンクが正しい形式であることを検証
    （ファイル名の命名規則チェック）
    """
    assert README_PATH.exists(), f"README file not found: {README_PATH}"
    readme_content = README_PATH.read_text(encoding="utf-8")

    # リンクを抽出
    linked_files = extract_completion_report_links(readme_content)

    # 命名規則: CR-NEXUS-XXX_COMPLETION_REPORT.md または CR-FASTAPI-XXX_COMPLETION_REPORT.md
    # XXX は数字3桁の後にオプションでアルファベットが続く（例: CR-FASTAPI-010A）
    pattern = re.compile(r"^CR-(NEXUS|FASTAPI)-\d{3}[A-Z]*_COMPLETION_REPORT\.md$")

    invalid_files = []
    for filename in linked_files:
        if not pattern.match(filename):
            invalid_files.append(filename)

    assert not invalid_files, (
        "Completion report files with invalid naming format:\n"
        + "\n".join(f"  - {f}" for f in invalid_files)
        + "\n\nExpected format: CR-NEXUS-XXX_COMPLETION_REPORT.md or CR-FASTAPI-XXX_COMPLETION_REPORT.md"
    )
