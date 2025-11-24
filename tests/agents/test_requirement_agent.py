import json

import pytest

from nexuscore.agents.requirement_agent import RequirementAgent


@pytest.fixture(autouse=True)
def disable_llm_router(monkeypatch):
    from nexuscore.agents import base_agent

    monkeypatch.setattr(base_agent, "LLMRouter", None)


def test_analyze_requirement_uses_fallback_when_invalid_json(monkeypatch):
    agent = RequirementAgent()
    agent.set_initial_requirement("Initial CLI tracker")
    agent.execute_llm_task = lambda *args, **kwargs: "not-json"

    plan = agent.analyze_requirement("")
    assert plan["summary"].startswith("Initial CLI tracker")
    assert agent.final_requirements == plan


def test_analyze_requirement_returns_sanitized_data():
    agent = RequirementAgent()
    response = json.dumps(
        {
            "summary": "Task board",
            "features": ["Add task", "List task"],
            "constraints": [],
            "acceptance_criteria": ["All tests pass"],
        }
    )
    agent.execute_llm_task = lambda *args, **kwargs: response
    result = agent.analyze_requirement("Implement board")
    assert result["summary"] == "Task board"
    assert agent.final_requirements == result


def test_generate_final_spec_uses_last_user_message():
    agent = RequirementAgent()
    history = [
        {"role": "assistant", "content": "Hello"},
        {"role": "user", "content": "First idea"},
        {"role": "assistant", "content": "How about..."},
        {"role": "user", "content": "Final request"},
    ]
    spec = agent.generate_final_spec(history)
    assert spec["details"] == "Final request"
