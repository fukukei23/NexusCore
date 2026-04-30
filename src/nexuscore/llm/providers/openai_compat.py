from __future__ import annotations

import json
import os

from nexuscore.llm.helpers import DEFAULT_STUB_CONTENT, _real_call_enabled, _strip_jsonish
from nexuscore.llm.http_client import RequestsHTTPError
from nexuscore.llm.runtime import HTTP_CLIENT_FACTORY, REQUEST_TIMEOUT

from .base import BaseLLM


class OpenAICompatLLM(BaseLLM):
    """
    OpenAI互換 chat/completions API の共通基底クラス。

    GLM, MiniMax, DeepSeek, Moonshot など、/v1/chat/completions または
    /chat/completions エンドポイントを持つプロバイダーはこのクラスを継承し、
    クラス属性のみで設定する。
    """

    # --- サブクラスで上書きするクラス属性 ---
    provider_name: str = "openai-compat"
    env_key_name: str = "API_KEY"
    env_base_urls: tuple[str, ...] = ()
    default_base_url: str = ""
    default_temperature: float = 0.2
    api_path: str = "/chat/completions"
    stub_label: str = "openai-compat"

    def __init__(self, model_name: str):
        env_model = os.getenv(f"{self.provider_name.upper()}_MODEL")
        super().__init__(env_model or model_name)
        self.api_key = os.getenv(self.env_key_name)
        http_available = HTTP_CLIENT_FACTORY.available
        self.real_calls = _real_call_enabled(self.api_key) and http_available
        if not self.api_key and self.real_calls:
            self.logger.warning("%s is not set. Falling back to stub mode.", self.env_key_name)
            self.real_calls = False

        base_url = self.default_base_url
        for env_var in self.env_base_urls:
            val = os.getenv(env_var)
            if val:
                base_url = val
                break
        self.base_url = base_url.rstrip("/")

        if self.real_calls:
            session = HTTP_CLIENT_FACTORY.create_session()
            if not session:
                self.logger.warning(
                    "%s could not obtain an HTTP session. Falling back to stub mode.",
                    self.__class__.__name__,
                )
                self.real_calls = False
            else:
                self.session = session
                self.logger.info("%s initialized in REAL-CALL mode.", self.__class__.__name__)
        else:
            self.logger.info(
                "%s initialized in STUB mode (reason: missing key or dry-run).",
                self.__class__.__name__,
            )

    def execute(self, prompt: str, system_prompt: str, **kwargs) -> str:
        temperature = kwargs.get("temperature", self.default_temperature)
        as_json = kwargs.get("as_json", False)

        if self.real_calls and self.session:
            try:
                url = f"{self.base_url}{self.api_path}"
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
                    finish = data.get("choices", [{}])[0].get("finish_reason")
                    raise RuntimeError(
                        f"{self.provider_name} returned no text (finish_reason: {finish})."
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
                return self._stub_response(as_json, "stub-fallback")

            except Exception as e:
                self.log_error("REAL-CALL failed", e)
                self.last_call_mode = "stub-fallback"
                return self._stub_response(as_json, "stub-fallback")

        self.last_call_mode = "stub"
        return self._stub_response(as_json, "stub")

    def _stub_response(self, as_json: bool, mode_suffix: str) -> str:
        fake = {
            "model": self.model_name,
            "mode": f"{self.stub_label}-{mode_suffix}",
            "as_json": as_json,
            "preview": f"This is a stubbed {self.provider_name} model response.",
            "content": DEFAULT_STUB_CONTENT,
        }
        return json.dumps(fake, ensure_ascii=False) if as_json else fake["preview"]


__all__ = ["OpenAICompatLLM"]
