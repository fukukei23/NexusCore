import importlib

import pytest

from nexuscore.agents import base_agent


class DummyLLM:
    def __init__(self, response: str = "ok"):
        self.response = response
        self.captured_kwargs = None

    def execute(self, **kwargs):
        self.captured_kwargs = kwargs
        return self.response


class DummyRouter:
    def __init__(self, llm: DummyLLM):
        self.llm = llm
        self.calls = []

    def get_llm_for_task(self, prompt, task_type=None):
        self.calls.append((prompt, task_type))
        return self.llm


def reload_base_agent():
    importlib.reload(base_agent)


@pytest.fixture
def base_agent_cls(monkeypatch):
    reload_base_agent()
    monkeypatch.setattr(base_agent, "HAS_RETRY", False)
    yield base_agent.BaseAgent
    reload_base_agent()


def test_execute_llm_task_routes_and_appends_guard(monkeypatch, base_agent_cls):
    dummy_llm = DummyLLM(response='{"result": "structured"}')
    router = DummyRouter(dummy_llm)
    monkeypatch.setattr(base_agent, "LLMRouter", lambda: router)
    monkeypatch.setattr(base_agent, "HAS_RETRY", False)

    class SampleAgent(base_agent_cls):
        SYSTEM_PROMPT = "Base prompt"

    agent = SampleAgent()
    result = agent.execute_llm_task("analyze", as_json=True, task_type="analysis", temperature=0.2)

    assert result == '{"result": "structured"}'
    assert router.calls == [("analyze", "analysis")]
    assert dummy_llm.captured_kwargs["prompt"] == "analyze"
    assert "Base prompt" in dummy_llm.captured_kwargs["system_prompt"]
    assert "JSON object or array" in dummy_llm.captured_kwargs["system_prompt"]
    assert dummy_llm.captured_kwargs["as_json"] is True
    assert dummy_llm.captured_kwargs["temperature"] == 0.2


def test_execute_llm_task_returns_empty_when_router_missing(monkeypatch, base_agent_cls):
    monkeypatch.setattr(base_agent, "LLMRouter", None)
    monkeypatch.setattr(base_agent, "HAS_RETRY", False)

    class SampleAgent(base_agent_cls):
        pass

    agent = SampleAgent()
    assert agent.llm_router is None
    assert agent.execute_llm_task("noop") == ""
    assert agent.execute_llm_task("json", as_json=True) == "{}"


def test_execute_llm_task_handles_llm_errors(monkeypatch, base_agent_cls):
    class ExplodingLLM(DummyLLM):
        def execute(self, **kwargs):
            raise RuntimeError("boom")

    router = DummyRouter(ExplodingLLM())
    monkeypatch.setattr(base_agent, "LLMRouter", lambda: router)
    monkeypatch.setattr(base_agent, "HAS_RETRY", False)

    class SampleAgent(base_agent_cls):
        pass

    agent = SampleAgent()
    assert agent.execute_llm_task("fails") == ""
    assert agent.execute_llm_task("fails-json", as_json=True) == "{}"
