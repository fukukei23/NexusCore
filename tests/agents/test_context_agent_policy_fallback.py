from pathlib import Path

from nexuscore.analyzer.context_agent import ContextAgent


def test_request_human_dev_policy_interface_exception(monkeypatch):
    class DummyPI:
        def launch_and_wait_for_input(self, timeout=180):
            raise RuntimeError("ui fail")

    monkeypatch.setattr("nexuscore.agents.context_agent.PolicyInterface", DummyPI)
    monkeypatch.setattr(ContextAgent, "_find_project_root", lambda self: str(Path.cwd()))
    monkeypatch.setattr(
        ContextAgent, "_command_line_policy_setup", lambda self: {"method": "cmd-fallback"}
    )
    agent = ContextAgent()
    policy = agent.request_human_dev_policy()
    assert policy["method"].startswith("cmd")
