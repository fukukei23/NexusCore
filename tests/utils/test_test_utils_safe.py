from types import SimpleNamespace
import importlib
import sys


def test_run_tests_file_not_found(monkeypatch):
    mod = importlib.import_module("nexuscore.utils.test_utils")
    monkeypatch.setattr(mod.subprocess, "run", lambda *a, **k: (_ for _ in ()).throw(FileNotFoundError()))
    ok, msg = mod.run_tests(".")
    assert ok is False
    assert "pytest" in msg


def test_run_tests_success(monkeypatch):
    class FakeResult:
        returncode = 0
        stdout = "ok"
        stderr = ""
    mod = importlib.import_module("nexuscore.utils.test_utils")
    monkeypatch.setattr(mod.subprocess, "run", lambda *a, **k: FakeResult())
    ok, msg = mod.run_tests(".")
    assert ok is True
