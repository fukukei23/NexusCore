import json
import os

import pytest

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


@pytest.mark.skip(reason="_real_call_enabled removed from llm_router.py")
def test_real_call_enabled_requires_key_and_flag(monkeypatch):
    pass


@pytest.mark.skip(reason="_stub_response removed from llm_router.py")
def test_stub_response_returns_json():
    pass


def test_alias_sync_uses_first_available(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setenv("GEMINI_API_KEY_AGENT_A", "value")
    synchronize_aliases()
    assert os.getenv("GEMINI_API_KEY") == "value"
