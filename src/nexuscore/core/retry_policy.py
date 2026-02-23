"""
CR-NEXUS-051-B: Retry Policy

このモジュールは Error Taxonomy (051-A) に基づき、各例外に対する Retry / Abort / Skip を判断する。
Decision Table が唯一の真実であり、実装はこの表をそのままコード化している。
"""

from __future__ import annotations

import logging
import random
from dataclasses import dataclass
from typing import Any

from nexuscore.core.errors import (
    InvalidModelOutputError,
    ModelConnectionError,
    ModelRateLimitError,
    ModelTimeoutError,
    PatchApplyError,
    SandboxExecutionError,
    SandboxSecurityError,
    UnexpectedSystemError,
)

logger = logging.getLogger(__name__)


@dataclass
class RetryDecision:
    """Retry 判断結果"""

    action: str  # "retry" | "abort" | "skip"
    reason: str  # 判断理由
    wait_seconds: float  # 次回試行までの待機時間（秒）
    should_retry: bool  # Retry すべきか


# Decision Table の定義（CR-NEXUS-051-B Spec Section 3）
DECISION_TABLE = {
    ModelRateLimitError: {
        "max_attempts": 5,
        "backoff": "exponential",
        "base": 2,
        "jitter_max": 1.0,
    },
    ModelTimeoutError: {
        "max_attempts": 3,
        "backoff": "linear",
        "base_interval": 10.0,
    },
    ModelConnectionError: {
        "max_attempts": 3,
        "backoff": "exponential",
        "base": 2,
        "jitter_max": 1.0,
    },
    InvalidModelOutputError: {
        "max_attempts": 3,
        "backoff": "linear",
        "base_interval": 5.0,
    },
    SandboxExecutionError: {
        "max_attempts": 0,
        "backoff": "none",
    },
    SandboxSecurityError: {
        "max_attempts": 0,
        "backoff": "none",
    },
    PatchApplyError: {
        "max_attempts": 0,
        "backoff": "none",
    },
    UnexpectedSystemError: {
        "max_attempts": 0,
        "backoff": "none",
    },
}


def _calculate_exponential_backoff(
    attempt: int, base: float = 2.0, jitter_max: float = 1.0
) -> float:
    """
    Exponential Backoff + Jitter を計算する。

    Args:
        attempt: 現在の試行回数（1-indexed）
        base: 指数のベース（デフォルト: 2）
        jitter_max: Jitter の最大値（秒）（デフォルト: 1.0）

    Returns:
        待機時間（秒）
    """
    wait_time = (base**attempt) + random.uniform(0, jitter_max)
    return wait_time


def _calculate_linear_backoff(base_interval: float) -> float:
    """
    Linear Backoff を計算する（固定待機時間）。

    Args:
        base_interval: 固定待機時間（秒）

    Returns:
        待機時間（秒）
    """
    return base_interval


def decide_retry(
    error: Exception, attempt: int, context: dict[str, Any] | None = None
) -> RetryDecision:
    """
    例外に対する Retry / Abort / Skip を判断する。

    この関数は Decision Table（CR-NEXUS-051-B Spec Section 3）をそのままコード化している。
    判断のみを行い、実際の Retry / Abort 実行は呼び出し側の責務である。

    Args:
        error: 発生した例外
        attempt: 現在の試行回数（1-indexed）
        context: コンテキスト情報（タスクタイプ、モデル ID 等）（オプション）

    Returns:
        RetryDecision: 判断結果

    Raises:
        None（すべての入力に対して RetryDecision を返す）

    Observability:
        - Retry 判断時に INFO ログを出力
        - 最終 Abort 時に WARNING ログを出力
    """
    # Step 1: Decision Table から設定を取得
    error_type = type(error)
    config = DECISION_TABLE.get(error_type)

    if config is None:
        # Decision Table に存在しない例外 → Unexpected として扱う
        logger.warning(
            f"Unknown exception type in Decision Table: {error_type.__name__}. "
            f"Treating as Unexpected. Error: {str(error)[:200]}"
        )
        return RetryDecision(
            action="abort",
            reason=f"Unknown exception type: {error_type.__name__}",
            wait_seconds=0.0,
            should_retry=False,
        )

    max_attempts = config["max_attempts"]
    backoff_type = config["backoff"]

    # Step 2: Max Attempts を超えているか判定
    if attempt > max_attempts:
        logger.warning(
            f"Max attempts ({max_attempts}) exceeded for {error_type.__name__}. "
            f"Attempt: {attempt}. Aborting. Error: {str(error)[:200]}"
        )
        return RetryDecision(
            action="abort",
            reason=f"Max attempts ({max_attempts}) exceeded",
            wait_seconds=0.0,
            should_retry=False,
        )

    # Step 3: Max Attempts が 0 の場合は即座に Abort
    if max_attempts == 0:
        logger.warning(f"Immediate abort for {error_type.__name__}. " f"Error: {str(error)[:200]}")
        return RetryDecision(
            action="abort",
            reason=f"{error_type.__name__} is not retryable (max_attempts=0)",
            wait_seconds=0.0,
            should_retry=False,
        )

    # Step 4: Backoff 戦略に従って待機時間を計算
    if backoff_type == "exponential":
        base = config.get("base", 2.0)
        jitter_max = config.get("jitter_max", 1.0)
        wait_seconds = _calculate_exponential_backoff(attempt, base, jitter_max)
    elif backoff_type == "linear":
        base_interval = config.get("base_interval", 5.0)
        wait_seconds = _calculate_linear_backoff(base_interval)
    else:
        # backoff_type が "none" の場合（到達不可、Step 3 で Abort）
        wait_seconds = 0.0

    # Step 5: Retry 判断をログに記録
    context_str = f", context={context}" if context else ""
    logger.info(
        f"Retry decision for {error_type.__name__}: "
        f"attempt={attempt}/{max_attempts}, "
        f"action=retry, "
        f"wait_seconds={wait_seconds:.2f}"
        f"{context_str}"
    )

    return RetryDecision(
        action="retry",
        reason=f"Retryable exception (attempt {attempt}/{max_attempts})",
        wait_seconds=wait_seconds,
        should_retry=True,
    )
