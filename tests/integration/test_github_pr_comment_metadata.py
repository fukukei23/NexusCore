"""
CR-E3: Self-Healing PR コメント メタ情報ブロックのテスト
"""
from __future__ import annotations

import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch

from nexuscore.integration.github_pr_comment import (
    format_metadata_block,
    _collect_run_metrics,
    _estimate_diff_lines_separated,
    PRCommentContext,
    build_pr_comment,
)


class TestEstimateDiffLinesSeparated:
    """_estimate_diff_lines_separated() のテスト"""

    def test_empty_diff(self):
        """空の diff は 0, 0 を返す"""
        added, removed = _estimate_diff_lines_separated("")
        assert added == 0
        assert removed == 0

    def test_simple_additions(self):
        """追加行のみの diff"""
        diff = """--- a/file.py
+++ b/file.py
@@ -1,3 +1,5 @@
 line1
+line2
+line3
 line4
"""
        added, removed = _estimate_diff_lines_separated(diff)
        assert added == 2
        assert removed == 0

    def test_simple_deletions(self):
        """削除行のみの diff"""
        diff = """--- a/file.py
+++ b/file.py
@@ -1,5 +1,3 @@
 line1
-line2
-line3
 line4
"""
        added, removed = _estimate_diff_lines_separated(diff)
        assert added == 0
        assert removed == 2

    def test_mixed_changes(self):
        """追加と削除が混在する diff"""
        diff = """--- a/file.py
+++ b/file.py
@@ -1,3 +1,4 @@
 line1
-line2
+line2_new
+line2_extra
 line3
"""
        added, removed = _estimate_diff_lines_separated(diff)
        assert added == 2
        assert removed == 1


class TestFormatMetadataBlock:
    """format_metadata_block() のテスト"""

    def test_basic_metadata_block(self):
        """基本的なメタ情報ブロックの生成"""
        start_time = datetime(2025, 12, 10, 7, 11, 30)
        end_time = datetime(2025, 12, 10, 7, 11, 49)

        block = format_metadata_block(
            run_id="RUN-20251210-00123",
            pr_number=123,
            commit_sha="abc1234567890def",
            start_time=start_time,
            end_time=end_time,
            duration_seconds=19.7,
            primary_model="gpt-4.1",
            aux_models=["gpt-4.1-mini"],
            changed_files=3,
            added_lines=120,
            removed_lines=40,
            success_rate_last_n=0.867,
            recent_runs_window=30,
        )

        # 必須フィールドが含まれていることを確認
        assert "RUN-20251210-00123" in block
        assert "#123" in block
        assert "abc1234" in block  # 短縮形式
        assert "2025-12-10T07:11:30Z" in block
        assert "2025-12-10T07:11:49Z" in block
        assert "19.7s" in block
        assert "gpt-4.1" in block
        assert "gpt-4.1-mini" in block
        assert "Changed files: 3" in block
        assert "+120" in block
        assert "-40" in block
        assert "86.7%" in block

    def test_metadata_block_without_optional_fields(self):
        """オプショナルフィールドがない場合のメタ情報ブロック"""
        block = format_metadata_block(
            run_id="RUN-20251210-00123",
            pr_number=None,
            commit_sha=None,
            start_time=None,
            end_time=None,
            duration_seconds=0.0,
            primary_model="gpt-4.1",
            aux_models=[],
            changed_files=0,
            added_lines=0,
            removed_lines=0,
            success_rate_last_n=None,
            recent_runs_window=30,
        )

        assert "RUN-20251210-00123" in block
        assert "N/A" in block  # オプショナルフィールドが N/A になる
        assert "PR:" not in block  # pr_number が None の場合は表示されない
        assert "Commit:" not in block  # commit_sha が None の場合は表示されない

    def test_metadata_block_duration_formatting(self):
        """経過時間のフォーマットテスト"""
        # 秒単位
        block = format_metadata_block(
            run_id="RUN-001",
            pr_number=None,
            commit_sha=None,
            start_time=None,
            end_time=None,
            duration_seconds=45.5,
            primary_model="gpt-4.1",
            aux_models=[],
            changed_files=1,
            added_lines=10,
            removed_lines=5,
        )
        assert "45.5s" in block

        # 分単位
        block = format_metadata_block(
            run_id="RUN-001",
            pr_number=None,
            commit_sha=None,
            start_time=None,
            end_time=None,
            duration_seconds=125.0,
            primary_model="gpt-4.1",
            aux_models=[],
            changed_files=1,
            added_lines=10,
            removed_lines=5,
        )
        assert "2.1m" in block

        # 時間単位
        block = format_metadata_block(
            run_id="RUN-001",
            pr_number=None,
            commit_sha=None,
            start_time=None,
            end_time=None,
            duration_seconds=3660.0,
            primary_model="gpt-4.1",
            aux_models=[],
            changed_files=1,
            added_lines=10,
            removed_lines=5,
        )
        assert "1h" in block


class TestCollectRunMetrics:
    """_collect_run_metrics() の拡張テスト（CR-E3）"""

    def test_collect_run_metrics_includes_added_removed_lines(self):
        """追加行数と削除行数が含まれることを確認"""
        # モック Run オブジェクト
        mock_run = MagicMock()
        mock_run.id = 1
        mock_run.started_at = datetime(2025, 12, 10, 7, 11, 30)
        mock_run.finished_at = datetime(2025, 12, 10, 7, 11, 49)

        # モック PatchRecord
        mock_patch = MagicMock()
        mock_patch.file_path = "test.py"
        mock_patch.diff_text = """--- a/test.py
+++ b/test.py
@@ -1,3 +1,5 @@
 line1
+line2
+line3
-line4
 line5
"""

        # webapp モデルをモック
        with patch("nexuscore.integration.github_pr_comment.HAS_WEBAPP", True), \
             patch("nexuscore.integration.github_pr_comment.PatchRecord") as MockPatchRecord, \
             patch("nexuscore.integration.github_pr_comment.ExecutionLog") as MockExecutionLog:

            MockPatchRecord.query.filter_by.return_value.all.return_value = [mock_patch]
            MockExecutionLog.query.filter_by.return_value.all.return_value = []

            metrics = _collect_run_metrics(mock_run)

            assert "added_lines" in metrics
            assert "removed_lines" in metrics
            assert metrics["added_lines"] == 2
            assert metrics["removed_lines"] == 1
            assert metrics["start_time"] == mock_run.started_at
            assert metrics["end_time"] == mock_run.finished_at
            assert metrics["duration_seconds"] == 19.0


class TestBuildPrCommentWithMetadata:
    """build_pr_comment() にメタ情報ブロックが含まれることを確認するテスト"""

    def test_build_pr_comment_includes_metadata_block(self):
        """PR コメントにメタ情報ブロックが含まれる"""
        # モック Run と Project
        mock_run = MagicMock()
        mock_run.run_id = "RUN-20251210-00123"
        mock_run.status = "SUCCESS"
        mock_run.id = 1
        mock_run.started_at = datetime(2025, 12, 10, 7, 11, 30)
        mock_run.finished_at = datetime(2025, 12, 10, 7, 11, 49)
        mock_run.project_id = 1

        mock_project = MagicMock()
        mock_project.id = 1
        mock_project.name = "Test Project"

        ctx = PRCommentContext(
            project=mock_project,
            run=mock_run,
            guardian_review_markdown="Test review",
            repo_full_name="owner/repo",
            pr_number=123,
            commit_sha="abc1234567890def",
        )

        # webapp モデルをモック
        with patch("nexuscore.integration.github_pr_comment.HAS_WEBAPP", True), \
             patch("nexuscore.integration.github_pr_comment.PatchRecord") as MockPatchRecord, \
             patch("nexuscore.integration.github_pr_comment.ExecutionLog") as MockExecutionLog, \
             patch("nexuscore.integration.github_pr_comment.Run") as MockRun:

            MockPatchRecord.query.filter_by.return_value.all.return_value = []
            MockExecutionLog.query.filter_by.return_value.all.return_value = []
            MockRun.query.filter.return_value.order_by.return_value.limit.return_value.all.return_value = [mock_run]

            comment = build_pr_comment(ctx)

            # メタ情報ブロックが含まれていることを確認
            assert "Self-Healing Summary" in comment
            assert "RUN-20251210-00123" in comment
            assert "#123" in comment
            assert "abc1234" in comment  # 短縮形式
            # 既存のコンテンツも含まれていることを確認
            assert "Guardian Review" in comment

