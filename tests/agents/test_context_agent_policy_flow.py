from pathlib import Path
from nexuscore.agents.context_agent import ContextAgent


def test_command_line_policy_setup(monkeypatch, capsys):
    answers = iter(["", "", "", ""])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(answers, ""))
    monkeypatch.setattr(ContextAgent, "_find_project_root", lambda self: str(Path.cwd()))
    agent = ContextAgent()
    policy = agent._command_line_policy_setup()
    assert policy["test_import_policy"] == "関数を直接埋め込み"
    assert policy["error_language"] == "日本語"


def test_request_human_dev_policy_uses_policy_interface(monkeypatch):
    class DummyPI:
        def launch_and_wait_for_input(self, timeout=180):
            return {"method": "ui"}
    monkeypatch.setattr(ContextAgent, "_find_project_root", lambda self: str(Path.cwd()))
    monkeypatch.setattr("nexuscore.agents.context_agent.PolicyInterface", DummyPI)
    agent = ContextAgent()
    policy = agent.request_human_dev_policy()
    assert policy["method"] == "ui"
