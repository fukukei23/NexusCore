"""diff_preview.py のテスト"""
import pytest

from nexuscore.core.diff_preview import (
    truncate_diff,
    wrap_diff_as_markdown,
    summarize_diff_files,
)


def test_truncate_diff_short():
    """短いdiffはそのまま返されるテスト"""
    diff = "--- a/file.py\n+++ b/file.py\n@@ -1,1 +1,1 @@\n-old\n+new"
    result = truncate_diff(diff, max_lines=200)

    assert result == diff


def test_truncate_diff_long():
    """長いdiffは切り詰められるテスト"""
    # 300行のdiffを作成
    lines = ["--- a/file.py", "+++ b/file.py"]
    for i in range(300):
        lines.append(f" line {i}")
    diff = "\n".join(lines)

    result = truncate_diff(diff, max_lines=200)

    assert "truncated" in result
    assert "total_lines=302" in result
    assert len(result.splitlines()) == 201  # 200行 + 1行のtruncatedメッセージ


def test_truncate_diff_exact_max_lines():
    """ちょうどmax_lines行の場合は切り詰められないテスト"""
    lines = ["--- a/file.py", "+++ b/file.py"]
    for i in range(198):  # 合計200行
        lines.append(f" line {i}")
    diff = "\n".join(lines)

    result = truncate_diff(diff, max_lines=200)

    assert "truncated" not in result
    assert result == diff


def test_wrap_diff_as_markdown():
    """diffがMarkdownコードブロックでラップされるテスト"""
    diff = "--- a/file.py\n+++ b/file.py\n@@ -1,1 +1,1 @@\n-old\n+new"
    result = wrap_diff_as_markdown(diff)

    assert result.startswith("```diff\n")
    assert result.endswith("\n```")
    assert "--- a/file.py" in result
    assert "+++ b/file.py" in result


def test_wrap_diff_as_markdown_truncates():
    """長いdiffはラップ前に切り詰められるテスト"""
    lines = ["--- a/file.py", "+++ b/file.py"]
    for i in range(300):
        lines.append(f" line {i}")
    diff = "\n".join(lines)

    result = wrap_diff_as_markdown(diff, max_lines=200)

    assert "truncated" in result
    assert result.startswith("```diff\n")
    assert result.endswith("\n```")


def test_summarize_diff_files_single():
    """単一ファイルのdiffからファイルパスを抽出するテスト"""
    diff = """--- a/src/file.py
+++ b/src/file.py
@@ -1,1 +1,1 @@
-old
+new"""

    files = summarize_diff_files(diff)

    assert len(files) == 1
    assert "b/src/file.py" in files


def test_summarize_diff_files_multiple():
    """複数ファイルのdiffからファイルパスを抽出するテスト"""
    diff = """--- a/src/file1.py
+++ b/src/file1.py
@@ -1,1 +1,1 @@
-old
+new
--- a/src/file2.py
+++ b/src/file2.py
@@ -1,1 +1,1 @@
-old
+new"""

    files = summarize_diff_files(diff)

    assert len(files) == 2
    assert "b/src/file1.py" in files
    assert "b/src/file2.py" in files


def test_summarize_diff_files_skips_dev_null():
    """/dev/nullは除外されるテスト"""
    diff = """--- a/src/file.py
+++ /dev/null
@@ -1,1 +0,0 @@
-old"""

    files = summarize_diff_files(diff)

    assert len(files) == 0
    assert "/dev/null" not in files


def test_summarize_diff_files_no_duplicates():
    """重複するファイルパスは除外されるテスト"""
    diff = """--- a/src/file.py
+++ b/src/file.py
@@ -1,1 +1,1 @@
-old
+new
--- a/src/file.py
+++ b/src/file.py
@@ -2,1 +2,1 @@
-old2
+new2"""

    files = summarize_diff_files(diff)

    assert len(files) == 1
    assert files.count("b/src/file.py") == 1


def test_summarize_diff_files_empty():
    """空のdiffからはファイルが抽出されないテスト"""
    diff = ""

    files = summarize_diff_files(diff)

    assert len(files) == 0


def test_summarize_diff_files_no_plus_plus_plus():
    """+++行がない場合は空リストを返すテスト"""
    diff = "--- a/file.py\n@@ -1,1 +1,1 @@\n-old\n+new"

    files = summarize_diff_files(diff)

    assert len(files) == 0


def test_wrap_diff_as_markdown_empty():
    """空のdiffもラップされるテスト"""
    diff = ""
    result = wrap_diff_as_markdown(diff)

    assert result == "```diff\n\n```"


def test_truncate_diff_empty():
    """空のdiffはそのまま返されるテスト"""
    diff = ""
    result = truncate_diff(diff, max_lines=200)

    assert result == ""


def test_summarize_diff_files_with_spaces():
    """ファイルパスにスペースが含まれる場合のテスト"""
    diff = """--- a/src/file name.py
+++ b/src/file name.py
@@ -1,1 +1,1 @@
-old
+new"""

    files = summarize_diff_files(diff)

    assert len(files) == 1
    assert "b/src/file name.py" in files


def test_summarize_diff_files_strips_whitespace():
    """ファイルパスの前後の空白が除去されるテスト"""
    diff = """--- a/src/file.py
+++   b/src/file.py
@@ -1,1 +1,1 @@
-old
+new"""

    files = summarize_diff_files(diff)

    assert len(files) == 1
    assert files[0] == "b/src/file.py"

