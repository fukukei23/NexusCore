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


# ---- MLR Task12レビュー採用7件の検証テスト（2026-09-04） ----

def test_load_or_quarantine_takes_lock(tmp_path, monkeypatch):
    """採用#1: load_or_quarantineも同一ロックで保護（saveと並走競合対策）"""
    import fcntl
    p = tmp_path / "state.json"
    p.write_text("{broken")
    calls = []
    real = fcntl.flock
    def spy(fd, op):
        calls.append(op)
        return real(fd, op)
    monkeypatch.setattr(fcntl, "flock", spy)
    s = RunStateStore(path=p)
    s.load_or_quarantine()
    assert fcntl.LOCK_EX in calls, "load_or_quarantineがロックを取得していない"


def test_save_blocks_while_load_holds_lock(tmp_path):
    """採用#1: loadがロック保持中のsaveは完了しない（並走排他の実動作）"""
    import fcntl
    import threading
    p = tmp_path / "state.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    lock = p.with_suffix(p.suffix + ".lock")
    s = RunStateStore(path=p)
    lf = open(lock, "w")
    fcntl.flock(lf.fileno(), fcntl.LOCK_EX)
    done = threading.Event()

    def worker():
        s.save(RunState(loop_steps=1))
        done.set()

    t = threading.Thread(target=worker)
    t.start()
    t.join(timeout=0.5)
    blocked = not done.is_set()
    fcntl.flock(lf.fileno(), fcntl.LOCK_UN)
    lf.close()
    t.join(timeout=5)
    assert blocked, "ロック保持中のsaveがブロックしていない"
    assert done.is_set(), "ロック解放後のsaveが完了していない"


def test_checksum_written_inside_lock(tmp_path, monkeypatch):
    """採用#2: .sha256書込はロック保持中に行う（解放後書込のレース窓対策）"""
    import fcntl
    from pathlib import Path as P
    p = tmp_path / "state.json"
    lock_held = {"v": False}
    real_flock = fcntl.flock
    def spy(fd, op):
        if op == fcntl.LOCK_EX:
            lock_held["v"] = True
        elif op == fcntl.LOCK_UN:
            lock_held["v"] = False
        return real_flock(fd, op)
    monkeypatch.setattr(fcntl, "flock", spy)
    real_write = P.write_text
    def write_spy(self, *a, **k):
        if self.name.endswith(".sha256"):
            assert lock_held["v"], "checksum書込がロック解放後に行われている"
        return real_write(self, *a, **k)
    monkeypatch.setattr(P, "write_text", write_spy)
    s = RunStateStore(path=p)
    assert s.save(RunState(loop_steps=1)) == SaveResult.SUCCESS


def test_quarantine_names_are_unique(tmp_path):
    """採用#3: 同一秒に2回quarantineしても上書きしない（一意名）"""
    p = tmp_path / "state.json"
    s = RunStateStore(path=p)
    p.write_text("{broken1")
    s.load_or_quarantine()
    p.write_text("{broken2")
    s.load_or_quarantine()
    quars = sorted(tmp_path.glob("quarantine-*"))
    assert len(quars) == 2, f"quarantineが衝突・上書きされた: {quars}"


def test_save_failure_removes_tmp_file(tmp_path, monkeypatch):
    """採用#4: save失敗時に.tmp残骸を残さない"""
    p = tmp_path / "state.json"
    s = RunStateStore(path=p)
    def boom(src, dst):
        raise OSError(28, "No space left on device")
    monkeypatch.setattr(os, "replace", boom)
    r = s.save(RunState(loop_steps=1))
    assert r == SaveResult.PARTIAL_FAILURE
    assert not p.with_suffix(p.suffix + ".tmp").exists(), "tmp残骸が残っている"


def test_load_rejects_future_schema_version(tmp_path):
    """採用#5: schema_version不一致は破損扱いでquarantine"""
    p = tmp_path / "state.json"
    p.write_text(json.dumps({"data": {"loop_steps": 1}, "checksum": "x", "schema_version": 999}))
    s = RunStateStore(path=p)
    state, reason = s.load_or_quarantine()
    assert state is None
    assert reason is not None
    assert any(tmp_path.glob("quarantine-*.json"))


def test_save_fsynces_directory(tmp_path, monkeypatch):
    """採用#6: os.replace後のディレクトリfsync（クラッシュ耐性）"""
    fsync_targets = []
    real = os.fsync
    def spy(fd):
        fsync_targets.append(fd)
        return real(fd)
    monkeypatch.setattr(os, "fsync", spy)
    s = RunStateStore(path=tmp_path / "state.json")
    s.save(RunState(loop_steps=1))
    assert len(fsync_targets) >= 2, "ファイル本体とディレクトリの2系統のfsyncが無い"
