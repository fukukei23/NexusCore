import pytest

from dev_tools.fast_lane_check import (
    FastLaneConfig,
    FileChangeStat,
    evaluate_fast_lane,
    format_human_readable,
)


def test_evaluate_fast_lane_respects_override(monkeypatch):
    monkeypatch.setenv("FAST_LANE_FORCE", "1")
    config = FastLaneConfig(allow_override_env="FAST_LANE_FORCE")
    stats = [FileChangeStat(path="a.py", added=1000, deleted=0)]
    result = evaluate_fast_lane(config, stats=stats)
    assert result.is_fast_lane_eligible
    assert "Override" in result.reason


@pytest.mark.parametrize(
    "stats,expected_reason",
    [
        (
            [FileChangeStat(path="a.py", added=10, deleted=5)],
            "Within fast lane thresholds",
        ),
        (
            [FileChangeStat(path="a.py", added=1000, deleted=0)],
            "total",
        ),
    ],
)
def test_evaluate_fast_lane_threshold_logic(stats, expected_reason):
    config = FastLaneConfig(max_total_changed_lines=200)
    result = evaluate_fast_lane(config, stats=stats)
    assert expected_reason in result.reason


def test_format_human_readable_includes_details():
    stats = [
        FileChangeStat(path="a.py", added=10, deleted=2),
        FileChangeStat(path="b.py", added=1, deleted=1),
    ]
    result = evaluate_fast_lane(FastLaneConfig(), stats=stats)
    text = format_human_readable(result)
    assert "a.py" in text
    assert "b.py" in text
