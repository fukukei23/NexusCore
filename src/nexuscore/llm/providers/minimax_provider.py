from __future__ import annotations

from .openai_compat import OpenAICompatLLM


class MiniMaxLLM(OpenAICompatLLM):
    """MiniMax M2.7 — OpenAI互換"""

    provider_name = "minimax"
    env_key_name = "MINIMAX_API_KEY"
    env_base_urls = ("MINIMAX_API_BASE", "MINIMAX_BASE_URL")
    default_base_url = "https://api.minimax.chat/v1"
    api_path = "/chat/completions"
    stub_label = "minimax"


__all__ = ["MiniMaxLLM"]
