"""
Tests for CR-NEXUS-051-B: Retry Policy

このテストは Decision Table を機械的に検証し、有限性・Unexpected 処理・Backoff を担保する。
"""

import pytest

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
from nexuscore.core.retry_policy import decide_retry

# ===== Decision Table 検証 =====


@pytest.mark.parametrize(
    "error_class,attempt,expected_action,expected_max_attempts",
    [
        # ModelRateLimitError: 5 回まで Retry
        (ModelRateLimitError("Rate limit"), 1, "retry", 5),
        (ModelRateLimitError("Rate limit"), 3, "retry", 5),
        (ModelRateLimitError("Rate limit"), 5, "retry", 5),
        (ModelRateLimitError("Rate limit"), 6, "abort", 5),
        # ModelTimeoutError: 3 回まで Retry
        (ModelTimeoutError("Timeout"), 1, "retry", 3),
        (ModelTimeoutError("Timeout"), 3, "retry", 3),
        (ModelTimeoutError("Timeout"), 4, "abort", 3),
        # ModelConnectionError: 3 回まで Retry
        (ModelConnectionError("Connection"), 1, "retry", 3),
        (ModelConnectionError("Connection"), 3, "retry", 3),
        (ModelConnectionError("Connection"), 4, "abort", 3),
        # InvalidModelOutputError: 3 回まで Retry
        (InvalidModelOutputError("Invalid output"), 1, "retry", 3),
        (InvalidModelOutputError("Invalid output"), 3, "retry", 3),
        (InvalidModelOutputError("Invalid output"), 4, "abort", 3),
        # SandboxExecutionError: 即座に Abort
        (SandboxExecutionError("Sandbox error"), 1, "abort", 0),
        # SandboxSecurityError: 即座に Abort
        (SandboxSecurityError("Security error"), 1, "abort", 0),
        # PatchApplyError: 即座に Abort
        (PatchApplyError("Patch error"), 1, "abort", 0),
        # UnexpectedSystemError: 即座に Abort
        (UnexpectedSystemError("Unexpected error"), 1, "abort", 0),
    ],
)
def test_decision_table(error_class, attempt, expected_action, expected_max_attempts):
    """Decision Table を機械的に検証する"""
    error = error_class
    decision = decide_retry(error, attempt)

    # Max Attempts を超えている場合は Abort
    if attempt > expected_max_attempts:
        assert (
            decision.action == "abort"
        ), f"{error_class.__name__}: attempt {attempt} should abort (max: {expected_max_attempts})"
        assert not decision.should_retry
    else:
        # Max Attempts 以内の場合は期待されるアクション
        assert (
            decision.action == expected_action
        ), f"{error_class.__name__}: attempt {attempt} should {expected_action}"
        if expected_action == "retry":
            assert decision.should_retry
        else:
            assert not decision.should_retry


# ===== 有限性検証 =====


def test_finite_retries_rate_limit():
    """ModelRateLimitError は 5 回で停止する"""
    error = ModelRateLimitError("Rate limit")

    for attempt in range(1, 6):
        decision = decide_retry(error, attempt)
        assert decision.action == "retry", f"Attempt {attempt} should retry"
        assert decision.should_retry

    # 6 回目は Abort
    decision = decide_retry(error, 6)
    assert decision.action == "abort", "Attempt 6 should abort"
    assert not decision.should_retry


def test_finite_retries_timeout():
    """ModelTimeoutError は 3 回で停止する"""
    error = ModelTimeoutError("Timeout")

    for attempt in range(1, 4):
        decision = decide_retry(error, attempt)
        assert decision.action == "retry", f"Attempt {attempt} should retry"
        assert decision.should_retry

    # 4 回目は Abort
    decision = decide_retry(error, 4)
    assert decision.action == "abort", "Attempt 4 should abort"
    assert not decision.should_retry


def test_finite_retries_connection():
    """ModelConnectionError は 3 回で停止する"""
    error = ModelConnectionError("Connection")

    for attempt in range(1, 4):
        decision = decide_retry(error, attempt)
        assert decision.action == "retry", f"Attempt {attempt} should retry"
        assert decision.should_retry

    # 4 回目は Abort
    decision = decide_retry(error, 4)
    assert decision.action == "abort", "Attempt 4 should abort"
    assert not decision.should_retry


def test_finite_retries_invalid_output():
    """InvalidModelOutputError は 3 回で停止する"""
    error = InvalidModelOutputError("Invalid output")

    for attempt in range(1, 4):
        decision = decide_retry(error, attempt)
        assert decision.action == "retry", f"Attempt {attempt} should retry"
        assert decision.should_retry

    # 4 回目は Abort
    decision = decide_retry(error, 4)
    assert decision.action == "abort", "Attempt 4 should abort"
    assert not decision.should_retry


# ===== Unexpected 処理検証 =====


def test_unexpected_no_retry():
    """UnexpectedSystemError は即座に Abort（Retry しない）"""
    error = UnexpectedSystemError("Unexpected error")
    decision = decide_retry(error, 1)

    assert decision.action == "abort", "UnexpectedSystemError should abort immediately"
    assert not decision.should_retry
    assert decision.wait_seconds == 0.0


def test_sandbox_execution_no_retry():
    """SandboxExecutionError は即座に Abort（Retry しない）"""
    error = SandboxExecutionError("Sandbox error")
    decision = decide_retry(error, 1)

    assert decision.action == "abort", "SandboxExecutionError should abort immediately"
    assert not decision.should_retry
    assert decision.wait_seconds == 0.0


def test_sandbox_security_no_retry():
    """SandboxSecurityError は即座に Abort（Retry しない）"""
    error = SandboxSecurityError("Security error")
    decision = decide_retry(error, 1)

    assert decision.action == "abort", "SandboxSecurityError should abort immediately"
    assert not decision.should_retry
    assert decision.wait_seconds == 0.0


# ===== Backoff 検証 =====


def test_exponential_backoff_rate_limit():
    """ModelRateLimitError の Exponential Backoff を検証"""
    error = ModelRateLimitError("Rate limit")

    # Attempt 1: 2秒 + jitter (0~1秒) = 2~3秒
    decision = decide_retry(error, 1)
    assert 2.0 <= decision.wait_seconds <= 3.0, f"Attempt 1 wait: {decision.wait_seconds}"

    # Attempt 2: 4秒 + jitter (0~1秒) = 4~5秒
    decision = decide_retry(error, 2)
    assert 4.0 <= decision.wait_seconds <= 5.0, f"Attempt 2 wait: {decision.wait_seconds}"

    # Attempt 3: 8秒 + jitter (0~1秒) = 8~9秒
    decision = decide_retry(error, 3)
    assert 8.0 <= decision.wait_seconds <= 9.0, f"Attempt 3 wait: {decision.wait_seconds}"


def test_exponential_backoff_connection():
    """ModelConnectionError の Exponential Backoff を検証"""
    error = ModelConnectionError("Connection")

    # Attempt 1: 2秒 + jitter (0~1秒) = 2~3秒
    decision = decide_retry(error, 1)
    assert 2.0 <= decision.wait_seconds <= 3.0, f"Attempt 1 wait: {decision.wait_seconds}"

    # Attempt 2: 4秒 + jitter (0~1秒) = 4~5秒
    decision = decide_retry(error, 2)
    assert 4.0 <= decision.wait_seconds <= 5.0, f"Attempt 2 wait: {decision.wait_seconds}"


def test_linear_backoff_timeout():
    """ModelTimeoutError の Linear Backoff を検証"""
    error = ModelTimeoutError("Timeout")

    # すべての試行で 10秒固定
    for attempt in range(1, 4):
        decision = decide_retry(error, attempt)
        assert decision.wait_seconds == 10.0, f"Attempt {attempt} should wait 10s"


def test_linear_backoff_invalid_output():
    """InvalidModelOutputError の Linear Backoff を検証"""
    error = InvalidModelOutputError("Invalid output")

    # すべての試行で 5秒固定
    for attempt in range(1, 4):
        decision = decide_retry(error, attempt)
        assert decision.wait_seconds == 5.0, f"Attempt {attempt} should wait 5s"


# ===== Context 引数の検証 =====


def test_decide_retry_with_context():
    """Context 引数が正しく処理されることを検証"""
    error = ModelRateLimitError("Rate limit")
    context = {"task_type": "code_generate", "model_id": "gpt-5.1-codex", "task_id": "test-123"}

    decision = decide_retry(error, 1, context)
    assert decision.action == "retry"
    assert decision.should_retry


def test_decide_retry_without_context():
    """Context なしでも動作することを検証"""
    error = ModelRateLimitError("Rate limit")

    decision = decide_retry(error, 1)
    assert decision.action == "retry"
    assert decision.should_retry
