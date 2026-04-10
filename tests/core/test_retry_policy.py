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


# ===== Unknown 例外タイプの検証（L143-147 カバー） =====


def test_unknown_exception_type_aborts():
    """Decision Table にない例外タイプは即座に Abort"""
    error = ValueError("Not in decision table")
    decision = decide_retry(error, 1)

    assert decision.action == "abort"
    assert not decision.should_retry
    assert decision.wait_seconds == 0.0
    assert "Unknown exception type" in decision.reason


def test_generic_exception_aborts():
    """一般的な Exception も Decision Table にないため Abort"""
    error = Exception("Generic error")
    decision = decide_retry(error, 1)

    assert decision.action == "abort"
    assert not decision.should_retry


# ===== max_attempts==0 の即時 Abort 検証（L172-173 カバー） =====


def test_retryable_error_max_zero_immediate_abort():
    """max_attempts=0 のエラー (SandboxExecutionError) で attempt=0 の場合、Step 2 (0>0=False) を通過し Step 3 (L171-178) で即時 Abort"""
    error = SandboxExecutionError("Sandbox failed")
    decision = decide_retry(error, 0)

    assert decision.action == "abort"
    assert not decision.should_retry
    assert decision.wait_seconds == 0.0
    assert "SandboxExecutionError" in decision.reason


def test_patch_apply_immediate_abort_max_zero():
    """PatchApplyError は max_attempts=0 で即時 Abort"""
    error = PatchApplyError("Patch failed")
    decision = decide_retry(error, 1)

    assert decision.action == "abort"
    assert not decision.should_retry
    assert "Max attempts" in decision.reason and "0" in decision.reason


def test_unexpected_system_error_immediate_abort():
    """UnexpectedSystemError は max_attempts=0 で即時 Abort"""
    error = UnexpectedSystemError("Unexpected")
    decision = decide_retry(error, 1)

    assert decision.action == "abort"
    assert not decision.should_retry


# ===== backoff_type="none" フォールスルー検証（L190 カバー） =====


def test_sandbox_execution_no_wait():
    """SandboxExecutionError は wait_seconds=0.0"""
    error = SandboxExecutionError("Sandbox failed")
    decision = decide_retry(error, 1)

    assert decision.wait_seconds == 0.0


class TestEnvHelpers:
    def test_env_float_invalid_returns_default(self, monkeypatch):
        from nexuscore.core import retry_policy
        monkeypatch.setenv("NEXUS_TEST_BAD_FLOAT", "not_a_number")
        result = retry_policy._env_float("NEXUS_TEST_BAD_FLOAT", 3.14)
        assert result == 3.14

    def test_env_int_invalid_returns_default(self, monkeypatch):
        from nexuscore.core import retry_policy
        monkeypatch.setenv("NEXUS_TEST_BAD_INT", "abc")
        result = retry_policy._env_int("NEXUS_TEST_BAD_INT", 42)
        assert result == 42

    def test_env_float_valid_value(self, monkeypatch):
        from nexuscore.core import retry_policy
        monkeypatch.setenv("NEXUS_TEST_GOOD_FLOAT", "7.5")
        result = retry_policy._env_float("NEXUS_TEST_GOOD_FLOAT", 1.0)
        assert result == 7.5

    def test_env_int_valid_value(self, monkeypatch):
        from nexuscore.core import retry_policy
        monkeypatch.setenv("NEXUS_TEST_GOOD_INT", "99")
        result = retry_policy._env_int("NEXUS_TEST_GOOD_INT", 1)
        assert result == 99

    def test_env_float_missing_returns_default(self):
        from nexuscore.core import retry_policy
        result = retry_policy._env_float("NEXUS_NONEXISTENT_VAR_XYZ", 2.71)
        assert result == 2.71

    def test_env_int_missing_returns_default(self):
        from nexuscore.core import retry_policy
        result = retry_policy._env_int("NEXUS_NONEXISTENT_VAR_XYZ", 10)
        assert result == 10


class TestValidateDecisionTable:
    def test_validate_passes(self):
        from nexuscore.core.retry_policy import validate_decision_table
        errors = validate_decision_table()
        assert errors == []

    def test_validate_with_missing_type(self, monkeypatch):
        from nexuscore.core import retry_policy
        original = dict(retry_policy.DECISION_TABLE)
        removed_key = list(original.keys())[0]
        monkeypatch.setattr(retry_policy, "DECISION_TABLE", {k: v for k, v in original.items() if k != removed_key})
        errors = retry_policy.validate_decision_table()
        assert any("Missing" in e for e in errors)

    def test_validate_with_invalid_backoff(self, monkeypatch):
        from nexuscore.core import retry_policy
        original = dict(retry_policy.DECISION_TABLE)
        first_key = list(original.keys())[0]
        bad_table = dict(original)
        bad_table[first_key] = {**original[first_key], "backoff": "invalid_type"}
        monkeypatch.setattr(retry_policy, "DECISION_TABLE", bad_table)
        errors = retry_policy.validate_decision_table()
        assert any("invalid backoff" in e for e in errors)

    def test_validate_exponential_missing_base(self, monkeypatch):
        from nexuscore.core import retry_policy
        from nexuscore.core.errors import ModelRateLimitError
        bad_table = dict(retry_policy.DECISION_TABLE)
        bad_table[ModelRateLimitError] = {"max_attempts": 5, "backoff": "exponential"}
        monkeypatch.setattr(retry_policy, "DECISION_TABLE", bad_table)
        errors = retry_policy.validate_decision_table()
        assert any("base" in e for e in errors)

    def test_validate_linear_missing_interval(self, monkeypatch):
        from nexuscore.core import retry_policy
        from nexuscore.core.errors import ModelTimeoutError
        bad_table = dict(retry_policy.DECISION_TABLE)
        bad_table[ModelTimeoutError] = {"max_attempts": 3, "backoff": "linear"}
        monkeypatch.setattr(retry_policy, "DECISION_TABLE", bad_table)
        errors = retry_policy.validate_decision_table()
        assert any("base_interval" in e for e in errors)

    def test_validate_negative_max_attempts(self, monkeypatch):
        from nexuscore.core import retry_policy
        first_key = list(retry_policy.DECISION_TABLE.keys())[0]
        bad_table = dict(retry_policy.DECISION_TABLE)
        bad_table[first_key] = {**retry_policy.DECISION_TABLE[first_key], "max_attempts": -1}
        monkeypatch.setattr(retry_policy, "DECISION_TABLE", bad_table)
        errors = retry_policy.validate_decision_table()
        assert any("non-negative" in e for e in errors)
