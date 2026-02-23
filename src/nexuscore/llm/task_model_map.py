"""
Task to model configuration map built on top of LLM profiles.
"""

from __future__ import annotations

from dataclasses import dataclass

from .llm_profiles import profile_to_model_name


@dataclass(frozen=True)
class TaskModelConfig:
    """Structured mapping from a task to LLM profile candidates."""

    primary: str
    secondary: list[str]
    fallback: str
    temperature: float | None = None


TASK_MODEL_CONFIGS: dict[str, TaskModelConfig] = {
    # --- Core coding tasks ---
    "code_generate": TaskModelConfig(
        primary="gpt5_codex",
        secondary=["deepseek_r1"],
        fallback="gpt5_default",
        temperature=0.2,
    ),
    "code_refactor": TaskModelConfig(
        primary="gpt5_codex",
        secondary=["deepseek_r1"],
        fallback="gpt5_default",
    ),
    "code_review": TaskModelConfig(
        primary="claude_sonnet_45",
        secondary=["gpt5_strict"],
        fallback="gpt5_default",
    ),
    "code_explain": TaskModelConfig(
        primary="gpt5_default",
        secondary=["claude_sonnet_45"],
        fallback="gpt5_nano",
    ),
    "test_generate": TaskModelConfig(
        primary="gpt5_codex",
        secondary=["claude_sonnet_45"],
        fallback="gpt5_default",
    ),
    "debug": TaskModelConfig(
        primary="gpt5_codex",
        secondary=["deepseek_r1"],
        fallback="gpt5_default",
    ),
    # --- Planning / architecture / requirements ---
    "architect": TaskModelConfig(
        primary="gpt5_strict",
        secondary=["gemini_3_pro"],
        fallback="gpt5_default",
    ),
    "arch_design": TaskModelConfig(
        primary="gpt5_strict",
        secondary=["gemini_3_pro"],
        fallback="gpt5_default",
    ),
    "plan_generate": TaskModelConfig(
        primary="gemini_3_pro",
        secondary=["gpt5_strict"],
        fallback="gpt5_default",
    ),
    "requirement": TaskModelConfig(
        primary="gpt5_strict",
        secondary=["claude_sonnet_45"],
        fallback="gpt5_default",
    ),
    "requirement_elicit": TaskModelConfig(
        primary="gpt5_strict",
        secondary=["claude_sonnet_45"],
        fallback="gpt5_default",
    ),
    # --- Maintenance / governance ---
    "self_heal": TaskModelConfig(
        primary="gpt5_codex",
        secondary=["deepseek_r1"],
        fallback="gpt5_default",
    ),
    "routing_classify": TaskModelConfig(
        primary="gpt5_nano",
        secondary=["gpt5_default"],
        fallback="gpt5_nano",
    ),
    "policy_check": TaskModelConfig(
        primary="claude_sonnet_45",
        secondary=["gpt5_strict"],
        fallback="gpt5_default",
    ),
    "postmortem_analyze": TaskModelConfig(
        primary="gpt5_strict",
        secondary=["claude_sonnet_45"],
        fallback="gpt5_default",
    ),
    "knowledge_curate": TaskModelConfig(
        primary="gemini_3_pro",
        secondary=["claude_sonnet_45"],
        fallback="gpt5_default",
    ),
    # --- Commerce / scraping ---
    "scraping_analyze": TaskModelConfig(
        primary="gemini_3_pro",
        secondary=["gpt5_default"],
        fallback="gpt5_nano",
    ),
    "pricing_strategy": TaskModelConfig(
        primary="gemini_3_pro",
        secondary=["claude_sonnet_45"],
        fallback="gpt5_default",
    ),
    "catalog_enrich": TaskModelConfig(
        primary="gemini_3_pro",
        secondary=["gpt5_nano"],
        fallback="gpt5_default",
    ),
    "shipping_infer": TaskModelConfig(
        primary="gpt5_default",
        secondary=["gemini_3_pro"],
        fallback="gpt5_nano",
    ),
    # --- General chat / creativity ---
    "chat_general": TaskModelConfig(
        primary="gpt5_default",
        secondary=["claude_sonnet_45"],
        fallback="gpt5_nano",
    ),
    "creative": TaskModelConfig(
        primary="gpt5_default",
        secondary=["claude_sonnet_45", "gemini_3_pro"],
        fallback="gpt5_nano",
    ),
    "analytical": TaskModelConfig(
        primary="gemini_3_pro",
        secondary=["gpt5_strict"],
        fallback="gpt5_default",
    ),
    "secure": TaskModelConfig(
        primary="claude_sonnet_45",
        secondary=["gpt5_strict"],
        fallback="gpt5_default",
    ),
    "general": TaskModelConfig(
        primary="gpt5_default",
        secondary=["claude_sonnet_45"],
        fallback="gpt5_nano",
    ),
    "vc_analysis": TaskModelConfig(
        primary="claude_sonnet_45",
        secondary=["gpt5_strict", "gemini_3_pro"],
        fallback="gpt5_default",
    ),
    "npe_govern": TaskModelConfig(
        primary="gpt5_strict",
        secondary=["claude_sonnet_45"],
        fallback="gpt5_default",
    ),
}

# Legacy task names expect concrete configs as well.
_TASK_ALIAS_SOURCE = {
    "testing": "test_generate",
    "debugging": "debug",
    "review": "code_review",
    "policy": "policy_check",
    "planning": "plan_generate",
    "requirements": "requirement",
}
for alias, target in _TASK_ALIAS_SOURCE.items():
    if target in TASK_MODEL_CONFIGS:
        TASK_MODEL_CONFIGS[alias] = TASK_MODEL_CONFIGS[target]


LEGACY_TO_TASK = {
    "qa": "testing",
    "test": "testing",
    "tdd": "testing",
    "unit_test": "testing",
    "analysis": "debugging",
    "debug": "debugging",
    "fix": "debugging",
    "review_code": "review",
    "compliance": "policy",
    "governance": "policy",
    "plan": "planning",
    "spec": "requirements",
}


def build_task_model_map_dict() -> dict[str, dict[str, object]]:
    """
    Build a dict matching the legacy TASK_MODEL_MAP_DEFAULT structure.
    """
    result: dict[str, dict[str, object]] = {}
    for task, cfg in TASK_MODEL_CONFIGS.items():
        primary_model = profile_to_model_name(cfg.primary)
        fallbacks = [profile_to_model_name(profile_id) for profile_id in cfg.secondary]
        fallback_model = profile_to_model_name(cfg.fallback)
        if fallback_model not in fallbacks:
            fallbacks.append(fallback_model)
        result_entry: dict[str, object] = {
            "primary": primary_model,
            "fallbacks": fallbacks,
        }
        if cfg.temperature is not None:
            result_entry["temperature"] = cfg.temperature
        result[task] = result_entry
    return result


__all__ = [
    "TaskModelConfig",
    "TASK_MODEL_CONFIGS",
    "LEGACY_TO_TASK",
    "build_task_model_map_dict",
]
