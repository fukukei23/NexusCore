import json
from datetime import datetime, timedelta, timezone

from nexuscore.gradio_app import repair_timeline


def test_read_json_handles_missing(tmp_path):
    f = tmp_path / "data.json"
    f.write_text('{"status":"ok"}', encoding="utf-8")
    assert repair_timeline._read_json(f) == {"status": "ok"}


def test_collect_items_filters_by_date(tmp_path, monkeypatch):
    dir_path = tmp_path / "patch_history"
    dir_path.mkdir()
    ts = (datetime.now(repair_timeline.JST) - timedelta(days=1)).strftime("%Y%m%d_%H%M%S")
    file_path = dir_path / f"patch_{ts}.json"
    file_path.write_text(json.dumps({"timestamp": ts, "status": "success"}), encoding="utf-8")
    monkeypatch.setattr(repair_timeline, "PATCH_HISTORY_DIRS", [dir_path])
    items = repair_timeline._collect_items(limit=None, date_filter="7days")
    assert len(items) == 1


def test_categorize_reason():
    assert repair_timeline._categorize_reason("edge case n=1") == "境界値/特例"
    assert repair_timeline._categorize_reason("unknown") == "不明"


def test_compute_metrics_summary():
    items = [
        {"status": "success", "reason": "edge", "summary": "edge"},
        {"status": "attempt_fail", "reason": "test", "summary": "test"},
        {"status": "initial_pass", "reason": "spec", "summary": "spec"},
    ]
    stats = repair_timeline._compute_metrics(items)
    assert stats["total"] == 3
    assert stats["success"] == 1
    assert "境界値/特例" in stats["categories"]


def test_make_policy_badge():
    assert repair_timeline._make_policy_badge(
        {"policy_profile": "alpha", "policy_version": "v1", "policy_icon": "🏷️"}
    ) == "[🏷️ alpha v1]"
    assert repair_timeline._make_policy_badge({}) == ""


def test_build_timeline_rows_filters(monkeypatch):
    items = [
        {"status": "success", "timestamp": "2025", "policy_profile": "p", "policy_version": "1", "policy_icon": "⭐"},
        {"status": "attempt_fail", "timestamp": "2024"},
    ]
    rows = repair_timeline.build_timeline_rows(items, pair_mode=False, show_attempt=False, show_success=True, show_initial=True)
    assert len(rows) == 1
    assert "success" in rows[0][0]


def test_build_timeline_rows_pair_mode_orders_success_first():
    items = [
        {"status": "attempt_fail", "timestamp": "20250101_120001"},
        {"status": "success", "timestamp": "20250101_120002"},
    ]
    rows = repair_timeline.build_timeline_rows(items, pair_mode=True, show_attempt=True, show_success=True, show_initial=True)
    assert len(rows) == 2
    # reverseソートにより success が先頭に来ることを確認
    assert rows[0][0].startswith("20250101") and "success" in rows[0][0]


def test_render_diff_md_handles_none_and_diff():
    assert repair_timeline._render_diff_md(None).startswith("> 差分はありません")
    diff = repair_timeline._render_diff_md("-old\n+new")
    assert diff.startswith("```diff")
    assert "new" in diff


def test_pick_detail_returns_expected_fields():
    items = [
        {
            "timestamp": "20250101_120001",
            "status": "success",
            "full_code_after": "print('ok')",
            "reason": "edge fix",
            "test_log": "pytest ok",
            "code_diff": "-a\n+b",
            "policy_profile": "alpha",
            "policy_version": "v1",
            "policy_icon": "⭐",
            "_file": "/tmp/patch.json",
            "llm_prompt": "prompt text " * 10,
        }
    ]
    code, reason, log, meta, fkb, diff_md = repair_timeline.pick_detail("20250101_120001", items)
    assert "ok" in code
    assert "edge" in reason
    assert "pytest" in log
    assert meta["policy_profile"] == "alpha"
    assert "diff" in diff_md or diff_md.startswith("```diff")
