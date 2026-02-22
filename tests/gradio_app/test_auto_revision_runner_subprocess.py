from types import SimpleNamespace

from nexuscore.gradio_app import auto_revision_runner as arr


def test_run_pytest_once_subprocess(monkeypatch):
    # simulate no RT functions, fallback to subprocess path
    monkeypatch.setattr(arr, "RT", None)
    fake = SimpleNamespace(returncode=1, stdout="fail", stderr="err")
    import shlex
    import subprocess

    monkeypatch.setattr(arr, "subprocess", subprocess, raising=False)
    monkeypatch.setattr(arr, "shlex", shlex, raising=False)
    monkeypatch.setattr(arr.subprocess, "run", lambda *a, **k: fake)
    monkeypatch.setattr(arr.shlex, "split", lambda cmd: cmd.split())
    ok, log = arr.run_pytest_once()
    assert ok is False
    assert "fail" in log
