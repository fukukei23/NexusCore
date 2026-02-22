import json
import sys
from types import SimpleNamespace

from nexuscore.llm.providers.anthropic_provider import AnthropicLLM
from nexuscore.llm.providers.deepseek_provider import DeepSeekLLM
from nexuscore.llm.providers.gemini_provider import GeminiLLM
from nexuscore.llm.providers.moonshot_provider import MoonshotLLM
from nexuscore.llm.providers.openai_provider import OpenAILLM


class FakeHTTPError(Exception):
    def __init__(self, response=None):
        super().__init__("fake http error")
        self.response = response


class FakeResp:
    def __init__(self, text="", json_data=None, status_code=500):
        self.text = text
        self._json = json_data or {}
        self.status_code = status_code

    def raise_for_status(self):
        raise FakeHTTPError(response=self)

    def json(self):
        return self._json


class FakeSession:
    def __init__(self, response=None):
        self.response = response or FakeResp()

    def post(self, *args, **kwargs):
        return self.response


def test_openai_stub_and_fallback(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "")
    oai = OpenAILLM("gpt-4o-mini")
    out = oai.execute("p", "s", as_json=True)
    data = json.loads(out)
    assert data["mode"] == "openai-stub"

    # fallback path when real_calls + http raises
    monkeypatch.setenv("OPENAI_API_KEY", "dummy")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://api.example.com")
    fake_session = FakeSession()
    monkeypatch.setattr(oai, "real_calls", True)
    monkeypatch.setattr(oai, "session", fake_session)
    monkeypatch.setattr(oai, "base_url", "https://api.example.com")
    monkeypatch.setattr(oai, "azure", False)
    monkeypatch.setattr(oai, "api_key", "dummy")

    def fake_raise():
        raise FakeHTTPError(response=FakeResp(text="bad"))

    monkeypatch.setattr(fake_session.response, "raise_for_status", fake_raise)
    out2 = oai.execute("p", "s", as_json=True)
    data2 = json.loads(out2)
    assert data2["mode"] == "openai-stub-fallback"


def test_gemini_stub_and_no_text_fallback(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "")
    gem = GeminiLLM("gemini-2.5-flash")
    stub = gem.execute("p", "s", as_json=True)
    assert "stub" in stub

    # real_calls path but no text -> stub-fallback
    monkeypatch.setenv("GEMINI_API_KEY", "key")
    monkeypatch.setattr(gem, "real_calls", True)
    monkeypatch.setattr(gem, "client", "ok")
    monkeypatch.delitem(sys.modules, "google.generativeai", raising=False)

    class FakePart:
        text = ""

    class FakeContent:
        parts = [FakePart()]

    class FakeCand:
        content = FakeContent()
        finish_reason = "blocked"

    class FakeModel:
        def __init__(self, *a, **k):
            pass

        def generate_content(self, *a, **k):
            return SimpleNamespace(candidates=[FakeCand()])

    class FakeGenAI:
        def GenerativeModel(self, *a, **k):
            return FakeModel()

    monkeypatch.setitem(sys.modules, "google.generativeai", FakeGenAI())
    out = gem.execute("p", "s", as_json=True)
    assert isinstance(out, str) and out


def _provider_fallback(provider_cls, env_key, monkeypatch):
    monkeypatch.setenv(env_key, "key")
    prov = provider_cls("model-x")
    monkeypatch.setattr(prov, "real_calls", True)
    monkeypatch.setattr(prov, "session", FakeSession())
    return prov


def test_deepseek_fallback(monkeypatch):
    prov = _provider_fallback(DeepSeekLLM, "DEEPSEEK_API_KEY", monkeypatch)
    out = prov.execute("p", "s", as_json=True)
    data = json.loads(out)
    assert data["mode"] == "deepseek-stub-fallback"


def test_moonshot_fallback(monkeypatch):
    prov = _provider_fallback(MoonshotLLM, "KIMI_API_KEY", monkeypatch)
    out = prov.execute("p", "s", as_json=True)
    data = json.loads(out)
    assert data["mode"] == "kimi-stub-fallback"


def test_anthropic_fallback(monkeypatch):
    prov = _provider_fallback(AnthropicLLM, "ANTHROPIC_API_KEY", monkeypatch)
    out = prov.execute("p", "s", as_json=True)
    data = json.loads(out)
    assert data["mode"] == "anthropic-stub-fallback"
