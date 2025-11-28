"""
Run 一覧テーブルのステータスバッジ表示のテスト
"""
import pytest

from nexuscore.webapp.views_projects import _render_run_status_badge


def test_render_run_status_badge_success():
    """SUCCESS ステータスのバッジが正しく生成されるか"""
    result = _render_run_status_badge("SUCCESS")
    assert "status-success" in result
    assert "✔" in result
    assert "SUCCESS" in result


def test_render_run_status_badge_running():
    """RUNNING ステータスのバッジが正しく生成されるか"""
    result = _render_run_status_badge("RUNNING")
    assert "status-running" in result
    assert "▶" in result
    assert "RUNNING" in result


def test_render_run_status_badge_failed():
    """FAILED ステータスのバッジが正しく生成されるか"""
    result = _render_run_status_badge("FAILED")
    assert "status-failed" in result
    assert "✖" in result
    assert "FAILED" in result


def test_render_run_status_badge_pending():
    """PENDING ステータスのバッジが正しく生成されるか"""
    result = _render_run_status_badge("PENDING")
    assert "status-pending" in result
    assert "⏱" in result
    assert "PENDING" in result


def test_render_run_status_badge_empty():
    """空文字列の場合のデフォルト処理"""
    result = _render_run_status_badge("")
    assert "status-pending" in result
    assert "PENDING" in result

