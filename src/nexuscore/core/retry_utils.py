"""
Retry ユーティリティ

LLM 呼び出しや Sandbox 実行に対して、指数バックオフによる再試行を提供する。
"""

from __future__ import annotations

import time
from collections.abc import Callable, Iterable
from functools import wraps
from typing import TypeVar, Optional, Any, Dict

from nexuscore.core.errors import classify_error, NexusCoreError
from nexuscore.logging_standard import get_logger

logger = get_logger(__name__)

T = TypeVar("T")


class RetryContext:
    """
    Retry 実行のコンテキスト情報を保持するクラス。

    各試行で retry_count と error_class を記録し、
    最終的に details に反映するために使用する。
    """
    def __init__(self) -> None:
        self.retry_count: int = 0
        self.last_error_class: Optional[str] = None
        self.error_summary: list[str] = []

    def record_attempt(self, attempt: int, error: Optional[Exception] = None) -> None:
        """
        試行を記録する。

        Args:
            attempt: 試行回数（0-indexed）
            error: 発生した例外（あれば）
        """
        if attempt > 0:
            self.retry_count = attempt
        if error:
            error_class = classify_error(error)
            self.last_error_class = error_class
            self.error_summary.append(f"Attempt {attempt}: {error_class} - {str(error)[:100]}")

    def to_dict(self) -> Dict[str, Any]:
        """
        details に追加するための辞書を返す。

        Returns:
            {"retry_count": int, "last_error_class": str, "error_summary": str}
        """
        return {
            "retry_count": self.retry_count,
            "last_error_class": self.last_error_class,
            "error_summary": "\n".join(self.error_summary) if self.error_summary else None,
        }


def retry_with_context(
    func: Callable[..., T],
    *,
    max_retries: int = 2,
    base_delay: float = 1.0,
    retry_on: Optional[Iterable[type[Exception]]] = None,
    logger_instance: Optional[logging.Logger] = None,
    context: Optional[RetryContext] = None,
) -> Callable[..., T]:
    """
    指定した例外クラスに対して、最大 max_retries 回まで指数バックオフで再試行するデコレータ。

    Args:
        func: 再試行対象の関数
        max_retries: 最大再試行回数（デフォルト: 2）
        base_delay: ベース遅延時間（秒、デフォルト: 1.0）
        retry_on: 再試行対象の例外クラスのイテラブル
        logger_instance: ログ出力用の Logger（省略時はデフォルトロガー）
        context: RetryContext インスタンス（retry_count と error_class を記録）

    Returns:
        ラップされた関数
    """
    if logger_instance is None:
        logger_instance = logger

    if retry_on is None:
        from nexuscore.core.errors import (
            ModelRateLimitError,
            ModelTimeoutError,
            ModelConnectionError,
        )
        retry_on = (ModelRateLimitError, ModelTimeoutError, ModelConnectionError)

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> T:
        last_exception: Optional[Exception] = None

        for attempt in range(max_retries + 1):
            try:
                result = func(*args, **kwargs)
                # 成功時は context に記録（初回成功の場合は retry_count=0）
                if context:
                    context.record_attempt(attempt)
                return result
            except Exception as e:
                last_exception = e

                # 3.3.1: リトライ可否の判断ルール
                should_retry = False
                try:
                    if isinstance(e, retry_on):
                        should_retry = True
                    elif isinstance(e, NexusCoreError):
                        # NexusCore カスタム例外の場合は classify_error で判定
                        error_class = classify_error(e)
                        # 3.3.4: Unexpected エラーのリトライ禁止
                        if error_class == "unexpected":
                            should_retry = False
                        # 3.3.1: retryable: rate_limit, timeout, connection, invalid_output
                        elif error_class in ("rate_limit", "timeout", "connection", "invalid_output"):
                            should_retry = True
                        # 3.3.1: non-retryable: sandbox, patch_apply
                        else:
                            should_retry = False
                    else:
                        # 一般的な例外の場合も分類を試みる
                        error_class = classify_error(e)
                        # 3.3.4: Unexpected エラーのリトライ禁止
                        if error_class == "unexpected":
                            should_retry = False
                        # 3.3.1: retryable: rate_limit, timeout, connection, invalid_output
                        elif error_class in ("rate_limit", "timeout", "connection", "invalid_output"):
                            should_retry = True
                        else:
                            should_retry = False
                except Exception as classification_error:
                    # 3.4.2: 分類不能エラー時のフォールバックフック
                    if logger_instance is not None:
                        logger_instance.warning(
                            f"Error classification failed during retry decision. "
                            f"Original error: {type(e).__name__} - {str(e)[:200]}. "
                            f"Classification error: {type(classification_error).__name__} - {str(classification_error)}. "
                            f"Treating as non-retryable (unexpected)."
                        )
                    should_retry = False

                # context に記録
                if context:
                    context.record_attempt(attempt, e)

                # 最後の試行、または再試行対象外の場合は例外を再発生
                if attempt >= max_retries or not should_retry:
                    error_class = classify_error(e) if context else "unknown"
                    logger_instance.error(
                        f"Function {func.__name__} failed after {attempt + 1} attempts. "
                        f"Error class: {error_class}, Error: {e}",
                        exc_info=True,
                    )
                    raise

                # 指数バックオフで待機
                delay = base_delay * (2 ** attempt)
                error_class = classify_error(e)
                logger_instance.warning(
                    f"Function {func.__name__} failed (attempt {attempt + 1}/{max_retries + 1}). "
                    f"Error class: {error_class}, Error: {e}. "
                    f"Retrying in {delay:.1f}s..."
                )
                time.sleep(delay)

        # ここには到達しないはずだが、型チェッカーのために追加
        if last_exception:
            raise last_exception
        raise RuntimeError("Unexpected retry loop exit")

    return wrapper


def retry(
    func: Optional[Callable[..., T]] = None,
    *,
    max_retries: int = 2,
    base_delay: float = 1.0,
    retry_on: Optional[Iterable[type[Exception]]] = None,
    logger_instance: Optional[logging.Logger] = None,
) -> Callable[..., T]:
    """
    デコレータとして使用する場合の簡易版。

    使用例:
        @retry(max_retries=2, base_delay=1.0)
        def my_function():
            ...

    または:
        retry(max_retries=2)(my_function)
    """
    if func is None:
        # デコレータとして呼び出された場合
        def decorator(f: Callable[..., T]) -> Callable[..., T]:
            return retry_with_context(
                f,
                max_retries=max_retries,
                base_delay=base_delay,
                retry_on=retry_on,
                logger_instance=logger_instance,
            )
        return decorator
    else:
        # 関数を直接渡された場合
        return retry_with_context(
            func,
            max_retries=max_retries,
            base_delay=base_delay,
            retry_on=retry_on,
            logger_instance=logger_instance,
        )
