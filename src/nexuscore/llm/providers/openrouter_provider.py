from __future__ import annotations

from .openai_compat import OpenAICompatLLM


class OpenRouterLLM(OpenAICompatLLM):
    """OpenRouter — 1つのAPIキーで100+モデルにアクセスできるルーター（OpenAI互換）"""

    provider_name = "openrouter"
    env_key_name = "OPENROUTER_API_KEY"
    env_base_urls = ("OPENROUTER_BASE_URL",)
    default_base_url = "https://openrouter.ai/api/v1"
    api_path = "/chat/completions"
    stub_label = "openrouter"


__all__ = ["OpenRouterLLM"]
