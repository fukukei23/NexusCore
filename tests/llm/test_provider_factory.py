import pytest

from nexuscore.llm.provider_factory import create_provider, get_provider_class
from nexuscore.llm.providers.local_provider import LocalLLM
from nexuscore.llm.providers.openai_provider import OpenAILLM


def test_create_provider_returns_openai_stub(monkeypatch):
    # ensure no real calls by clearing API key
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    provider = create_provider("openai:gpt-5.1")
    assert isinstance(provider, OpenAILLM)
    assert provider.real_calls is False


def test_create_provider_defaults_to_local():
    provider = create_provider("some-unknown-model")
    assert isinstance(provider, LocalLLM)


def test_get_provider_class_invalid_family():
    with pytest.raises(ValueError):
        get_provider_class("nonexistent")
