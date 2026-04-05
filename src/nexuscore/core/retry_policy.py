"""
CR-NEXUS-051-B: Retry Policy

このモジュールは Error Taxonomy (051-A) に基づき、各例外に対する Retry / Abort / Skip を判断する。
Decision Table が唯一の真実であり、実装はこの表をそのままコード化している。

Spec 要件:
    - 3.3.1: リトライ可否の判断ルール
    - 3.3.2: リトライの有限性保証（SHALL要件）
    - 3.3.3: Backoff 戦略（指数・線形・なし）
    - 3.3.4: Unexpected エラーのリトライ禁止
"""

from __future__ import annotations

import logging
import os
import random
from dataclasses import dataclass
from typing import Any, TypedDict

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

# ============================================================================
# 定数定義（Spec 3.3.3 Backoff 戦略の設定値）
# 環境変数 NEXUS_RETRY_* で実行時にオーバーライド可能
# ============================================================================


def _env_float(key: str, default: float) -> float:
    """環境変数から浮動小数点値を取得。不正値はdefaultを返す。"""
    val = os.getenv(key)
    if val is not None:
        try:
            return float(val)
        except ValueError:
            logger.debug(f"Invalid env {key}={val!r}, using default {default}")
    return default


def _env_int(key: str, default: int) -> int:
    """環境変数から整数値を取得。不正値はdefaultを返す。"""
    val = os.getenv(key)
    if val is not None:
        try:
            return int(val)
        except ValueError:
            logger.debug(f"Invalid env {key}={val!r}, using default {default}")
    return default

# Exponential Backoff
EXPONENTIAL_BASE: float = _env_float("NEXUS_RETRY_EXPONENTIAL_BASE", 2.0)
"""指数関数的バックオフのベース（Spec: 2^n 秒）"""

JITTER_MAX_SECONDS: float = _env_float("NEXUS_RETRY_JITTER_MAX", 1.0)
"""Exponential Backoff に付与するランダムジッターの最大値（秒）"""

# Linear Backoff
LINEAR_BASE_TIMEOUT_SECONDS: float = _env_float("NEXUS_RETRY_LINEAR_BASE_TIMEOUT", 10.0)
"""ModelTimeoutError の固定待機時間（秒）"""

LINEAR_BASE_INVALID_OUTPUT_SECONDS: float = _env_float("NEXUS_RETRY_LINEAR_BASE_INVALID_OUTPUT", 5.0)
"""InvalidModelOutputError の固定待機時間（秒）"""

# Retry 許容回数
MAX_RETRIES_RATE_LIMIT: int = _env_int("NEXUS_RETRY_MAX_RATE_LIMIT", 5)
"""ModelRateLimitError の最大リトライ回数"""

MAX_RETRIES_STANDARD: int = _env_int("NEXUS_RETRY_MAX_STANDARD", 3)
"""ModelTimeoutError / ModelConnectionError / InvalidModelOutputError の最大リトライ回数"""

MAX_RETRIES_IMMEDIATE_ABORT: int = 0
"""Sandbox / Security / PatchApply / Unexpected の最大リトライ回数（即時中止）"""


class _DecisionEntry(TypedDict, total=False):
    """DECISION_TABLE 各エントリの型定義"""

    max_attempts: int
    backoff: str
    base: float
    jitter_max: float
    base_interval: float


@dataclass
class RetryDecision:
    """Retry 判断結果（不変）"""

    action: str  # "retry" | "abort" | "skip"
    reason: str  # 判断理由
    wait_seconds: float  # 次回試行までの待機時間（秒）
    should_retry: bool  # Retry すべきか


# Decision Table の定義（CR-NEXUS-051-B Spec Section 3）
DECISION_TABLE: dict[type[Exception], _DecisionEntry] = {
    ModelRateLimitError: {
        "max_attempts": MAX_RETRIES_RATE_LIMIT,
        "backoff": "exponential",
        "base": EXPONENTIAL_BASE,
        "jitter_max": JITTER_MAX_SECONDS,
    },
    ModelTimeoutError: {
        "max_attempts": MAX_RETRIES_STANDARD,
        "backoff": "linear",
        "base_interval": LINEAR_BASE_TIMEOUT_SECONDS,
    },
    ModelConnectionError: {
        "max_attempts": MAX_RETRIES_STANDARD,
        "backoff": "exponential",
        "base": EXPONENTIAL_BASE,
        "jitter_max": JITTER_MAX_SECONDS,
    },
    InvalidModelOutputError: {
        "max_attempts": MAX_RETRIES_STANDARD,
        "backoff": "linear",
        "base_interval": LINEAR_BASE_INVALID_OUTPUT_SECONDS,
    },
    SandboxExecutionError: {
        "max_attempts": MAX_RETRIES_IMMEDIATE_ABORT,
        "backoff": "none",
    },
    SandboxSecurityError: {
        "max_attempts": MAX_RETRIES_IMMEDIATE_ABORT,
        "backoff": "none",
    },
    PatchApplyError: {
        "max_attempts": MAX_RETRIES_IMMEDIATE_ABORT,
        "backoff": "none",
    },
    UnexpectedSystemError: {
        "max_attempts": MAX_RETRIES_IMMEDIATE_ABORT,
        "backoff": "none",
    },
}


def _calculate_exponential_backoff(
    attempt: int,
    base: float = EXPONENTIAL_BASE,
    jitter_max: float = JITTER_MAX_SECONDS,
) -> float:
    """
    Exponential Backoff + Jitter を計算する（Spec 3.3.3）。

    wait_seconds = base^attempt + uniform(0, jitter_max)

    Args:
        attempt: 現在の試行回数（1-indexed）
        base: 指数のベース
        jitter_max: Jitter の最大値（秒）

    Returns:
        待機時間（秒）。attempt=1 → 2~3秒、attempt=3 → 8~9秒
    """
    wait_time = (base**attempt) + random.uniform(0, jitter_max)
    return wait_time


def _calculate_linear_backoff(base_interval: float) -> float:
    """
    Linear Backoff を計算する（固定待機時間、Spec 3.3.3）。

    全ての試行で同一の待機時間を返す。

    Args:
        base_interval: 固定待機時間（秒）

    Returns:
        base_interval をそのまま返す
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
            "Unknown exception type in Decision Table: %s. Treating as Unexpected.",
            error_type.__name__,
            extra={"error_type": error_type.__name__, "action": "abort", "attempt": attempt},
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
            "Max attempts (%d) exceeded for %s. Attempt: %d. Aborting.",
            max_attempts,
            error_type.__name__,
            attempt,
            extra={
                "error_type": error_type.__name__,
                "action": "abort",
                "attempt": attempt,
                "max_attempts": max_attempts,
            },
        )
        return RetryDecision(
            action="abort",
            reason=f"Max attempts ({max_attempts}) exceeded",
            wait_seconds=0.0,
            should_retry=False,
        )

    # Step 3: Max Attempts が 0 の場合は即座に Abort
    if max_attempts == 0:
        logger.warning(
            "Immediate abort for %s.",
            error_type.__name__,
            extra={"error_type": error_type.__name__, "action": "abort", "max_attempts": 0},
        )
        return RetryDecision(
            action="abort",
            reason=f"{error_type.__name__} is not retryable (max_attempts=0)",
            wait_seconds=0.0,
            should_retry=False,
        )

    # Step 4: Backoff 戦略に従って待機時間を計算
    if backoff_type == "exponential":
        base = config.get("base", EXPONENTIAL_BASE)
        jitter_max = config.get("jitter_max", JITTER_MAX_SECONDS)
        wait_seconds = _calculate_exponential_backoff(attempt, base, jitter_max)
    elif backoff_type == "linear":
        base_interval = config.get("base_interval", LINEAR_BASE_INVALID_OUTPUT_SECONDS)
        wait_seconds = _calculate_linear_backoff(base_interval)
    else:
        # backoff_type が "none" の場合（到達不能: max_attempts==0 は Step 3 で Abort済み）
        wait_seconds = 0.0  # type: ignore[unreachable]

    # Step 5: Retry 判断をログに記録
    logger.info(
        "Retry decision for %s: attempt=%d/%d, action=retry, wait=%.2fs",
        error_type.__name__,
        attempt,
        max_attempts,
        wait_seconds,
        extra={
            "error_type": error_type.__name__,
            "action": "retry",
            "attempt": attempt,
            "max_attempts": max_attempts,
            "wait_seconds": wait_seconds,
            "backoff": backoff_type,
            "context": context,
        },
    )

    return RetryDecision(
        action="retry",
        reason=f"Retryable exception (attempt {attempt}/{max_attempts})",
        wait_seconds=wait_seconds,
        should_retry=True,
    )


# ============================================================================
# Policy Validation（CR-NEXUS-055 Phase 1）
# ============================================================================

# Spec 3.3.1 で定義される全エラータイプ
_REQUIRED_ERROR_TYPES: frozenset[type[Exception]] = frozenset({
    ModelRateLimitError,
    ModelTimeoutError,
    ModelConnectionError,
    InvalidModelOutputError,
    SandboxExecutionError,
    SandboxSecurityError,
    PatchApplyError,
    UnexpectedSystemError,
})

# Spec 3.3.3 で定義される有効な backoff 戦略
_VALID_BACKOFF_TYPES: frozenset[str] = frozenset({"exponential", "linear", "none"})


def validate_decision_table() -> list[str]:
    """
    DECISION_TABLE が Spec 準拠であることを検証する。

    Returns:
        検証エラーのリスト（空なら準拠）

    検証項目:
        - 全エラータイプがカバーされている
        - max_attempts >= 0
        - backoff が有効な値
        - exponential には base と jitter_max が定義されている
        - linear には base_interval が定義されている
    """
    errors: list[str] = []

    # 1. 必須エラータイプの網羅性チェック
    defined_types = set(DECISION_TABLE.keys())
    missing = _REQUIRED_ERROR_TYPES - defined_types
    if missing:
        errors.append(f"Missing error types: {sorted(t.__name__ for t in missing)}")

    # 2. 各エントリの整合性チェック
    for error_type, config in DECISION_TABLE.items():
        prefix = f"{error_type.__name__}: "

        max_attempts = config.get("max_attempts")
        if max_attempts is None:
            errors.append(f"{prefix}missing max_attempts")
        elif not isinstance(max_attempts, int) or max_attempts < 0:
            errors.append(f"{prefix}max_attempts must be non-negative int, got {max_attempts}")

        backoff = config.get("backoff")
        if backoff not in _VALID_BACKOFF_TYPES:
            errors.append(f"{prefix}invalid backoff '{backoff}'")

        if backoff == "exponential":
            if "base" not in config:
                errors.append(f"{prefix}exponential backoff requires 'base'")
            if "jitter_max" not in config:
                errors.append(f"{prefix}exponential backoff requires 'jitter_max'")
        elif backoff == "linear":
            if "base_interval" not in config:
                errors.append(f"{prefix}linear backoff requires 'base_interval'")

    if errors:
        logger.warning("Decision Table validation failed: %d errors", len(errors))
    else:
        logger.info("Decision Table validation passed")

    return errors


# モジュールロード時のオプション検証（NEXUS_VALIDATE_POLICY=1 で有効）
if os.getenv("NEXUS_VALIDATE_POLICY", "").lower() in ("1", "true", "yes"):
    _validation_errors = validate_decision_table()
    if _validation_errors:
        for _err in _validation_errors:
            logger.error("Policy validation: %s", _err)
