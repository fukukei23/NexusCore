from __future__ import annotations

import os

from nexuscore.harness.tool_calling_mixin import InternalToolCall, ToolCallingMixin
from nexuscore.llm.helpers import _real_call_enabled, _strip_jsonish
from nexuscore.llm.runtime import HTTP_CLIENT_FACTORY, REQUEST_TIMEOUT

from .base import BaseLLM


class AnthropicLLM(ToolCallingMixin, BaseLLM):
    """Claude 3.x 系 (Anthropic).

    Task 7: ToolCallingMixin を Mix-in。Anthropic 形式 (`content` 配列) ↔ OpenAI 形式を変換する専用 adapter を実装。
    """

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
                self.logger.warning(
                    "AnthropicLLM could not obtain an HTTP session. Falling back to stub mode."
                )
                self.real_calls = False
            else:
                self.session = session
                self.logger.info("AnthropicLLM initialized in REAL-CALL mode (Retry: On).")
        else:
            self.logger.info(
                "AnthropicLLM initialized in STUB mode (reason: missing key or dry-run)."
            )

    def _build_real_call(self, prompt: str, system_prompt: str, **kwargs):
        """Return a callable that performs the real HTTP call."""
        temperature = kwargs.get("temperature", 0.3)
        as_json = kwargs.get("as_json", False)
        max_out = kwargs.get("max_tokens") or os.getenv("NEXUS_DEFAULT_MAX_OUT_TOKENS")

        url = f"{self.base_url}/v1/messages"
        headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01",
        }
        payload = {
            "model": self.model_name,
            "messages": [{"role": "user", "content": prompt}],
            "system": system_prompt,
            "temperature": float(temperature),
        }
        if max_out:
            payload["max_tokens"] = int(max_out)

        def _call():
            resp = self.session.post(url, headers=headers, json=payload, timeout=REQUEST_TIMEOUT)
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
            return _strip_jsonish(text) if as_json else text

        return _call

    def execute(self, prompt: str, system_prompt: str, **kwargs) -> str:
        as_json = kwargs.get("as_json", False)
        if self.real_calls and self.session:
            return self.execute_real_or_fallback("anthropic", self._build_real_call(prompt, system_prompt, **kwargs), as_json=as_json)
        return self._stub_response("anthropic", as_json=as_json)

    # --- ToolCallingMixin 3差分フック実装（Task 7・Anthropic 専用変換） ---

    def _adapt_request_openai_to_native(
        self, messages: list[dict], tools: list[dict], **kwargs: object
    ) -> dict:
        """OpenAI 形式 → Anthropic `/v1/messages` リクエスト形式

        主な変換:
        - messages 先頭の `system` ロールは別フィールド `system` に分離
        - tools は `{"name", "description", "input_schema"}` 形式に変換
        """
        sys_msg = next((m["content"] for m in messages if m.get("role") == "system"), None)
        msgs = [m for m in messages if m.get("role") != "system"]
        return {
            "model": self.model_name,
            "system": sys_msg,
            "messages": msgs,
            "tools": [
                {
                    "name": t["function"]["name"],
                    "description": t["function"].get("description", ""),
                    "input_schema": t["function"].get("parameters", {"type": "object", "properties": {}}),
                }
                for t in tools
            ],
            **kwargs,
        }

    def _adapt_response_native_to_internal(self, raw: dict) -> dict:
        """Anthropic response → 中立 {content, tool_calls, usage}

        Anthropic の `content` 配列は text/tool_use ブロックの混在。防御ガード付き。
        """
        blocks = raw.get("content") or []
        if not isinstance(blocks, list):
            blocks = []
        tcs = []
        text_parts = []
        for b in blocks:
            if not isinstance(b, dict):
                continue
            btype = b.get("type")
            if btype == "tool_use":
                if not b.get("name"):
                    continue  # name 不在はスキップ
                tcs.append(InternalToolCall.from_anthropic(b))
            elif btype == "text" and b.get("text"):
                text_parts.append(str(b["text"]))
        return {
            "content": "\n".join(text_parts),
            "tool_calls": tcs,
            "usage": raw.get("usage") or {"input_tokens": 0, "output_tokens": 0},
        }

    def _call_http_tool(self, body: dict) -> dict:
        """tool 用 HTTP 呼び出し: `/v1/messages` にPOST。stub 時は固定 tool_use 応答"""
        if not getattr(self, "real_calls", False):
            return {
                "content": [
                    {"type": "tool_use", "id": "call_test", "name": "echo", "input": {"x": "hi"}}
                ],
                "usage": {"input_tokens": 1, "output_tokens": 1},
            }

        url = f"{self.base_url}/v1/messages"
        headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01",
        }

        def _call() -> dict:
            r = self.session.post(url, headers=headers, json=body, timeout=REQUEST_TIMEOUT)
            r.raise_for_status()
            return r.json()

        return self.execute_real_or_fallback("anthropic", _call, as_json=False)


__all__ = ["AnthropicLLM"]
