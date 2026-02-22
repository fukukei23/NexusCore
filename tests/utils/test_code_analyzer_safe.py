from nexuscore.utils import code_analyzer


def test_run_tools_handle_exception(monkeypatch):
    monkeypatch.setattr(
        code_analyzer.subprocess, "run", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom"))
    )
    assert code_analyzer.run_pylint("x.py") == 0.0
    ok, msg = code_analyzer.run_mypy("x.py")
    assert ok is False
    ok2, msg2 = code_analyzer.run_bandit(".")
    assert isinstance(ok2, bool)


def test_run_pytest_cov_missing_output(monkeypatch):
    class FakeResult:
        stdout = "no total line"
        stderr = ""

    monkeypatch.setattr(code_analyzer.subprocess, "run", lambda *a, **k: FakeResult())
    cov = code_analyzer.run_pytest_cov(".")
    assert cov == 0.0
