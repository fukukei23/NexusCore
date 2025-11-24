import json

import pytest

from nexuscore.agents.tester_agent import TesterAgent


@pytest.fixture(autouse=True)
def disable_llm_router(monkeypatch):
    from nexuscore.agents import base_agent

    monkeypatch.setattr(base_agent, "LLMRouter", None)


@pytest.fixture
def tester() -> TesterAgent:
    return TesterAgent()


def test_generate_tests_and_testimony_requests_json(tester):
    captured = {}

    def fake_exec(prompt, as_json=False):
        captured["prompt"] = prompt
        captured["as_json"] = as_json
        return json.dumps({"test_code": "assert 1", "testimony": "ok"})

    tester.execute_llm_task = fake_exec
    result = tester.generate_tests_and_testimony("def foo(): pass")

    assert json.loads(result)["test_code"] == "assert 1"
    assert "foo" in captured["prompt"]
    assert captured["as_json"] is True


def test_generate_tests_from_plan_serializes_and_mentions_module(tester):
    captured = {}

    def fake_exec(prompt, as_json=False):
        captured["prompt"] = prompt
        captured["as_json"] = as_json
        return "{}"

    tester.execute_llm_task = fake_exec
    plan = {"functions_to_implement": [{"name": "add", "args": []}]}
    tester.generate_tests_from_plan(plan, "module_x")

    assert "module_x" in captured["prompt"]
    assert '"name": "add"' in captured["prompt"]
    assert captured["as_json"] is True


def test_generate_tests_from_plan_handles_serialization_errors(tester):
    captured = {}

    def fake_exec(prompt, as_json=False):
        captured["prompt"] = prompt
        return "{}"

    tester.execute_llm_task = fake_exec

    class Unserializable:
        pass

    tester.generate_tests_from_plan({"bad": Unserializable()}, "module_y")
    assert "Unserializable" in captured["prompt"]


def test_generate_tests_includes_requirement_summary(tester):
    captured = {}

    def fake_exec(prompt, as_json=False):
        captured["prompt"] = prompt
        return "{}"

    tester.execute_llm_task = fake_exec

    tester.generate_tests("Implement login")
    assert "Implement login" in captured["prompt"]
