from __future__ import annotations

import json
import os

from nexuscore.llm.helpers import DEFAULT_STUB_CONTENT, _real_call_enabled, _strip_jsonish
from nexuscore.llm.runtime import HTTP_CLIENT_FACTORY, REQUEST_TIMEOUT

from .base import BaseLLM


class AnthropicLLM(BaseLLM):
    """Claude 3.x 系 (Anthropic)."""

    def __init__(self, model_name: str):
        super().__init__(model_name)
        self.api_key = os.getenv("ANTHROPIC_API_KEY")
        http_available = HTTP_CLIENT_FACTORY.available
        self.real_calls = _real_call_enabled(self.api_key) and http_available
        if not self.api_key and self.real_calls:
            self.logger.warning("ANTHROPIC_API_KEY is not set. Falling back to stub mode.")
            self.real_calls = False
        self.base_url = (os.getenv("ANTHROPIC_BASE_URL") or "https://api.anthropic.com").rstrip("/")
        if self.real_calls:
            session = HTTP_CLIENT_FACTORY.create_session()
            if not session:
                self.logger.warning("AnthropicLLM could not obtain an HTTP session. Falling back to stub mode.")
                self.real_calls = False
            else:
                self.session = session
                self.logger.info("AnthropicLLM initialized in REAL-CALL mode (Retry: On).")
        else:
            self.logger.info("AnthropicLLM initialized in STUB mode (reason: missing key or dry-run).")

    def execute(self, prompt: str, system_prompt: str, **kwargs) -> str:
        temperature = kwargs.get("temperature", 0.3)
        as_json = kwargs.get("as_json", False)
        max_out = kwargs.get("max_tokens") or os.getenv("NEXUS_DEFAULT_MAX_OUT_TOKENS")
        if self.real_calls and self.session:
            try:
                url = f"{self.base_url}/v1/messages"
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    "anthropic-version": "2023-06-01",
                }
                payload = {
                    "model": self.model_name,
                    "messages": [
                        {"role": "user", "content": prompt},
                    ],
                    "system": system_prompt,
                    "temperature": float(temperature),
                }
                if max_out:
                    payload["max_tokens"] = int(max_out)
                resp = self.session.post(
                    url,
                    headers=headers,
                    json=payload,
                    timeout=REQUEST_TIMEOUT,
                )
                resp.raise_for_status()
                data = resp.json()
                content_blocks = data.get("content") or []
                text_parts = []
                for block in content_blocks:
                    if isinstance(block, dict) and block.get("type") == "text" and block.get("text"):
                        text_parts.append(str(block["text"]))
                text = "\n".join(text_parts).strip()

                usage = data.get("usage") or {}
                self.record_usage(
                    prompt_tokens=usage.get("input_tokens"),
                    completion_tokens=usage.get("output_tokens"),
                )

                if not text:
                    raise RuntimeError("Anthropic returned no text.")
                self.last_call_mode = "real"
                return _strip_jsonish(text) if as_json else text
            except Exception as e:
                self.log_error("REAL-CALL failed (after retries)", e)
                self.last_call_mode = "stub-fallback"
                fake = {
                    "model": self.model_name,
                    "mode": "anthropic-stub-fallback",
                    "preview": "Real call failed. Fallback to stub.",
                    "content": DEFAULT_STUB_CONTENT,
                }
                return json.dumps(fake, ensure_ascii=False) if as_json else fake["preview"]

        self.last_call_mode = "stub"
        fake = {
            "model": self.model_name,
            "mode": "anthropic-stub",
            "as_json": as_json,
            "preview": "This is a stubbed Anthropic model response.",
            "content": DEFAULT_STUB_CONTENT,
        }
        return json.dumps(fake, ensure_ascii=False) if as_json else fake["preview"]


__all__ = ["AnthropicLLM"]
