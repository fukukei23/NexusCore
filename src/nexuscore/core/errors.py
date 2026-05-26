from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class NexusCoreError(Exception):
    """NexusCore 全例外の基底クラス。

    全てのカスタム例外はこのクラスを継承する。
    """

    pass


class ModelRateLimitError(NexusCoreError):
    """LLM API レートリミット（HTTP 429）。

    一時的エラー。Exponential backoff で最大5回リトライ。
    """

    pass


class ModelTimeoutError(NexusCoreError):
    """LLM 応答タイムアウト。

    一時的エラー。Linear backoff（10秒固定）で最大3回リトライ。
    """

    pass


class ModelConnectionError(NexusCoreError):
    """ネットワーク接続の一時的エラー。

    一時的エラー。Exponential backoff で最大3回リトライ。
    """

    pass


class InvalidModelOutputError(NexusCoreError):
    """LLM 出力が期待する JSON/構造になっていない。

    一時的エラー。Linear backoff（5秒固定）で最大3回リトライ。
    """

    pass


class SandboxExecutionError(NexusCoreError):
    """テスト実行・コード実行系のエラー。

    非リトライ可能。即座に abort。
    """

    pass


class SandboxSecurityError(NexusCoreError):
    """サンドボックスセキュリティ違反。

    禁止モジュールの利用など。非リトライ可能。即座に abort。
    """

    pass


class PatchApplyError(NexusCoreError):
    """パッチ適用失敗。

    非リトライ可能。即座に abort。
    """

    pass


class UnexpectedSystemError(NexusCoreError):
    """想定外の例外ラッパ。

    非リトライ可能。即座に abort。
    """

    pass


_VALID_CATEGORIES = frozenset({
    "rate_limit", "timeout", "connection", "invalid_output", "sandbox", "patch_apply", "unexpected",
})

_EXCEPTION_MAP: dict[type, str] = {
    ModelRateLimitError: "rate_limit",
    ModelTimeoutError: "timeout",
    ModelConnectionError: "connection",
    InvalidModelOutputError: "invalid_output",
    SandboxExecutionError: "sandbox",
    PatchApplyError: "patch_apply",
    NexusCoreError: "unexpected",
}

_KEYWORD_MAP: list[tuple[str, tuple[str, ...], tuple[str, ...]]] = [
    ("rate_limit", ("429", "rate limit"), ("ratelimit",)),
    ("timeout", ("timeout", "timed out"), ("timeout",)),
    ("connection", ("connection", "connect", "network", "dns", "resolve"), ("connection", "connect", "network")),
    ("invalid_output", ("json", "parse", "decode", "invalid format"), ("json", "parse", "decode")),
    ("sandbox", ("sandbox", "subprocess", "execution failed"), ()),
    ("patch_apply", ("patch", "apply", "diff"), ()),
]


def _classify_by_message(error_str: str, error_type: str) -> str:
    """エラーメッセージと型名からヒューリスティックに分類する。"""
    for category, msg_keywords, type_keywords in _KEYWORD_MAP:
        if any(kw in error_str for kw in msg_keywords):
            return category
        if any(kw in error_type for kw in type_keywords):
            return category
    return "unexpected"


def classify_error(exc: Exception) -> str:
    """例外からエラー種別を分類する。'unexpected' を含む7種のいずれかを返す。"""
    if exc is None:
        logger.warning("classify_error received None. Treating as unclassifiable error.")
        return "unexpected"

    try:
        for exc_type, category in _EXCEPTION_MAP.items():
            if isinstance(exc, exc_type):
                result = category
                break
        else:
            try:
                error_str = str(exc).lower()
                error_type = type(exc).__name__.lower()
            except Exception:  # noqa: BLE001 — error object stringification can fail
                logger.warning(f"Failed to stringify error object (type: {type(exc).__name__}).")
                return "unexpected"
            result = _classify_by_message(error_str, error_type)

        logger.info(f"Error classified as '{result}': {type(exc).__name__} - {str(exc)[:200]}")

        if result not in _VALID_CATEGORIES:
            logger.warning(f"classify_error returned invalid category '{result}'. Falling back to 'unexpected'.")
            result = "unexpected"

        return result

    except Exception:  # noqa: BLE001 — classification error fallback
        logger.warning(f"Exception during error classification. Original: {type(exc).__name__}.", exc_info=True)
        return "unexpected"


_CONVERT_MAP: dict[str, type[NexusCoreError]] = {
    "rate_limit": ModelRateLimitError,
    "timeout": ModelTimeoutError,
    "connection": ModelConnectionError,
    "invalid_output": InvalidModelOutputError,
    "sandbox": SandboxExecutionError,
    "patch_apply": PatchApplyError,
}

_LABEL_MAP: dict[str, str] = {
    "rate_limit": "Rate limit error",
    "timeout": "Timeout error",
    "connection": "Connection error",
    "invalid_output": "Invalid model output",
    "sandbox": "Sandbox execution error",
    "patch_apply": "Patch apply error",
}


def convert_http_error_to_nexus_error(exc: Exception) -> NexusCoreError:
    """HTTP/SDK エラーを NexusCore カスタム例外に変換する。"""
    try:
        error_class = classify_error(exc)
        try:
            error_str = str(exc) if exc is not None else "None"
        except Exception:  # noqa: BLE001
            error_str = f"<unstringifiable {type(exc).__name__ if exc is not None else 'None'}>"
        error_type = type(exc).__name__ if exc is not None else "NoneType"

        nexus_cls = _CONVERT_MAP.get(error_class, UnexpectedSystemError)
        label = _LABEL_MAP.get(error_class, f"Unexpected error ({error_type})")
        return nexus_cls(f"{label}: {error_str}")

    except Exception:  # noqa: BLE001
        logger.warning(f"Exception during error conversion. Original: {type(exc).__name__}.", exc_info=True)
        try:
            error_str = str(exc) if exc is not None else "None"
        except Exception:  # noqa: BLE001
            error_str = f"<unstringifiable {type(exc).__name__ if exc is not None else 'None'}>"
        return UnexpectedSystemError(f"Unclassifiable error ({type(exc).__name__ if exc else 'None'}): {error_str}")
