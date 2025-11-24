import pytest

from nexuscore.agents.architect_agent import ArchitectAgent


@pytest.fixture(autouse=True)
def disable_llm_router(monkeypatch):
    from nexuscore.agents import base_agent

    monkeypatch.setattr(base_agent, "LLMRouter", None)


def test_design_project_structure_uses_json_mode():
    agent = ArchitectAgent()
    captured = {}

    def fake_execute(prompt, as_json=False):
        captured["prompt"] = prompt
        captured["as_json"] = as_json
        return '{"project": {"files": []}}'

    agent.execute_llm_task = fake_execute
    result = agent.design_project_structure("CLI app")
    assert result == '{"project": {"files": []}}'
    assert "CLI app" in captured["prompt"]
    assert captured["as_json"] is True
