from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

from nexuscore.llm.helpers import DEFAULT_STUB_CONTENT, normalize_model

if TYPE_CHECKING:  # pragma: no cover - typing only
    from requests import Session


class BaseLLM:
    """Common state shared by all provider clients."""

    def __init__(self, model_name: str):
        self.model_name = normalize_model(model_name)
        self.logger = logging.getLogger(self.__class__.__name__)
        self._last_usage: dict[str, int | None] | None = None
        self.last_call_mode: str = "stub"
        self.session: Session | None = None

    def record_usage(
        self,
        prompt_tokens: int | None = None,
        completion_tokens: int | None = None,
    ) -> None:
        """Store usage info in a consistent shape for RoutedLLM."""

        def _cast(value: int | None) -> int | None:
            if value is None:
                return None
            try:
                return int(value)
            except (TypeError, ValueError):
                return None

        self._last_usage = {
            "prompt_tokens": _cast(prompt_tokens),
            "completion_tokens": _cast(completion_tokens),
        }

    def log_error(
        self,
        context: str,
        exc: Exception,
        response_text: str | None = None,
        level: int = logging.ERROR,
    ) -> None:
        """Emit a normalized log message for provider failures."""
        snippet = ""
        if response_text:
            snippet = f" | response_snippet={response_text[:2000]}"
        message = f"{self.__class__.__name__} {context}: {exc}{snippet}"
        self.logger.log(level, message)

    def _stub_fallback_response(
        self,
        mode_prefix: str,
        preview: str = "Real call failed. Fallback to stub.",
        as_json: bool = False,
    ) -> str:
        """Build a stub-fallback response when a real LLM call fails."""
        self.last_call_mode = "stub-fallback"
        fake = {
            "model": self.model_name,
            "mode": f"{mode_prefix}-stub-fallback",
            "preview": preview,
            "content": DEFAULT_STUB_CONTENT,
        }
        return json.dumps(fake, ensure_ascii=False) if as_json else fake["preview"]

    def _stub_response(
        self,
        mode_prefix: str,
        as_json: bool = False,
    ) -> str:
        """Build a stub response when real calls are disabled."""
        self.last_call_mode = "stub"
        fake = {
            "model": self.model_name,
            "mode": f"{mode_prefix}-stub",
            "as_json": as_json,
            "preview": f"This is a stubbed {mode_prefix} model response.",
            "content": DEFAULT_STUB_CONTENT,
        }
        return json.dumps(fake, ensure_ascii=False) if as_json else fake["preview"]

    def execute(
        self, prompt: str, system_prompt: str, **kwargs
    ) -> str:  # pragma: no cover - interface
        raise NotImplementedError("Subclasses must implement execute()")


__all__ = ["BaseLLM"]
