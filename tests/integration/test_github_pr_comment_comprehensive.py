"""
GitHub PR コメント組み立ての包括的テスト

カバレッジ:
- _format_duration: 実行時間フォーマット
- _estimate_diff_lines: 変更行数推定
- _collect_run_metrics: メトリクス収集
- _compute_recent_success_rate: 成功率計算
- build_run_logs_url: Run ログURL構築
- build_project_logs_url: プロジェクトログURL構築
- build_project_dashboard_url: ダッシュボードURL構築
- load_run_markdown: Markdownレポート読み込み
- format_markdown_report_block: Markdownブロックフォーマット
- render_summary_card: サマリーカードレンダリング
- format_semantic_diff_block: Semantic Diffブロックフォーマット
- build_pr_comment: PRコメント組み立て

NOTE: format_diff_summary_block は source code に関数定義行が欠けているためスキップ
"""

from datetime import datetime
from unittest.mock import Mock, patch

import pytest

try:
    from nexuscore.integration.github_pr_comment import (
        PRCommentContext,
        _collect_run_metrics,
        _compute_recent_success_rate,
        _estimate_diff_lines,
        _format_duration,
        build_pr_comment,
        build_project_dashboard_url,
        build_project_logs_url,
        build_run_logs_url,
        format_markdown_report_block,
        format_semantic_diff_block,
        load_run_markdown,
        render_summary_card,
    )

    HAS_GITHUB_PR_COMMENT = True
except ImportError:
    HAS_GITHUB_PR_COMMENT = False
    _format_duration = None  # type: ignore
    _estimate_diff_lines = None  # type: ignore
    _collect_run_metrics = None  # type: ignore
    _compute_recent_success_rate = None  # type: ignore
    build_run_logs_url = None  # type: ignore
    build_project_logs_url = None  # type: ignore
    build_project_dashboard_url = None  # type: ignore
    load_run_markdown = None  # type: ignore
    format_markdown_report_block = None  # type: ignore
    render_summary_card = None  # type: ignore
    format_semantic_diff_block = None  # type: ignore
    build_pr_comment = None  # type: ignore
    PRCommentContext = None  # type: ignore


@pytest.mark.skipif(not HAS_GITHUB_PR_COMMENT, reason="github_pr_comment module not available")
class TestFormatDuration:
    """_format_duration() のテスト"""

    def test_format_duration_no_timestamps(self):
        """タイムスタンプがない場合は N/A"""
        run = Mock()
        run.started_at = None
        run.finished_at = None

        result = _format_duration(run)
        assert result == "N/A"

    def test_format_duration_seconds_only(self):
        """秒単位のフォーマット"""
        run = Mock()
        run.started_at = datetime(2025, 1, 1, 10, 0, 0)
        run.finished_at = datetime(2025, 1, 1, 10, 0, 45)

        result = _format_duration(run)
        assert result == "45s"

    def test_format_duration_minutes_seconds(self):
        """分秒フォーマット"""
        run = Mock()
        run.started_at = datetime(2025, 1, 1, 10, 0, 0)
        run.finished_at = datetime(2025, 1, 1, 10, 3, 25)

        result = _format_duration(run)
        assert result == "3m 25s"

    def test_format_duration_hours_minutes(self):
        """時分フォーマット"""
        run = Mock()
        run.started_at = datetime(2025, 1, 1, 10, 0, 0)
        run.finished_at = datetime(2025, 1, 1, 11, 45, 0)

        result = _format_duration(run)
        assert result == "1h 45m"


@pytest.mark.skipif(not HAS_GITHUB_PR_COMMENT, reason="github_pr_comment module not available")
class TestEstimateDiffLines:
    """_estimate_diff_lines() のテスト"""

    def test_estimate_diff_lines_empty(self):
        """空文字列は0行"""
        assert _estimate_diff_lines("") == 0

    def test_estimate_diff_lines_none(self):
        """None は0行"""
        assert _estimate_diff_lines(None) == 0

    def test_estimate_diff_lines_adds_only(self):
        """追加行のみ"""
        diff = "+line1\n+line2\n+line3"
        assert _estimate_diff_lines(diff) == 3

    def test_estimate_diff_lines_deletes_only(self):
        """削除行のみ"""
        diff = "-line1\n-line2"
        assert _estimate_diff_lines(diff) == 2

    def test_estimate_diff_lines_mixed(self):
        """追加と削除の混在"""
        diff = "+added\n-removed\n unchanged\n+another"
        assert _estimate_diff_lines(diff) == 3

    def test_estimate_diff_lines_excludes_headers(self):
        """ファイルヘッダーは除外"""
        diff = "--- a/file.py\n+++ b/file.py\n+line1\n-line2"
        assert _estimate_diff_lines(diff) == 2


@pytest.mark.skipif(not HAS_GITHUB_PR_COMMENT, reason="github_pr_comment module not available")
class TestCollectRunMetrics:
    """_collect_run_metrics() のテスト"""

    @pytest.fixture
    def enable_webapp(self):
        """HAS_WEBAPP を有効化"""
        with patch("nexuscore.integration.github_pr_comment.HAS_WEBAPP", True):
            yield

    def test_collect_run_metrics_without_webapp(self):
        """Webapp が利用できない場合"""
        with patch("nexuscore.integration.github_pr_comment.HAS_WEBAPP", False):
            result = _collect_run_metrics(Mock())

        assert result["duration_str"] == "N/A"
        assert result["patch_files_count"] == 0
        assert result["patch_lines"] == 0
        assert result["model_call_counts"] == {}
        assert result["estimated_cost_jpy"] == 0.0

    def test_collect_run_metrics_with_patches(self, enable_webapp):
        """パッチ情報を収集"""
        mock_run = Mock(id=1)

        mock_patch1 = Mock(file_path="file1.py", diff_text="+line1\n+line2")
        mock_patch2 = Mock(file_path="file2.py", diff_text="+line3\n-line4\n-line5")

        mock_query = Mock()
        mock_query.filter_by.return_value.all.return_value = [mock_patch1, mock_patch2]

        with patch("nexuscore.integration.github_pr_comment.PatchRecord") as mock_patch_cls:
            mock_patch_cls.query = mock_query

            with patch("nexuscore.integration.github_pr_comment.ExecutionLog") as mock_log_cls:
                mock_log_cls.query.filter_by.return_value.all.return_value = []

                result = _collect_run_metrics(mock_run)

        assert result["patch_files_count"] == 2
        assert result["patch_lines"] == 5  # 2 + 3


@pytest.mark.skipif(not HAS_GITHUB_PR_COMMENT, reason="github_pr_comment module not available")
class TestComputeRecentSuccessRate:
    """_compute_recent_success_rate() のテスト"""

    @pytest.fixture
    def enable_webapp(self):
        """HAS_WEBAPP を有効化"""
        with patch("nexuscore.integration.github_pr_comment.HAS_WEBAPP", True):
            yield

    def test_compute_recent_success_rate_without_webapp(self):
        """Webapp が利用できない場合は0.0"""
        with patch("nexuscore.integration.github_pr_comment.HAS_WEBAPP", False):
            result = _compute_recent_success_rate(1)

        assert result == 0.0

    def test_compute_recent_success_rate_all_success(self, enable_webapp):
        """全て成功の場合は1.0"""
        mock_runs = [Mock(status="SUCCESS") for _ in range(10)]

        mock_query = Mock()
        mock_query.filter.return_value.order_by.return_value.limit.return_value.all.return_value = (
            mock_runs
        )

        with patch("nexuscore.integration.github_pr_comment.Run") as mock_run:
            mock_run.query = mock_query
            mock_run.project_id = None  # Mock attribute

            result = _compute_recent_success_rate(1, limit=10)

        assert result == 1.0

    def test_compute_recent_success_rate_partial_success(self, enable_webapp):
        """部分的に成功の場合"""
        mock_runs = [
            Mock(status="SUCCESS"),
            Mock(status="FAILED"),
            Mock(status="SUCCESS"),
            Mock(status="SUCCESS"),
        ]

        mock_query = Mock()
        mock_query.filter.return_value.order_by.return_value.limit.return_value.all.return_value = (
            mock_runs
        )

        with patch("nexuscore.integration.github_pr_comment.Run") as mock_run:
            mock_run.query = mock_query
            mock_run.project_id = None

            result = _compute_recent_success_rate(1, limit=10)

        assert result == 0.75  # 3/4


@pytest.mark.skipif(not HAS_GITHUB_PR_COMMENT, reason="github_pr_comment module not available")
class TestBuildUrls:
    """URL構築関数のテスト"""

    def test_build_run_logs_url_with_run_id(self):
        """run_id 属性がある場合"""
        run = Mock(run_id="RUN-123")
        url = build_run_logs_url(1, run)

        assert "/logs/runs/RUN-123" in url

    def test_build_run_logs_url_with_id(self):
        """id 属性のみの場合"""
        run = Mock(spec=["id"])
        run.id = 456

        url = build_run_logs_url(1, run)

        assert "/logs/runs/456" in url

    def test_build_run_logs_url_no_id(self):
        """ID属性がない場合"""
        run = Mock(spec=[])

        url = build_run_logs_url(1, run)

        assert "/logs/runs/unknown" in url

    def test_build_project_logs_url(self):
        """プロジェクトログURLの構築"""
        url = build_project_logs_url(123)

        assert "/logs/projects/123" in url

    def test_build_project_dashboard_url(self):
        """ダッシュボードURLの構築"""
        url = build_project_dashboard_url(123)

        assert "/dashboard/projects/123" in url


@pytest.mark.skipif(not HAS_GITHUB_PR_COMMENT, reason="github_pr_comment module not available")
class TestLoadRunMarkdown:
    """load_run_markdown() のテスト"""

    def test_load_run_markdown_file_exists(self, tmp_path):
        """ファイルが存在する場合"""
        report_content = "# Run Report\n\nTest content"

        with patch("nexuscore.integration.github_pr_comment.get_markdown_report_path") as mock_path:
            mock_file = tmp_path / "RUN_test.md"
            mock_file.write_text(report_content, encoding="utf-8")
            mock_path.return_value = mock_file

            result = load_run_markdown("RUN-test")

        assert result == report_content

    def test_load_run_markdown_file_not_exists(self, tmp_path):
        """ファイルが存在しない場合"""
        with patch("nexuscore.integration.github_pr_comment.get_markdown_report_path") as mock_path:
            mock_file = tmp_path / "nonexistent.md"
            mock_path.return_value = mock_file

            result = load_run_markdown("RUN-test")

        assert result == ""

    def test_load_run_markdown_exception_handled(self):
        """例外が発生した場合"""
        with patch("nexuscore.integration.github_pr_comment.get_markdown_report_path") as mock_path:
            mock_path.side_effect = Exception("Import error")

            result = load_run_markdown("RUN-test")

        assert result == ""


@pytest.mark.skipif(not HAS_GITHUB_PR_COMMENT, reason="github_pr_comment module not available")
class TestFormatMarkdownReportBlock:
    """format_markdown_report_block() のテスト"""

    def test_format_markdown_report_block_with_content(self):
        """内容がある場合"""
        md_text = "# Test Report\n\nContent here"
        result = format_markdown_report_block(md_text)

        assert "<details>" in result
        assert "Run Report" in result
        assert "# Test Report" in result

    def test_format_markdown_report_block_empty(self):
        """空文字列の場合"""
        result = format_markdown_report_block("")
        assert result == ""

    def test_format_markdown_report_block_whitespace_only(self):
        """空白のみの場合"""
        result = format_markdown_report_block("   \n  \n  ")
        assert result == ""


@pytest.mark.skipif(not HAS_GITHUB_PR_COMMENT, reason="github_pr_comment module not available")
class TestRenderSummaryCard:
    """render_summary_card() のテスト"""

    def test_render_summary_card_basic(self):
        """基本的なメトリクスのレンダリング"""
        metrics = {
            "duration_str": "5m 30s",
            "patch_files_count": 3,
            "patch_lines": 120,
            "model_call_counts": {"gpt-5": 2},
            "estimated_cost_jpy": 45.6,
        }

        result = render_summary_card(metrics)

        assert "Self-Healing Summary" in result
        assert "Model" in result
        assert "Exec Time" in result
        assert "5m 30s" in result
        assert "Files Changed" in result
        assert "3" in result

    def test_render_summary_card_with_details(self):
        """details 付きのレンダリング"""
        metrics = {
            "duration_str": "N/A",
            "patch_files_count": 0,
            "patch_lines": 0,
            "model_call_counts": {},
            "estimated_cost_jpy": 0.0,
        }

        details = {
            "execution_ms": 5500,  # 5.5 seconds
            "retry_count": 2,
            "model": "gpt-5",
            "token_usage": "1000 tokens",
            "cost_usd": 0.015,
            "files_changed": 5,
            "last_error_class": "SyntaxError",
        }

        result = render_summary_card(metrics, details)

        assert "gpt-5" in result
        assert "5.5s" in result  # converted from ms
        assert "Retry | 2" in result
        assert "Files Changed | 5" in result
        assert "Token Usage | 1000 tokens" in result
        assert "$0.0150 USD" in result
        assert "Last Error | SyntaxError" in result


@pytest.mark.skipif(not HAS_GITHUB_PR_COMMENT, reason="github_pr_comment module not available")
class TestFormatSemanticDiffBlock:
    """format_semantic_diff_block() のテスト"""

    def test_format_semantic_diff_block_empty(self):
        """空の場合"""
        assert format_semantic_diff_block(None) == ""
        assert format_semantic_diff_block({}) == ""

    def test_format_semantic_diff_block_with_functions(self):
        """関数変更がある場合"""
        semantic_diffs = {
            "sample.py": {
                "functions": [
                    {
                        "name": "foo",
                        "kind": "added",
                        "signature_before": "",
                        "signature_after": "foo(x: int) -> int",
                    }
                ],
                "behavior_hints": [],
            }
        }

        result = format_semantic_diff_block(semantic_diffs)

        assert "Semantic Diff" in result
        assert "sample.py" in result
        assert "foo" in result
        assert "added" in result

    def test_format_semantic_diff_block_with_behavior_hints(self):
        """behavior hints がある場合"""
        semantic_diffs = {
            "module.py": {
                "functions": [],
                "behavior_hints": [
                    {
                        "description": "例外パスが追加されました",
                        "risk_level": "high",
                    },
                    {
                        "description": "return文が変更されました",
                        "risk_level": "low",
                    },
                ],
            }
        }

        result = format_semantic_diff_block(semantic_diffs)

        assert "例外パスが追加されました" in result
        assert "return文が変更されました" in result
        assert "🔴" in result  # high risk emoji
        assert "🟢" in result  # low risk emoji


@pytest.mark.skipif(not HAS_GITHUB_PR_COMMENT, reason="github_pr_comment module not available")
class TestBuildPrComment:
    """build_pr_comment() のテスト"""

    @pytest.fixture
    def enable_webapp(self):
        """HAS_WEBAPP を有効化"""
        with patch("nexuscore.integration.github_pr_comment.HAS_WEBAPP", True):
            yield

    def test_build_pr_comment_basic(self):
        """基本的なコメント組み立て"""
        ctx = PRCommentContext(
            guardian_review_markdown="## Review\n\nLooks good!",
        )

        result = build_pr_comment(ctx)

        assert "Guardian Review" in result
        assert "Looks good!" in result

    def test_build_pr_comment_with_change_summary(self):
        """変更サマリー付き"""
        ctx = PRCommentContext(
            guardian_review_markdown="Review content",
            change_summary="Fixed bug in login function",
        )

        result = build_pr_comment(ctx)

        assert "Change Summary" in result
        assert "Fixed bug in login function" in result

    def test_build_pr_comment_with_semantic_diffs(self):
        """Semantic Diff 付き"""
        ctx = PRCommentContext(
            guardian_review_markdown="Review",
            semantic_diffs={
                "test.py": {
                    "functions": [
                        {
                            "name": "test_func",
                            "kind": "modified",
                            "signature_before": "test_func()",
                            "signature_after": "test_func(x: int)",
                        }
                    ],
                    "behavior_hints": [],
                }
            },
        )

        result = build_pr_comment(ctx)

        assert "Semantic Diff" in result
        assert "test.py" in result
        assert "test_func" in result

    def test_build_pr_comment_with_markdown_report(self):
        """Markdown レポート付き"""
        ctx = PRCommentContext(
            guardian_review_markdown="Review",
            markdown_report="# Run Report\n\nDetails here",
        )

        result = build_pr_comment(ctx)

        assert "Run Report" in result
        assert "Details here" in result

    def test_build_pr_comment_with_run_and_project(self, enable_webapp):
        """Run と Project 付き（メトリクス収集あり）"""
        mock_project = Mock(id=1, name="TestProject")
        mock_run = Mock(id=1, run_id="RUN-123", status="SUCCESS")

        ctx = PRCommentContext(
            project=mock_project,
            run=mock_run,
            guardian_review_markdown="Review",
            repo_full_name="owner/repo",
        )

        with patch("nexuscore.integration.github_pr_comment._collect_run_metrics") as mock_metrics:
            with patch(
                "nexuscore.integration.github_pr_comment._compute_recent_success_rate"
            ) as mock_rate:
                mock_metrics.return_value = {
                    "duration_str": "2m 30s",
                    "patch_files_count": 1,
                    "patch_lines": 10,
                    "model_call_counts": {"gpt-5": 1},
                    "estimated_cost_jpy": 10.5,
                }
                mock_rate.return_value = 0.9

                result = build_pr_comment(ctx)

        assert "Self-Healing Summary" in result
        assert "TestProject" in result
        assert "RUN-123" in result
        assert "90.0%" in result  # success rate
        assert "Observability Links" in result


@pytest.mark.skipif(not HAS_GITHUB_PR_COMMENT, reason="github_pr_comment module not available")
class TestEdgeCases:
    """エッジケースのテスト"""

    def test_format_duration_without_webapp_attrs(self):
        """Webapp属性がないオブジェクト"""
        with patch("nexuscore.integration.github_pr_comment.HAS_WEBAPP", False):
            result = _format_duration(Mock())

        assert result == "N/A"

    def test_build_pr_comment_empty_context(self):
        """空のコンテキスト"""
        ctx = PRCommentContext()

        result = build_pr_comment(ctx)

        assert "Guardian Review" in result
        assert "(no review content)" in result

    def test_render_summary_card_execution_ms_formatting(self):
        """実行時間の異なるフォーマット"""
        metrics = {
            "duration_str": "N/A",
            "patch_files_count": 0,
            "patch_lines": 0,
            "model_call_counts": {},
            "estimated_cost_jpy": 0.0,
        }

        # ミリ秒 < 1000
        details = {"execution_ms": 500}
        result = render_summary_card(metrics, details)
        assert "500ms" in result

        # 秒 < 60
        details = {"execution_ms": 15000}
        result = render_summary_card(metrics, details)
        assert "15.0s" in result

        # 分 >= 60
        details = {"execution_ms": 120000}
        result = render_summary_card(metrics, details)
        assert "2.0m" in result
