# -*- coding: utf-8 -*-
"""
Comprehensive tests for nexuscore.gradio_app.dashboard module.

This test file provides extensive coverage for all functions, metrics calculation,
visualization, UI components, and edge cases in the dashboard module.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, date, timedelta
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, call
from typing import List, Dict, Any

import pytest
import sys

# Mock gradio and matplotlib before importing dashboard
sys.modules['gradio'] = MagicMock()
sys.modules['matplotlib'] = MagicMock()
sys.modules['matplotlib.pyplot'] = MagicMock()

from nexuscore.gradio_app import dashboard


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def temp_patch_dir(tmp_path):
    """Create a temporary patch_history directory with sample data."""
    patch_dir = tmp_path / "patch_history"
    patch_dir.mkdir(parents=True, exist_ok=True)
    return patch_dir


@pytest.fixture
def sample_patch_files(temp_patch_dir):
    """Create sample patch history JSON files."""
    files = []

    # Success patch
    patch1 = temp_patch_dir / "patch_20250101_120000.json"
    patch1.write_text(json.dumps({
        "timestamp": "20250101_120000",
        "status": "success",
        "reason": "Fixed edge case for n=2",
        "prompt": "Fix is_prime",
        "code": "def is_prime(n): return n >= 2",
        "test_log": "5 passed"
    }), encoding="utf-8")
    files.append(patch1)

    # Attempt patch
    patch2 = temp_patch_dir / "patch_20250101_130000.json"
    patch2.write_text(json.dumps({
        "timestamp": "20250101_130000",
        "status": "attempt_fail",
        "reason": "Test failed",
        "prompt": "Retry",
        "code": "def test(): pass",
        "test_log": "3 failed"
    }), encoding="utf-8")
    files.append(patch2)

    # Initial pass
    patch3 = temp_patch_dir / "patch_20250102_100000.json"
    patch3.write_text(json.dumps({
        "timestamp": "20250102_100000",
        "status": "initial_pass",
        "reason": "Spec compliant",
        "prompt": "Implement spec",
        "code": "def new_func(): pass",
        "test_log": "10 passed"
    }), encoding="utf-8")
    files.append(patch3)

    return files


@pytest.fixture
def sample_items():
    """Sample patch history items for testing."""
    return [
        {
            "timestamp": "20250101_120000",
            "status": "success",
            "reason": "Handle n=2 edge case",
            "summary": "Fixed boundary condition",
        },
        {
            "timestamp": "20250101_130000",
            "status": "attempt_fail",
            "reason": "Algorithm complexity improved with two pointers",
            "summary": "Optimization attempt",
        },
        {
            "timestamp": "20250102_100000",
            "status": "initial_pass",
            "reason": "Spec implementation complete",
            "summary": "Initial implementation",
        },
        {
            "timestamp": "20250102_110000",
            "status": "success",
            "reason": "Test fixture added",
            "summary": "Test improvement",
        },
    ]


@pytest.fixture
def mock_matplotlib():
    """Mock matplotlib to prevent actual plot rendering."""
    with patch.object(plt, "subplots") as mock_subplots:
        fig = Mock()
        ax = Mock()
        mock_subplots.return_value = (fig, ax)
        yield fig, ax


# ============================================================================
# Tests for _parse_ts()
# ============================================================================


class TestParseTimestamp:
    """Tests for timestamp parsing function."""

    def test_parse_ts_standard_format(self):
        """Test parsing standard YYYYMMDD_HHMMSS format."""
        ts = "20250615_143022"
        dt = dashboard._parse_ts(ts)

        assert dt.year == 2025
        assert dt.month == 6
        assert dt.day == 15
        assert dt.hour == 14
        assert dt.minute == 30
        assert dt.second == 22

    def test_parse_ts_datetime_format(self):
        """Test parsing YYYY-MM-DD HH:MM:SS format."""
        ts = "2025-06-15 14:30:22"
        dt = dashboard._parse_ts(ts)

        assert dt.year == 2025
        assert dt.month == 6
        assert dt.day == 15
        assert dt.hour == 14
        assert dt.minute == 30
        assert dt.second == 22

    def test_parse_ts_invalid_format(self):
        """Test parsing invalid timestamp returns epoch."""
        ts = "invalid_timestamp"
        dt = dashboard._parse_ts(ts)

        assert dt.year == 1970
        assert dt.month == 1
        assert dt.day == 1

    def test_parse_ts_empty_string(self):
        """Test parsing empty string."""
        dt = dashboard._parse_ts("")
        assert dt.year == 1970

    def test_parse_ts_partial_timestamp(self):
        """Test parsing partial timestamp."""
        dt = dashboard._parse_ts("2025")
        assert dt.year == 1970  # Falls back to epoch

    @pytest.mark.parametrize("timestamp,expected_year", [
        ("20250101_000000", 2025),
        ("2024-12-31 23:59:59", 2024),
        ("invalid", 1970),
        ("", 1970),
        ("20260215_120000", 2026),
    ])
    def test_parse_ts_parametrized(self, timestamp, expected_year):
        """Parametrized tests for various timestamp formats."""
        dt = dashboard._parse_ts(timestamp)
        assert dt.year == expected_year


# ============================================================================
# Tests for _read_json()
# ============================================================================


class TestReadJson:
    """Tests for JSON file reading function."""

    def test_read_json_valid_file(self, tmp_path):
        """Test reading a valid JSON file."""
        json_file = tmp_path / "data.json"
        data = {"key": "value", "number": 42}
        json_file.write_text(json.dumps(data), encoding="utf-8")

        result = dashboard._read_json(json_file)

        assert result == data
        assert result["key"] == "value"
        assert result["number"] == 42

    def test_read_json_empty_file(self, tmp_path):
        """Test reading an empty JSON file."""
        json_file = tmp_path / "empty.json"
        json_file.write_text("", encoding="utf-8")

        result = dashboard._read_json(json_file)

        assert result == {}

    def test_read_json_invalid_json(self, tmp_path):
        """Test reading a file with invalid JSON."""
        json_file = tmp_path / "invalid.json"
        json_file.write_text("{invalid json", encoding="utf-8")

        result = dashboard._read_json(json_file)

        assert result == {}

    def test_read_json_nonexistent_file(self, tmp_path):
        """Test reading a nonexistent file."""
        json_file = tmp_path / "nonexistent.json"

        result = dashboard._read_json(json_file)

        assert result == {}

    def test_read_json_with_unicode(self, tmp_path):
        """Test reading JSON with unicode characters."""
        json_file = tmp_path / "unicode.json"
        data = {"message": "こんにちは", "emoji": "🎉"}
        json_file.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

        result = dashboard._read_json(json_file)

        assert result["message"] == "こんにちは"
        assert result["emoji"] == "🎉"

    def test_read_json_nested_structure(self, tmp_path):
        """Test reading JSON with nested structure."""
        json_file = tmp_path / "nested.json"
        data = {
            "level1": {
                "level2": {
                    "level3": "deep value"
                }
            }
        }
        json_file.write_text(json.dumps(data), encoding="utf-8")

        result = dashboard._read_json(json_file)

        assert result["level1"]["level2"]["level3"] == "deep value"


# ============================================================================
# Tests for _collect_files()
# ============================================================================


class TestCollectFiles:
    """Tests for patch file collection function."""

    def test_collect_files_finds_patches(self, temp_patch_dir, monkeypatch):
        """Test that _collect_files finds patch files."""
        # Create patch files
        (temp_patch_dir / "patch_20250101_120000.json").write_text("{}", encoding="utf-8")
        (temp_patch_dir / "patch_20250102_120000.json").write_text("{}", encoding="utf-8")

        monkeypatch.setattr(dashboard, "PATCH_HISTORY_DIRS", [temp_patch_dir])

        files = dashboard._collect_files()

        assert len(files) == 2
        assert all(f.name.startswith("patch_") for f in files)

    def test_collect_files_sorted_descending(self, temp_patch_dir, monkeypatch):
        """Test that files are sorted newest first."""
        (temp_patch_dir / "patch_20250101_120000.json").write_text("{}", encoding="utf-8")
        (temp_patch_dir / "patch_20250103_120000.json").write_text("{}", encoding="utf-8")
        (temp_patch_dir / "patch_20250102_120000.json").write_text("{}", encoding="utf-8")

        monkeypatch.setattr(dashboard, "PATCH_HISTORY_DIRS", [temp_patch_dir])

        files = dashboard._collect_files()

        # Should be sorted newest first
        assert files[0].stem == "patch_20250103_120000"
        assert files[1].stem == "patch_20250102_120000"
        assert files[2].stem == "patch_20250101_120000"

    def test_collect_files_empty_directory(self, temp_patch_dir, monkeypatch):
        """Test collecting files from empty directory."""
        monkeypatch.setattr(dashboard, "PATCH_HISTORY_DIRS", [temp_patch_dir])

        files = dashboard._collect_files()

        assert len(files) == 0

    def test_collect_files_nonexistent_directory(self, tmp_path, monkeypatch):
        """Test collecting files from nonexistent directory."""
        nonexistent = tmp_path / "nonexistent"
        monkeypatch.setattr(dashboard, "PATCH_HISTORY_DIRS", [nonexistent])

        files = dashboard._collect_files()

        assert len(files) == 0

    def test_collect_files_multiple_directories(self, tmp_path, monkeypatch):
        """Test collecting files from multiple directories."""
        dir1 = tmp_path / "dir1"
        dir2 = tmp_path / "dir2"
        dir1.mkdir()
        dir2.mkdir()

        (dir1 / "patch_20250101_120000.json").write_text("{}", encoding="utf-8")
        (dir2 / "patch_20250102_120000.json").write_text("{}", encoding="utf-8")

        monkeypatch.setattr(dashboard, "PATCH_HISTORY_DIRS", [dir1, dir2])

        files = dashboard._collect_files()

        assert len(files) == 2

    def test_collect_files_ignores_non_patch_files(self, temp_patch_dir, monkeypatch):
        """Test that non-patch files are ignored."""
        (temp_patch_dir / "patch_20250101_120000.json").write_text("{}", encoding="utf-8")
        (temp_patch_dir / "other_file.json").write_text("{}", encoding="utf-8")
        (temp_patch_dir / "readme.txt").write_text("text", encoding="utf-8")

        monkeypatch.setattr(dashboard, "PATCH_HISTORY_DIRS", [temp_patch_dir])

        files = dashboard._collect_files()

        assert len(files) == 1
        assert files[0].name == "patch_20250101_120000.json"


# ============================================================================
# Tests for _load_items()
# ============================================================================


class TestLoadItems:
    """Tests for loading and filtering patch items."""

    def test_load_items_no_filter(self, sample_patch_files, temp_patch_dir, monkeypatch):
        """Test loading items without filters."""
        monkeypatch.setattr(dashboard, "PATCH_HISTORY_DIRS", [temp_patch_dir])

        items = dashboard._load_items(limit=None, date_filter="all")

        assert len(items) == 3
        assert all("_file" in item for item in items)

    def test_load_items_with_limit(self, sample_patch_files, temp_patch_dir, monkeypatch):
        """Test loading items with limit."""
        monkeypatch.setattr(dashboard, "PATCH_HISTORY_DIRS", [temp_patch_dir])

        items = dashboard._load_items(limit=2, date_filter="all")

        assert len(items) <= 2

    def test_load_items_today_filter(self, temp_patch_dir, monkeypatch):
        """Test loading items with today filter."""
        today = datetime.now()
        ts_today = today.strftime("%Y%m%d_120000")
        yesterday = (today - timedelta(days=1)).strftime("%Y%m%d_120000")

        (temp_patch_dir / f"patch_{ts_today}.json").write_text(
            json.dumps({"timestamp": ts_today, "status": "success"}),
            encoding="utf-8"
        )
        (temp_patch_dir / f"patch_{yesterday}.json").write_text(
            json.dumps({"timestamp": yesterday, "status": "success"}),
            encoding="utf-8"
        )

        monkeypatch.setattr(dashboard, "PATCH_HISTORY_DIRS", [temp_patch_dir])

        items = dashboard._load_items(limit=None, date_filter="today")

        # Should only include today's items
        assert all(
            dashboard._parse_ts(item["timestamp"]).date() == today.date()
            for item in items
        )

    def test_load_items_7days_filter(self, temp_patch_dir, monkeypatch):
        """Test loading items with 7 days filter."""
        now = datetime.now()
        recent = (now - timedelta(days=3)).strftime("%Y%m%d_120000")
        old = (now - timedelta(days=10)).strftime("%Y%m%d_120000")

        (temp_patch_dir / f"patch_{recent}.json").write_text(
            json.dumps({"timestamp": recent, "status": "success"}),
            encoding="utf-8"
        )
        (temp_patch_dir / f"patch_{old}.json").write_text(
            json.dumps({"timestamp": old, "status": "success"}),
            encoding="utf-8"
        )

        monkeypatch.setattr(dashboard, "PATCH_HISTORY_DIRS", [temp_patch_dir])

        items = dashboard._load_items(limit=None, date_filter="7days")

        # Should only include items from last 7 days
        assert len(items) == 1
        assert items[0]["timestamp"] == recent

    def test_load_items_30days_filter(self, temp_patch_dir, monkeypatch):
        """Test loading items with 30 days filter."""
        now = datetime.now()
        recent = (now - timedelta(days=15)).strftime("%Y%m%d_120000")
        old = (now - timedelta(days=40)).strftime("%Y%m%d_120000")

        (temp_patch_dir / f"patch_{recent}.json").write_text(
            json.dumps({"timestamp": recent, "status": "success"}),
            encoding="utf-8"
        )
        (temp_patch_dir / f"patch_{old}.json").write_text(
            json.dumps({"timestamp": old, "status": "success"}),
            encoding="utf-8"
        )

        monkeypatch.setattr(dashboard, "PATCH_HISTORY_DIRS", [temp_patch_dir])

        items = dashboard._load_items(limit=None, date_filter="30days")

        assert len(items) == 1

    def test_load_items_sorted_newest_first(self, temp_patch_dir, monkeypatch):
        """Test that loaded items are sorted newest first."""
        timestamps = ["20250101_120000", "20250103_120000", "20250102_120000"]
        for ts in timestamps:
            (temp_patch_dir / f"patch_{ts}.json").write_text(
                json.dumps({"timestamp": ts, "status": "success"}),
                encoding="utf-8"
            )

        monkeypatch.setattr(dashboard, "PATCH_HISTORY_DIRS", [temp_patch_dir])

        items = dashboard._load_items(limit=None, date_filter="all")

        assert items[0]["timestamp"] == "20250103_120000"
        assert items[1]["timestamp"] == "20250102_120000"
        assert items[2]["timestamp"] == "20250101_120000"

    def test_load_items_adds_file_path(self, sample_patch_files, temp_patch_dir, monkeypatch):
        """Test that _file path is added to items."""
        monkeypatch.setattr(dashboard, "PATCH_HISTORY_DIRS", [temp_patch_dir])

        items = dashboard._load_items(limit=None, date_filter="all")

        assert all("_file" in item for item in items)
        assert all(Path(item["_file"]).exists() for item in items)


# ============================================================================
# Tests for _categorize()
# ============================================================================


class TestCategorize:
    """Tests for reason categorization function."""

    def test_categorize_boundary_case(self):
        """Test categorization of boundary/edge cases."""
        assert dashboard._categorize("Edge case for n=0") == "境界値/特例"
        assert dashboard._categorize("Handle n=1") == "境界値/特例"
        assert dashboard._categorize("Fix n=2 issue") == "境界値/特例"
        assert dashboard._categorize("Off-by-one error") == "境界値/特例"
        assert dashboard._categorize("Boundary condition") == "境界値/特例"

    def test_categorize_algorithm(self):
        """Test categorization of algorithm improvements."""
        assert dashboard._categorize("Use two pointers approach") == "アルゴリズム/計算量"
        assert dashboard._categorize("Binary search optimization") == "アルゴリズム/計算量"
        assert dashboard._categorize("Improved O(n) complexity") == "アルゴリズム/計算量"
        assert dashboard._categorize("while i * i <= n") == "アルゴリズム/計算量"

    def test_categorize_io_path(self):
        """Test categorization of I/O and path issues."""
        assert dashboard._categorize("Fix path handling") == "I/O・パス・環境"
        assert dashboard._categorize("Windows compatibility") == "I/O・パス・環境"
        assert dashboard._categorize("Encoding issue resolved") == "I/O・パス・環境"
        assert dashboard._categorize("Permission error") == "I/O・パス・環境"
        assert dashboard._categorize("ENV variable fix") == "I/O・パス・環境"

    def test_categorize_test_quality(self):
        """Test categorization of test/quality improvements."""
        assert dashboard._categorize("Test fixture added") == "テスト修正/品質"
        assert dashboard._categorize("Pytest update") == "テスト修正/品質"
        assert dashboard._categorize("Assert statement fix") == "テスト修正/品質"

    def test_categorize_spec_design(self):
        """Test categorization of spec/design issues."""
        assert dashboard._categorize("Spec compliance") == "設計/仕様"
        assert dashboard._categorize("仕様変更") == "設計/仕様"
        assert dashboard._categorize("Contract updated") == "設計/仕様"
        assert dashboard._categorize("Interface change") == "設計/仕様"

    def test_categorize_unknown(self):
        """Test categorization of unknown reasons."""
        assert dashboard._categorize("Random text") == "不明"
        assert dashboard._categorize("") == "不明"
        assert dashboard._categorize("Something else") == "不明"

    def test_categorize_special_cases(self):
        """Test special case categorization."""
        assert dashboard._categorize("even numbers handling") == "境界値/特例"
        assert dashboard._categorize("handle n=2 properly") == "境界値/特例"

    def test_categorize_case_insensitive(self):
        """Test that categorization is case insensitive."""
        assert dashboard._categorize("EDGE CASE") == "境界値/特例"
        assert dashboard._categorize("Edge Case") == "境界値/特例"
        assert dashboard._categorize("edge case") == "境界値/特例"

    @pytest.mark.parametrize("text,expected_category", [
        ("Fix n=0 edge case", "境界値/特例"),
        ("O(n log n) improvement", "アルゴリズム/計算量"),
        ("Path separator fix", "I/O・パス・環境"),
        ("pytest fixture", "テスト修正/品質"),
        ("spec update", "設計/仕様"),
        ("unknown reason", "不明"),
        ("", "不明"),
        (None, "不明"),
    ])
    def test_categorize_parametrized(self, text, expected_category):
        """Parametrized tests for various categorizations."""
        assert dashboard._categorize(text) == expected_category


# ============================================================================
# Tests for _metrics()
# ============================================================================


class TestMetrics:
    """Tests for metrics calculation function."""

    def test_metrics_basic_counts(self, sample_items):
        """Test basic counting metrics."""
        stats = dashboard._metrics(sample_items)

        assert stats["total"] == 4
        assert stats["success"] == 2
        assert stats["attempts"] == 1
        assert stats["initial"] == 1

    def test_metrics_success_rate(self, sample_items):
        """Test success rate calculation."""
        stats = dashboard._metrics(sample_items)

        expected_rate = (2 / 4) * 100
        assert stats["success_rate"] == expected_rate

    def test_metrics_recent_success_rate(self, sample_items):
        """Test recent success rate calculation (last 10 items)."""
        stats = dashboard._metrics(sample_items)

        # All 4 items are in "recent", 2 are success
        expected_recent_rate = (2 / 4) * 100
        assert stats["recent_success_rate"] == expected_recent_rate

    def test_metrics_avg_attempts(self, sample_items):
        """Test average attempts per success calculation."""
        stats = dashboard._metrics(sample_items)

        expected_avg = 1 / 2  # 1 attempt, 2 successes
        assert stats["avg_attempts_per_success"] == expected_avg

    def test_metrics_winning_streak(self):
        """Test winning streak calculation."""
        items = [
            {"timestamp": "20250104_000000", "status": "success", "reason": "fix"},
            {"timestamp": "20250103_000000", "status": "success", "reason": "fix"},
            {"timestamp": "20250102_000000", "status": "success", "reason": "fix"},
            {"timestamp": "20250101_000000", "status": "attempt_fail", "reason": "fail"},
        ]

        stats = dashboard._metrics(items)

        assert stats["streak_win"] == 3
        assert stats["streak_lose"] == 0

    def test_metrics_losing_streak(self):
        """Test losing streak calculation."""
        items = [
            {"timestamp": "20250103_000000", "status": "attempt_fail", "reason": "fail"},
            {"timestamp": "20250102_000000", "status": "attempt_fail", "reason": "fail"},
            {"timestamp": "20250101_000000", "status": "success", "reason": "fix"},
        ]

        stats = dashboard._metrics(items)

        assert stats["streak_win"] == 0
        assert stats["streak_lose"] == 2

    def test_metrics_category_distribution(self, sample_items):
        """Test category distribution calculation."""
        stats = dashboard._metrics(sample_items)

        assert "categories" in stats
        assert stats["categories"]["境界値/特例"] >= 1
        assert stats["categories"]["アルゴリズム/計算量"] >= 1
        assert stats["categories"]["設計/仕様"] >= 1
        assert stats["categories"]["テスト修正/品質"] >= 1

    def test_metrics_daily_breakdown(self, sample_items):
        """Test daily breakdown of events."""
        stats = dashboard._metrics(sample_items)

        assert "by_day" in stats
        assert len(stats["by_day"]) > 0

        # Check structure of daily data
        for day_data in stats["by_day"].values():
            assert "success" in day_data
            assert "attempt" in day_data
            assert "initial" in day_data

    def test_metrics_empty_items(self):
        """Test metrics calculation with empty items."""
        stats = dashboard._metrics([])

        assert stats["total"] == 0
        assert stats["success"] == 0
        assert stats["attempts"] == 0
        assert stats["initial"] == 0
        assert stats["success_rate"] == 0.0
        assert stats["streak_win"] == 0
        assert stats["streak_lose"] == 0

    def test_metrics_single_item(self):
        """Test metrics with single item."""
        items = [{"timestamp": "20250101_000000", "status": "success", "reason": "fix"}]

        stats = dashboard._metrics(items)

        assert stats["total"] == 1
        assert stats["success"] == 1
        assert stats["success_rate"] == 100.0

    def test_metrics_handles_missing_status(self):
        """Test metrics with items missing status field."""
        items = [
            {"timestamp": "20250101_000000", "reason": "fix"},
            {"timestamp": "20250102_000000", "status": "success", "reason": "fix"},
        ]

        stats = dashboard._metrics(items)

        assert stats["total"] == 2
        assert stats["success"] == 1

    def test_metrics_handles_missing_reason(self):
        """Test metrics with items missing reason field."""
        items = [
            {"timestamp": "20250101_000000", "status": "success"},
            {"timestamp": "20250102_000000", "status": "attempt_fail", "summary": "edge case"},
        ]

        stats = dashboard._metrics(items)

        assert "categories" in stats
        assert stats["categories"]["境界値/特例"] >= 1


# ============================================================================
# Tests for _make_cat_plot()
# ============================================================================


class TestMakeCatPlot:
    """Tests for category plot generation."""

    def test_make_cat_plot_creates_figure(self):
        """Test that category plot creates a figure."""
        cats = {"境界値/特例": 5, "アルゴリズム/計算量": 3}

        fig = dashboard._make_cat_plot(cats)

        assert fig is not None
        assert hasattr(fig, "get_axes")

    def test_make_cat_plot_empty_categories(self):
        """Test category plot with empty categories."""
        fig = dashboard._make_cat_plot({})

        assert fig is not None
        # Should create a figure with "no data" message

    def test_make_cat_plot_single_category(self):
        """Test category plot with single category."""
        cats = {"境界値/特例": 10}

        fig = dashboard._make_cat_plot(cats)

        assert fig is not None

    def test_make_cat_plot_multiple_categories(self):
        """Test category plot with multiple categories."""
        cats = {
            "境界値/特例": 15,
            "アルゴリズム/計算量": 8,
            "I/O・パス・環境": 5,
            "テスト修正/品質": 12,
            "設計/仕様": 6,
        }

        fig = dashboard._make_cat_plot(cats)

        assert fig is not None

    def test_make_cat_plot_returns_figure_type(self):
        """Test that return type is matplotlib figure."""
        cats = {"Test": 1}
        fig = dashboard._make_cat_plot(cats)

        # Check it's a matplotlib figure
        assert hasattr(fig, "savefig")


# ============================================================================
# Tests for _make_daily_plot()
# ============================================================================


class TestMakeDailyPlot:
    """Tests for daily timeline plot generation."""

    def test_make_daily_plot_creates_figure(self):
        """Test that daily plot creates a figure."""
        by_day = {
            date(2025, 1, 1): {"success": 3, "attempt": 1, "initial": 0},
            date(2025, 1, 2): {"success": 2, "attempt": 2, "initial": 1},
        }

        fig = dashboard._make_daily_plot(by_day)

        assert fig is not None
        assert hasattr(fig, "get_axes")

    def test_make_daily_plot_empty_data(self):
        """Test daily plot with empty data."""
        fig = dashboard._make_daily_plot({})

        assert fig is not None

    def test_make_daily_plot_single_day(self):
        """Test daily plot with single day."""
        by_day = {
            date(2025, 1, 1): {"success": 5, "attempt": 2, "initial": 1},
        }

        fig = dashboard._make_daily_plot(by_day)

        assert fig is not None

    def test_make_daily_plot_multiple_days(self):
        """Test daily plot with multiple days."""
        by_day = {
            date(2025, 1, i): {"success": i, "attempt": i * 2, "initial": 0}
            for i in range(1, 8)
        }

        fig = dashboard._make_daily_plot(by_day)

        assert fig is not None


# ============================================================================
# Tests for build_ui()
# ============================================================================


class TestBuildUI:
    """Tests for the Gradio UI building function."""

    def test_build_ui_returns_blocks(self):
        """Test that build_ui returns a Gradio Blocks object."""
        with patch.object(dashboard, "_load_items", return_value=[]):
            demo = dashboard.build_ui()

        assert isinstance(demo, gr.Blocks)

    def test_build_ui_with_mock_data(self, sample_items, monkeypatch, temp_patch_dir):
        """Test UI building with mocked data."""
        monkeypatch.setattr(dashboard, "PATCH_HISTORY_DIRS", [temp_patch_dir])

        with patch.object(dashboard, "_load_items", return_value=sample_items):
            demo = dashboard.build_ui()

        assert demo is not None


# ============================================================================
# Integration Tests
# ============================================================================


class TestIntegration:
    """Integration tests for complete workflows."""

    def test_full_dashboard_workflow(self, sample_patch_files, temp_patch_dir, monkeypatch):
        """Test complete dashboard data processing workflow."""
        monkeypatch.setattr(dashboard, "PATCH_HISTORY_DIRS", [temp_patch_dir])

        # Collect files
        files = dashboard._collect_files()
        assert len(files) == 3

        # Load items
        items = dashboard._load_items(limit=None, date_filter="all")
        assert len(items) == 3

        # Calculate metrics
        stats = dashboard._metrics(items)
        assert stats["total"] == 3
        assert stats["success"] >= 1

        # Generate plots
        cat_fig = dashboard._make_cat_plot(stats["categories"])
        day_fig = dashboard._make_daily_plot(stats["by_day"])

        assert cat_fig is not None
        assert day_fig is not None

    def test_end_to_end_with_filtering(self, temp_patch_dir, monkeypatch):
        """Test end-to-end workflow with date filtering."""
        # Create patches spanning multiple days
        now = datetime.now()
        for i in range(5):
            ts = (now - timedelta(days=i)).strftime("%Y%m%d_120000")
            patch_file = temp_patch_dir / f"patch_{ts}.json"
            patch_file.write_text(json.dumps({
                "timestamp": ts,
                "status": "success" if i % 2 == 0 else "attempt_fail",
                "reason": f"Fix {i}",
            }), encoding="utf-8")

        monkeypatch.setattr(dashboard, "PATCH_HISTORY_DIRS", [temp_patch_dir])

        # Test different filters
        all_items = dashboard._load_items(limit=None, date_filter="all")
        assert len(all_items) == 5

        recent_items = dashboard._load_items(limit=None, date_filter="7days")
        assert len(recent_items) <= 5

        limited_items = dashboard._load_items(limit=2, date_filter="all")
        assert len(limited_items) == 2

    def test_metrics_with_real_categorization(self):
        """Test metrics calculation with real categorization."""
        items = [
            {"timestamp": "20250101_000000", "status": "success", "reason": "Fix n=2 edge case"},
            {"timestamp": "20250102_000000", "status": "attempt_fail", "reason": "Binary search failed"},
            {"timestamp": "20250103_000000", "status": "success", "reason": "Path handling on Windows"},
            {"timestamp": "20250104_000000", "status": "initial_pass", "reason": "pytest fixture added"},
        ]

        stats = dashboard._metrics(items)

        # Verify categorization worked
        cats = stats["categories"]
        assert "境界値/特例" in cats
        assert "アルゴリズム/計算量" in cats
        assert "I/O・パス・環境" in cats
        assert "テスト修正/品質" in cats

    def test_daily_aggregation_accuracy(self):
        """Test accuracy of daily event aggregation."""
        items = [
            {"timestamp": "20250101_100000", "status": "success", "reason": "fix1"},
            {"timestamp": "20250101_110000", "status": "success", "reason": "fix2"},
            {"timestamp": "20250101_120000", "status": "attempt_fail", "reason": "fail1"},
            {"timestamp": "20250102_100000", "status": "initial_pass", "reason": "init1"},
        ]

        stats = dashboard._metrics(items)
        by_day = stats["by_day"]

        # Check Jan 1st
        jan1 = date(2025, 1, 1)
        assert by_day[jan1]["success"] == 2
        assert by_day[jan1]["attempt"] == 1
        assert by_day[jan1]["initial"] == 0

        # Check Jan 2nd
        jan2 = date(2025, 1, 2)
        assert by_day[jan2]["success"] == 0
        assert by_day[jan2]["attempt"] == 0
        assert by_day[jan2]["initial"] == 1


# ============================================================================
# Edge Case Tests
# ============================================================================


class TestEdgeCases:
    """Tests for edge cases and error conditions."""

    def test_metrics_division_by_zero_protection(self):
        """Test that metrics handles division by zero."""
        items = []
        stats = dashboard._metrics(items)

        # Should not raise ZeroDivisionError
        assert stats["success_rate"] == 0.0
        assert stats["recent_success_rate"] == 0.0

    def test_load_items_with_malformed_json(self, temp_patch_dir, monkeypatch):
        """Test loading items with malformed JSON files."""
        # Create malformed JSON
        bad_file = temp_patch_dir / "patch_20250101_000000.json"
        bad_file.write_text("{invalid json", encoding="utf-8")

        monkeypatch.setattr(dashboard, "PATCH_HISTORY_DIRS", [temp_patch_dir])

        # Should not crash, just skip bad files
        items = dashboard._load_items(limit=None, date_filter="all")
        assert isinstance(items, list)

    def test_categorize_with_none_input(self):
        """Test categorization with None input."""
        result = dashboard._categorize(None)
        assert result == "不明"

    def test_parse_ts_with_none_input(self):
        """Test timestamp parsing with None input."""
        with pytest.raises((TypeError, AttributeError)):
            dashboard._parse_ts(None)
