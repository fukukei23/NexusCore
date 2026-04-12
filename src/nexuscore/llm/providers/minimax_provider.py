from __future__ import annotations

import json
import os

from nexuscore.llm.helpers import DEFAULT_STUB_CONTENT, _real_call_enabled, _strip_jsonish
from nexuscore.llm.http_client import RequestsHTTPError
from nexuscore.llm.runtime import HTTP_CLIENT_FACTORY, REQUEST_TIMEOUT

from .base import BaseLLM


class MiniMaxLLM(BaseLLM):
    """
    MiniMax M2.7 等のMiniMaxモデル想定
    OpenAI互換 chat/completions API使用
    """

    def __init__(self, model_name: str):
        env_model = os.getenv("MINIMAX_MODEL")
        super().__init__(env_model or model_name)
        self.api_key = os.getenv("MINIMAX_API_KEY")
        http_available = HTTP_CLIENT_FACTORY.available
        self.real_calls = _real_call_enabled(self.api_key) and http_available
        if not self.api_key and self.real_calls:
            self.logger.warning("MINIMAX_API_KEY is not set. Falling back to stub mode.")
            self.real_calls = False

        self.base_url = (
            os.getenv("MINIMAX_API_BASE") or os.getenv("MINIMAX_BASE_URL") or "https://api.minimax.chat/v1"
        ).rstrip("/")

        if self.real_calls:
            session = HTTP_CLIENT_FACTORY.create_session()
            if not session:
                self.logger.warning(
                    "MiniMaxLLM could not obtain an HTTP session. Falling back to stub mode."
                )
                self.real_calls = False
            else:
                self.session = session
                self.logger.info("MiniMaxLLM initialized in REAL-CALL mode.")
        else:
            self.logger.info("MiniMaxLLM initialized in STUB mode (reason: missing key or dry-run).")

    def execute(self, prompt: str, system_prompt: str, **kwargs) -> str:
        temperature = kwargs.get("temperature", 0.2)
        as_json = kwargs.get("as_json", False)

        if self.real_calls and self.session:
            try:
                url = f"{self.base_url}/chat/completions"
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                }
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt},
                ]
                payload = {
                    "model": self.model_name,
                    "messages": messages,
                }

                try:
                    payload["temperature"] = float(temperature)
                except (TypeError, ValueError):
                    pass

                max_out = os.getenv("NEXUS_DEFAULT_MAX_OUT_TOKENS")
                if max_out:
                    try:
                        payload["max_tokens"] = int(max_out)
                    except ValueError:
                        pass

                if as_json:
                    payload["response_format"] = {"type": "json_object"}

                resp = self.session.post(
                    url, headers=headers, json=payload, timeout=REQUEST_TIMEOUT
                )
                resp.raise_for_status()

                data = resp.json()
                text = ""
                for ch in data.get("choices") or []:
                    msg = ch.get("message") or {}
                    if msg.get("content"):
                        text += str(msg["content"])

                usage = data.get("usage") or {}
                self.record_usage(
                    prompt_tokens=usage.get("prompt_tokens"),
                    completion_tokens=usage.get("completion_tokens"),
                )

                if not text:
                    raise RuntimeError(
                        f"MiniMax returned no text (finish_reason: {data.get('choices', [{}])[0].get('finish_reason')})."
                    )

                self.last_call_mode = "real"
                return _strip_jsonish(text) if as_json else text

            except RequestsHTTPError as e:
                body = ""
                try:
                    body = e.response.text
                except Exception:
                    pass
                self.log_error("REAL-CALL HTTP error", e, body)
                self.last_call_mode = "stub-fallback"
                fake = {
                    "model": self.model_name,
                    "mode": "minimax-stub-fallback",
                    "preview": "Real call failed. Fallback to stub.",
                    "content": DEFAULT_STUB_CONTENT,
                }
                return json.dumps(fake, ensure_ascii=False) if as_json else fake["preview"]
            except Exception as e:
                self.log_error("REAL-CALL failed", e)
                self.last_call_mode = "stub-fallback"
                fake = {
                    "model": self.model_name,
                    "mode": "minimax-stub-fallback",
                    "preview": "Real call failed. Fallback to stub.",
                    "content": DEFAULT_STUB_CONTENT,
                }
                return json.dumps(fake, ensure_ascii=False) if as_json else fake["preview"]

        self.last_call_mode = "stub"
        fake = {
            "model": self.model_name,
            "mode": "minimax-stub",
            "as_json": as_json,
            "preview": "This is a stubbed MiniMax model response.",
            "content": DEFAULT_STUB_CONTENT,
        }
        return json.dumps(fake, ensure_ascii=False) if as_json else fake["preview"]


__all__ = ["MiniMaxLLM"]
