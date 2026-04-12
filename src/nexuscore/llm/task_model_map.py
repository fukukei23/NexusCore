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
        primary="glm_codex",
        secondary=["minimax_analytical"],
        fallback="glm_default",
        temperature=0.2,
    ),
    "code_refactor": TaskModelConfig(
        primary="glm_codex",
        secondary=["minimax_analytical"],
        fallback="glm_default",
    ),
    "code_review": TaskModelConfig(
        primary="glm_strict",
        secondary=["minimax_analytical"],
        fallback="glm_default",
    ),
    "code_explain": TaskModelConfig(
        primary="glm_default",
        secondary=["minimax_default"],
        fallback="glm_nano",
    ),
    "test_generate": TaskModelConfig(
        primary="glm_codex",
        secondary=["minimax_analytical"],
        fallback="glm_default",
    ),
    "debug": TaskModelConfig(
        primary="glm_codex",
        secondary=["minimax_analytical"],
        fallback="glm_default",
    ),
    # --- Planning / architecture / requirements ---
    "architect": TaskModelConfig(
        primary="glm_strict",
        secondary=["minimax_analytical"],
        fallback="glm_default",
    ),
    "arch_design": TaskModelConfig(
        primary="glm_strict",
        secondary=["minimax_analytical"],
        fallback="glm_default",
    ),
    "plan_generate": TaskModelConfig(
        primary="minimax_analytical",
        secondary=["glm_strict"],
        fallback="glm_default",
    ),
    "requirement": TaskModelConfig(
        primary="glm_strict",
        secondary=["minimax_analytical"],
        fallback="glm_default",
    ),
    "requirement_elicit": TaskModelConfig(
        primary="glm_strict",
        secondary=["minimax_analytical"],
        fallback="glm_default",
    ),
    # --- Maintenance / governance ---
    "self_heal": TaskModelConfig(
        primary="glm_codex",
        secondary=["minimax_analytical"],
        fallback="glm_default",
    ),
    "routing_classify": TaskModelConfig(
        primary="glm_nano",
        secondary=["glm_default"],
        fallback="glm_nano",
    ),
    "policy_check": TaskModelConfig(
        primary="glm_strict",
        secondary=["minimax_analytical"],
        fallback="glm_default",
    ),
    "postmortem_analyze": TaskModelConfig(
        primary="glm_strict",
        secondary=["minimax_analytical"],
        fallback="glm_default",
    ),
    "knowledge_curate": TaskModelConfig(
        primary="minimax_analytical",
        secondary=["glm_strict"],
        fallback="glm_default",
    ),
    # --- Commerce / scraping ---
    "scraping_analyze": TaskModelConfig(
        primary="minimax_analytical",
        secondary=["glm_default"],
        fallback="glm_nano",
    ),
    "pricing_strategy": TaskModelConfig(
        primary="minimax_analytical",
        secondary=["glm_strict"],
        fallback="glm_default",
    ),
    "catalog_enrich": TaskModelConfig(
        primary="minimax_default",
        secondary=["glm_nano"],
        fallback="glm_default",
    ),
    "shipping_infer": TaskModelConfig(
        primary="glm_default",
        secondary=["minimax_default"],
        fallback="glm_nano",
    ),
    # --- General chat / creativity ---
    "chat_general": TaskModelConfig(
        primary="minimax_default",
        secondary=["glm_default"],
        fallback="glm_nano",
    ),
    "creative": TaskModelConfig(
        primary="minimax_default",
        secondary=["glm_default"],
        fallback="glm_nano",
    ),
    "analytical": TaskModelConfig(
        primary="minimax_analytical",
        secondary=["glm_strict"],
        fallback="glm_default",
    ),
    "secure": TaskModelConfig(
        primary="glm_strict",
        secondary=["minimax_analytical"],
        fallback="glm_default",
    ),
    "general": TaskModelConfig(
        primary="glm_default",
        secondary=["minimax_default"],
        fallback="glm_nano",
    ),
    "vc_analysis": TaskModelConfig(
        primary="minimax_analytical",
        secondary=["glm_strict"],
        fallback="glm_default",
    ),
    "npe_govern": TaskModelConfig(
        primary="glm_strict",
        secondary=["minimax_analytical"],
        fallback="glm_default",
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
