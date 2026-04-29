"""
Central registry for LLM profiles referenced by the router.

NexusCore uses a multi-provider architecture:
- Quality tier: GPT-5.5, Sonnet 4.6, Gemini 3.1 Pro
- Lightweight tier: GLM-5.1, MiniMax M2.7
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
    # --- Quality tier: OpenAI ---
    "gpt5_codex": LLMProfile(
        name="gpt5_codex",
        provider="openai",
        model="gpt-5.5",
        description="GPT-5.5 for code generation and debugging",
        default_temperature=0.2,
    ),
    "gpt5_strict": LLMProfile(
        name="gpt5_strict",
        provider="openai",
        model="gpt-5.5",
        description="GPT-5.5 for high-accuracy reasoning",
        default_temperature=0.15,
    ),
    # --- Quality tier: Anthropic ---
    "sonnet_review": LLMProfile(
        name="sonnet_review",
        provider="anthropic",
        model="claude-sonnet-4-6",
        description="Sonnet 4.6 for review and architecture design",
        default_temperature=0.15,
    ),
    "sonnet_code": LLMProfile(
        name="sonnet_code",
        provider="anthropic",
        model="claude-sonnet-4-6",
        description="Sonnet 4.6 for code and debug tasks",
        default_temperature=0.2,
    ),
    # --- Quality tier: Google ---
    "gemini_secondary": LLMProfile(
        name="gemini_secondary",
        provider="google",
        model="gemini-3.1-pro",
        description="Gemini 3.1 Pro as secondary analysis provider",
        default_temperature=0.2,
    ),
    # --- Lightweight tier: GLM ---
    "glm_default": LLMProfile(
        name="glm_default",
        provider="glm",
        model="glm-5.1",
        description="GLM-5.1 for lightweight general tasks",
        default_temperature=0.2,
    ),
    "glm_strict": LLMProfile(
        name="glm_strict",
        provider="glm",
        model="glm-5.1",
        description="GLM-5.1 for lightweight high-accuracy tasks",
        default_temperature=0.15,
    ),
    # --- Lightweight tier: MiniMax ---
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
