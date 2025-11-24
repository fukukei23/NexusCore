from nexuscore.agents.debugger_agent import DebuggerAgent


def test_debug_and_patch_no_files():
    dbg = DebuggerAgent()
    result = dbg.debug_and_patch("log", {}, ".")
    assert result["error"].startswith("No files")


def test_generate_fixed_code_handles_fence(monkeypatch):
    dbg = DebuggerAgent()
    monkeypatch.setattr(dbg, "execute_llm_task", lambda *a, **k: "```python\nprint('x')\n```")
    fixed = dbg._generate_fixed_code("log", "file.py", "print('old')", "inst")
    assert "print('x')" in fixed


def test_generate_fixed_code_handles_exception(monkeypatch):
    dbg = DebuggerAgent()
    monkeypatch.setattr(dbg, "execute_llm_task", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")))
    fixed = dbg._generate_fixed_code("log", "f.py", "code", "inst")
    assert fixed is None
