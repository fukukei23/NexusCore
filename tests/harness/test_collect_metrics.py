"""Task 25: collect_harness_metrics の単体テスト（tmp_path完結・実artifacts非依存）"""
from __future__ import annotations

import json
from pathlib import Path

from scripts.collect_harness_metrics import _extract_last_json, collect_metrics


def _write_state(root: Path, name: str, abort: str | None, tokens: int,
                 breaker: str = "CLOSED", opened: str | None = None) -> None:
    d = root / "artifacts/harness"
    d.mkdir(parents=True, exist_ok=True)
    data = {"loop_steps": 1, "tokens_used": tokens, "breaker_state": breaker,
            "provider": "mock", "abort_reason": abort, "breaker_opened_at": opened,
            "probe_attempts": 0, "probe_results": [], "in_flight_tool": None,
            "schema_version": 1, "updated_at": "2026-09-09T00:00:00Z"}
    (d / name).write_text(json.dumps({"data": data, "checksum": "x", "schema_version": 1}))


def test_abort_distribution_and_tokens(tmp_path: Path) -> None:
    _write_state(tmp_path, "run_state.json", "limits", 100)
    _write_state(tmp_path, "run_state_a.json", None, 300)
    m = collect_metrics(tmp_path)["metrics"]
    assert m["abort_distribution"] == {"limits": 1, "none": 1}
    assert m["tokens_per_task"] == {"runs": 2, "mean": 200, "max": 300, "min": 100}


def test_breaker_open_counts_as_429_proxy(tmp_path: Path) -> None:
    _write_state(tmp_path, "run_state.json", None, 10,
                 breaker="OPEN", opened="2026-09-09T00:00:00Z")
    _write_state(tmp_path, "run_state_b.json", None, 10)
    m = collect_metrics(tmp_path)["metrics"]
    assert m["rate_limit_429_proxy_breaker_opens"] == 1
    assert m["breaker_transitions"] == 1


def test_checkpoint_last_json_extracted(tmp_path: Path) -> None:
    cp = tmp_path / "artifacts/checkpoints/phase1/2026-09-09"
    cp.mkdir(parents=True)
    log = 'y\n[ASK] tool=read_file → approve?: y\n{"content": "ok", "abort_reason": null}'
    (cp / "log.json").write_text(log)
    m = collect_metrics(tmp_path)["metrics"]
    assert m["checkpoint_failure_rate"] == {"failed": 0, "total": 1, "rate": 0.0}


def test_checkpoint_unparseable_counts_as_failure(tmp_path: Path) -> None:
    cp = tmp_path / "artifacts/checkpoints/phase2/2026-09-09"
    cp.mkdir(parents=True)
    (cp / "log.json").write_text("not json at all")
    m = collect_metrics(tmp_path)["metrics"]
    assert m["checkpoint_failure_rate"]["failed"] == 1


def test_extract_last_json_prefers_trailing_object() -> None:
    text = 'pre {"a": 1} post {"content": "x", "abort_reason": "limits"}'
    assert _extract_last_json(text) == {"content": "x", "abort_reason": "limits"}


def test_extract_last_json_pure_json_with_braces_in_content() -> None:
    """回帰（2026-09-09 phase1 log実測）: 純JSONファイル（外括弧=位置0・
    content内に波括弧混入）が range(len-1, 0, -1) の境界抜けで None になっていた"""
    text = '{"content": "報告 ```json {a:1}``` 含む", "abort_reason": null}'
    assert _extract_last_json(text) == {"content": "報告 ```json {a:1}``` 含む",
                                        "abort_reason": None}


def test_main_writes_to_custom_out(tmp_path: Path) -> None:
    """collect main(): --out指定で指定パスに書く（CLI経路・4周目網羅）"""
    import sys

    from scripts import collect_harness_metrics as c
    out = tmp_path / "custom" / "metrics.json"
    old_argv = sys.argv
    sys.argv = ["collect_harness_metrics.py", "--root", str(tmp_path),
                "--out", str(out)]
    try:
        rc = c.main()
    finally:
        sys.argv = old_argv
    assert rc == 0 and out.exists()
