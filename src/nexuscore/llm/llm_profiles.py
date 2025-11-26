"""
Central registry for LLM profiles referenced by the router.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional


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


PROFILE_REGISTRY: Dict[str, LLMProfile] = {
    "gpt5_default": LLMProfile(
        name="gpt5_default",
        provider="openai",
        model="gpt-5.1-mini",
        description="Fast + low-cost GPT-5.1 mini profile",
        default_temperature=0.2,
    ),
    "gpt5_strict": LLMProfile(
        name="gpt5_strict",
        provider="openai",
        model="gpt-5.1",
        description="Full GPT-5.1 model for high-accuracy reasoning",
        default_temperature=0.15,
    ),
    "gpt5_codex": LLMProfile(
        name="gpt5_codex",
        provider="openai",
        model="gpt-5.1-codex",
        description="Code-oriented GPT-5 variant",
        default_temperature=0.2,
    ),
    "gpt5_nano": LLMProfile(
        name="gpt5_nano",
        provider="openai",
        model="gpt-5-nano",
        description="Ultra-fast GPT-5 nano profile used for lightweight calls",
        default_temperature=0.2,
    ),
    "claude_sonnet_45": LLMProfile(
        name="claude_sonnet_45",
        provider="anthropic",
        model="claude-4.5-sonnet",
        description="Claude 4.5 Sonnet for structured reviews and QA",
        default_temperature=0.2,
    ),
    "gemini_3_pro": LLMProfile(
        name="gemini_3_pro",
        provider="google",
        model="gemini-3.0-pro",
        description="Gemini 3 Pro for planning and analytical tasks",
        default_temperature=0.2,
    ),
    "deepseek_r1": LLMProfile(
        name="deepseek_r1",
        provider="deepseek",
        model="deepseek-r1",
        description="DeepSeek R1 for cross-checking and long-form reasoning",
        default_temperature=0.2,
    ),
}


def get_profile(name: str) -> Optional[LLMProfile]:
    """Return a registered LLM profile by id."""
    return PROFILE_REGISTRY.get(name)


def profile_ids() -> List[str]:
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

