import logging

import pytest

from nexuscore.agents.coder_agent import CoderAgent


@pytest.fixture(autouse=True)
def patch_base_init(monkeypatch):
    monkeypatch.setattr(
        "nexuscore.agents.coder_agent.BaseAgent.__init__", lambda self: None
    )


def test_implement_code_success(monkeypatch):
    agent = CoderAgent()
    agent.logger = logging.getLogger("test")

    execute_calls = []

    def fake_execute(self, prompt, task_type=None):
        execute_calls.append((prompt, task_type))
        return "print('ok')"

    monkeypatch.setattr(CoderAgent, "execute_llm_task", fake_execute)

    validate_calls = []

    def fake_validate(self, language, code):
        validate_calls.append((language, code))
        return True, ""

    monkeypatch.setattr(CoderAgent, "_validate_code", fake_validate)

    result = agent.implement_code("do work", "pass")

    assert result == "print('ok')"
    assert len(execute_calls) == 1
    assert validate_calls == [("python", "print('ok')")]


def test_implement_code_retries_on_syntax_error(monkeypatch):
    agent = CoderAgent()
    agent.logger = logging.getLogger("test")

    prompts = []
    outputs = ["bad-code", "good_code"]

    def fake_execute(self, prompt, task_type=None):
        prompts.append(prompt)
        return outputs.pop(0)

    monkeypatch.setattr(CoderAgent, "execute_llm_task", fake_execute)

    validations = iter([(False, "SyntaxError: boom"), (True, "")])

    def fake_validate(self, language, code):
        valid, msg = next(validations)
        return valid, msg

    monkeypatch.setattr(CoderAgent, "_validate_code", fake_validate)

    result = agent.implement_code("task", "code")

    assert result == "good_code"
    assert len(prompts) == 2
    assert "# AST検査フィードバック: SyntaxError: boom" in prompts[1]
