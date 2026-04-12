import pytest

from nexuscore.llm.routing_policy import (
    LEGACY_TO_TASK,
    TASK_MODEL_MAP_DEFAULT,
    model_family,
    split_provider,
)


def test_model_family_detects_glm_and_minimax():
    assert model_family("glm:glm-4-plus") == "glm"
    assert model_family("minimax:minimax-m2.7") == "minimax"
    assert model_family("unknown-fallback") == "glm"


def test_split_provider_handles_vendorless():
    assert split_provider("glm:glm-4-plus") == ("glm", "glm-4-plus")
    assert split_provider("glm-4-plus")[0] == "glm"
    assert split_provider("minimax-m2.7")[0] == "minimax"


def test_task_map_has_general_entry():
    assert "general" in TASK_MODEL_MAP_DEFAULT
    assert TASK_MODEL_MAP_DEFAULT["general"]["primary"]


def test_legacy_mapping_alias():
    assert LEGACY_TO_TASK["qa"] == "testing"
    with pytest.raises(KeyError):
        _ = LEGACY_TO_TASK["unknown"]
