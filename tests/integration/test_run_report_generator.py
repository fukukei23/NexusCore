"""
Run レポート生成のテスト
"""
import pytest
from pathlib import Path
from unittest.mock import Mock, patch

from nexuscore.integration.run_report_generator import (
    generate_run_report_markdown,
    write_run_report_file,
    _format_duration,
    _collect_run_metrics,
)


def test_format_duration():
    """実行時間のフォーマットが正しく動作するか"""
    run = Mock()
    run.started_at = None
    run.finished_at = None

    result = _format_duration(run)
    assert result == "N/A"

    from datetime import datetime, timedelta
    run.started_at = datetime(2025, 1, 1, 10, 0, 0)
    run.finished_at = datetime(2025, 1, 1, 10, 0, 30)
    result = _format_duration(run)
    assert result == "30s"

    run.finished_at = datetime(2025, 1, 1, 10, 5, 30)
    result = _format_duration(run)
    assert "5m" in result and "30s" in result


@pytest.mark.skipif(
    not hasattr(__import__("nexuscore.webapp.models", fromlist=["Run"]), "Run"),
    reason="Webapp models not available",
)
def test_generate_run_report_markdown():
    """Run レポートの Markdown が正しく生成されるか"""
    # このテストは実際のDBが必要なので、モックで簡易テスト
    with patch("nexuscore.integration.run_report_generator.HAS_WEBAPP", False):
        result = generate_run_report_markdown(1)
        assert "# Run Report" in result
        assert "Webapp models not available" in result


def test_generate_run_report_markdown_without_webapp():
    """Webapp が利用できない場合のフォールバック"""
    with patch("nexuscore.integration.run_report_generator.HAS_WEBAPP", False):
        result = generate_run_report_markdown(1)
        assert "# Run Report" in result
        assert "Webapp models not available" in result

