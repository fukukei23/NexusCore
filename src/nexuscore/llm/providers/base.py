from __future__ import annotations

import json
import logging
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, TypeVar, overload

from nexuscore.llm.helpers import DEFAULT_STUB_CONTENT, _env_flag, normalize_model
from nexuscore.llm.http_client import RequestsHTTPError

if TYPE_CHECKING:  # pragma: no cover - typing only
    from requests import Session

# real_call_fn の戻り値型。execute() 経路は str、tool-calling 経路は provider native dict。
_R = TypeVar("_R")


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
        # silent failure 対策: real呼出無効時(APIキー無し等)に黙ってダミー応答すると
        # 「本物のLLMが動いたか」が判別不能になるため、明示的に WARN を出す。
        self.logger.warning(
            "%s STUB response (real calls disabled): model=%s — "
            "本物のLLMは呼ばれていません（APIキー未設定/real_calls=False 等の可能性）",
            self.__class__.__name__,
            self.model_name,
        )
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

    def _require_session(self) -> Session:
        """HTTP セッションを取得する（未初期化なら明示的に落とす）

        `self.session` は `Session | None` のため、未初期化のまま real 呼び出しすると
        `'NoneType' object has no attribute 'post'` という原因の分かりにくい
        AttributeError になる。各 provider で None チェックを重複させないよう
        ここに集約する（mypy の union-attr も同時に解消）。
        """
        if self.session is None:
            raise RuntimeError(
                f"{self.__class__.__name__}: HTTP session is not initialized "
                "(session が None のまま real 呼び出しが行われました)"
            )
        return self.session

    @overload
    def execute_real_or_fallback(
        self,
        provider_name: str,
        real_call_fn: Callable[[], str],
        as_json: bool = ...,
        stub_factory: None = ...,
    ) -> str: ...

    @overload
    def execute_real_or_fallback(
        self,
        provider_name: str,
        real_call_fn: Callable[[], _R],
        as_json: bool = ...,
        *,
        stub_factory: Callable[[], _R],
    ) -> _R: ...

    def execute_real_or_fallback(
        self,
        provider_name: str,
        real_call_fn: Callable[[], Any],
        as_json: bool = False,
        stub_factory: Callable[[], Any] | None = None,
    ) -> Any:
        """Execute a real LLM call with standardized error handling.

        Wraps the common try/except pattern: real call → HTTP error log →
        generic error log → stub fallback. Providers should use this
        instead of duplicating the error handling boilerplate.

        Args:
            provider_name: Display name for log messages (e.g. "openai").
            real_call_fn: Callable that performs the actual HTTP/SDK call.
                Returns str on the `execute()` path, provider-native dict on
                the tool-calling path.
            as_json: Whether to return JSON-formatted stub on fallback
                (`stub_factory` 未指定時のみ有効)。
            stub_factory: fallback 応答を `real_call_fn` と同じ型で作る callable。
                tool-calling 経路のように戻り値が str でない場合は**必須**。
                未指定だと str の stub が返り、呼び出し側の契約（dict 等）を破る
                （2026-09-05 に AttributeError として実測）。overload により
                mypy が渡し忘れを検出する。
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
            if _env_flag("NEXUSCORE_ALLOW_STUB_FALLBACK", False):
                return self._build_fallback(provider_name, as_json, stub_factory)
            raise
        except Exception as e:  # noqa: BLE001 — リアルコール全体のフォールバック
            self.log_error("REAL-CALL failed (after retries)", e)
            if _env_flag("NEXUSCORE_ALLOW_STUB_FALLBACK", False):
                return self._build_fallback(provider_name, as_json, stub_factory)
            raise

    def _build_fallback(
        self,
        provider_name: str,
        as_json: bool,
        stub_factory: Callable[[], Any] | None,
    ) -> Any:
        """fallback 応答を組み立てる（stub_factory があれば呼び出し側の型に合わせる）"""
        if stub_factory is not None:
            self.last_call_mode = "stub-fallback"
            return stub_factory()
        return self._stub_fallback_response(provider_name, as_json=as_json)


__all__ = ["BaseLLM"]
