from pathlib import Path

from nexuscore.analyzer.context_agent import ContextAgent


def test_ask_choice_reprompts(monkeypatch, capsys):
    answers = iter(["x", "1"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(answers))
    agent = ContextAgent(project_root=str(Path.cwd()))
    choice = agent._ask_choice("q", ["a", "b"], default=0)
    assert choice == "b"


def test_ask_multiple_choice(monkeypatch):
    answers = iter(["bad", "0 1"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(answers))
    agent = ContextAgent(project_root=str(Path.cwd()))
    res = agent._ask_multiple_choice("q", ["a", "b", "c"], default=[0])
    assert res[0] == "a"
