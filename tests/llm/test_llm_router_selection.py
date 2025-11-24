from types import MethodType

from nexuscore.llm.llm_router import LLMRouter
from nexuscore.llm.providers.base import BaseLLM


class DummyLLM(BaseLLM):
    def execute(self, prompt: str, system_prompt: str, **kwargs) -> str:
        self.last_call_mode = "stub"
        return "dummy"


def test_router_fallback_on_provider_failure(monkeypatch):
    task_map = {
        "custom": {
            "primary": "openai:fail-model",
            "fallbacks": [
                "local:dummy-model",
            ],
        }
    }
    router = LLMRouter(task_model_map=task_map)

    calls = []

    def fake_make(self, model_name: str):
        calls.append(model_name)
        if len(calls) == 1:
            raise ValueError("boom")
        return DummyLLM(model_name)

    router._make_client = MethodType(fake_make, router)

    routed = router.get_llm_for_task("please fix bug", task_type="custom")
    assert isinstance(routed.inner, DummyLLM)
    assert calls == ["openai:fail-model", "local:dummy-model"]
