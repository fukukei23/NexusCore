from __future__ import annotations

import os

from nexuscore.llm.helpers import _real_call_enabled, _strip_jsonish
from nexuscore.llm.http_client import RequestsHTTPError
from nexuscore.llm.runtime import HTTP_CLIENT_FACTORY, REQUEST_TIMEOUT

from .base import BaseLLM


class OpenAILLM(BaseLLM):
    """
    gpt-5.5 / gpt-5 等のOpenAI系モデル想定
    (v2.3.5: BASE URL 誤植修正 + Retry)
    """

    def __init__(self, model_name: str):
        super().__init__(model_name)
        self.api_key = os.getenv("OPENAI_API_KEY")
        http_available = HTTP_CLIENT_FACTORY.available
        self.real_calls = _real_call_enabled(self.api_key) and http_available
        if not self.api_key and self.real_calls:
            self.logger.warning("OPENAI_API_KEY is not set. Falling back to stub mode.")
            self.real_calls = False

        self.base_url = (os.getenv("OPENAI_BASE_URL") or "https://api.openai.com").rstrip("/")
        self.azure = os.getenv("OPENAI_AZURE", "0") == "1"
        self.azure_deployment = os.getenv("OPENAI_AZURE_DEPLOYMENT")
        self.azure_api_version = os.getenv("OPENAI_AZURE_API_VERSION", "2024-08-01-preview")

        if self.real_calls:
            if self.azure and not self.azure_deployment:
                raise ValueError("OPENAI_AZURE=1 requires OPENAI_AZURE_DEPLOYMENT to be set.")
            session = HTTP_CLIENT_FACTORY.create_session()
            if not session:
                self.logger.warning(
                    "OpenAILLM could not obtain an HTTP session. Falling back to stub mode."
                )
                self.real_calls = False
            else:
                self.session = session
                self.logger.info(
                    "OpenAILLM initialized in REAL-CALL mode (Azure: %s, Retry: On).",
                    self.azure,
                )
        else:
            self.logger.info("OpenAILLM initialized in STUB mode (reason: missing key or dry-run).")

    def execute(self, prompt: str, system_prompt: str, **kwargs) -> str:
        temperature = kwargs.get("temperature", 0.2)
        as_json = kwargs.get("as_json", False)

        if self.real_calls and self.session:
            try:
                if self.azure:
                    if not self.azure_deployment:
                        raise ValueError(
                            "OPENAI_AZURE=1 requires OPENAI_AZURE_DEPLOYMENT to be set."
                        )
                    url = (
                        f"{self.base_url}/openai/deployments/{self.azure_deployment}/chat/completions"
                        f"?api-version={self.azure_api_version}"
                    )
                    headers = {"api-key": self.api_key, "Content-Type": "application/json"}
                else:
                    url = f"{self.base_url}/v1/chat/completions"
                    headers = {
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    }

                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt},
                ]
                is_gpt5_or_o = self.model_name.startswith("gpt-5") or self.model_name.startswith(
                    "o"
                )

                payload = {
                    "model": self.model_name,
                    "messages": messages,
                }

                if not is_gpt5_or_o:
                    try:
                        payload["temperature"] = float(temperature)
                    except (TypeError, ValueError):
                        pass

                max_out = os.getenv("NEXUS_DEFAULT_MAX_OUT_TOKENS")
                if max_out:
                    try:
                        max_val = int(max_out)
                    except ValueError:
                        max_val = None

                    if max_val is not None and not (
                        self.model_name.startswith("gpt-5") or self.model_name.startswith("o")
                    ):
                        payload["max_tokens"] = max_val

                if as_json:
                    payload["response_format"] = {"type": "json_object"}

                timeout = REQUEST_TIMEOUT
                resp = self.session.post(url, headers=headers, json=payload, timeout=timeout)
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
                        f"OpenAI returned no text (FinishReason: {data.get('choices', [{}])[0].get('finish_reason')})."
                    )

                self.last_call_mode = "real"
                return _strip_jsonish(text) if as_json else text
            except RequestsHTTPError as e:
                body = ""
                try:
                    body = e.response.text
                except Exception:
                    pass
                self.log_error("REAL-CALL HTTP error (after retries)", e, body)
                return self._stub_fallback_response("openai", as_json=as_json)
            except Exception as e:
                self.log_error("REAL-CALL failed (after retries)", e)
                return self._stub_fallback_response("openai", as_json=as_json)

        return self._stub_response("openai", as_json=as_json)


__all__ = ["OpenAILLM"]
