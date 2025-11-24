import pytest

from nexuscore.llm.routing_policy import (
    LEGACY_TO_TASK,
    TASK_MODEL_MAP_DEFAULT,
    model_family,
    split_provider,
)


def test_model_family_detects_openai():
    assert model_family("openai:gpt-5") == "openai"
    assert model_family("google:gemini-2.5-flash") == "gemini"
    assert model_family("local-fallback") == "local"


def test_split_provider_handles_vendorless():
    assert split_provider("anthropic:claude-3") == ("anthropic", "claude-3")
    assert split_provider("gpt-5.1")[0] == "openai"


def test_task_map_has_general_entry():
    assert "general" in TASK_MODEL_MAP_DEFAULT
    assert TASK_MODEL_MAP_DEFAULT["general"]["primary"]


def test_legacy_mapping_alias():
    assert LEGACY_TO_TASK["qa"] == "testing"
    with pytest.raises(KeyError):
        _ = LEGACY_TO_TASK["unknown"]
