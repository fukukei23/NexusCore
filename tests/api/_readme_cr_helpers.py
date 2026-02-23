"""
README から CR-ID を抽出するテスト専用ヘルパー

このモジュールは、tests/api/ 配下のテストで使用するためのユーティリティ関数を提供します。
"""

import re


def extract_completed_cr_ids(readme_content: str) -> list[str]:
    """
    README.md から「✅ 完了」となっている CR-ID を抽出する

    対象フォーマット:
    - 見出し: ### CR-NEXUS-XXX: または ### CR-FASTAPI-XXX:
    - 同一ブロック内に '- **ステータス**: ✅ 完了' または '**ステータス**: ✅ 完了' が存在する場合のみ対象

    Args:
        readme_content: README の内容

    Returns:
        抽出された CR-ID のリスト（例: ["CR-FASTAPI-001", "CR-NEXUS-035"]）
    """
    completed_cr_ids = []
    lines = readme_content.split("\n")

    i = 0
    while i < len(lines):
        line = lines[i]

        # CR 見出し行を検出: ### CR-XXX: ...
        cr_header_match = re.match(r"^### (CR-(?:NEXUS|FASTAPI)-\d{3}[A-Z]*):", line)
        if cr_header_match:
            cr_id = cr_header_match.group(1)

            # 次の見出し（### または ##）まで、またはファイル終端までをブロックとして扱う
            block_end = len(lines)
            for j in range(i + 1, len(lines)):
                if lines[j].startswith("### ") or lines[j].startswith("## "):
                    block_end = j
                    break

            # ブロック内に「✅ 完了」があるかチェック
            block_lines = lines[i:block_end]
            block_text = "\n".join(block_lines)
            if "- **ステータス**: ✅ 完了" in block_text or "**ステータス**: ✅ 完了" in block_text:
                completed_cr_ids.append(cr_id)

            i = block_end
        else:
            i += 1

    return completed_cr_ids


def extract_cr_blocks(readme_content: str) -> list[dict]:
    """
    README.md から CR ブロックを抽出する

    Args:
        readme_content: README の内容

    Returns:
        CR ブロックのリスト。各ブロックは以下のキーを持つ辞書：
        - cr_id: CR-ID（例: "CR-NEXUS-035"）
        - block_text: ブロック全体のテキスト（見出し行含む）
        - block_start_line: ブロックの開始行番号（0始まり）
    """
    blocks = []
    lines = readme_content.split("\n")

    i = 0
    while i < len(lines):
        line = lines[i]

        # CR 見出し行を検出: ### CR-XXX: ...
        cr_header_match = re.match(r"^### (CR-(?:NEXUS|FASTAPI)-\d{3}[A-Z]*):", line)
        if cr_header_match:
            cr_id = cr_header_match.group(1)

            # 次の見出し（### または ##）まで、またはファイル終端までをブロックとして扱う
            block_end = len(lines)
            for j in range(i + 1, len(lines)):
                if lines[j].startswith("### ") or lines[j].startswith("## "):
                    block_end = j
                    break

            block_lines = lines[i:block_end]
            block_text = "\n".join(block_lines)

            blocks.append(
                {
                    "cr_id": cr_id,
                    "block_text": block_text,
                    "block_start_line": i,
                }
            )

            i = block_end
        else:
            i += 1

    return blocks


def extract_cr_status(block_text: str) -> str | None:
    """
    CR ブロックからステータスを抽出する

    Args:
        block_text: CR ブロックのテキスト

    Returns:
        ステータス文字列（例: "✅ 完了"）。見つからない場合は None
    """
    # パターン: - **ステータス**: <status> または **ステータス**: <status>
    pattern = r"(?:^|\n)\s*[-*]\s+\*\*ステータス\*\*:\s*([^\n]+)"
    match = re.search(pattern, block_text)
    if match:
        return match.group(1).strip()
    return None


def extract_cr_reason(block_text: str) -> str | None:
    """
    CR ブロックから理由を抽出する（保留/中断用）

    Args:
        block_text: CR ブロックのテキスト

    Returns:
        理由文字列。見つからない場合は None
    """
    # パターン: - **理由**: <reason> または **理由**: <reason>
    pattern = r"(?:^|\n)\s*[-*]\s+\*\*理由\*\*:\s*([^\n]+)"
    match = re.search(pattern, block_text)
    if match:
        return match.group(1).strip()
    return None


def extract_cr_field(block_text: str, field_name: str) -> str | None:
    """
    CR ブロックから指定フィールドの値を抽出する汎用関数

    Args:
        block_text: CR ブロックのテキスト
        field_name: フィールド名（例: "目的", "出力", "完了レポート"）

    Returns:
        フィールドの値（文字列）。見つからない場合は None
    """
    # パターン: - **<field_name>**: <value> または **<field_name>**: <value>
    escaped_field = re.escape(field_name)
    pattern = rf"(?:^|\n)\s*[-*]\s+\*\*{escaped_field}\*\*:\s*([^\n]+)"
    match = re.search(pattern, block_text)
    if match:
        return match.group(1).strip()
    return None


def is_effectively_empty(value: str) -> bool:
    """
    値が実質的に空（空文字、空白のみ、プレースホルダのみ）かどうかを判定する

    Args:
        value: 判定する値

    Returns:
        実質的に空の場合は True、そうでない場合は False
    """
    if not value or not value.strip():
        return True

    value_stripped = value.strip()

    # Markdown の記号だけ（例: -, *, ` だけ）
    if re.match(r"^[-*`\s]+$", value_stripped):
        return True

    # プレースホルダパターン（大小文字・全半角揺れを許容）
    placeholder_patterns = [
        r"^tbd$",
        r"^todo$",
        r"^未定$",
        r"^後で",
        r"^作成中",
        r"^\(作成中\)",
        r"^未実装",
        r"^未対応",
        r"^今後",
        r"^pending",
    ]

    value_lower = value_stripped.lower()
    for pattern in placeholder_patterns:
        if re.match(pattern, value_lower, re.IGNORECASE):
            return True

    return False
