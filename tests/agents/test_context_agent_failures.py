from pathlib import Path

from nexuscore.analyzer.context_agent import ContextAgent


def test_load_cached_context_bad_json(tmp_path, capsys, monkeypatch):
    cache = tmp_path / ".nexus_context.json"
    cache.write_text("{ bad", encoding="utf-8")
    monkeypatch.setattr(ContextAgent, "_find_project_root", lambda self: str(tmp_path))
    monkeypatch.setattr(ContextAgent, "_command_line_policy_setup", lambda self: {"method": "cmd"})
    monkeypatch.setattr("nexuscore.agents.context_agent.PolicyInterface", None)
    agent = ContextAgent()
    # should recreate new context instead of crashing
    assert isinstance(agent.context_profile, dict)
    out = capsys.readouterr().out
    assert "コンテキストキャッシュの読み込みに失敗" in out


def test_request_human_dev_policy_no_policy_interface(monkeypatch):
    monkeypatch.setattr(ContextAgent, "_find_project_root", lambda self: str(Path.cwd()))
    # force analyzer/policy_interface init failure
    monkeypatch.setattr(
        "nexuscore.agents.context_agent.ContextAnalyzer",
        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("fail")),
    )
    monkeypatch.setattr(ContextAgent, "_command_line_policy_setup", lambda self: {"method": "cmd"})
    monkeypatch.setattr("nexuscore.agents.context_agent.PolicyInterface", None)
    agent = ContextAgent()
    policy = agent.request_human_dev_policy()
    assert isinstance(policy, dict)
