from pathlib import Path

from nexuscore.analyzer.context_agent import ContextAgent


def test_create_new_context_fallback(monkeypatch, tmp_path):
    # isolate from real project files
    monkeypatch.setattr(ContextAgent, "_find_project_root", lambda self: str(tmp_path))
    # avoid file I/O prompts
    monkeypatch.setattr(ContextAgent, "save_context", lambda self, ctx: None)
    monkeypatch.setattr(
        ContextAgent,
        "_create_enhanced_context",
        lambda self: (_ for _ in ()).throw(RuntimeError("fail")),
    )
    monkeypatch.setattr(ContextAgent, "request_human_dev_policy", lambda self: {"method": "mock"})

    agent = ContextAgent()
    ctx = agent.create_new_context()
    assert ctx["dev_policy"]["method"] == "mock"
    assert "tech_stack" in ctx


def test_ask_multiple_choice_default(monkeypatch):
    # empty input should return default indices
    monkeypatch.setattr("builtins.input", lambda prompt="": "")
    agent = ContextAgent(project_root=str(Path.cwd()))
    res = agent._ask_multiple_choice("q", ["a", "b"], default=[1])
    assert res == ["b"]
