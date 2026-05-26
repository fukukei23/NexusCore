from __future__ import annotations

import json
import logging
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from nexuscore.llm.helpers import DEFAULT_STUB_CONTENT, normalize_model
from nexuscore.llm.http_client import RequestsHTTPError

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

    def execute_real_or_fallback(
        self,
        provider_name: str,
        real_call_fn: Callable[[], str],
        as_json: bool = False,
    ) -> str:
        """Execute a real LLM call with standardized error handling.

        Wraps the common try/except pattern: real call → HTTP error log →
        generic error log → stub fallback. Providers should use this
        instead of duplicating the error handling boilerplate.

        Args:
            provider_name: Display name for log messages (e.g. "openai").
            real_call_fn: Callable that performs the actual HTTP/SDK call
                and returns the response text.
            as_json: Whether to return JSON-formatted stub on fallback.
        """
        try:
            result = real_call_fn()
            self.last_call_mode = "real"
            return result
        except RequestsHTTPError as e:
            body = ""
            try:
                body = e.response.text
            except Exception:  # noqa: BLE001 — HTTPレスポンスボディ取得の防御的キャッチ
                pass
            self.log_error("REAL-CALL HTTP error (after retries)", e, body)
            return self._stub_fallback_response(provider_name, as_json=as_json)
        except Exception as e:  # noqa: BLE001 — リアルコール全体のフォールバック
            self.log_error("REAL-CALL failed (after retries)", e)
            return self._stub_fallback_response(provider_name, as_json=as_json)


__all__ = ["BaseLLM"]
