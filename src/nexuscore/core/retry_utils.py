from __future__ import annotations

import time
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from enum import Enum
from functools import wraps
from typing import Any, TypeVar

from nexuscore.core.errors import NexusCoreError, classify_error
from nexuscore.logging_standard import get_logger

logger = get_logger(__name__)

T = TypeVar("T")


class BackoffStrategy(Enum):
    """Backoff 戦略の意味論レベル定義（3.3.3）"""

    INCREASING_LONG = "increasing_long"  # 増加型待機戦略（長）
    INCREASING_MEDIUM = "increasing_medium"  # 増加型待機戦略（中）
    INCREASING_SHORT = "increasing_short"  # 増加型待機戦略（短）
    FIXED = "fixed"  # 一定待機戦略
    NO_WAIT = "no_wait"  # 待機なし再試行


@dataclass
class RetryConfig:
    """
    リトライ設定（設定値の注入を前提）

    Args:
        max_retries: 最大リトライ回数（3.3.2 SHALL要件: 有限性保証）
        base_delay: ベース遅延時間（秒、増加型戦略の初期値）
        fixed_delay: 一定待機戦略の待機時間（秒）
        backoff_multiplier: 増加型戦略の係数（設定可能、デフォルトは実装詳細）
        strategy_map: エラー種別ごとの Backoff 戦略マッピング
    """

    max_retries: int = 3
    base_delay: float = 1.0
    fixed_delay: float = 1.0
    backoff_multiplier: float = 2.0
    strategy_map: dict[str, BackoffStrategy] | None = None

    def __post_init__(self):
        """デフォルトの戦略マッピングを設定"""
        if self.strategy_map is None:
            self.strategy_map = {
                "rate_limit": BackoffStrategy.INCREASING_LONG,
                "timeout": BackoffStrategy.INCREASING_MEDIUM,
                "connection": BackoffStrategy.INCREASING_SHORT,
                "invalid_output": BackoffStrategy.NO_WAIT,
            }


class RetryContext:
    """
    Retry 実行のコンテキスト情報を保持するクラス。

    各試行で retry_count と error_class を記録し、
    最終的に details に反映するために使用する。
    """

    def __init__(self) -> None:
        self.retry_count: int = 0
        self.last_error_class: str | None = None
        self.error_summary: list[str] = []

    def record_attempt(self, attempt: int, error: Exception | None = None) -> None:
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

    def to_dict(self) -> dict[str, Any]:
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


def _is_retryable(error_class: str) -> bool:
    """
    エラー種別がリトライ可能か判定（3.3.1）

    Args:
        error_class: エラー種別文字列

    Returns:
        リトライ可能な場合 True、不可の場合 False
    """
    retryable_categories = {"rate_limit", "timeout", "connection", "invalid_output"}
    return error_class in retryable_categories


def _calculate_backoff_delay(attempt: int, error_class: str, config: RetryConfig) -> float:
    """
    Backoff 戦略に基づいて待機時間を計算（3.3.3）

    Args:
        attempt: 試行回数（0-indexed）
        error_class: エラー種別
        config: RetryConfig インスタンス

    Returns:
        待機時間（秒）
    """
    strategy = config.strategy_map.get(error_class, BackoffStrategy.INCREASING_MEDIUM)  # type: ignore[union-attr]

    if strategy == BackoffStrategy.NO_WAIT:
        # 待機なし再試行（初回のみ、attempt=0 の場合は待機なし）
        return 0.0 if attempt == 0 else config.base_delay
    elif strategy == BackoffStrategy.FIXED:
        # 一定待機戦略
        return config.fixed_delay
    elif strategy in (
        BackoffStrategy.INCREASING_LONG,
        BackoffStrategy.INCREASING_MEDIUM,
        BackoffStrategy.INCREASING_SHORT,
    ):
        # 増加型待機戦略（長/中/短の違いは base_delay の初期値で調整）
        # 意味論レベル: リトライ回数の増加に応じて、待機時間を段階的に延長
        return config.base_delay * (config.backoff_multiplier**attempt)
    else:
        # フォールバック: 増加型（中）— L152-154 と同一のため到達不能
        return config.base_delay * (config.backoff_multiplier**attempt)


_RETRYABLE_CATEGORIES = frozenset({"rate_limit", "timeout", "connection", "invalid_output"})


def _classify_and_should_retry(
    error: Exception,
    retry_on: Iterable[type[Exception]] | None,
    logger_instance: Any | None,
) -> tuple[bool, str]:
    """エラーを分類し、リトライ可否を判定する。return (should_retry, error_class)"""
    try:
        if retry_on is not None and isinstance(error, tuple(retry_on)):  # type: ignore[arg-type]
            return True, "user_specified"
        error_class = classify_error(error)
        if error_class == "unexpected":
            return False, error_class
        return error_class in _RETRYABLE_CATEGORIES, error_class
    except Exception as classification_error:  # noqa: BLE001
        if logger_instance is not None:
            logger_instance.warning(
                f"Error classification failed during retry decision. "
                f"Original error: {type(error).__name__} - {str(error)[:200]}. "
                f"Classification error: {type(classification_error).__name__} - {str(classification_error)}. "
                f"Treating as non-retryable (unexpected)."
            )
        return False, "unknown"


def retry_with_context(
    func: Callable[..., T],
    *,
    max_retries: int = 3,
    base_delay: float = 1.0,
    retry_on: Iterable[type[Exception]] | None = None,
    logger_instance: Any | None = None,
    context: RetryContext | None = None,
    retry_config: RetryConfig | None = None,
) -> Callable[..., T]:
    """指定した例外クラスに対して再試行を提供するデコレータ（Spec CR-NEXUS-051 準拠）。"""
    if logger_instance is None:
        logger_instance = logger

    if retry_config is None:
        retry_config = RetryConfig(max_retries=max_retries, base_delay=base_delay)
    else:
        import copy
        retry_config = copy.copy(retry_config)
        if max_retries != 3:
            retry_config.max_retries = max_retries
        if base_delay != 1.0:
            retry_config.base_delay = base_delay

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> T:
        last_exception: Exception | None = None
        max_attempts = retry_config.max_retries + 1

        for attempt in range(max_attempts):
            try:
                result = func(*args, **kwargs)
                if context:
                    context.record_attempt(attempt)
                return result
            except Exception as e:  # noqa: BLE001 — retry target call broad catch
                last_exception = e
                should_retry, error_class = _classify_and_should_retry(e, retry_on, logger_instance)

                if context:
                    context.record_attempt(attempt, e)

                if attempt >= retry_config.max_retries or not should_retry:
                    if logger_instance is not None:
                        logger_instance.error(
                            f"Function {func.__name__} failed after {attempt + 1} attempts. "
                            f"Error class: {error_class}, Error: {e}",
                            exc_info=True,
                        )
                    raise

                delay = _calculate_backoff_delay(attempt, error_class, retry_config)
                if logger_instance is not None:
                    logger_instance.warning(
                        f"Function {func.__name__} failed (attempt {attempt + 1}/{max_attempts}). "
                        f"Error class: {error_class}, Error: {e}. "
                        f"Retrying in {delay:.2f}s..."
                    )
                if delay > 0:
                    time.sleep(delay)

        raise last_exception  # type: ignore[misc]

    return wrapper


def retry(
    func: Callable[..., T] | None = None,
    *,
    max_retries: int = 3,
    base_delay: float = 1.0,
    retry_on: Iterable[type[Exception]] | None = None,
    logger_instance: Any | None = None,  # logging.Logger の型ヒントを避ける
    retry_config: RetryConfig | None = None,
) -> Callable[..., T] | Callable[[Callable[..., T]], Callable[..., T]]:
    """
    デコレータとして使用する場合の簡易版。

    使用例:
        @retry(max_retries=3, base_delay=1.0)
        def my_function():
            ...

    または:
        retry(max_retries=3)(my_function)

    Args:
        func: 再試行対象の関数（デコレータとして使用する場合）
        max_retries: 最大再試行回数（デフォルト: 3）
        base_delay: ベース遅延時間（秒、デフォルト: 1.0）
        retry_on: 再試行対象の例外クラスのイテラブル
        logger_instance: ログ出力用の Logger
        retry_config: RetryConfig インスタンス（設定値の注入）
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
                retry_config=retry_config,
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
            retry_config=retry_config,
        )
