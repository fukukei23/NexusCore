import sys
import importlib


def test_test_generator_generate(monkeypatch):
    class DummyChoice:
        def __init__(self, content):
            self.message = type("M", (), {"content": content})

    class DummyResponse:
        def __init__(self, content):
            self.choices = [DummyChoice(content)]

    class DummyClient:
        class chat:
            class completions:
                @staticmethod
                def create(*a, **k):
                    return DummyResponse("generated tests")

    sys.modules["openai"] = type("M", (), {"OpenAI": lambda api_key=None: DummyClient()})
    sys.modules["dotenv"] = type("M", (), {"load_dotenv": lambda *a, **k: None})

    mod = importlib.import_module("nexuscore.utils.test_generator")
    out = mod.generate_unit_tests("code")
    assert "generated" in out
