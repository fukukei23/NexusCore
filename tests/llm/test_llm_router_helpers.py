import json
import os

import pytest

from nexuscore.llm.llm_router import _real_call_enabled, _stub_response
from nexuscore.llm.config import synchronize_aliases


@pytest.fixture(autouse=True)
def clear_env(monkeypatch):
    env_keys = [
        "LLM_DRY_RUN",
        "NEXUS_REAL_CALLS",
        "OPENAI_API_KEY",
        "GEMINI_API_KEY",
        "GEMINI_API_KEY_AGENT_A",
    ]
    for key in env_keys:
        monkeypatch.delenv(key, raising=False)


def test_real_call_enabled_requires_key_and_flag(monkeypatch):
    monkeypatch.setenv("NEXUS_REAL_CALLS", "0")
    assert _real_call_enabled("key") is False  # default NEXUS_REAL_CALLS=0
    monkeypatch.setenv("NEXUS_REAL_CALLS", "1")
    assert _real_call_enabled("key") is True
    monkeypatch.setenv("LLM_DRY_RUN", "1")
    assert _real_call_enabled("key") is False


def test_stub_response_returns_json():
    response = _stub_response("model-x", "stub", "reason", as_json=True)
    payload = json.loads(response)
    assert payload["model"] == "model-x"
    assert payload["content"]["plan"][0]["step"] == "analyze_requirement"


def test_alias_sync_uses_first_available(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setenv("GEMINI_API_KEY_AGENT_A", "value")
    synchronize_aliases()
    assert os.getenv("GEMINI_API_KEY") == "value"
