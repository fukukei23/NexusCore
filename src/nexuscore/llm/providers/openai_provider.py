from __future__ import annotations

import json
import os

from nexuscore.harness.tool_calling_mixin import InternalToolCall, ToolCallingMixin
from nexuscore.llm.helpers import _real_call_enabled, _strip_jsonish
from nexuscore.llm.runtime import HTTP_CLIENT_FACTORY, REQUEST_TIMEOUT

from .base import BaseLLM


class OpenAILLM(ToolCallingMixin, BaseLLM):
    """
    gpt-5.5 / gpt-5 等のOpenAI系モデル想定
    (v2.3.5: BASE URL 誤植修正 + Retry)
    (Task 6: ToolCallingMixin を Mix-in・3差分フックをここで吸収)
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

    def _build_real_call(self, prompt: str, system_prompt: str, **kwargs):
        """Return a callable that performs the real HTTP call."""
        temperature = kwargs.get("temperature", 0.2)
        as_json = kwargs.get("as_json", False)

        if self.azure:
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
        is_gpt5_or_o = self.model_name.startswith("gpt-5") or self.model_name.startswith("o")

        payload = {"model": self.model_name, "messages": messages}
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
            if max_val is not None and not is_gpt5_or_o:
                payload["max_tokens"] = max_val

        if as_json:
            payload["response_format"] = {"type": "json_object"}

        def _call():
            resp = self.session.post(url, headers=headers, json=payload, timeout=REQUEST_TIMEOUT)
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
            return _strip_jsonish(text) if as_json else text

        return _call

    def execute(self, prompt: str, system_prompt: str, **kwargs) -> str:
        as_json = kwargs.get("as_json", False)
        if self.real_calls and self.session:
            call_fn = self._build_real_call(prompt, system_prompt, **kwargs)
            return self.execute_real_or_fallback("openai", call_fn, as_json=as_json)
        return self._stub_response("openai", as_json=as_json)

    # --- ToolCallingMixin 3差分フック実装（Task 6・template provider） ---

    def _adapt_request_openai_to_native(
        self, messages: list[dict], tools: list[dict], **kwargs: object
    ) -> dict:
        """OpenAI 形式 → provider native (実は OpenAI そのまま) request body へ変換"""
        return {"model": self.model_name, "messages": messages, "tools": tools, **kwargs}

    def _adapt_response_native_to_internal(self, raw: dict) -> dict:
        """OpenAI chat completions response → {content, tool_calls, usage} へ変換

        OpenAI は tool_calls を `choices[0].message.tool_calls` に `[OpenAI形式TC, ...]` で持つ。
        不正応答（choices 空 / message 不在 / tool_call に function.name 不在等）は
        KeyError/AttributeError で silent crash させないよう防御的にスキップする。
        """
        choices = raw.get("choices") or []
        if not choices:
            return {"content": "", "tool_calls": [], "usage": raw.get("usage") or {}}
        choice = choices[0].get("message") or {}
        tcs = []
        for t in choice.get("tool_calls") or []:
            func = (t or {}).get("function") or {}
            if not func.get("name"):
                # function.name 不在の tool_call はスキップ（不正応答への防御）
                continue
            tcs.append(InternalToolCall.from_openai(t))
        return {
            "content": choice.get("content"),
            "tool_calls": tcs,
            "usage": raw.get("usage") or {},
        }

    def _call_http_tool(self, body: dict) -> dict:
        """HTTP 呼び出し（real_calls=True）または stub 固定応答（real_calls=False）

        既存の self.session / self.real_calls / Azure 設定を再利用する。
        stub 分岐は Task 9 の force_429 経路と区別するため、固定の echo 応答を返す。
        real_calls 経路は execute_real_or_fallback に包んで C5(silent-fallback)対策と
        NEXUSCORE_ALLOW_STUB_FALLBACK の互換性を維持する。
        """
        if not getattr(self, "real_calls", False):
            # stub モード: 固定の echo tool_calls を返す（Task 9 の force_429 とは別経路）
            return {
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": None,
                            "tool_calls": [
                                {
                                    "id": "call_test",
                                    "type": "function",
                                    "function": {"name": "echo", "arguments": json.dumps({"x": "hi"})},
                                }
                            ],
                        }
                    }
                ],
                "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
            }

        # real_calls=True: 既存 execute() と同じ execute_real_or_fallback 経路に乗せる
        # (C5 対策の stub-fallback 制御 / NEXUSCORE_ALLOW_STUB_FALLBACK 互換性を維持)
        if self.azure:
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

        def _call() -> dict:
            r = self.session.post(url, headers=headers, json=body, timeout=REQUEST_TIMEOUT)
            r.raise_for_status()
            return r.json()

        return self.execute_real_or_fallback("openai", _call, as_json=False)


__all__ = ["OpenAILLM"]
