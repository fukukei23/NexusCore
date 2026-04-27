import json

from nexuscore.archive.gradio_app import dashboard


def test_categorize_rules():
    assert dashboard._categorize("Edge case for n=1") == "境界値/特例"
    assert dashboard._categorize("unknown text") == "不明"


def test_load_items_reads_patch(tmp_path, monkeypatch):
    patch_dir = tmp_path / "patch_history"
    patch_dir.mkdir()
    file_path = patch_dir / "patch_20250101_000000.json"
    file_path.write_text(
        json.dumps({"timestamp": "20250101_000000", "status": "success", "reason": "Edge case"}),
        encoding="utf-8",
    )
    monkeypatch.setattr(dashboard, "PATCH_HISTORY_DIRS", [patch_dir])
    items = dashboard._load_items(limit=None, date_filter="all")
    assert len(items) == 1
    assert items[0]["status"] == "success"


def test_metrics_calculation(monkeypatch):
    items = [
        {"status": "success", "timestamp": "20250101_000000", "reason": "test"},
        {"status": "attempt_fail", "timestamp": "20250102_000000", "reason": "edge"},
        {"status": "initial_pass", "timestamp": "20250103_000000", "reason": "spec"},
    ]
    stats = dashboard._metrics(items)
    assert stats["total"] == 3
    assert stats["success"] == 1
    assert stats["categories"]["境界値/特例"] >= 1
    assert "by_day" in stats


def test_make_cat_plot_returns_figure():
    fig = dashboard._make_cat_plot({"A": 1})
    assert fig.get_axes()
