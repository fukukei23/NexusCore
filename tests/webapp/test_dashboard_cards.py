"""
プロジェクトダッシュボードのカードレイアウトのテスト
"""
import pytest
from unittest.mock import Mock, patch

from nexuscore.webapp.views_dashboard import render_project_dashboard_html


def test_render_project_dashboard_html_contains_sections():
    """ダッシュボードHTMLに主要セクションが含まれているか"""
    project = Mock()
    project.id = 1
    project.name = "Test Project"

    stats = {
        "total_runs": 10,
        "success_runs": 8,
        "failed_runs": 2,
        "success_rate": 0.8,
    }

    latest_run = Mock()
    latest_run.run_id = "test-run-123"
    latest_run.status = "SUCCESS"

    latest_run_metrics = {
        "patch_count": 3,
        "affected_files": 2,
        "llm_call_count_total": 5,
        "estimated_cost_total": 123.45,
        "duration_sec": 120.0,
    }

    llm_breakdown = {
        "gpt-4.1": {
            "call_count": 3,
            "token_prompt": 1000,
            "token_completion": 500,
            "token_total": 1500,
            "cost_total": 50.0,
        }
    }

    html = render_project_dashboard_html(
        project=project,
        stats=stats,
        recent_runs=[],
        latest_run=latest_run,
        latest_run_metrics=latest_run_metrics,
        llm_breakdown=llm_breakdown,
    )

    # 主要セクションが含まれているか確認
    assert "Project Summary" in html
    assert "Latest Run" in html
    assert "LLM Cost Breakdown" in html
    assert "Recent Runs" in html

    # 統計情報が含まれているか確認
    assert "Test Project" in html
    assert "10" in html  # total_runs
    assert "8" in html  # success_runs
    assert "2" in html  # failed_runs

    # 最新Run情報が含まれているか確認
    assert "test-run-123"[:8] in html
    assert "SUCCESS" in html
    assert "123.45" in html  # estimated_cost_total


def test_render_project_dashboard_html_without_latest_run():
    """最新Runがない場合でもHTMLが生成されるか"""
    project = Mock()
    project.id = 1
    project.name = "Test Project"

    stats = {
        "total_runs": 0,
        "success_runs": 0,
        "failed_runs": 0,
        "success_rate": 0.0,
    }

    html = render_project_dashboard_html(
        project=project,
        stats=stats,
        recent_runs=[],
        latest_run=None,
        latest_run_metrics=None,
        llm_breakdown={},
    )

    # 主要セクションが含まれているか確認
    assert "Project Summary" in html
    assert "Latest Run" in html
    assert "Test Project" in html

