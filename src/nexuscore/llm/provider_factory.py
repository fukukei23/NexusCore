"""
Factory helpers that map model names to provider classes.
"""

from __future__ import annotations

from nexuscore.llm.providers import (
    AnthropicLLM,
    BaseLLM,
    DeepSeekLLM,
    GeminiLLM,
    LocalLLM,
    MoonshotLLM,
    OpenAILLM,
)
from nexuscore.llm.routing_policy import model_family, split_provider

PROVIDER_CLASSES: dict[str, type[BaseLLM]] = {
    "openai": OpenAILLM,
    "gemini": GeminiLLM,
    "kimi": MoonshotLLM,
    "anthropic": AnthropicLLM,
    "deepseek": DeepSeekLLM,
    "local": LocalLLM,
}


def get_provider_class(family: str) -> type[BaseLLM]:
    try:
        return PROVIDER_CLASSES[family]
    except KeyError:
        raise ValueError(f"Unsupported model family '{family}'")


def create_provider(model_name: str) -> BaseLLM:
    vendor, pure_model = split_provider(model_name)
    family = model_family(vendor or pure_model)
    provider_cls = get_provider_class(family)
    return provider_cls(pure_model)


__all__ = ["PROVIDER_CLASSES", "get_provider_class", "create_provider"]
