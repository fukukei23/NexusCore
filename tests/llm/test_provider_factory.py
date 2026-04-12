import pytest

from nexuscore.llm.provider_factory import create_provider, get_provider_class
from nexuscore.llm.providers.glm_provider import GLMLLM


def test_create_provider_returns_glm_stub(monkeypatch):
    # ensure no real calls by clearing API key
    monkeypatch.delenv("GLM_API_KEY", raising=False)
    provider = create_provider("glm:glm-4-plus")
    assert isinstance(provider, GLMLLM)
    assert provider.real_calls is False


def test_create_provider_defaults_to_glm():
    provider = create_provider("some-unknown-model")
    assert isinstance(provider, GLMLLM)


def test_get_provider_class_invalid_family():
    with pytest.raises(ValueError):
        get_provider_class("nonexistent")
