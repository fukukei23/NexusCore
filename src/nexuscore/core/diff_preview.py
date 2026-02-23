"""
diff_preview.py

Self-Healing / PatchApplier が生成した unified diff を、
人間がレビューしやすい形に整形するユーティリティ群。

主な用途:
- GitHub PR コメントに貼るための Markdown ラップ
- 長すぎる diff のトリミング
- 変更されたファイル一覧の抽出
"""

from __future__ import annotations


def truncate_diff(diff_text: str, max_lines: int = 200) -> str:
    """
    diff が長すぎる場合に先頭 max_lines 行だけ残し、
    それ以降は '... (diff truncated)' を付けて返す。

    :param diff_text: unified diff 文字列
    :param max_lines: 最大行数
    """
    lines = diff_text.splitlines()
    if len(lines) <= max_lines:
        return diff_text

    head_lines = lines[:max_lines]
    head = "\n".join(head_lines)
    return f"{head}\n... (diff truncated; total_lines={len(lines)})"


def wrap_diff_as_markdown(diff_text: str, max_lines: int = 200) -> str:
    """
    GitHub PR コメントなどに貼るために、```diff でラップした文字列を返す。

    例:
        comment_body = wrap_diff_as_markdown(patch_text)
        # これを GitHub API で PR コメントとして投稿

    :param diff_text: unified diff 文字列
    :param max_lines: 表示する最大行数
    """
    safe = truncate_diff(diff_text, max_lines=max_lines)
    return "```diff\n" + safe + "\n```"


def summarize_diff_files(diff_text: str) -> list[str]:
    """
    unified diff から変更ファイルのパス一覧を抽出する。

    - '+++ ' から始まる行（ただし '/dev/null' は除外）を拾う。
    - 重複は除く。

    :param diff_text: unified diff 文字列
    :return: 変更されたファイルパスのリスト
    """
    files: list[str] = []
    for line in diff_text.splitlines():
        line = line.rstrip("\n")
        if not line.startswith("+++ "):
            continue

        path = line[4:].strip()
        # /dev/null は「削除されたファイル」などに使われるのでスキップ
        if path == "/dev/null":
            continue

        if path not in files:
            files.append(path)

    return files
