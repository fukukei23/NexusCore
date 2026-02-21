"""
Comprehensive tests for diff_preview module.

Tests diff formatting utilities for PR comments and review UI.
"""

import pytest
from nexuscore.core.diff_preview import (
    truncate_diff,
    wrap_diff_as_markdown,
    summarize_diff_files,
)


class TestTruncateDiff:
    """Tests for truncate_diff function."""

    def test_short_diff_unchanged(self):
        """Test short diff is returned unchanged."""
        diff = "line 1\nline 2\nline 3"

        result = truncate_diff(diff, max_lines=10)

        assert result == diff

    def test_exact_max_lines_unchanged(self):
        """Test diff with exactly max_lines is unchanged."""
        lines = [f"line {i}" for i in range(5)]
        diff = "\n".join(lines)

        result = truncate_diff(diff, max_lines=5)

        assert result == diff

    def test_long_diff_truncated(self):
        """Test long diff is truncated with message."""
        lines = [f"line {i}" for i in range(10)]
        diff = "\n".join(lines)

        result = truncate_diff(diff, max_lines=5)

        # Should contain first 5 lines
        assert "line 0" in result
        assert "line 4" in result
        # Should not contain later lines
        assert "line 5" not in result
        assert "line 9" not in result
        # Should have truncation message
        assert "diff truncated" in result
        assert "total_lines=10" in result

    def test_truncate_preserves_line_count_message(self):
        """Test truncation message includes correct total line count."""
        lines = [f"line {i}" for i in range(100)]
        diff = "\n".join(lines)

        result = truncate_diff(diff, max_lines=20)

        assert "total_lines=100" in result

    def test_default_max_lines_is_200(self):
        """Test default max_lines parameter is 200."""
        lines = [f"line {i}" for i in range(250)]
        diff = "\n".join(lines)

        result = truncate_diff(diff)

        # Should truncate at 200
        assert "line 199" in result
        assert "line 200" not in result
        assert "total_lines=250" in result

    def test_empty_diff_unchanged(self):
        """Test empty diff is returned unchanged."""
        result = truncate_diff("")

        assert result == ""

    def test_single_line_diff_unchanged(self):
        """Test single line diff is unchanged."""
        diff = "single line"

        result = truncate_diff(diff, max_lines=5)

        assert result == diff

    def test_truncate_with_max_lines_1(self):
        """Test truncation with max_lines=1."""
        diff = "line 1\nline 2\nline 3"

        result = truncate_diff(diff, max_lines=1)

        assert "line 1" in result
        assert "line 2" not in result
        assert "diff truncated" in result

    def test_truncate_real_unified_diff(self):
        """Test truncation with realistic unified diff format."""
        diff = """diff --git a/file.py b/file.py
index 1234567..abcdefg 100644
--- a/file.py
+++ b/file.py
@@ -10,6 +10,7 @@ def function():
     line 1
     line 2
+    new line
     line 3
""" + "\n".join([f"     line {i}" for i in range(4, 100)])

        result = truncate_diff(diff, max_lines=10)

        assert "diff --git" in result
        assert "diff truncated" in result


class TestWrapDiffAsMarkdown:
    """Tests for wrap_diff_as_markdown function."""

    def test_wraps_simple_diff(self):
        """Test wraps diff in markdown code block."""
        diff = "- old line\n+ new line"

        result = wrap_diff_as_markdown(diff, max_lines=100)

        assert result.startswith("```diff\n")
        assert result.endswith("\n```")
        assert "- old line" in result
        assert "+ new line" in result

    def test_wraps_empty_diff(self):
        """Test wraps empty diff."""
        result = wrap_diff_as_markdown("", max_lines=100)

        assert result == "```diff\n\n```"

    def test_applies_truncation_before_wrapping(self):
        """Test applies truncation before wrapping in markdown."""
        lines = [f"line {i}" for i in range(10)]
        diff = "\n".join(lines)

        result = wrap_diff_as_markdown(diff, max_lines=5)

        assert "```diff\n" in result
        assert "line 0" in result
        assert "line 4" in result
        assert "line 9" not in result
        assert "diff truncated" in result
        assert result.endswith("\n```")

    def test_default_max_lines_is_200(self):
        """Test default max_lines parameter is 200."""
        lines = [f"line {i}" for i in range(250)]
        diff = "\n".join(lines)

        result = wrap_diff_as_markdown(diff)

        assert "line 199" in result
        assert "line 200" not in result
        assert "total_lines=250" in result

    def test_wraps_real_unified_diff(self):
        """Test wraps realistic unified diff."""
        diff = """diff --git a/main.py b/main.py
--- a/main.py
+++ b/main.py
@@ -1,3 +1,4 @@
 def main():
+    print("hello")
     pass
"""

        result = wrap_diff_as_markdown(diff, max_lines=100)

        assert result.startswith("```diff\n")
        assert "diff --git" in result
        assert "+    print" in result
        assert result.endswith("\n```")

    def test_markdown_format_for_github_pr(self):
        """Test output is suitable for GitHub PR comment."""
        diff = "+ added line\n- removed line"

        result = wrap_diff_as_markdown(diff)

        # Should be valid markdown diff block
        assert result.count("```diff") == 1
        assert result.count("```") == 2  # Opening and closing


class TestSummarizeDiffFiles:
    """Tests for summarize_diff_files function."""

    def test_extract_single_file(self):
        """Test extracts single changed file."""
        diff = """--- a/file.py
+++ b/file.py
@@ -1,1 +1,2 @@
 old line
+new line
"""

        result = summarize_diff_files(diff)

        assert result == ["b/file.py"]

    def test_extract_multiple_files(self):
        """Test extracts multiple changed files."""
        diff = """--- a/file1.py
+++ b/file1.py
@@ -1,1 +1,1 @@
-old
+new
--- a/file2.py
+++ b/file2.py
@@ -1,1 +1,1 @@
-old2
+new2
--- a/file3.py
+++ b/file3.py
"""

        result = summarize_diff_files(diff)

        assert result == ["b/file1.py", "b/file2.py", "b/file3.py"]

    def test_excludes_dev_null(self):
        """Test excludes /dev/null (deleted files)."""
        diff = """--- a/deleted.py
+++ /dev/null
@@ -1,1 +0,0 @@
-deleted content
--- a/modified.py
+++ b/modified.py
"""

        result = summarize_diff_files(diff)

        # Should only include modified.py, not /dev/null
        assert result == ["b/modified.py"]

    def test_removes_duplicate_files(self):
        """Test removes duplicate file paths."""
        diff = """--- a/file.py
+++ b/file.py
@@ -1,1 +1,1 @@
-old1
+new1
--- a/file.py
+++ b/file.py
@@ -10,1 +10,1 @@
-old2
+new2
"""

        result = summarize_diff_files(diff)

        # Should only appear once
        assert result == ["b/file.py"]

    def test_empty_diff_returns_empty_list(self):
        """Test empty diff returns empty list."""
        result = summarize_diff_files("")

        assert result == []

    def test_diff_without_plus_lines_returns_empty(self):
        """Test diff without +++ lines returns empty list."""
        diff = """Some random text
that doesn't contain
file markers
"""

        result = summarize_diff_files(diff)

        assert result == []

    def test_extracts_paths_with_spaces(self):
        """Test extracts file paths containing spaces."""
        diff = """--- a/path with spaces/file.py
+++ b/path with spaces/file.py
"""

        result = summarize_diff_files(diff)

        assert result == ["b/path with spaces/file.py"]

    def test_extracts_complex_paths(self):
        """Test extracts complex nested paths."""
        diff = """--- a/src/components/ui/Button/Button.tsx
+++ b/src/components/ui/Button/Button.tsx
--- a/tests/integration/test_button.py
+++ b/tests/integration/test_button.py
"""

        result = summarize_diff_files(diff)

        assert "b/src/components/ui/Button/Button.tsx" in result
        assert "b/tests/integration/test_button.py" in result

    def test_handles_git_diff_format(self):
        """Test handles standard git diff format."""
        diff = """diff --git a/main.py b/main.py
index abc123..def456 100644
--- a/main.py
+++ b/main.py
@@ -1,3 +1,4 @@
"""

        result = summarize_diff_files(diff)

        assert result == ["b/main.py"]

    def test_preserves_order_of_appearance(self):
        """Test preserves order of file appearance in diff."""
        diff = """--- a/first.py
+++ b/first.py
--- a/second.py
+++ b/second.py
--- a/third.py
+++ b/third.py
"""

        result = summarize_diff_files(diff)

        assert result == ["b/first.py", "b/second.py", "b/third.py"]

    def test_handles_new_file_creation(self):
        """Test handles new file creation (--- /dev/null)."""
        diff = """--- /dev/null
+++ b/new_file.py
@@ -0,0 +1,5 @@
+def new_function():
+    pass
"""

        result = summarize_diff_files(diff)

        assert result == ["b/new_file.py"]

    def test_multiple_dev_null_exclusions(self):
        """Test excludes multiple /dev/null entries."""
        diff = """--- a/deleted1.py
+++ /dev/null
--- a/kept.py
+++ b/kept.py
--- a/deleted2.py
+++ /dev/null
"""

        result = summarize_diff_files(diff)

        assert result == ["b/kept.py"]

    def test_real_world_git_diff(self):
        """Test with realistic git diff output."""
        diff = """diff --git a/src/nexuscore/core/retry_utils.py b/src/nexuscore/core/retry_utils.py
index 1234567..abcdefg 100644
--- a/src/nexuscore/core/retry_utils.py
+++ b/src/nexuscore/core/retry_utils.py
@@ -10,6 +10,7 @@ def retry():
     pass
diff --git a/tests/test_retry.py b/tests/test_retry.py
index 9876543..fedcba9 100644
--- a/tests/test_retry.py
+++ b/tests/test_retry.py
@@ -5,3 +5,4 @@ def test_retry():
     assert True
"""

        result = summarize_diff_files(diff)

        assert "b/src/nexuscore/core/retry_utils.py" in result
        assert "b/tests/test_retry.py" in result


class TestDiffPreviewIntegration:
    """Integration tests for diff preview utilities."""

    def test_truncate_and_wrap_integration(self):
        """Test truncation and wrapping work together."""
        lines = [f"line {i}" for i in range(20)]
        diff = "\n".join(lines)

        wrapped = wrap_diff_as_markdown(diff, max_lines=10)

        assert wrapped.startswith("```diff\n")
        assert "line 0" in wrapped
        assert "line 9" in wrapped
        assert "line 19" not in wrapped
        assert "diff truncated" in wrapped
        assert wrapped.endswith("\n```")

    def test_full_workflow_short_diff(self):
        """Test full workflow with short diff that doesn't need truncation."""
        diff = """--- a/main.py
+++ b/main.py
@@ -1,1 +1,2 @@
 print("hello")
+print("world")
"""

        # Extract files
        files = summarize_diff_files(diff)
        assert files == ["b/main.py"]

        # Wrap for PR comment
        markdown = wrap_diff_as_markdown(diff, max_lines=100)
        assert "```diff" in markdown
        assert '+print("world")' in markdown

    def test_full_workflow_long_diff(self):
        """Test full workflow with long diff requiring truncation."""
        header = """--- a/large.py
+++ b/large.py
@@ -1,100 +1,101 @@
"""
        lines = [f"+line {i}" for i in range(100)]
        diff = header + "\n".join(lines)

        # Extract files
        files = summarize_diff_files(diff)
        assert "b/large.py" in files

        # Truncate
        truncated = truncate_diff(diff, max_lines=20)
        assert "line 0" in truncated
        assert "line 99" not in truncated
        assert "diff truncated" in truncated

        # Wrap
        markdown = wrap_diff_as_markdown(diff, max_lines=20)
        assert "```diff" in markdown
        assert "diff truncated" in markdown
