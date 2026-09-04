"""Task 12: run_state.py（原子的save/load/quarantine）

plan + round7修正条項:
- save戻り値=Success/PartialFailure（plan本文にはないがround7修正条項）
- orphan temp検出（同一run_idの本体+チェックサムあれば本体採用・なければquarantine）
- breaker_stateに加えbreaker_opened_at/probe_attempts/probe_resultsを状態保持
"""
import json
import os

from nexuscore.harness.run_state import RunState, RunStateStore, SaveResult


def test_atomic_write_creates_file(tmp_path):
    s = RunStateStore(path=tmp_path / "state.json")
    r = s.save(RunState(loop_steps=5, tokens_used=100, breaker_state="CLOSED",
                        provider="openai", in_flight_tool=None, abort_reason=None))
    assert r == SaveResult.SUCCESS
    assert (tmp_path / "state.json").exists()


def test_corrupted_file_goes_to_quarantine(tmp_path):
    p = tmp_path / "state.json"
    p.write_text("{broken json")
    s = RunStateStore(path=p)
    state, reason = s.load_or_quarantine()
    assert state is None
    assert reason is not None
    assert any(tmp_path.glob("quarantine-*.json"))


def test_fcntl_flock_is_available():
    # spec §10: fcntl.flock固定（Linux/WSL前提）
    import fcntl
    assert hasattr(fcntl, "flock")


def test_save_returns_partial_failure_on_disk_full(tmp_path, monkeypatch):
    """round7修正条項: save戻り値でPartialFailureを区別"""
    s = RunStateStore(path=tmp_path / "state.json")
    def boom(*a, **k):
        raise OSError(28, "No space left on device")
    monkeypatch.setattr(os, "replace", boom)
    r = s.save(RunState(loop_steps=1, tokens_used=0))
    assert r == SaveResult.PARTIAL_FAILURE


def test_orphan_temp_with_checksum_adopts_main(tmp_path):
    """round7修正条項: 起動時scanで*.tmp発見→同一run_idのチェックサム+本体があれば本体採用"""
    p = tmp_path / "state.json"
    ck = p.parent / (p.name + ".sha256")
    p.write_text(json.dumps({"data": {"loop_steps": 1}, "checksum": "abc", "schema_version": 1}))
    ck.write_text("abc")
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps({"data": {"loop_steps": 99}, "checksum": "xyz", "schema_version": 1}))
    s = RunStateStore(path=p)
    state, reason = s.load_or_quarantine()
    assert reason is None
    assert state is not None and state.loop_steps == 1  # 本体採用


def test_orphan_temp_without_checksum_quarantines(tmp_path):
    """round7修正条項: *.tmpはあるが本体/チェックサムなし → quarantine化"""
    p = tmp_path / "state.json"
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text("garbage")
    s = RunStateStore(path=p)
    state, reason = s.load_or_quarantine()
    assert state is None
    assert any(tmp_path.glob("quarantine-*.tmp"))


def test_run_state_breaker_extension_fields():
    """round7修正条項: breaker_opened_at/probe_attempts/probe_results"""
    rs = RunState(loop_steps=0, breaker_opened_at="2026-09-04T00:00:00Z",
                  probe_attempts=2, probe_results=[True, False])
    d = rs.to_dict()
    assert d["breaker_opened_at"] == "2026-09-04T00:00:00Z"
    assert d["probe_attempts"] == 2
    assert d["probe_results"] == [True, False]
