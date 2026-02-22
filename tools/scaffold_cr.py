#!/usr/bin/env python3
"""
CR の README エントリと Completion Report 雛形を自動生成する scaffold

Usage:
    python tools/scaffold_cr.py --cr-id CR-NEXUS-048 --title "README/Completion Report テンプレ自動生成（scaffold）"
"""

import argparse
import re
import sys
from datetime import date
from pathlib import Path
from typing import Optional

# プロジェクトルートのパス（このスクリプトは tools/ 配下にある）
PROJECT_ROOT = Path(__file__).parent.parent
# src/ を Python パスに追加（nexuscore モジュールを import するため）
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from nexuscore.governance.cr_spec import (
    ALLOWED_STATUSES,
    COMPLETION_REPORT_SECTIONS,
    COMPLETION_REPORT_TEMPLATE_STRUCTURE,
    README_CR_REQUIRED_FIELDS,
    SCAFFOLD_PLACEHOLDERS,
    STATUS_RULES,
)

# プロジェクトルートのパス（このスクリプトは tools/ 配下にある）
PROJECT_ROOT = Path(__file__).parent.parent


def parse_cr_id(cr_id: str) -> tuple[str, str, int]:
    """
    CR-ID を解析して（prefix, series, number）を返す

    Args:
        cr_id: CR-ID（例: "CR-NEXUS-048" または "CR-FASTAPI-012"）

    Returns:
        (prefix, series, number) のタプル
        - prefix: "CR"
        - series: "NEXUS" または "FASTAPI"
        - number: 数値部分

    Raises:
        ValueError: CR-ID の形式が不正な場合
    """
    match = re.match(r"^CR-(NEXUS|FASTAPI)-(\d{3})([A-Z]*)$", cr_id.upper())
    if not match:
        raise ValueError(f"Invalid CR-ID format: {cr_id}. Expected format: CR-NEXUS-XXX or CR-FASTAPI-XXX")

    series = match.group(1)
    number_str = match.group(2)
    suffix = match.group(3) if match.group(3) else ""

    return ("CR", series, int(number_str), suffix)


def extract_existing_cr_entries(readme_content: str) -> list[dict]:
    """
    README から既存の CR エントリを抽出する

    Args:
        readme_content: README の内容

    Returns:
        CR エントリのリスト。各エントリは以下のキーを持つ辞書：
        - cr_id: CR-ID（例: "CR-NEXUS-048"）
        - block_text: ブロック全体のテキスト
        - start_line: 開始行番号（0始まり）
    """
    entries = []
    lines = readme_content.split("\n")

    i = 0
    while i < len(lines):
        line = lines[i]

        # CR 見出し行を検出: ### CR-XXX: ...
        cr_header_match = re.match(r"^### (CR-(?:NEXUS|FASTAPI)-\d{3}[A-Z]*):\s*(.*)$", line)
        if cr_header_match:
            cr_id = cr_header_match.group(1)
            title = cr_header_match.group(2)

            # 次の見出し（### または ##）までをブロックとして扱う
            block_end = len(lines)
            for j in range(i + 1, len(lines)):
                if lines[j].startswith("### ") or lines[j].startswith("## "):
                    block_end = j
                    break

            block_lines = lines[i:block_end]
            block_text = "\n".join(block_lines)

            # CR-ID を解析して数値を取得
            try:
                _, series, number, suffix = parse_cr_id(cr_id)
                entries.append(
                    {
                        "cr_id": cr_id,
                        "series": series,
                        "number": number,
                        "suffix": suffix,
                        "title": title,
                        "block_text": block_text,
                        "start_line": i,
                    }
                )
            except ValueError:
                # パースできない CR-ID はスキップ
                pass

            i = block_end
        else:
            i += 1

    return entries


def find_insert_position(readme_content: str, new_cr_id: str) -> int:
    """
    新しい CR エントリの挿入位置を決定する

    Args:
        readme_content: README の内容
        new_cr_id: 新しい CR-ID

    Returns:
        挿入位置（行番号、0始まり）。既存 CR-ID が存在する場合は -1
    """
    entries = extract_existing_cr_entries(readme_content)
    _, new_series, new_number, new_suffix = parse_cr_id(new_cr_id)

    # 同じ CR-ID が既に存在する場合は -1 を返す
    for entry in entries:
        if entry["cr_id"].upper() == new_cr_id.upper():
            return -1

    # 同じ系統（NEXUS/FASTAPI）で数値順に並ぶように挿入位置を決定
    # 同じ系統のエントリの中で、数値が小さい順に並べる
    lines = readme_content.split("\n")

    # 同じ系統のエントリをフィルタ
    same_series_entries = [e for e in entries if e["series"] == new_series]

    # 数値順にソート
    same_series_entries.sort(key=lambda x: (x["number"], x["suffix"]))

    # 新しい CR を挿入する位置を決定
    for entry in same_series_entries:
        if entry["number"] > new_number or (entry["number"] == new_number and entry["suffix"] > new_suffix):
            # このエントリの前に挿入
            return entry["start_line"]

    # 同じ系統のエントリが最後の場合は、最後のエントリの後
    if same_series_entries:
        last_entry = same_series_entries[-1]
        # 最後のエントリのブロックの終わりを探す
        last_block_lines = last_entry["block_text"].split("\n")
        return last_entry["start_line"] + len(last_block_lines)

    # 同じ系統のエントリがない場合、最初の CR エントリの前に挿入
    # または "## プロンプト一覧" セクションの後に挿入
    for i, line in enumerate(lines):
        if line.startswith("## プロンプト一覧"):
            # 次の CR エントリまで探す
            for j in range(i + 1, len(lines)):
                if lines[j].startswith("### CR-"):
                    return j
            # CR エントリがない場合は、セクションの直後に挿入
            return i + 2

    # デフォルト: 最後に追加
    return len(lines)


def generate_readme_entry(cr_id: str, title: str, status: str = "⏳ 進行中") -> str:
    """
    README CR エントリの雛形を生成する（cr_spec の定義から生成）

    Args:
        cr_id: CR-ID
        title: タイトル
        status: ステータス（デフォルト: "⏳ 進行中"）

    Returns:
        README エントリのテキスト
    """
    lines = [f"### {cr_id}: {title}"]

    # cr_spec の README_CR_REQUIRED_FIELDS の順序でフィールドを生成
    for field_name in README_CR_REQUIRED_FIELDS:
        if field_name == "ファイル":
            lines.append(f"- **ファイル**: プロンプトは {cr_id} として実行")
        elif field_name == "目的":
            lines.append(f"- **目的**: {SCAFFOLD_PLACEHOLDERS['purpose']}")
        elif field_name == "出力":
            lines.append(f"- **出力**: `docs/api/{cr_id}_COMPLETION_REPORT.md`")
        elif field_name == "ステータス":
            lines.append(f"- **ステータス**: {status}")

    # ステータスが「✅ 完了」の場合は完了レポートフィールドを追加
    status_rule = STATUS_RULES.get(status, {})
    if status_rule.get("completion_report_required", False):
        lines.append(f"- **完了レポート**: [CR-NEXUS-048_COMPLETION_REPORT.md](./{cr_id}_COMPLETION_REPORT.md)")
    else:
        lines.append(f"- **完了レポート**: {SCAFFOLD_PLACEHOLDERS['completion_report_not_created']}")

    return "\n".join(lines) + "\n"


def generate_completion_report(cr_id: str, title: str) -> str:
    """
    Completion Report の雛形を生成する（cr_spec の定義から生成）

    Args:
        cr_id: CR-ID
        title: タイトル

    Returns:
        Completion Report のテキスト
    """
    today = date.today().strftime("%Y年%m月%d日")
    lines = [f"# {cr_id}: {title}{COMPLETION_REPORT_TEMPLATE_STRUCTURE['title_suffix']}", ""]

    # cr_spec の COMPLETION_REPORT_SECTIONS の順序でセクションを生成
    for section_def in COMPLETION_REPORT_SECTIONS:
        if not section_def.required:
            continue

        lines.append(f"## {section_def.name}")
        lines.append("")

        # セクション固有の内容を生成
        if section_def.name == "実装日時":
            lines.append(today)
            lines.append("")
        elif section_def.name == "概要":
            lines.append("### 目的")
            lines.append(SCAFFOLD_PLACEHOLDERS["purpose"])
            lines.append("")
            lines.append("### ゴール")
            lines.append(f"- {SCAFFOLD_PLACEHOLDERS['goal']}")
            lines.append("")
            lines.append("### 原則")
            for principle_line in SCAFFOLD_PLACEHOLDERS["principle"].split("\n"):
                lines.append(f"- {principle_line}")
            lines.append("")
        elif section_def.name == "実装ステップ":
            # min_steps_required に基づいて Step を生成
            for step_num in range(1, section_def.min_steps_required + 1):
                lines.append(f"### Step {step_num}: 雛形生成")
                lines.append(f"- {SCAFFOLD_PLACEHOLDERS['step_description']}")
                lines.append(f"- {SCAFFOLD_PLACEHOLDERS['step_reason']}")
                lines.append("")
        elif section_def.name == "変更ファイル一覧":
            lines.append("### 新規作成ファイル")
            lines.append(f"- `docs/api/{cr_id}_COMPLETION_REPORT.md` - Completion Report（scaffold 生成）")
            lines.append(f"- `tools/scaffold_cr.py` - CR 雛形生成ツール（scaffold 生成）")
            lines.append(f"- `tests/api/test_scaffold_cr.py` - scaffold 品質ゲートテスト（scaffold 生成）")
            lines.append("")
            lines.append("### 変更ファイル")
            lines.append(f"- `docs/api/README.md` - CR エントリ追加（scaffold 生成）")
            lines.append("")
        elif section_def.name == "動作確認結果":
            lines.append("### テスト結果")
            lines.append("")
            lines.append("実行コマンド:")
            lines.append("```bash")
            lines.append(SCAFFOLD_PLACEHOLDERS["validation_command"])
            lines.append("```")
            lines.append("")
            lines.append("結果:")
            lines.append(SCAFFOLD_PLACEHOLDERS["validation_result"])
            lines.append("")
        elif section_def.name == "設計上の改善点":
            lines.append("雛形の標準化により、作業ブレ・記載漏れを削減する")
            lines.append("")
        elif section_def.name == "既知の制約・注意事項":
            lines.append("scaffold は骨格のみ生成する。実内容は作業完了時に追記する必要がある")
            lines.append("")
        elif section_def.name == "次のステップ":
            lines.append("実装完了後、この Completion Report を実内容で更新する")
            lines.append("")
            lines.append("README のステータスを ✅ 完了 にし、完了レポートリンクを更新する")
            lines.append("")

    return "\n".join(lines)


def scaffold_cr(
    cr_id: str,
    title: str,
    readme_path: Path,
    docs_dir: Path,
    status: str = "⏳ 進行中",
    dry_run: bool = False,
) -> int:
    """
    CR の README エントリと Completion Report 雛形を生成する

    Args:
        cr_id: CR-ID
        title: タイトル
        readme_path: README ファイルのパス
        docs_dir: docs/api ディレクトリのパス
        status: ステータス（デフォルト: "⏳ 進行中"）
        dry_run: ドライランモード（ファイルを書かず、差分のみ表示）

    Returns:
        終了コード（0: 成功, 2: 入力不正, 3: 既存衝突）
    """
    # CR-ID の形式を検証
    try:
        parse_cr_id(cr_id)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 2

    # ステータスの検証（cr_spec の定義に準拠）
    if status not in ALLOWED_STATUSES:
        print(f"Error: Invalid status '{status}'. Allowed: {', '.join(ALLOWED_STATUSES)}", file=sys.stderr)
        return 2

    # README を読み込む
    if not readme_path.exists():
        print(f"Error: README file not found: {readme_path}", file=sys.stderr)
        return 2

    readme_content = readme_path.read_text(encoding="utf-8")

    # 既存 CR-ID のチェック
    entries = extract_existing_cr_entries(readme_content)
    for entry in entries:
        if entry["cr_id"].upper() == cr_id.upper():
            print(f"Error: CR-ID '{cr_id}' already exists in README at line {entry['start_line'] + 1}", file=sys.stderr)
            return 3

    # 挿入位置を決定
    insert_pos = find_insert_position(readme_content, cr_id)

    # README エントリを生成
    readme_entry = generate_readme_entry(cr_id, title, status)

    # Completion Report を生成
    completion_report = generate_completion_report(cr_id, title)

    # Completion Report ファイルパス
    report_path = docs_dir / f"{cr_id}_COMPLETION_REPORT.md"

    if dry_run:
        # ドライラン: 差分のみ表示
        print("=" * 80)
        print("DRY RUN: README changes")
        print("=" * 80)
        lines = readme_content.split("\n")
        insert_line = lines[insert_pos] if insert_pos < len(lines) else ""
        print(f"  Insert after line {insert_pos + 1}: {insert_line[:60]}...")
        print()
        print("  +" + "-" * 78)
        for line in readme_entry.split("\n"):
            print(f"  +{line}")
        print("  +" + "-" * 78)
        print()

        if report_path.exists():
            print(f"SKIP: Completion Report already exists: {report_path}")
        else:
            print("=" * 80)
            print("DRY RUN: New Completion Report")
            print("=" * 80)
            print(f"  File: {report_path}")
            print()
            for line in completion_report.split("\n"):
                print(f"  {line}")
        return 0

    # README にエントリを挿入
    lines = readme_content.split("\n")
    # 挿入位置の後に空行を追加（必要に応じて）
    if insert_pos < len(lines) and lines[insert_pos].strip():
        lines.insert(insert_pos, "")
        insert_pos += 1

    # エントリを挿入
    entry_lines = readme_entry.split("\n")
    for i, line in enumerate(entry_lines):
        lines.insert(insert_pos + i, line)

    # 最後に空行を追加（次の CR エントリとの間）
    lines.insert(insert_pos + len(entry_lines), "")

    new_readme_content = "\n".join(lines)
    readme_path.write_text(new_readme_content, encoding="utf-8")
    print(f"✅ Added CR entry to README: {readme_path}")

    # Completion Report を生成（既に存在する場合はスキップ）
    if report_path.exists():
        print(f"⏭️  SKIP: Completion Report already exists: {report_path}")
    else:
        docs_dir.mkdir(parents=True, exist_ok=True)
        report_path.write_text(completion_report, encoding="utf-8")
        print(f"✅ Created Completion Report: {report_path}")

    return 0


def main():
    """CLI エントリーポイント"""
    parser = argparse.ArgumentParser(description="CR の README エントリと Completion Report 雛形を自動生成")
    parser.add_argument("--cr-id", required=True, help="CR-ID (例: CR-NEXUS-048, CR-FASTAPI-012)")
    parser.add_argument("--title", required=True, help="CR のタイトル")
    parser.add_argument("--readme-path", type=Path, default=PROJECT_ROOT / "docs" / "api" / "README.md", help="README ファイルのパス")
    parser.add_argument("--docs-dir", type=Path, default=PROJECT_ROOT / "docs" / "api", help="docs/api ディレクトリのパス")
    parser.add_argument(
        "--status",
        default="⏳ 進行中",
        help='ステータス（デフォルト: "⏳ 進行中"）',
    )
    parser.add_argument("--dry-run", action="store_true", help="ファイルを書かず、差分のみ表示")

    args = parser.parse_args()

    exit_code = scaffold_cr(
        cr_id=args.cr_id,
        title=args.title,
        readme_path=args.readme_path,
        docs_dir=args.docs_dir,
        status=args.status,
        dry_run=args.dry_run,
    )

    sys.exit(exit_code)


if __name__ == "__main__":
    main()

