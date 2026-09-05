from __future__ import annotations

import os
from typing import TYPE_CHECKING, cast

from nexuscore.harness.tool_calling_mixin import InternalToolCall, ToolCallingMixin  # noqa: F401
from nexuscore.llm.helpers import _real_call_enabled, _strip_jsonish
from nexuscore.llm.runtime import REQUEST_TIMEOUT

from .base import BaseLLM

if TYPE_CHECKING:
    # google-generativeai のバージョン差で types が存在しない環境があるため、実行時importは避ける
    from google.generativeai.types import GenerationConfigDict  # pragma: no cover


class GeminiLLM(ToolCallingMixin, BaseLLM):
    """
    gemini-3.1-pro / gemini-2.5-flash 等のGoogle/Geminiモデル想定
    (v2.3.4: Hotfix 3 適用済)

    Task 7: ToolCallingMixin を Mix-in。Gemini `generateContent` 形式 ↔ OpenAI 形式の専用 adapter。
    既存 `execute()` は SDK 経由 (`google.generativeai`) を使うが、`complete_with_tools` は
    HTTP 直接 (`/v1beta/models/{model}:generateContent?key=...`) で叩く。
    """

    def __init__(self, model_name: str):
        super().__init__(model_name)
        api_key = os.getenv("GEMINI_API_KEY")
        self.real_calls = _real_call_enabled(api_key)
        if self.real_calls:
            try:
                import google.generativeai as genai

                genai.configure(api_key=api_key)
                self.client = "ok"
                self.logger.info("GeminiLLM initialized in REAL-CALL mode.")
            except ImportError as e:
                self.logger.warning(
                    "google-generativeai not installed — falling back to stub mode (%s)", e,
                )
                self.client = None  # type: ignore[assignment]
                self.real_calls = False
        else:
            self.client = None  # type: ignore[assignment]
            self.logger.info("GeminiLLM initialized in STUB mode (reason: missing key or dry-run).")

    def _build_real_call(self, prompt: str, system_prompt: str, **kwargs):
        """Return a callable that performs the real SDK call."""
        temperature = kwargs.get("temperature", 0.3)
        as_json = kwargs.get("as_json", False)

        import google.generativeai as genai

        model = genai.GenerativeModel(
            self.model_name,
            system_instruction=system_prompt,
        )

        gen_cfg = {"temperature": float(temperature)}
        max_out = os.getenv("NEXUS_DEFAULT_MAX_OUT_TOKENS")
        if max_out:
            try:
                gen_cfg["max_output_tokens"] = int(max_out)
            except ValueError:
                pass
        gen_cfg["response_mime_type"] = "application/json" if as_json else "text/plain"  # type: ignore[assignment]

        def _call():
            resp = model.generate_content(
                prompt,
                generation_config=cast("GenerationConfigDict", gen_cfg),
            )
            text = ""
            for cand in getattr(resp, "candidates", []) or []:
                parts = getattr(getattr(cand, "content", None), "parts", []) or []
                for part in parts:
                    if hasattr(part, "text") and part.text:
                        text += part.text
            if not text:
                try:
                    text = getattr(resp, "text", "") or ""
                except (AttributeError, ValueError):
                    text = ""
            if not text:
                raise RuntimeError("Gemini returned no text (possibly blocked)")
            return _strip_jsonish(text) if as_json else text

        return _call

    def execute(self, prompt: str, system_prompt: str, **kwargs) -> str:
        as_json = kwargs.get("as_json", False)
        if self.real_calls and self.client:
            try:
                call_fn = self._build_real_call(prompt, system_prompt, **kwargs)
            except Exception as e:  # noqa: BLE001 — Gemini SDK初期化失敗時のフォールバック
                self.log_error("init failed (system)", e)
                return self._stub_fallback_response("gemini", preview="Init failed. Fallback to stub.", as_json=as_json)
            return self.execute_real_or_fallback("gemini", call_fn, as_json=as_json)
        return self._stub_response("gemini", as_json=as_json)

    # --- ToolCallingMixin 3差分フック実装（Task 7・Gemini 専用変換） ---

    def _adapt_request_openai_to_native(
        self, messages: list[dict], tools: list[dict], **kwargs: object
    ) -> dict:
        """OpenAI 形式 → Gemini `generateContent` 形式

        主な変換:
        - system ロールは `systemInstruction.parts[].text` に分離
        - user/assistant は `contents[].parts[].text` に変換（assistant → model）
        - tools は `tools[].functionDeclarations[]` に変換
        """
        sys_msg = next((m.get("content") for m in messages if m.get("role") == "system"), None)
        sys_msg_str = sys_msg if isinstance(sys_msg, str) else ""
        contents = [
            {
                "role": "model" if m.get("role") == "assistant" else "user",
                "parts": [{"text": m.get("content", "")}],
            }
            for m in messages
            if m.get("role") != "system"
        ]
        return {
            "contents": contents,
            "systemInstruction": {"parts": [{"text": sys_msg_str}]} if sys_msg_str else None,
            "tools": [
                {
                    "functionDeclarations": [
                        {
                            "name": t["function"]["name"],
                            "parameters": t["function"].get(
                                "parameters", {"type": "object", "properties": {}}
                            ),
                        }
                        for t in tools
                    ]
                }
            ],
            **kwargs,
        }

    def _adapt_response_native_to_internal(self, raw: dict) -> dict:
        """Gemini `generateContent` response → 中立 {content, tool_calls, usage}

        Gemini は `candidates[0].content.parts[]` に text/functionCall ブロックを混在させる。
        防御ガード付き（candidates空/parts不在等）。
        """
        candidates = raw.get("candidates") or []
        if not candidates:
            return {
                "content": "",
                "tool_calls": [],
                "usage": {"input_tokens": 0, "output_tokens": 0},
            }
        parts = ((candidates[0] or {}).get("content") or {}).get("parts") or []
        if not isinstance(parts, list):
            parts = []
        tcs = []
        text_parts = []
        for p in parts:
            if not isinstance(p, dict):
                continue
            if "functionCall" in p:
                fc = p["functionCall"] or {}
                if not fc.get("name"):
                    continue  # name 不在はスキップ
                tcs.append(InternalToolCall.from_gemini(fc))
            if "text" in p and p["text"]:
                text_parts.append(str(p["text"]))
        usage_meta = raw.get("usageMetadata") or {}
        return {
            "content": "\n".join(text_parts),
            "tool_calls": tcs,
            "usage": {
                "input_tokens": usage_meta.get("promptTokenCount", 0),
                "output_tokens": usage_meta.get("candidatesTokenCount", 0),
            },
        }

    def _call_http_tool(self, body: dict) -> dict:
        """tool 用 HTTP 呼び出し: `/v1beta/models/{model}:generateContent?key=...` にPOST。
        stub 時は固定 functionCall 応答"""
        if not getattr(self, "real_calls", False):
            return self._tool_stub_response()

        url = f"{self.base_url}/v1beta/models/{self.model_name}:generateContent"

        # api_key を query string に乗せる形（既存 Gemini 仕様）
        params = {"key": self.api_key} if getattr(self, "api_key", None) else None

        def _call() -> dict:
            r = self._require_session().post(
                url, params=params, json=body, timeout=REQUEST_TIMEOUT
            )
            r.raise_for_status()
            return r.json()

        # stub_factory 必須: 未指定だと fallback が str を返し dict 契約を破る
        return self.execute_real_or_fallback(
            "gemini", _call, as_json=False, stub_factory=self._tool_stub_response
        )

    def _tool_stub_response(self) -> dict:
        """tool-calling 経路の stub 応答（stub モードと real 失敗時の fallback で共用）"""
        return {
            "candidates": [
                {"content": {"parts": [{"functionCall": {"name": "echo", "args": {"x": "hi"}}}]}}
            ],
            "usageMetadata": {"promptTokenCount": 1, "candidatesTokenCount": 1},
        }


__all__ = ["GeminiLLM"]
