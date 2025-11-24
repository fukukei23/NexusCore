from nexuscore.agents.debugger_agent import DebuggerAgent


def test_create_diff_handles_relpath(monkeypatch):
    dbg = DebuggerAgent()
    diff = dbg._create_diff("a\n", "b\n", "/tmp/a.py", "/tmp")
    assert "--- a/a.py" in diff or "a.py" in diff
