from __future__ import annotations

from .openai_compat import OpenAICompatLLM


class GLMLLM(OpenAICompatLLM):
    """GLM-5.1 / GLM-4-Plus (Zhipu AI) — OpenAI互換"""

    provider_name = "glm"
    env_key_name = "GLM_API_KEY"
    env_base_urls = ("GLM_API_BASE", "GLM_BASE_URL")
    default_base_url = "https://open.bigmodel.cn/api/paas/v4"
    api_path = "/chat/completions"
    stub_label = "glm"


__all__ = ["GLMLLM"]
