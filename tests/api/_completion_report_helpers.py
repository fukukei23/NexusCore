"""
Completion Report から情報を抽出するテスト専用ヘルパー

このモジュールは、tests/api/ 配下のテストで使用するためのユーティリティ関数を提供します。
README 解析は _readme_cr_helpers.py が担当し、本モジュールは Completion Report 本文の解析を担当します。
"""

import re


def extract_section_content(report_content: str, section_name: str) -> str | None:
    """
    Completion Report から指定セクションの内容を抽出する

    Args:
        report_content: Completion Report の内容
        section_name: セクション名（例: "実装ステップ"）

    Returns:
        セクションの内容（見出し行を除く）。セクションが見つからない場合は None
    """
    # セクション見出しのパターン（## または ###）
    # 日本語対応のため \b は使わず、見出しの後に空白または行末が続くことを確認
    section_pattern = rf"^\s*#{{2,3}}\s*{re.escape(section_name)}(\s|$)"
    lines = report_content.split("\n")

    section_start = None
    section_level = None
    for i, line in enumerate(lines):
        match = re.match(section_pattern, line)
        if match:
            section_start = i + 1
            # 見出しのレベル（# の数）を記録
            section_level_match = re.match(r"^(\s*)(#+)", line)
            if section_level_match:
                section_level = len(section_level_match.group(2))
            break

    if section_start is None or section_level is None:
        return None

    # 同じレベルまたは上位レベルの見出し（## または #）までをセクション内容とする
    # 下位レベル（### など）はセクション内容として扱う
    section_content_lines = []
    for i in range(section_start, len(lines)):
        line = lines[i]
        # 見出し行かチェック
        header_match = re.match(r"^(\s*)(#+)\s+", line)
        if header_match:
            current_level = len(header_match.group(2))
            # 同じレベル以上の見出しが見つかったら終了
            if current_level <= section_level:
                break
        section_content_lines.append(line)

    return "\n".join(section_content_lines).strip()


def is_effectively_empty_text(text: str) -> bool:
    """
    テキストが実質的に空（空行のみ、Markdown記号のみ、プレースホルダのみ）かどうかを判定する

    Args:
        text: 判定するテキスト

    Returns:
        実質的に空の場合は True、そうでない場合は False
    """
    if not text or not text.strip():
        return True

    text_stripped = text.strip()

    # Markdown の記号だけ（例: -, *, ` だけ）
    if re.match(r"^[-*`\s]+$", text_stripped):
        return True

    # プレースホルダパターン（大小文字・全半角揺れを許容）
    placeholder_patterns = [
        r"^(なし|特になし|todo|未実装|未対応|今後追加|tbd)$",
    ]

    text_lower = text_stripped.lower()
    for pattern in placeholder_patterns:
        if re.match(pattern, text_lower, re.IGNORECASE):
            return True

    # 空行のみの場合は NG
    non_empty_lines = [line.strip() for line in text.split("\n") if line.strip()]
    if not non_empty_lines:
        return True

    # プレースホルダ的な文のみの場合は NG（簡易チェック）
    if len(non_empty_lines) == 1:
        single_line_patterns = [
            r"^(なし|特になし|todo|未実装|未対応|今後追加|tbd|pending)$",
        ]
        for pattern in single_line_patterns:
            if re.match(pattern, non_empty_lines[0], re.IGNORECASE):
                return True

    return False


def contains_step_markers(text: str) -> bool:
    """
    テキストに Step マーカーが含まれているかチェック

    Args:
        text: チェックするテキスト

    Returns:
        Step マーカーが含まれている場合は True
    """
    # Step のパターン（### Step 1: / - Step 1: / Step 1: など）
    step_patterns = [
        r"^\s*#+\s*Step\s+\d+",
        r"^\s*[-*]\s*Step\s+\d+",
        r"^\s*\d+\.\s+Step",
        r"^\s*Step\s+\d+",
    ]

    for line in text.split("\n"):
        for pattern in step_patterns:
            if re.search(pattern, line, re.IGNORECASE):
                return True

    return False


def contains_file_paths(text: str) -> bool:
    """
    テキストにファイルパス表記が含まれているかチェック

    Args:
        text: チェックするテキスト

    Returns:
        ファイルパス表記が含まれている場合は True
    """
    # ファイルパスのパターン（docs/, tests/, src/ などで始まるパス）
    file_path_patterns = [
        r"[`'\"](docs|tests|src|tools|sdk)/[^\s`'\"]+",
        r"[`'\"][\w\-_/]+\.(py|md|ts|js|json|toml|yaml|yml|txt|sh|bash)",
        r"docs/api/",
        r"tests/api/",
        r"src/nexuscore/",
    ]

    for line in text.split("\n"):
        for pattern in file_path_patterns:
            if re.search(pattern, line):
                return True

    return False


def contains_evidence(text: str) -> bool:
    """
    テキストに実行コマンドや結果記述が含まれているかチェック

    Args:
        text: チェックするテキスト

    Returns:
        実行コマンドまたは結果記述が含まれている場合は True
    """
    # 実行コマンドのパターン
    command_patterns = [
        r"python\s+-m\s+pytest",
        r"pytest",
        r"make\s+\w+",
        r"bash\s+\S+",
        r"curl\s+",
        r"```(bash|sh|shell)",
    ]

    # 結果のパターン
    result_patterns = [
        r"PASS",
        r"FAIL",
        r"passed",
        r"failed",
        r"\d+\s+passed",
        r"\d+\s+failed",
        r"✅",
        r"成功",
        r"失敗",
    ]

    text_lower = text.lower()
    has_command = any(re.search(pattern, text_lower) for pattern in command_patterns)
    has_result = any(re.search(pattern, text_lower) for pattern in result_patterns)

    return has_command or has_result
