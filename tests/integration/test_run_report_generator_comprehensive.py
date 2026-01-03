"""
Run レポート生成の包括的テスト

カバレッジ:
- _format_duration: 実行時間フォーマット
- _estimate_diff_lines: 変更行数推定
- _collect_run_metrics: メトリクス収集
- _compute_recent_success_rate: 成功率計算
- _collect_test_results: テスト結果収集
- generate_run_report_markdown: Markdown生成
- write_run_report_file: ファイル書き出し
- get_markdown_report_path: パス生成
"""

import json
import pytest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from collections import defaultdict

from nexuscore.integration.run_report_generator import (
    _format_duration,
    _estimate_diff_lines,
    _collect_run_metrics,
    _compute_recent_success_rate,
    _collect_test_results,
    generate_run_report_markdown,
    write_run_report_file,
    get_markdown_report_path,
)


class TestFormatDuration:
    """_format_duration() のテスト"""

    def test_format_duration_no_timestamps(self):
        """タイムスタンプがない場合は N/A"""
        run = Mock()
        run.started_at = None
        run.finished_at = None

        result = _format_duration(run)
        assert result == "N/A"

    def test_format_duration_only_started(self):
        """開始時刻のみの場合は N/A"""
        run = Mock()
        run.started_at = datetime(2025, 1, 1, 10, 0, 0)
        run.finished_at = None

        result = _format_duration(run)
        assert result == "N/A"

    def test_format_duration_seconds_only(self):
        """秒単位のフォーマット（< 60秒）"""
        run = Mock()
        run.started_at = datetime(2025, 1, 1, 10, 0, 0)
        run.finished_at = datetime(2025, 1, 1, 10, 0, 30)

        result = _format_duration(run)
        assert result == "30s"

    def test_format_duration_minutes_seconds(self):
        """分秒フォーマット（< 3600秒）"""
        run = Mock()
        run.started_at = datetime(2025, 1, 1, 10, 0, 0)
        run.finished_at = datetime(2025, 1, 1, 10, 5, 30)

        result = _format_duration(run)
        assert result == "5m 30s"

    def test_format_duration_hours_minutes(self):
        """時分フォーマット（>= 3600秒）"""
        run = Mock()
        run.started_at = datetime(2025, 1, 1, 10, 0, 0)
        run.finished_at = datetime(2025, 1, 1, 12, 35, 0)

        result = _format_duration(run)
        assert result == "2h 35m"

    def test_format_duration_zero_seconds(self):
        """0秒の場合"""
        run = Mock()
        run.started_at = datetime(2025, 1, 1, 10, 0, 0)
        run.finished_at = datetime(2025, 1, 1, 10, 0, 0)

        result = _format_duration(run)
        assert result == "0s"


class TestEstimateDiffLines:
    """_estimate_diff_lines() のテスト"""

    def test_estimate_diff_lines_empty(self):
        """空文字列は0行"""
        assert _estimate_diff_lines("") == 0

    def test_estimate_diff_lines_none(self):
        """None は0行"""
        assert _estimate_diff_lines(None) == 0

    def test_estimate_diff_lines_simple_add(self):
        """単純な追加行"""
        diff = "+line1\n+line2\n+line3"
        assert _estimate_diff_lines(diff) == 3

    def test_estimate_diff_lines_simple_delete(self):
        """単純な削除行"""
        diff = "-line1\n-line2"
        assert _estimate_diff_lines(diff) == 2

    def test_estimate_diff_lines_mixed(self):
        """追加と削除の混在"""
        diff = "+added\n-removed\n unchanged\n+another"
        assert _estimate_diff_lines(diff) == 3  # +added, -removed, +another

    def test_estimate_diff_lines_excludes_file_headers(self):
        """ファイルヘッダー行（+++/---）は除外"""
        diff = "--- a/file.py\n+++ b/file.py\n+line1\n-line2"
        assert _estimate_diff_lines(diff) == 2  # ヘッダーは除外

    def test_estimate_diff_lines_context_lines_excluded(self):
        """コンテキスト行は除外"""
        diff = " context1\n+added\n context2\n-removed"
        assert _estimate_diff_lines(diff) == 2


class TestCollectRunMetrics:
    """_collect_run_metrics() のテスト"""

    @pytest.fixture
    def enable_webapp(self):
        """HAS_WEBAPP を有効化"""
        with patch("nexuscore.integration.run_report_generator.HAS_WEBAPP", True):
            yield

    def test_collect_run_metrics_without_webapp(self):
        """Webapp が利用できない場合のフォールバック"""
        # github_pr_comment からのインポートを失敗させる
        with patch("nexuscore.integration.run_report_generator.HAS_WEBAPP", False):
            with patch.dict("sys.modules", {"nexuscore.integration.github_pr_comment": None}):
                result = _collect_run_metrics(Mock())

        assert result["duration_str"] == "N/A"
        assert result["patch_files_count"] == 0
        assert result["patch_lines"] == 0
        assert result["model_call_counts"] == {}
        assert result["estimated_cost_jpy"] == 0.0

    # NOTE: github_pr_comment への委譲テストは削除
    # （別モジュールへの委譲は統合テストで検証される）


class TestComputeRecentSuccessRate:
    """_compute_recent_success_rate() のテスト"""

    @pytest.fixture
    def enable_webapp(self):
        """HAS_WEBAPP を有効化"""
        with patch("nexuscore.integration.run_report_generator.HAS_WEBAPP", True):
            yield

    def test_compute_recent_success_rate_without_webapp(self):
        """Webapp が利用できない場合は0.0"""
        with patch("nexuscore.integration.run_report_generator.HAS_WEBAPP", False):
            result = _compute_recent_success_rate(1)

        assert result == 0.0

    # NOTE: github_pr_comment への委譲テストは削除
    # （別モジュールへの委譲は統合テストで検証される）


class TestCollectTestResults:
    """_collect_test_results() のテスト"""

    @pytest.fixture
    def enable_webapp(self):
        """HAS_WEBAPP を有効化"""
        with patch("nexuscore.integration.run_report_generator.HAS_WEBAPP", True):
            yield

    def test_collect_test_results_without_webapp(self):
        """Webapp が利用できない場合のフォールバック"""
        with patch("nexuscore.integration.run_report_generator.HAS_WEBAPP", False):
            result = _collect_test_results(Mock())

        assert result["error_count"] == 0
        assert result["warning_count"] == 0
        assert result["info_count"] == 0
        assert result["test_output"] == ""

    def test_collect_test_results_with_logs(self, enable_webapp):
        """ログからテスト結果を収集"""
        mock_run = Mock(id=1)

        # ログを作成
        log1 = Mock(level="ERROR", source="SANDBOX", message="Test failed")
        log2 = Mock(level="WARNING", source="ORCHESTRATOR", message="Flaky test")
        log3 = Mock(level="INFO", source="NPE", message="LLM call")

        mock_query = Mock()
        mock_query.filter_by.return_value.all.return_value = [log1, log2, log3]

        with patch("nexuscore.integration.run_report_generator.ExecutionLog") as mock_log:
            mock_log.query = mock_query

            result = _collect_test_results(mock_run)

        assert result["error_count"] == 1
        assert result["warning_count"] == 1
        assert result["info_count"] == 1
        assert "[ERROR] Test failed" in result["test_output"]
        assert "[WARNING] Flaky test" in result["test_output"]

    def test_collect_test_results_truncates_output(self, enable_webapp):
        """テスト出力は最大20件まで"""
        mock_run = Mock(id=1)

        # 30件のログを作成
        logs = [
            Mock(level="ERROR", source="SANDBOX", message=f"Error {i}")
            for i in range(30)
        ]

        mock_query = Mock()
        mock_query.filter_by.return_value.all.return_value = logs

        with patch("nexuscore.integration.run_report_generator.ExecutionLog") as mock_log:
            mock_log.query = mock_query

            result = _collect_test_results(mock_run)

        # 最大20件のみ含まれる
        lines = result["test_output"].split("\n")
        assert len(lines) <= 20


class TestGenerateRunReportMarkdown:
    """generate_run_report_markdown() のテスト"""

    @pytest.fixture
    def enable_webapp(self):
        """HAS_WEBAPP を有効化"""
        with patch("nexuscore.integration.run_report_generator.HAS_WEBAPP", True):
            yield

    def test_generate_run_report_markdown_without_webapp(self):
        """Webapp が利用できない場合"""
        with patch("nexuscore.integration.run_report_generator.HAS_WEBAPP", False):
            result = generate_run_report_markdown(1)

        assert "# Run Report" in result
        assert "Webapp models not available" in result

    def test_generate_run_report_markdown_run_not_found(self, enable_webapp):
        """Run が見つからない場合"""
        mock_query = Mock()
        mock_query.get.return_value = None

        with patch("nexuscore.integration.run_report_generator.Run") as mock_run:
            mock_run.query = mock_query

            result = generate_run_report_markdown(999)

        assert "# Run Report" in result
        assert "Run not found: ID=999" in result

    def test_generate_run_report_markdown_project_not_found(self, enable_webapp):
        """Project が見つからない場合"""
        mock_run = Mock(id=1, run_id="RUN-123", project=None)

        mock_query = Mock()
        mock_query.get.return_value = mock_run

        with patch("nexuscore.integration.run_report_generator.Run") as mock_run_cls:
            mock_run_cls.query = mock_query

            result = generate_run_report_markdown(1)

        assert "# Run Report" in result
        assert "Project not found for Run ID=1" in result

    def test_generate_run_report_markdown_success(self, enable_webapp):
        """正常にレポートを生成"""
        # モックの作成
        mock_project = Mock(
            id=1,
            name="TestProject",
            repo_url="https://github.com/test/repo",
            local_path="/path/to/project"
        )

        mock_run = Mock(
            id=1,
            run_id="RUN-123",
            status="SUCCESS",
            started_at=datetime(2025, 1, 1, 10, 0, 0),
            finished_at=datetime(2025, 1, 1, 10, 5, 30),
            autonomy_level=2,
            project=mock_project
        )

        mock_query = Mock()
        mock_query.get.return_value = mock_run

        mock_metrics = {
            "duration_str": "5m 30s",
            "patch_files_count": 3,
            "patch_lines": 120,
            "model_call_counts": {"gpt-5": 2, "gpt-5-mini": 1},
            "estimated_cost_jpy": 45.6,
        }

        mock_test_results = {
            "error_count": 0,
            "warning_count": 1,
            "info_count": 5,
            "test_output": "[WARNING] Flaky test",
        }

        mock_patch = Mock(file_path="src/main.py", applied=True)
        mock_patch_query = Mock()
        mock_patch_query.filter_by.return_value.all.return_value = [mock_patch]

        with patch("nexuscore.integration.run_report_generator.Run") as mock_run_cls:
            with patch("nexuscore.integration.run_report_generator._collect_run_metrics", return_value=mock_metrics):
                with patch("nexuscore.integration.run_report_generator._collect_test_results", return_value=mock_test_results):
                    with patch("nexuscore.integration.run_report_generator._compute_recent_success_rate", return_value=0.85):
                        with patch("nexuscore.integration.run_report_generator.PatchRecord") as mock_patch_cls:
                            mock_run_cls.query = mock_query
                            mock_patch_cls.query = mock_patch_query

                            result = generate_run_report_markdown(1)

        # レポート内容の検証
        assert "# Run Report: RUN-123" in result
        assert "TestProject" in result
        assert "SUCCESS" in result
        assert "5m 30s" in result
        assert "3 files, 120 lines changed" in result
        assert "`gpt-5`: 2 calls" in result
        assert "45.60 JPY" in result
        assert "85.0%" in result  # success rate
        assert "`src/main.py` (applied)" in result


class TestWriteRunReportFile:
    """write_run_report_file() のテスト"""

    @pytest.fixture
    def enable_webapp(self):
        """HAS_WEBAPP を有効化"""
        with patch("nexuscore.integration.run_report_generator.HAS_WEBAPP", True):
            yield

    def test_write_run_report_file_without_webapp(self):
        """Webapp が利用できない場合はエラー"""
        with patch("nexuscore.integration.run_report_generator.HAS_WEBAPP", False):
            with pytest.raises(RuntimeError, match="Webapp models not available"):
                write_run_report_file(1)

    def test_write_run_report_file_run_not_found(self, enable_webapp):
        """Run が見つからない場合はエラー"""
        mock_query = Mock()
        mock_query.get.return_value = None

        with patch("nexuscore.integration.run_report_generator.Run") as mock_run:
            mock_run.query = mock_query

            with pytest.raises(ValueError, match="Run not found: ID=999"):
                write_run_report_file(999)

    def test_write_run_report_file_success(self, enable_webapp, tmp_path):
        """正常にファイルを書き出し"""
        mock_run = Mock(id=1, run_id="RUN-123")

        mock_query = Mock()
        mock_query.get.return_value = mock_run

        mock_markdown = "# Run Report: RUN-123\n\nTest content"

        with patch("nexuscore.integration.run_report_generator.Run") as mock_run_cls:
            with patch("nexuscore.integration.run_report_generator.generate_run_report_markdown", return_value=mock_markdown):
                mock_run_cls.query = mock_query

                result = write_run_report_file(1, base_dir=tmp_path)

        # ファイルパスの検証
        expected_path = tmp_path / "docs" / "run_reports" / "RUN_RUN-123.md"
        assert result == expected_path
        assert result.exists()

        # ファイル内容の検証
        content = result.read_text(encoding="utf-8")
        assert content == mock_markdown

    def test_write_run_report_file_default_base_dir(self, enable_webapp):
        """base_dir が None の場合はプロジェクトルートを使用"""
        mock_run = Mock(id=1, run_id="RUN-123")

        mock_query = Mock()
        mock_query.get.return_value = mock_run

        mock_markdown = "# Run Report"

        with patch("nexuscore.integration.run_report_generator.Run") as mock_run_cls:
            with patch("nexuscore.integration.run_report_generator.generate_run_report_markdown", return_value=mock_markdown):
                with patch("pathlib.Path.write_text") as mock_write:
                    mock_run_cls.query = mock_query

                    result = write_run_report_file(1)

        # write_text が呼ばれたことを確認
        mock_write.assert_called_once_with(mock_markdown, encoding="utf-8")


class TestGetMarkdownReportPath:
    """get_markdown_report_path() のテスト"""

    def test_get_markdown_report_path_with_base_dir(self, tmp_path):
        """base_dir を指定した場合"""
        result = get_markdown_report_path("RUN-123", base_dir=tmp_path)

        expected = tmp_path / "docs" / "run_reports" / "RUN_RUN-123.md"
        assert result == expected

    def test_get_markdown_report_path_default_base_dir(self):
        """base_dir が None の場合はプロジェクトルートを使用"""
        result = get_markdown_report_path("RUN-456")

        # パスにプロジェクト構造が含まれることを確認
        assert "docs" in str(result)
        assert "run_reports" in str(result)
        assert result.name == "RUN_RUN-456.md"

    def test_get_markdown_report_path_file_does_not_need_to_exist(self, tmp_path):
        """ファイルが存在しなくてもパスを返す"""
        result = get_markdown_report_path("RUN-NONEXISTENT", base_dir=tmp_path)

        # ファイルは存在しないがパスは返る
        assert not result.exists()
        assert result.name == "RUN_RUN-NONEXISTENT.md"


class TestEdgeCases:
    """エッジケースのテスト"""

    def test_format_duration_very_long_duration(self):
        """非常に長い実行時間（数日）"""
        run = Mock()
        run.started_at = datetime(2025, 1, 1, 0, 0, 0)
        run.finished_at = datetime(2025, 1, 3, 5, 30, 0)  # 2日5時間30分

        result = _format_duration(run)
        # 時間フォーマットが使われる
        assert "53h 30m" in result

    def test_estimate_diff_lines_unicode(self):
        """Unicode 文字を含む diff"""
        diff = "+日本語の行\n-English line\n+中文行"
        assert _estimate_diff_lines(diff) == 3

    def test_generate_run_report_markdown_handles_exception(self):
        """例外が発生した場合のエラーハンドリング"""
        with patch("nexuscore.integration.run_report_generator.HAS_WEBAPP", True):
            with patch("nexuscore.integration.run_report_generator.Run") as mock_run:
                mock_run.query.get.side_effect = Exception("Database error")

                result = generate_run_report_markdown(1)

        assert "# Run Report" in result
        assert "Error generating report" in result
        assert "Database error" in result

    def test_collect_run_metrics_handles_exception_in_patches(self):
        """パッチ収集でエラーが発生してもメトリクスは返る"""
        # この関数は内部で例外をキャッチしてログに記録するのみなので、
        # 実際の動作を確認するには詳細なモックが必要
        # 簡易的に、関数が例外を投げないことを確認
        mock_run = Mock(id=1)

        with patch("nexuscore.integration.run_report_generator.HAS_WEBAPP", False):
            with patch.dict("sys.modules", {"nexuscore.integration.github_pr_comment": None}):
                result = _collect_run_metrics(mock_run)

        # エラーハンドリングされて、デフォルト値が返る
        assert isinstance(result, dict)
        assert "duration_str" in result
