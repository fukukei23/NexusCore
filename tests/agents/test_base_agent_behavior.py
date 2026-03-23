from nexuscore.agents.base_agent import BaseAgent


class DummyRouter:
    def __init__(self, llm):
        self.llm = llm

    def get_llm_for_task(self, prompt, task_type=None):
        return self.llm


class DummyLLM:
    def __init__(self):
        self.executed = False
        self.args = None
        self.kwargs = None

    def execute(self, *args, **kwargs):
        self.executed = True
        self.args = args
        self.kwargs = kwargs
        return '{"status": "ok"}'


def test_execute_llm_task_with_json_guard(monkeypatch):
    llm = DummyLLM()
    router = DummyRouter(llm)

    class JsonAgent(BaseAgent):
        SYSTEM_PROMPT = "Base Prompt"

    agent = JsonAgent()
    agent.llm_router = router

    result = agent.execute_llm_task("generate data", as_json=True)

    assert result == '{"status": "ok"}'
    assert llm.executed is True
    assert llm.kwargs["as_json"] is True
    system_prompt = llm.kwargs["system_prompt"]
    assert "Base Prompt" in system_prompt
    assert "Return ONLY a valid JSON object" in system_prompt


def test_execute_llm_task_fallback_when_router_missing(monkeypatch):
    class FallbackAgent(BaseAgent):
        SYSTEM_PROMPT = "Test"

    agent = FallbackAgent()
    agent.llm_router = None

    result = agent.execute_llm_task("anything", as_json=True)
    assert result == "{}"

    result = agent.execute_llm_task("anything", as_json=False)
    assert result == ""
