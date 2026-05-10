from __future__ import annotations

import os
from typing import TYPE_CHECKING, cast

from nexuscore.llm.helpers import _real_call_enabled, _strip_jsonish

from .base import BaseLLM

if TYPE_CHECKING:
    # google-generativeai のバージョン差で types が存在しない環境があるため、実行時importは避ける
    from google.generativeai.types import GenerationConfigDict  # pragma: no cover


class GeminiLLM(BaseLLM):
    """
    gemini-3.1-pro / gemini-2.5-flash 等のGoogle/Geminiモデル想定
    (v2.3.4: Hotfix 3 適用済)
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

    def execute(self, prompt: str, system_prompt: str, **kwargs) -> str:
        temperature = kwargs.get("temperature", 0.3)
        as_json = kwargs.get("as_json", False)

        if self.real_calls and self.client:
            try:
                import google.generativeai as genai

                model = genai.GenerativeModel(
                    self.model_name,
                    system_instruction=system_prompt,
                )
            except Exception as e:
                self.log_error("init failed (system)", e)
                return self._stub_fallback_response("gemini", preview="Init failed. Fallback to stub.", as_json=as_json)

            gen_cfg = {"temperature": float(temperature)}
            max_out = os.getenv("NEXUS_DEFAULT_MAX_OUT_TOKENS")
            if max_out:
                try:
                    gen_cfg["max_output_tokens"] = int(max_out)
                except ValueError:
                    pass
            gen_cfg["response_mime_type"] = "application/json" if as_json else "text/plain"  # type: ignore[assignment]

            try:
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
                    finish_reason = None
                    try:
                        finish_reason = getattr(
                            getattr(resp, "candidates", [None])[0], "finish_reason", None
                        )
                    except (AttributeError, IndexError):
                        pass
                    self.logger.warning(
                        "Gemini returned no text (finish_reason=%s). Fallback to stub.",
                        finish_reason,
                    )
                    return self._stub_fallback_response("gemini", preview="No text returned (possibly blocked).", as_json=as_json)

                self.last_call_mode = "real"
                return _strip_jsonish(text) if as_json else text

            except Exception as e:
                self.log_error("REAL-CALL failed", e)
                return self._stub_fallback_response("gemini", as_json=as_json)

        return self._stub_response("gemini", as_json=as_json)


__all__ = ["GeminiLLM"]
