from __future__ import annotations

from nexuscore.llm.providers import (
    AnthropicLLM,
    BaseLLM,
    DeepSeekLLM,
    GeminiLLM,
    GLMLLM,
    LocalLLM,
    MiniMaxLLM,
    MoonshotLLM,
    OpenAILLM,
    OpenRouterLLM,
)
from nexuscore.llm.routing_policy import model_family, split_provider

PROVIDER_CLASSES: dict[str, type[BaseLLM]] = {
    "openai": OpenAILLM,
    "anthropic": AnthropicLLM,
    "google": GeminiLLM,
    "deepseek": DeepSeekLLM,
    "glm": GLMLLM,
    "minimax": MiniMaxLLM,
    "moonshot": MoonshotLLM,
    "local": LocalLLM,
    "openrouter": OpenRouterLLM,
}


def get_provider_class(family: str) -> type[BaseLLM]:
    try:
        return PROVIDER_CLASSES[family]
    except KeyError:
        raise ValueError(f"Unsupported model family '{family}'") from None


def create_provider(model_name: str, api_key: str | None = None) -> BaseLLM:
    vendor, pure_model = split_provider(model_name)
    family = model_family(vendor or pure_model)
    provider_cls = get_provider_class(family)
    instance = provider_cls(pure_model)
    # BYOKキーが渡された場合は環境変数より優先して注入
    if api_key and hasattr(instance, "api_key"):
        instance.api_key = api_key
        instance.real_calls = True
    return instance


__all__ = ["PROVIDER_CLASSES", "get_provider_class", "create_provider"]
