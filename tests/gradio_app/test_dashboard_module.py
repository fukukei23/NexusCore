import json
from datetime import datetime

import pytest

from nexuscore.gradio_app import dashboard


@pytest.fixture
def patch_history_dir(tmp_path, monkeypatch):
    dir_path = tmp_path / "patch_history"
    dir_path.mkdir()
    monkeypatch.setattr(dashboard, "PATCH_HISTORY_DIRS", [dir_path])
    return dir_path


def _write_patch(dir_path, name, content):
    file_path = dir_path / name
    file_path.write_text(json.dumps(content), encoding="utf-8")
    return file_path


def test_load_items_filters_by_date(patch_history_dir):
    recent_ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    old_ts = "19700101_000000"
    _write_patch(
        patch_history_dir, f"patch_{recent_ts}.json", {"timestamp": recent_ts, "status": "success"}
    )
    _write_patch(
        patch_history_dir, f"patch_{old_ts}.json", {"timestamp": old_ts, "status": "attempt"}
    )

    items_today = dashboard._load_items(limit=None, date_filter="today")
    assert len(items_today) == 1
    assert items_today[0]["timestamp"] == recent_ts

    items_all = dashboard._load_items(limit=1, date_filter="all")
    assert len(items_all) == 1  # limit applied


def test_metrics_and_plots():
    items = [
        {"status": "success", "timestamp": "20250101_000000", "reason": "edge case n=1"},
        {"status": "attempt", "timestamp": "20250102_000000", "reason": "test failure"},
        {"status": "initial_pass", "timestamp": "20250103_000000", "reason": "spec update"},
    ]
    metrics = dashboard._metrics(items)
    assert metrics["total"] == 3
    assert metrics["success"] == 1
    assert "境界値/特例" in metrics["categories"]

    fig_cat = dashboard._make_cat_plot(metrics["categories"])
    fig_day = dashboard._make_daily_plot(metrics["by_day"])
    assert fig_cat is not None
    assert fig_day is not None
