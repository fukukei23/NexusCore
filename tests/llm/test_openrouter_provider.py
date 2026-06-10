from __future__ import annotations

import pytest

from nexuscore.llm.provider_factory import create_provider, PROVIDER_CLASSES
from nexuscore.llm.providers.openrouter_provider import OpenRouterLLM
from nexuscore.llm.routing_policy import model_family


def test_openrouter_in_provider_classes() -> None:
    assert "openrouter" in PROVIDER_CLASSES
    assert PROVIDER_CLASSES["openrouter"] is OpenRouterLLM


def test_model_family_recognizes_openrouter() -> None:
    assert model_family("openrouter") == "openrouter"
    assert model_family("openrouter:openai/gpt-4o") == "openrouter"


def test_create_provider_returns_openrouter_instance(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NEXUS_LLM_REAL_CALLS", "0")
    provider = create_provider("openrouter:openai/gpt-4o")
    assert isinstance(provider, OpenRouterLLM)


def test_byok_injection_overrides_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NEXUS_LLM_REAL_CALLS", "0")
    provider = create_provider("openrouter:openai/gpt-4o", api_key="sk-or-test-key")
    assert provider.api_key == "sk-or-test-key"
    assert provider.real_calls is True


def test_openrouter_default_base_url() -> None:
    assert OpenRouterLLM.default_base_url == "https://openrouter.ai/api/v1"
    assert OpenRouterLLM.env_key_name == "OPENROUTER_API_KEY"
