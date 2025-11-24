import pytest

from nexuscore.agents.coder_agent import CoderAgent


@pytest.fixture(autouse=True)
def disable_llm_router(monkeypatch):
    from nexuscore.agents import base_agent

    monkeypatch.setattr(base_agent, "LLMRouter", None)


def test_implement_code_returns_first_valid_result():
    agent = CoderAgent()
    agent.execute_llm_task = lambda *args, **kwargs: "print('ok')"
    agent._validate_code = lambda lang, code: (True, "")

    result = agent.implement_code("task", "pass")
    assert result == "print('ok')"


def test_implement_code_retries_and_appends_feedback(monkeypatch):
    agent = CoderAgent()
    calls = []
    responses = iter(["bad code", "good code"])

    def fake_execute(prompt, **kwargs):
        calls.append(prompt)
        return next(responses)

    agent.execute_llm_task = fake_execute

    def fake_validate(language, code):
        if code == "good code":
            return True, ""
        return False, "Syntax error"

    agent._validate_code = fake_validate

    result = agent.implement_code("task", "print('hi')")
    assert result == "good code"
    assert any("AST検査フィードバック" in prompt for prompt in calls[1:])


def test_validate_code_catches_python_errors():
    agent = CoderAgent()
    ok, message = agent._validate_code("python", "def bad(")
    assert not ok
    assert "SyntaxError" in message
