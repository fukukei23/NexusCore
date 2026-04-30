from __future__ import annotations

from .openai_compat import OpenAICompatLLM


class DeepSeekLLM(OpenAICompatLLM):
    """DeepSeek — OpenAI互換"""

    provider_name = "deepseek"
    env_key_name = "DEEPSEEK_API_KEY"
    env_base_urls = ("DEEPSEEK_BASE_URL",)
    default_base_url = "https://api.deepseek.com"
    api_path = "/v1/chat/completions"
    stub_label = "deepseek"


DeepseekLLM = DeepSeekLLM

__all__ = ["DeepSeekLLM", "DeepseekLLM"]
