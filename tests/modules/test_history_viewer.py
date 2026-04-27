"""
history_viewer.py 包括テスト
load_history() と format_history_markdown() を完全カバー
"""
from __future__ import annotations

import json
import os

import pytest

from nexuscore.archive.modules.history_viewer import format_history_markdown, load_history


@pytest.fixture
def history_dir(tmp_path):
    """テスト用の一時 history ディレクトリ"""
    return tmp_path


def _write_json(directory, filename, data):
    path = os.path.join(str(directory), filename)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    return path


class TestLoadHistory:
    def test_load_history_empty_directory(self, history_dir):
        result = load_history(str(history_dir))
        assert result == []

    def test_load_history_single_success_entry(self, history_dir):
        _write_json(history_dir, "2026-01-01.json", {
            "timestamp": "2026-01-01 10:00:00",
            "test_log": "5 passed",
            "reason": "FooBar fixed",
        })
        result = load_history(str(history_dir))
        assert len(result) == 1
        assert result[0]["time"] == "2026-01-01 10:00:00"
        assert result[0]["result"] == "✅ Success"

    def test_load_history_failed_entry(self, history_dir):
        _write_json(history_dir, "2026-01-02.json", {
            "timestamp": "2026-01-02 12:00:00",
            "test_log": "2 passed, 3 failed",
            "reason": "Something broke",
        })
        result = load_history(str(history_dir))
        assert len(result) == 1
        assert result[0]["result"] == "❌ Failed"

    def test_load_history_ignores_non_json_files(self, history_dir):
        _write_json(history_dir, "2026-01-01.json", {
            "timestamp": "2026-01-01",
            "test_log": "1 passed",
            "reason": "ok",
        })
        with open(os.path.join(str(history_dir), "notes.txt"), "w") as f:
            f.write("ignore me")
        result = load_history(str(history_dir))
        assert len(result) == 1

    def test_load_history_reason_truncated_to_200_plus_dots(self, history_dir):
        long_reason = "x" * 250
        _write_json(history_dir, "2026-01-01.json", {
            "timestamp": "2026-01-01",
            "test_log": "ok",
            "reason": long_reason,
        })
        result = load_history(str(history_dir))
        # reason は [:200] + "..." に切り詰め → 203文字
        assert len(result[0]["reason"]) == 203

    def test_load_history_short_reason_gets_dots_appended(self, history_dir):
        _write_json(history_dir, "2026-01-01.json", {
            "timestamp": "2026-01-01",
            "test_log": "1 passed",
            "reason": "short reason",
        })
        result = load_history(str(history_dir))
        assert result[0]["reason"].endswith("...")

    def test_load_history_missing_reason_key(self, history_dir):
        _write_json(history_dir, "2026-01-01.json", {
            "timestamp": "2026-01-01",
            "test_log": "1 passed",
        })
        result = load_history(str(history_dir))
        assert len(result) == 1
        assert "..." in result[0]["reason"]

    def test_load_history_multiple_entries_sorted_reverse(self, history_dir):
        for day in ["2026-01-01", "2026-01-02", "2026-01-03"]:
            _write_json(history_dir, f"{day}.json", {
                "timestamp": day,
                "test_log": "ok",
                "reason": "r",
            })
        result = load_history(str(history_dir))
        assert len(result) == 3
        timestamps = [e["time"] for e in result]
        assert timestamps == sorted(timestamps, reverse=True)

    def test_load_history_entry_has_required_keys(self, history_dir):
        _write_json(history_dir, "2026-01-01.json", {
            "timestamp": "2026-01-01",
            "test_log": "ok",
            "reason": "r",
        })
        result = load_history(str(history_dir))
        entry = result[0]
        assert "time" in entry
        assert "result" in entry
        assert "reason" in entry


class TestFormatHistoryMarkdown:
    def test_format_empty_entries_has_header(self):
        result = format_history_markdown([])
        assert "# 🧾 修正履歴一覧" in result

    def test_format_single_entry(self):
        entries = [{"time": "2026-01-01", "result": "✅ Success", "reason": "Fixed it"}]
        result = format_history_markdown(entries)
        assert "2026-01-01" in result
        assert "✅ Success" in result
        assert "Fixed it" in result

    def test_format_multiple_entries(self):
        entries = [
            {"time": "2026-01-02", "result": "❌ Failed", "reason": "Bug"},
            {"time": "2026-01-01", "result": "✅ Success", "reason": "OK"},
        ]
        result = format_history_markdown(entries)
        assert "2026-01-02" in result
        assert "2026-01-01" in result
        assert "❌ Failed" in result

    def test_format_returns_string(self):
        result = format_history_markdown([])
        assert isinstance(result, str)

    def test_format_header_at_start(self):
        result = format_history_markdown([])
        assert result.startswith("# 🧾 修正履歴一覧")
