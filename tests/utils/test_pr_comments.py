"""
test_pr_comments.py

PR コメント組み立てユーティリティのテスト。
"""

from __future__ import annotations

from nexuscore.utils.pr_comments import build_self_healing_pr_comment, summarize_patch


class TestSummarizePatch:
    """summarize_patch() のテスト"""

    def test_single_file_simple(self):
        """単一ファイルのシンプルなパッチ"""
        patch = """+++ b/src/example.py
@@ -0,0 +1,3 @@
+def hello():
+    return "world"
+
"""
        line_count, file_count = summarize_patch(patch)

        assert line_count == 3  # + で始まる3行
        assert file_count == 1  # 1ファイル

    def test_multiple_files(self):
        """複数ファイルのパッチ"""
        patch = """+++ b/src/file1.py
@@ -0,0 +1,2 @@
+content1
+content2
+++ b/src/file2.py
@@ -0,0 +1,1 @@
+content3
"""
        line_count, file_count = summarize_patch(patch)

        assert line_count == 3  # + で始まる3行
        assert file_count == 2  # 2ファイル

    def test_with_deletions(self):
        """削除行を含むパッチ"""
        patch = """+++ b/src/example.py
@@ -1,3 +1,2 @@
-old line
 new line
+another line
"""
        line_count, file_count = summarize_patch(patch)

        assert line_count == 2  # - と + で始まる2行
        assert file_count == 1

    def test_exclude_file_headers(self):
        """ファイルヘッダー（+++, ---）は除外"""
        patch = """+++ b/src/example.py
--- a/src/example.py
@@ -1,1 +1,1 @@
-old
+new
"""
        line_count, file_count = summarize_patch(patch)

        assert line_count == 2  # -old と +new のみ
        assert file_count == 1

    def test_empty_patch(self):
        """空のパッチ"""
        patch = ""
        line_count, file_count = summarize_patch(patch)

        assert line_count == 0
        assert file_count == 0


class TestBuildSelfHealingPrComment:
    """build_self_healing_pr_comment() のテスト"""

    def test_basic_comment(self):
        """基本的なコメント生成"""
        comment = build_self_healing_pr_comment(
            run_id="test-123",
            result_status="fixed",
            started_at="2025-11-28T01:23:45Z",
            finished_at="2025-11-28T01:23:48Z",
            duration_seconds=3.21,
            model_name="gpt-4.1-mini",
            patch_str="",
            success_rate_30=73.3,
            success_count_30=22,
            total_count_30=30,
        )

        assert "test-123" in comment
        assert "✅ FIXED" in comment
        assert "3.21s" in comment
        assert "gpt-4.1-mini" in comment
        assert "73.3%" in comment
        assert "22 / 30" in comment
        assert "| Item |" in comment  # テーブル形式

    def test_with_patch(self):
        """パッチを含むコメント"""
        patch = """+++ b/src/example.py
@@ -0,0 +1,2 @@
+def hello():
+    return "world"
"""
        comment = build_self_healing_pr_comment(
            run_id="test-456",
            result_status="fixed",
            started_at="2025-11-28T01:23:45Z",
            finished_at="2025-11-28T01:23:48Z",
            duration_seconds=3.21,
            model_name="gpt-4.1-mini",
            patch_str=patch,
            success_rate_30=73.3,
            success_count_30=22,
            total_count_30=30,
        )

        assert "2 lines / 1 files" in comment
        assert "<details>" in comment
        assert "Patch Preview" in comment
        assert "```diff" in comment

    def test_no_history(self):
        """履歴データがない場合"""
        comment = build_self_healing_pr_comment(
            run_id="test-789",
            result_status="not_fixed",
            started_at="2025-11-28T01:23:45Z",
            finished_at="2025-11-28T01:23:48Z",
            duration_seconds=3.21,
            model_name="claude-3.5-sonnet",
            patch_str="",
            success_rate_30=0.0,
            success_count_30=0,
            total_count_30=0,
        )

        assert "⚠️ NOT FIXED" in comment
        assert "N/A (insufficient data)" in comment

    def test_with_guardian_review(self):
        """Guardian レビューを含むコメント"""
        comment = build_self_healing_pr_comment(
            run_id="test-999",
            result_status="fixed",
            started_at="2025-11-28T01:23:45Z",
            finished_at="2025-11-28T01:23:48Z",
            duration_seconds=3.21,
            model_name="gpt-4.1-mini",
            patch_str="",
            success_rate_30=73.3,
            success_count_30=22,
            total_count_30=30,
            guardian_status="approve",
            guardian_comment="Looks good!",
        )

        assert "🔍 Guardian Review" in comment
        assert "approve" in comment
        assert "Looks good!" in comment

    def test_with_blocked_test_paths(self):
        """ブロックされたテストファイルを含むコメント"""
        comment = build_self_healing_pr_comment(
            run_id="test-blocked",
            result_status="blocked",
            started_at="2025-11-28T01:23:45Z",
            finished_at="2025-11-28T01:23:48Z",
            duration_seconds=3.21,
            model_name="gpt-4.1-mini",
            patch_str="",
            success_rate_30=73.3,
            success_count_30=22,
            total_count_30=30,
            blocked_test_paths=["tests/test_example.py", "tests/unit/test_foo.py"],
        )

        assert "🚫 Blocked Test Files" in comment
        assert "tests/test_example.py" in comment
        assert "tests/unit/test_foo.py" in comment
