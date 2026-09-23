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


#: 契約中のプロバイダのプロファイルID接頭辞（2026-09-23・ふくけい方針「GLM と MiniMax のみ」）
ALLOWED_PROFILE_PREFIXES = ("glm_", "minimax_")


def test_no_offpolicy_provider_anywhere():
    """契約外プロバイダが primary/secondary/fallback のどこにも現れない.

    旧 test_gemini_primary_restricted_to_3_core_tasks（Gemini を3タスクに制限）を
    より強い契約へ置換したもの。非常用フォールバックであっても契約外プロバイダへ
    黙って流れる経路を作らない（2026-09-23: OpenAI は残高枯渇で HTTP 429、
    Gemini/DeepSeek は応答するが契約方針の対象外）。
    """
    def allowed(profile_id: str) -> bool:
        return profile_id.startswith(ALLOWED_PROFILE_PREFIXES)

    violations: list[str] = []
    for task, cfg in TASK_MODEL_CONFIGS.items():
        if not allowed(cfg.primary):
            violations.append(f"{task}.primary={cfg.primary}")
        for sec in cfg.secondary:
            if not allowed(sec):
                violations.append(f"{task}.secondary={sec}")
        if cfg.fallback and not allowed(cfg.fallback):
            violations.append(f"{task}.fallback={cfg.fallback}")

    assert not violations, "契約外プロバイダへの経路が残っています: " + ", ".join(violations)


def test_glm_split_strict_vs_default():
    """GLM 内の使い分けが成立している（重要=glm_strict / 軽量=glm_default）.

    2026-09-23 ふくけい方針「大事なところは GLM-5.3・軽量は GLM-5.3-flash」の固定。
    """
    heavy = ["code_generate", "code_refactor", "debug", "self_heal"]
    light = ["code_explain", "test_generate"]
    for t in heavy:
        assert TASK_MODEL_CONFIGS[t].primary == "glm_strict", f"{t} は重要タスク（glm_strict）"
    for t in light:
        assert TASK_MODEL_CONFIGS[t].primary == "glm_default", f"{t} は軽量タスク（glm_default）"


def test_generation_and_review_use_different_providers():
    """生成(GLM)とレビュー(MiniMax)が別プロバイダであること（自己チェックの偏り回避）."""
    gen = TASK_MODEL_CONFIGS["code_generate"].primary
    rev = TASK_MODEL_CONFIGS["code_review"].primary
    assert gen.startswith("glm_")
    assert rev.startswith("minimax_")


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
