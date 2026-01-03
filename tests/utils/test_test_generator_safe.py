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

    # モジュールをリロードする前にモックを設定
    sys.modules["openai"] = type("M", (), {"OpenAI": lambda api_key=None: DummyClient()})
    sys.modules["dotenv"] = type("M", (), {"load_dotenv": lambda *a, **k: None})

    # モジュールをインポートして、_get_client をモック
    mod = importlib.import_module("nexuscore.utils.test_generator")
    monkeypatch.setattr(mod, "_get_client", lambda: DummyClient())

    out = mod.generate_unit_tests("code")
    # generate_unit_tests は文字列を返すはず
    assert isinstance(out, str)
    assert "generated" in out or "test" in out.lower() or "pytest" in out.lower()
