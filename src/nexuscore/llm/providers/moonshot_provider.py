from __future__ import annotations

from .openai_compat import OpenAICompatLLM


class MoonshotLLM(OpenAICompatLLM):
    """Kimi / Moonshot — OpenAI互換"""

    provider_name = "moonshot"
    env_key_name = "KIMI_API_KEY"
    env_base_urls = ("KIMI_BASE_URL",)
    default_base_url = "https://api.moonshot.cn"
    api_path = "/v1/chat/completions"
    default_temperature = 0.3
    stub_label = "kimi"


__all__ = ["MoonshotLLM"]
