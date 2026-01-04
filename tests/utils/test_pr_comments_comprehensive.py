"""
Comprehensive tests for pr_comments module.
Tests GitHub PR comment generation and patch summarization.
"""

import pytest
from nexuscore.utils.pr_comments import summarize_patch, build_self_healing_pr_comment


# ==============================================================================
# summarize_patch Tests
# ==============================================================================


class TestSummarizePatch:
    """Test summarize_patch function"""

    def test_summarize_patch_empty_string(self):
        """Empty patch returns zero counts"""
        patch_line_count, affected_files = summarize_patch("")
        assert patch_line_count == 0
        assert affected_files == 0

    def test_summarize_patch_single_file_addition(self):
        """Single file with additions"""
        patch = """+++ b/test.py
@@ -1,0 +1,3 @@
+line1
+line2
+line3"""
        patch_line_count, affected_files = summarize_patch(patch)
        assert patch_line_count == 3
        assert affected_files == 1

    def test_summarize_patch_single_file_deletion(self):
        """Single file with deletions"""
        patch = """--- a/test.py
+++ b/test.py
@@ -1,3 +1,0 @@
-line1
-line2
-line3"""
        patch_line_count, affected_files = summarize_patch(patch)
        assert patch_line_count == 3
        assert affected_files == 1

    def test_summarize_patch_mixed_additions_deletions(self):
        """Mixed additions and deletions"""
        patch = """+++ b/file.py
@@ -1,5 +1,5 @@
 context1
-old line
+new line
 context2"""
        patch_line_count, affected_files = summarize_patch(patch)
        assert patch_line_count == 2  # 1 deletion + 1 addition
        assert affected_files == 1

    def test_summarize_patch_multiple_files(self):
        """Multiple files in patch"""
        patch = """+++ b/file1.py
+line1
+++ b/file2.py
+line2
+++ b/file3.py
+line3"""
        patch_line_count, affected_files = summarize_patch(patch)
        assert patch_line_count == 3
        assert affected_files == 3

    def test_summarize_patch_ignores_file_headers(self):
        """Excludes +++ and --- file headers from line count"""
        patch = """--- a/file.py
+++ b/file.py
@@ -1,2 +1,3 @@
 context
+added line"""
        patch_line_count, affected_files = summarize_patch(patch)
        assert patch_line_count == 1  # Only +added line
        assert affected_files == 1

    def test_summarize_patch_with_context_lines(self):
        """Context lines (no prefix) are not counted"""
        patch = """+++ b/file.py
@@ -1,5 +1,5 @@
 context1
 context2
+added
-removed
 context3"""
        patch_line_count, affected_files = summarize_patch(patch)
        assert patch_line_count == 2  # +added, -removed
        assert affected_files == 1

    def test_summarize_patch_file_path_extraction(self):
        """Extracts file paths correctly"""
        patch = """+++ b/path/to/file.py
+line1"""
        patch_line_count, affected_files = summarize_patch(patch)
        assert affected_files == 1

    def test_summarize_patch_duplicate_file_paths(self):
        """Deduplicates file paths"""
        patch = """+++ b/file.py
+line1
+++ b/file.py
+line2"""
        patch_line_count, affected_files = summarize_patch(patch)
        assert patch_line_count == 2
        assert affected_files == 1  # Same file mentioned twice

    def test_summarize_patch_empty_file_path(self):
        """Handles empty file path"""
        patch = """+++ b/
+line1"""
        patch_line_count, affected_files = summarize_patch(patch)
        assert patch_line_count == 1
        assert affected_files == 0  # Empty path not counted

    def test_summarize_patch_with_hunk_headers(self):
        """Hunk headers @@ are not counted as patch lines"""
        patch = """+++ b/file.py
@@ -1,3 +1,4 @@
 context
+added
-removed"""
        patch_line_count, affected_files = summarize_patch(patch)
        assert patch_line_count == 2
        assert affected_files == 1


# ==============================================================================
# build_self_healing_pr_comment Tests
# ==============================================================================


class TestBuildSelfHealingPRComment:
    """Test build_self_healing_pr_comment function"""

    def test_build_pr_comment_minimal(self):
        """Build comment with minimal required fields"""
        comment = build_self_healing_pr_comment(
            run_id="test-123",
            result_status="fixed",
            started_at="2024-01-01T10:00:00Z",
            finished_at="2024-01-01T10:01:00Z",
            duration_seconds=60.0,
            model_name="gpt-4",
        )
        
        assert "test-123" in comment
        assert "✅" in comment  # fixed emoji
        assert "60.00s" in comment
        assert "gpt-4" in comment

    def test_build_pr_comment_contains_header(self):
        """Comment contains NexusCore header"""
        comment = build_self_healing_pr_comment(
            run_id="test",
            result_status="fixed",
            started_at="2024-01-01T10:00:00Z",
            finished_at="2024-01-01T10:00:01Z",
            duration_seconds=1.0,
            model_name="test-model",
        )
        
        assert "NexusCore Self-Healing Report" in comment

    def test_build_pr_comment_status_fixed(self):
        """Status 'fixed' shows correct emoji and text"""
        comment = build_self_healing_pr_comment(
            run_id="test",
            result_status="fixed",
            started_at="2024-01-01T10:00:00Z",
            finished_at="2024-01-01T10:00:01Z",
            duration_seconds=1.0,
            model_name="test-model",
        )
        
        assert "✅" in comment
        assert "FIXED" in comment

    def test_build_pr_comment_status_not_fixed(self):
        """Status 'not_fixed' shows correct emoji"""
        comment = build_self_healing_pr_comment(
            run_id="test",
            result_status="not_fixed",
            started_at="2024-01-01T10:00:00Z",
            finished_at="2024-01-01T10:00:01Z",
            duration_seconds=1.0,
            model_name="test-model",
        )
        
        assert "⚠️" in comment
        assert "NOT FIXED" in comment

    def test_build_pr_comment_status_no_issues(self):
        """Status 'no_issues' shows correct emoji"""
        comment = build_self_healing_pr_comment(
            run_id="test",
            result_status="no_issues",
            started_at="2024-01-01T10:00:00Z",
            finished_at="2024-01-01T10:00:01Z",
            duration_seconds=1.0,
            model_name="test-model",
        )
        
        assert "ℹ️" in comment
        assert "NO ISSUES" in comment

    def test_build_pr_comment_status_blocked(self):
        """Status 'blocked' shows correct emoji"""
        comment = build_self_healing_pr_comment(
            run_id="test",
            result_status="blocked",
            started_at="2024-01-01T10:00:00Z",
            finished_at="2024-01-01T10:00:01Z",
            duration_seconds=1.0,
            model_name="test-model",
        )
        
        assert "🚫" in comment
        assert "BLOCKED" in comment

    def test_build_pr_comment_status_error(self):
        """Status 'error' shows correct emoji"""
        comment = build_self_healing_pr_comment(
            run_id="test",
            result_status="error",
            started_at="2024-01-01T10:00:00Z",
            finished_at="2024-01-01T10:00:01Z",
            duration_seconds=1.0,
            model_name="test-model",
        )
        
        assert "❌" in comment
        assert "ERROR" in comment

    def test_build_pr_comment_unknown_status(self):
        """Unknown status shows question mark emoji"""
        comment = build_self_healing_pr_comment(
            run_id="test",
            result_status="unknown_status",
            started_at="2024-01-01T10:00:00Z",
            finished_at="2024-01-01T10:00:01Z",
            duration_seconds=1.0,
            model_name="test-model",
        )
        
        assert "❓" in comment

    def test_build_pr_comment_with_patch(self):
        """Include patch information when provided"""
        patch = """+++ b/file.py
+line1
+line2"""
        
        comment = build_self_healing_pr_comment(
            run_id="test",
            result_status="fixed",
            started_at="2024-01-01T10:00:00Z",
            finished_at="2024-01-01T10:00:01Z",
            duration_seconds=1.0,
            model_name="test-model",
            patch_str=patch,
        )
        
        assert "2 lines / 1 files" in comment
        assert "Patch Preview" in comment
        assert "+line1" in comment

    def test_build_pr_comment_without_patch(self):
        """Shows N/A when no patch provided"""
        comment = build_self_healing_pr_comment(
            run_id="test",
            result_status="fixed",
            started_at="2024-01-01T10:00:00Z",
            finished_at="2024-01-01T10:00:01Z",
            duration_seconds=1.0,
            model_name="test-model",
            patch_str="",
        )
        
        assert "N/A" in comment

    def test_build_pr_comment_with_success_rate(self):
        """Include success rate statistics"""
        comment = build_self_healing_pr_comment(
            run_id="test",
            result_status="fixed",
            started_at="2024-01-01T10:00:00Z",
            finished_at="2024-01-01T10:00:01Z",
            duration_seconds=1.0,
            model_name="test-model",
            success_rate_30=85.5,
            success_count_30=25,
            total_count_30=30,
        )
        
        assert "85.5%" in comment
        assert "25 / 30" in comment

    def test_build_pr_comment_without_success_rate(self):
        """Shows N/A when insufficient data"""
        comment = build_self_healing_pr_comment(
            run_id="test",
            result_status="fixed",
            started_at="2024-01-01T10:00:00Z",
            finished_at="2024-01-01T10:00:01Z",
            duration_seconds=1.0,
            model_name="test-model",
            total_count_30=0,
        )
        
        assert "N/A (insufficient data)" in comment

    def test_build_pr_comment_with_summary(self):
        """Include summary when provided"""
        comment = build_self_healing_pr_comment(
            run_id="test",
            result_status="fixed",
            started_at="2024-01-01T10:00:00Z",
            finished_at="2024-01-01T10:00:01Z",
            duration_seconds=1.0,
            model_name="test-model",
            summary="Fixed 3 test failures by updating assertions",
        )
        
        assert "Summary" in comment
        assert "Fixed 3 test failures" in comment

    def test_build_pr_comment_with_guardian_review(self):
        """Include Guardian review when provided"""
        comment = build_self_healing_pr_comment(
            run_id="test",
            result_status="fixed",
            started_at="2024-01-01T10:00:00Z",
            finished_at="2024-01-01T10:00:01Z",
            duration_seconds=1.0,
            model_name="test-model",
            guardian_status="APPROVED",
            guardian_comment="Changes look good",
        )
        
        assert "Guardian Review" in comment
        assert "APPROVED" in comment
        assert "Changes look good" in comment

    def test_build_pr_comment_with_blocked_tests(self):
        """Include blocked test paths when provided"""
        blocked = ["tests/test_critical.py", "tests/test_security.py"]
        
        comment = build_self_healing_pr_comment(
            run_id="test",
            result_status="blocked",
            started_at="2024-01-01T10:00:00Z",
            finished_at="2024-01-01T10:00:01Z",
            duration_seconds=1.0,
            model_name="test-model",
            blocked_test_paths=blocked,
        )
        
        assert "Blocked Test Files" in comment
        assert "test_critical.py" in comment
        assert "test_security.py" in comment

    def test_build_pr_comment_with_long_patch(self):
        """Truncate very long patches"""
        long_patch = "\n".join([f"+line{i}" for i in range(1500)])
        long_patch = "+++ b/file.py\n" + long_patch
        
        comment = build_self_healing_pr_comment(
            run_id="test",
            result_status="fixed",
            started_at="2024-01-01T10:00:00Z",
            finished_at="2024-01-01T10:00:01Z",
            duration_seconds=1.0,
            model_name="test-model",
            patch_str=long_patch,
        )
        
        assert "truncated" in comment.lower()
        assert "1501 total lines" in comment

    def test_build_pr_comment_duration_formatting(self):
        """Duration formatted with 2 decimal places"""
        comment = build_self_healing_pr_comment(
            run_id="test",
            result_status="fixed",
            started_at="2024-01-01T10:00:00Z",
            finished_at="2024-01-01T10:01:23Z",
            duration_seconds=83.456,
            model_name="test-model",
        )
        
        assert "83.46s" in comment

    def test_build_pr_comment_is_markdown(self):
        """Comment is valid Markdown"""
        comment = build_self_healing_pr_comment(
            run_id="test",
            result_status="fixed",
            started_at="2024-01-01T10:00:00Z",
            finished_at="2024-01-01T10:00:01Z",
            duration_seconds=1.0,
            model_name="test-model",
        )
        
        # Check for Markdown table syntax
        assert "|" in comment
        assert "---|" in comment
        # Check for heading
        assert "###" in comment


# ==============================================================================
# Integration Tests
# ==============================================================================


class TestPRCommentsIntegration:
    """Integration tests for pr_comments module"""

    def test_full_pr_comment_with_all_fields(self):
        """Generate complete PR comment with all optional fields"""
        patch = """+++ b/src/main.py
@@ -1,3 +1,4 @@
 def main():
-    print("old")
+    print("new")
+    return 0"""
        
        comment = build_self_healing_pr_comment(
            run_id="run-abc123",
            result_status="fixed",
            started_at="2024-01-01T10:00:00Z",
            finished_at="2024-01-01T10:05:30Z",
            duration_seconds=330.0,
            model_name="gpt-4-turbo",
            patch_str=patch,
            success_rate_30=90.0,
            success_count_30=27,
            total_count_30=30,
            summary="Fixed test failures in main module",
            guardian_status="APPROVED",
            guardian_comment="All changes are safe",
            blocked_test_paths=["tests/test_blocked.py"],
        )
        
        # Verify all sections are present
        assert "run-abc123" in comment
        assert "✅" in comment
        assert "330.00s" in comment
        assert "gpt-4-turbo" in comment
        assert "3 lines / 1 files" in comment
        assert "90.0%" in comment
        assert "Fixed test failures" in comment
        assert "APPROVED" in comment
        assert "test_blocked.py" in comment
        assert "Patch Preview" in comment

    def test_summarize_and_build_integration(self):
        """Use summarize_patch result in build_self_healing_pr_comment"""
        patch = """+++ b/file1.py
+line1
+line2
+++ b/file2.py
-removed"""
        
        patch_line_count, affected_files = summarize_patch(patch)
        
        comment = build_self_healing_pr_comment(
            run_id="test",
            result_status="fixed",
            started_at="2024-01-01T10:00:00Z",
            finished_at="2024-01-01T10:00:01Z",
            duration_seconds=1.0,
            model_name="test-model",
            patch_str=patch,
        )
        
        # Verify summarize_patch results appear in comment
        assert f"{patch_line_count} lines" in comment
        assert f"{affected_files} files" in comment
