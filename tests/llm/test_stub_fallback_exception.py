"""C5: silent stub-fallback 解消のテスト（spec E+α改）。

real call 失敗時:
- NEXUSCORE_ALLOW_STUB_FALLBACK 未設定(デフォルト・本番) → 例外送出（汚染ブロック）
- NEXUSCORE_ALLOW_STUB_FALLBACK=1（統合テスト保護） → 従来の stub-fallback 文字列
"""
import json

import pytest

from nexuscore.llm.providers.deepseek_provider import DeepSeekLLM
from nexuscore.llm.providers.openai_provider import OpenAILLM


class FakeHTTPError(Exception):
    """RequestsHTTPError の代替（requests 非依存）。"""

    def __init__(self, response=None):
        super().__init__("fake http error")
        self.response = response


class FakeResp:
    def __init__(self, text="", status_code=500):
        self.text = text
        self.status_code = status_code

    def raise_for_status(self):
        raise FakeHTTPError(response=self)

    def json(self):
        return {}


class FakeSession:
    def __init__(self, response=None):
        self.response = response or FakeResp()

    def post(self, *args, **kwargs):
        return self.response


def _force_real_http_error(provider, monkeypatch, env_key):
    """プロバイダを real_calls 有効 + HTTPエラー必発 に設定。"""
    monkeypatch.setenv(env_key, "dummy")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://api.example.com") if env_key == "OPENAI_API_KEY" else None
    fake_session = FakeSession()
    monkeypatch.setattr(provider, "real_calls", True)
    monkeypatch.setattr(provider, "session", fake_session)
    monkeypatch.setattr(provider, "base_url", "https://api.example.com")
    monkeypatch.setattr(provider, "azure", False)
    monkeypatch.setattr(provider, "api_key", "dummy")

    def fake_raise():
        raise FakeHTTPError(response=FakeResp(text="bad"))

    monkeypatch.setattr(fake_session.response, "raise_for_status", fake_raise)
    return provider


# --- T1: base.py execute_real_or_fallback 経由（openai/gemini/anthropic）---

def test_openai_fallback_raises_without_flag(monkeypatch):
    """フラグOFF(デフォルト)で real失敗時は例外（stub返却しない）。"""
    monkeypatch.delenv("NEXUSCORE_ALLOW_STUB_FALLBACK", raising=False)
    oai = OpenAILLM("gpt-4o-mini")
    _force_real_http_error(oai, monkeypatch, "OPENAI_API_KEY")
    with pytest.raises(FakeHTTPError):
        oai.execute("p", "s", as_json=True)


def test_openai_fallback_stub_with_flag(monkeypatch):
    """フラグONで従来の stub-fallback 文字列を維持（統合テスト保護）。"""
    monkeypatch.setenv("NEXUSCORE_ALLOW_STUB_FALLBACK", "1")
    oai = OpenAILLM("gpt-4o-mini")
    _force_real_http_error(oai, monkeypatch, "OPENAI_API_KEY")
    out = oai.execute("p", "s", as_json=True)
    data = json.loads(out)
    assert data["mode"] == "openai-stub-fallback"


# --- T2: openai_compat.py 経由（deepseek/glm/minimax/moonshot/openrouter）---

def test_deepseek_fallback_raises_without_flag(monkeypatch):
    """フラグOFF(デフォルト)で real失敗時は例外（openai_compat系）。"""
    monkeypatch.delenv("NEXUSCORE_ALLOW_STUB_FALLBACK", raising=False)
    monkeypatch.setenv("DEEPSEEK_API_KEY", "key")
    prov = DeepSeekLLM("model-x")
    monkeypatch.setattr(prov, "real_calls", True)
    fake_session = FakeSession()
    monkeypatch.setattr(prov, "session", fake_session)

    def fake_raise():
        raise FakeHTTPError(response=FakeResp(text="bad"))

    monkeypatch.setattr(fake_session.response, "raise_for_status", fake_raise)
    with pytest.raises(FakeHTTPError):
        prov.execute("p", "s", as_json=True)


def test_deepseek_fallback_stub_with_flag(monkeypatch):
    """フラグONで従来の stub-fallback 文字列を維持（openai_compat系）。"""
    monkeypatch.setenv("NEXUSCORE_ALLOW_STUB_FALLBACK", "1")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "key")
    prov = DeepSeekLLM("model-x")
    monkeypatch.setattr(prov, "real_calls", True)
    monkeypatch.setattr(prov, "session", FakeSession())
    out = prov.execute("p", "s", as_json=True)
    data = json.loads(out)
    assert data["mode"] == "deepseek-stub-fallback"
