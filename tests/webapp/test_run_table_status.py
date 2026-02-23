"""
Run 一覧テーブルのステータスバッジ表示のテスト

注意: このテストファイルは Flask レガシー前提です。
CR-FASTAPI-010 で Flask API が削除されたため、このテストファイルは skip されます。
FastAPI 側のテストは tests/api/test_fastapi_*.py を参照してください。
"""

import pytest

# CR-FASTAPI-010: Flask レガシー前提のテストは削除済み
# FastAPI 側のテストは tests/api/test_fastapi_*.py を参照してください
pytest.skip(
    "Flask legacy run_table_status tests have been removed in CR-FASTAPI-010. "
    "Use FastAPI tests in tests/api/test_fastapi_*.py instead.",
    allow_module_level=True,
)


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
