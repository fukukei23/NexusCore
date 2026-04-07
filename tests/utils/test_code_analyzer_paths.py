import json

from nexuscore.utils import code_analyzer


def test_run_pylint_parses_score(monkeypatch):
    class FakeResult:
        stdout = "Your code has been rated at 8.50/10"

    monkeypatch.setattr(code_analyzer.subprocess, "run", lambda *a, **k: FakeResult())
    score = code_analyzer.run_pylint("x.py")
    assert score == 8.5


def test_run_mypy_success(monkeypatch):
    class FakeResult:
        stdout = "Success: no issues found"
        stderr = ""

    monkeypatch.setattr(code_analyzer.subprocess, "run", lambda *a, **k: FakeResult())
    ok, msg = code_analyzer.run_mypy("x.py")
    assert ok is True
    assert msg == "Passed"


def test_run_bandit_reports_issue(monkeypatch):
    report = {
        "results": [
            {"issue_text": "bad", "issue_severity": "HIGH", "filename": "f.py", "line_number": 1}
        ]
    }

    class FakeResult:
        stdout = json.dumps(report)

    monkeypatch.setattr(code_analyzer.subprocess, "run", lambda *a, **k: FakeResult())
    ok, summary = code_analyzer.run_bandit(".")
    assert ok is False
    assert any("bad" in issue.get("issue_text", "") for issue in summary)


def test_run_pytest_cov_parses_total(monkeypatch):
    class FakeResult:
        stdout = "TOTAL 10 0 100%\n"
        stderr = ""

    monkeypatch.setattr(code_analyzer.subprocess, "run", lambda *a, **k: FakeResult())
    cov = code_analyzer.run_pytest_cov(".")
    assert cov == 100.0
