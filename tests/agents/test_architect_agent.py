from unittest.mock import patch

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


def test_design_architecture_calls_llm_and_returns_directive():
    agent = ArchitectAgent()
    with patch.object(
        agent,
        "execute_llm_task",
        return_value='{"design_directive": "レイヤードアーキテクチャで実装せよ"}',
    ) as mock_llm:
        result = agent.design_architecture(
            specs={"raw_requirement": "CRUDアプリ"},
            plan={"functions_to_implement": ["create", "read"]},
        )
    mock_llm.assert_called_once()
    assert mock_llm.call_args.kwargs.get("as_json") is True or mock_llm.call_args[0]
    assert result["design_directive"] == "レイヤードアーキテクチャで実装せよ"


def test_design_architecture_empty_llm_response_returns_empty_directive():
    agent = ArchitectAgent()
    with patch.object(agent, "execute_llm_task", return_value=""):
        result = agent.design_architecture(specs={}, plan={})
    assert result == {"design_directive": ""}
