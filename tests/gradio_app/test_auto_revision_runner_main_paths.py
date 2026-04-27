import json

from nexuscore.archive.gradio_app import auto_revision_runner as arr


def test_snapshot_and_diff(tmp_path, monkeypatch):
    # prepare sandbox
    monkeypatch.setattr(arr, "SANDBOX_DIRS", [tmp_path])
    f = tmp_path / "a.py"
    f.write_text("x=1\n", encoding="utf-8")
    snap1 = arr.snapshot_sandbox_files()
    f.write_text("x=2\n", encoding="utf-8")
    snap2 = arr.snapshot_sandbox_files()
    diff = arr.build_unified_diff(snap1, snap2)
    assert "x=1" in diff and "x=2" in diff


def test_write_patch_json_and_legacy(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(arr, "PATCH_DIR", tmp_path)
    monkeypatch.setattr(arr, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(arr, "SANDBOX_DIRS", [tmp_path])
    ts = "20250101_000000"
    path = arr.write_patch_json(
        timestamp=ts,
        status="success",
        reason="ok",
        test_log="log",
        code_diff="diff",
        policy={"policy_profile": "p", "policy_version": "v", "policy_icon": "i"},
        attempts=1,
    )
    assert path.exists()
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["status"] == "success"
    arr.write_legacy_log(ts, "log")
    arr.append_legacy_history_line("status", "reason")
    assert (tmp_path / "patch_history.txt").exists()


def test_main_handles_attempt_error(monkeypatch, tmp_path):
    monkeypatch.setattr(arr, "PATCH_DIR", tmp_path)
    monkeypatch.setattr(arr, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(arr, "SANDBOX_DIRS", [tmp_path])
    monkeypatch.setattr(arr, "run_pytest_once", lambda: (False, "log"))
    monkeypatch.setattr(arr, "snapshot_sandbox_files", lambda: {})
    monkeypatch.setattr(arr, "build_unified_diff", lambda *a, **k: "diff")
    monkeypatch.setattr(
        arr, "attempt_auto_fix", lambda prev: (_ for _ in ()).throw(RuntimeError("boom"))
    )
    monkeypatch.setattr(arr, "write_legacy_log", lambda *a, **k: None)
    monkeypatch.setattr(arr, "append_legacy_history_line", lambda *a, **k: None)

    records = []

    def fake_write_patch(**kwargs):
        records.append(kwargs["status"])
        return tmp_path / f"patch_{kwargs['timestamp']}.json"

    monkeypatch.setattr(arr, "write_patch_json", lambda **kw: fake_write_patch(**kw))
    monkeypatch.setattr(arr, "now_tag", lambda: "TS")
    arr.main()
    assert any(status == "attempt_error" for status in records)
