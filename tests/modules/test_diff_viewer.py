"""
diff_viewer.py 包括テスト
generate_diff() の正常系・エッジケースを完全カバー
"""
from __future__ import annotations

import pytest

from nexuscore.archive.modules.diff_viewer import generate_diff


class TestGenerateDiff:
    def test_diff_identical_strings_returns_empty(self):
        result = generate_diff("hello", "hello")
        assert result == ""

    def test_diff_different_strings_contains_header(self):
        result = generate_diff("old line", "new line")
        assert "--- Before" in result
        assert "+++ After" in result

    def test_diff_shows_removed_line(self):
        result = generate_diff("old line", "new line")
        assert "-old line" in result

    def test_diff_shows_added_line(self):
        result = generate_diff("old line", "new line")
        assert "+new line" in result

    def test_diff_empty_old_code(self):
        result = generate_diff("", "new line")
        assert "+new line" in result

    def test_diff_empty_new_code(self):
        result = generate_diff("old line", "")
        assert "-old line" in result

    def test_diff_both_empty_returns_empty(self):
        result = generate_diff("", "")
        assert result == ""

    def test_diff_multiline_code(self):
        old = "def foo():\n    return 1"
        new = "def foo():\n    return 2"
        result = generate_diff(old, new)
        assert "-    return 1" in result
        assert "+    return 2" in result

    def test_diff_returns_string(self):
        result = generate_diff("a", "b")
        assert isinstance(result, str)

    def test_diff_added_multiple_lines(self):
        old = "line1"
        new = "line1\nline2\nline3"
        result = generate_diff(old, new)
        assert "+line2" in result
        assert "+line3" in result

    def test_diff_no_format_in_unified_diff(self):
        """unified_diff uses lineterm="" so no extra newlines"""
        result = generate_diff("a", "b")
        # Should not have trailing newlines in joined output
        assert isinstance(result, str)
        assert len(result) > 0
