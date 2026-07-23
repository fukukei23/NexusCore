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
    # --- OpenAI profiles ---
    "gpt_codex": LLMProfile(
        name="gpt_codex",
        provider="openai",
        model="gpt-5.5",
        description="GPT-5.5 for code generation and debugging",
        default_temperature=0.2,
    ),
    "gpt_strict": LLMProfile(
        name="gpt_strict",
        provider="openai",
        model="gpt-5.5",
        description="GPT-5.5 for high-accuracy reasoning",
        default_temperature=0.15,
    ),
    # --- Anthropic profiles ---
    "sonnet_review": LLMProfile(
        name="sonnet_review",
        provider="anthropic",
        model="claude-sonnet-4-6",
        description="Claude Sonnet for reviews and architecture design",
        default_temperature=0.15,
    ),
    "sonnet_code": LLMProfile(
        name="sonnet_code",
        provider="anthropic",
        model="claude-sonnet-4-6",
        description="Claude Sonnet for code and debugging",
        default_temperature=0.2,
    ),
    # --- Google Gemini profiles ---
    "gemini_secondary": LLMProfile(
        name="gemini_secondary",
        provider="google",
        model="gemini-3.1-pro-preview",
        description="Gemini 3.1 Pro Preview for secondary analysis",
        default_temperature=0.2,
    ),
    # --- GLM (Zhipu AI) profiles ---
    "glm_default": LLMProfile(
        name="glm_default",
        provider="glm",
        model="glm-5.2",
        description="GLM-5.2 for lightweight general tasks",
        default_temperature=0.2,
    ),
    "glm_strict": LLMProfile(
        name="glm_strict",
        provider="glm",
        model="glm-5.2",
        description="GLM-5.2 for lightweight high-accuracy tasks",
        default_temperature=0.15,
    ),
    # --- MiniMax profiles ---
    "minimax_default": LLMProfile(
        name="minimax_default",
        provider="minimax",
        model="minimax-m3",
        description="MiniMax M3 for general chat and creative tasks",
        default_temperature=0.2,
    ),
    "minimax_analytical": LLMProfile(
        name="minimax_analytical",
        provider="minimax",
        model="minimax-m3",
        description="MiniMax M3 for analytical and structured tasks",
        default_temperature=0.15,
    ),
    # --- OpenRouter BYOK profiles (ユーザーのOpenRouterキーで100+モデルにアクセス) ---
    "or_gpt_codex": LLMProfile(
        name="or_gpt_codex",
        provider="openrouter",
        model="openai/gpt-4.1",
        description="GPT-4.1 via OpenRouter — code generation",
        default_temperature=0.2,
    ),
    "or_sonnet": LLMProfile(
        name="or_sonnet",
        provider="openrouter",
        model="anthropic/claude-sonnet-4-6",
        description="Claude Sonnet via OpenRouter — reviews & architecture",
        default_temperature=0.15,
    ),
    "or_gemini": LLMProfile(
        name="or_gemini",
        provider="openrouter",
        model="google/gemini-2.5-flash-preview",
        description="Gemini 2.5 Flash via OpenRouter — secondary analysis",
        default_temperature=0.2,
    ),
    "or_deepseek": LLMProfile(
        name="or_deepseek",
        provider="openrouter",
        model="deepseek/deepseek-r1-0528",
        description="DeepSeek R1 via OpenRouter — reasoning",
        default_temperature=0.15,
    ),
    "or_glm": LLMProfile(
        name="or_glm",
        provider="openrouter",
        model="thudm/glm-4-32k",
        description="GLM-4 via OpenRouter — lightweight chat",
        default_temperature=0.2,
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
