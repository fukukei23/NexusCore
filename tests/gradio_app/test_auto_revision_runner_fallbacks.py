from types import SimpleNamespace

from nexuscore.archive.gradio_app import auto_revision_runner as arr


def test_load_policy_context_prefers_env(monkeypatch, tmp_path):
    monkeypatch.setenv("NEXUS_POLICY_PROFILE", "env-prof")
    ctx = arr.load_policy_context()
    assert ctx["policy_profile"] == "env-prof"


def test_run_pytest_once_uses_revision_tab(monkeypatch):
    fake_rt = SimpleNamespace(run_pytest=lambda: (True, "ok"))
    monkeypatch.setattr(arr, "RT", fake_rt)
    ok, log = arr.run_pytest_once()
    assert ok is True
    assert "ok" in log

    # when exception, returns false
    fake_rt2 = SimpleNamespace(run_pytest=lambda: (_ for _ in ()).throw(RuntimeError("boom")))
    monkeypatch.setattr(arr, "RT", fake_rt2)
    ok2, log2 = arr.run_pytest_once()
    assert ok2 is False
    assert "rt.run_pytest" in log2


def test_attempt_auto_fix_noop(monkeypatch):
    monkeypatch.setattr(arr, "RT", None)
    ok, log, changes = arr.attempt_auto_fix("prev")
    assert ok is False
    assert "no available" in log
    assert changes == {}
