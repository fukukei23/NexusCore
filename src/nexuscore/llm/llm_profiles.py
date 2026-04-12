"""
Central registry for LLM profiles referenced by the router.

NexusCore uses GLM (Zhipu AI) and MiniMax as the sole LLM providers.
All tasks are routed through these two providers only.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LLMProfile:
    """
    Named model profile that captures provider-specific identifiers plus
    basic routing defaults such as preferred temperature.
    """

    name: str
    provider: str
    model: str
    description: str | None = None
    default_temperature: float = 0.2


PROFILE_REGISTRY: dict[str, LLMProfile] = {
    # --- GLM (Zhipu AI) profiles ---
    "glm_default": LLMProfile(
        name="glm_default",
        provider="glm",
        model="glm-4-plus",
        description="GLM-4-Plus for general tasks and code generation",
        default_temperature=0.2,
    ),
    "glm_strict": LLMProfile(
        name="glm_strict",
        provider="glm",
        model="glm-4-plus",
        description="GLM-4-Plus for high-accuracy reasoning and planning",
        default_temperature=0.15,
    ),
    "glm_codex": LLMProfile(
        name="glm_codex",
        provider="glm",
        model="glm-4-plus",
        description="GLM-4-Plus for code generation and debugging",
        default_temperature=0.2,
    ),
    "glm_nano": LLMProfile(
        name="glm_nano",
        provider="glm",
        model="glm-4-flash",
        description="GLM-4-Flash for lightweight and fast calls",
        default_temperature=0.2,
    ),
    # --- MiniMax profiles ---
    "minimax_default": LLMProfile(
        name="minimax_default",
        provider="minimax",
        model="minimax-m2.7",
        description="MiniMax M2.7 for general chat and creative tasks",
        default_temperature=0.2,
    ),
    "minimax_analytical": LLMProfile(
        name="minimax_analytical",
        provider="minimax",
        model="minimax-m2.7",
        description="MiniMax M2.7 for analytical and structured tasks",
        default_temperature=0.15,
    ),
}


def get_profile(name: str) -> LLMProfile | None:
    """Return a registered LLM profile by id."""
    return PROFILE_REGISTRY.get(name)


def profile_ids() -> list[str]:
    """Return all known profile identifiers."""
    return list(PROFILE_REGISTRY.keys())


def profile_to_model_name(profile_id: str) -> str:
    """
    Convert a profile id into the canonical `vendor:model` string.
    Raises ValueError if the profile is missing so issues are caught early.
    """
    profile = get_profile(profile_id)
    if profile is None:
        raise ValueError(f"Unknown LLM profile: {profile_id}")
    return f"{profile.provider}:{profile.model}"


__all__ = [
    "LLMProfile",
    "PROFILE_REGISTRY",
    "get_profile",
    "profile_ids",
    "profile_to_model_name",
]
