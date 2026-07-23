from nexuscore.llm.task_model_map import (
    LEGACY_TO_TASK,
    TASK_MODEL_CONFIGS,
    build_task_model_map_dict,
)


def test_build_task_model_map_dict_shapes():
    mapping = build_task_model_map_dict()
    for task, _cfg in TASK_MODEL_CONFIGS.items():
        assert task in mapping
        entry = mapping[task]
        primary = entry["primary"]
        fallbacks = entry["fallbacks"]
        assert isinstance(primary, str) and ":" in primary
        assert fallbacks, f"{task} must define fallbacks"
        for model in [primary, *fallbacks]:
            vendor, name = model.split(":", 1)
            assert vendor and name


def test_legacy_mapping_targets_exist():
    for legacy_task, resolved in LEGACY_TO_TASK.items():
        assert (
            resolved in TASK_MODEL_CONFIGS
        ), f"Legacy task '{legacy_task}' resolves to missing '{resolved}'"


def test_gemini_primary_restricted_to_3_core_tasks():
    """Gemini節約: Gemini primary は requirement/plan_generate/code_review のみ（エイリアス除く）."""
    aliases = {"testing", "debugging", "review", "policy", "planning", "requirements"}
    core = {k for k in TASK_MODEL_CONFIGS if k not in aliases}
    gemini = {k for k in core if TASK_MODEL_CONFIGS[k].primary == "gemini_secondary"}
    assert gemini == {"requirement", "plan_generate", "code_review"}
    # architect系5タスクはGeminiでない（GLM_strict化）
    for t in ["architect", "arch_design", "requirement_elicit", "policy_check", "postmortem_analyze"]:
        assert TASK_MODEL_CONFIGS[t].primary != "gemini_secondary", f"{t} must not be Gemini"


def test_glm_strict_replaces_gemini_for_5_tasks():
    """5タスクが GLM_strict に切り替わっている."""
    for t in ["architect", "arch_design", "requirement_elicit", "policy_check", "postmortem_analyze"]:
        assert TASK_MODEL_CONFIGS[t].primary == "glm_strict", f"{t} should be glm_strict"


def test_no_gemini_in_code_generation_secondary():
    """Gemini節約: code_generate系3タスクの secondary に gemini_secondary を含まない."""
    for t in ["code_generate", "code_refactor", "code_explain"]:
        assert "gemini_secondary" not in TASK_MODEL_CONFIGS[t].secondary, (
            f"{t} secondary must not contain gemini_secondary"
        )
