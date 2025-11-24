from nexuscore.llm.llm_router import LLMRouter
from nexuscore.llm.providers.base import BaseLLM


class DummyLLM(BaseLLM):
    def execute(self, prompt: str, system_prompt: str, **kwargs) -> str:
        self.last_call_mode = "stub"
        return "ok"


def test_router_uses_task_classifier(monkeypatch):
    calls = []

    class DummyClassifier:
        def __init__(self, model_name, client):
            self.model_name = model_name
            self.client = client

        def classify(self, prompt: str, task_map):
            calls.append((prompt, tuple(sorted(task_map.keys()))))
            return "general"

    monkeypatch.setattr("nexuscore.llm.task_classifier.TaskClassifier", DummyClassifier)

    def fake_make(self, model_name: str):
        return DummyLLM(model_name)

    monkeypatch.setattr(LLMRouter, "_make_client", fake_make, raising=False)
    router = LLMRouter(task_model_map={"general": {"primary": "local:mock", "fallbacks": []}})

    router.get_llm_for_task("please summarize code")
    assert calls
    assert calls[0][0].startswith("please summarize code")


def test_router_maps_legacy_task(monkeypatch):
    class DummyClassifier:
        def __init__(self, model_name, client):
            self.client = client

        def classify(self, prompt: str, task_map):
            return "qa"

    monkeypatch.setattr("nexuscore.llm.task_classifier.TaskClassifier", DummyClassifier)

    def fake_make(self, model_name: str):
        return DummyLLM(model_name)

    monkeypatch.setattr(LLMRouter, "_make_client", fake_make, raising=False)
    router = LLMRouter(
        task_model_map={
            "testing": {
                "primary": "local:test",
                "fallbacks": [],
            },
            "general": {
                "primary": "local:general",
                "fallbacks": [],
            },
        }
    )

    routed = router.get_llm_for_task("ensure coverage high")
    assert routed.task_type == "testing"
