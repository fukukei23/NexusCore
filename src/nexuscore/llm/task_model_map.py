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
    # --- Code generation (quality tier) ---
    "code_generate": TaskModelConfig(
        primary="gpt5_codex",
        secondary=["sonnet_code"],
        fallback="glm_default",
        temperature=0.2,
    ),
    "code_refactor": TaskModelConfig(
        primary="gpt5_codex",
        secondary=["sonnet_code"],
        fallback="glm_default",
    ),
    "debug": TaskModelConfig(
        primary="gpt5_codex",
        secondary=["sonnet_code"],
        fallback="glm_default",
    ),
    "test_generate": TaskModelConfig(
        primary="gpt5_codex",
        secondary=["sonnet_code"],
        fallback="glm_default",
    ),
    "self_heal": TaskModelConfig(
        primary="gpt5_codex",
        secondary=["sonnet_code"],
        fallback="glm_default",
    ),
    # --- Reasoning / design (quality tier) ---
    "architect": TaskModelConfig(
        primary="sonnet_review",
        secondary=["gpt5_strict"],
        fallback="glm_strict",
    ),
    "arch_design": TaskModelConfig(
        primary="sonnet_review",
        secondary=["gpt5_strict"],
        fallback="glm_strict",
    ),
    "code_review": TaskModelConfig(
        primary="sonnet_review",
        secondary=["gpt5_strict"],
        fallback="glm_strict",
    ),
    "requirement": TaskModelConfig(
        primary="sonnet_review",
        secondary=["gpt5_strict"],
        fallback="glm_strict",
    ),
    "requirement_elicit": TaskModelConfig(
        primary="sonnet_review",
        secondary=["gpt5_strict"],
        fallback="glm_strict",
    ),
    "plan_generate": TaskModelConfig(
        primary="sonnet_review",
        secondary=["gpt5_strict", "gemini_secondary"],
        fallback="glm_strict",
    ),
    "policy_check": TaskModelConfig(
        primary="sonnet_review",
        secondary=["gpt5_strict"],
        fallback="glm_strict",
    ),
    "postmortem_analyze": TaskModelConfig(
        primary="sonnet_review",
        secondary=["gpt5_strict", "gemini_secondary"],
        fallback="glm_strict",
    ),
    # --- Lightweight general ---
    "chat_general": TaskModelConfig(
        primary="glm_default",
        secondary=["minimax_default"],
        fallback="glm_default",
    ),
    "creative": TaskModelConfig(
        primary="glm_default",
        secondary=["minimax_default"],
        fallback="glm_default",
    ),
    "general": TaskModelConfig(
        primary="glm_default",
        secondary=["minimax_default"],
        fallback="glm_default",
    ),
    "routing_classify": TaskModelConfig(
        primary="glm_strict",
        secondary=["glm_default"],
        fallback="glm_default",
    ),
    # --- Lightweight analytical ---
    "analytical": TaskModelConfig(
        primary="minimax_analytical",
        secondary=["glm_default"],
        fallback="glm_default",
    ),
    "scraping_analyze": TaskModelConfig(
        primary="minimax_analytical",
        secondary=["glm_default"],
        fallback="glm_default",
    ),
    "catalog_enrich": TaskModelConfig(
        primary="minimax_default",
        secondary=["glm_default"],
        fallback="glm_default",
    ),
    "pricing_strategy": TaskModelConfig(
        primary="minimax_analytical",
        secondary=["glm_default"],
        fallback="glm_default",
    ),
    "shipping_infer": TaskModelConfig(
        primary="glm_default",
        secondary=["minimax_default"],
        fallback="glm_default",
    ),
    "vc_analysis": TaskModelConfig(
        primary="minimax_analytical",
        secondary=["glm_default"],
        fallback="glm_default",
    ),
    # --- Governance ---
    "knowledge_curate": TaskModelConfig(
        primary="glm_strict",
        secondary=["minimax_analytical"],
        fallback="glm_default",
    ),
    "npe_govern": TaskModelConfig(
        primary="glm_strict",
        secondary=["minimax_analytical"],
        fallback="glm_default",
    ),
    "secure": TaskModelConfig(
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
