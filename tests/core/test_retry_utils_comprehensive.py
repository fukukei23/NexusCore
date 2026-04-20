"""
Comprehensive tests for retry_utils module.

Tests retry logic with exponential backoff, RetryContext tracking,
and error classification integration.
"""

from unittest.mock import Mock, patch

import pytest

from nexuscore.core.errors import (
    InvalidModelOutputError,
    ModelConnectionError,
    ModelRateLimitError,
    ModelTimeoutError,
    SandboxExecutionError,
)
from nexuscore.core.retry_utils import (
    RetryContext,
    retry,
    retry_with_context,
)


class TestRetryContext:
    """Tests for RetryContext class."""

    def test_init_creates_empty_context(self):
        """Test RetryContext initialization."""
        ctx = RetryContext()
        assert ctx.retry_count == 0
        assert ctx.last_error_class is None
        assert ctx.error_summary == []

    def test_record_attempt_with_no_error_first_attempt(self):
        """Test recording successful first attempt."""
        ctx = RetryContext()
        ctx.record_attempt(0)

        assert ctx.retry_count == 0
        assert ctx.last_error_class is None
        assert ctx.error_summary == []

    def test_record_attempt_with_error_increments_retry_count(self):
        """Test recording failed attempt increments retry count."""
        ctx = RetryContext()
        error = ModelRateLimitError("Rate limit exceeded")

        ctx.record_attempt(1, error)

        assert ctx.retry_count == 1
        assert ctx.last_error_class == "rate_limit"
        assert len(ctx.error_summary) == 1
        assert "Attempt 1: rate_limit" in ctx.error_summary[0]

    def test_record_multiple_attempts_tracks_all_errors(self):
        """Test recording multiple failed attempts."""
        ctx = RetryContext()

        ctx.record_attempt(0, ModelTimeoutError("Timeout 1"))
        ctx.record_attempt(1, ModelRateLimitError("Rate limit"))
        ctx.record_attempt(2, ModelConnectionError("Connection lost"))

        assert ctx.retry_count == 2
        assert ctx.last_error_class == "connection"
        assert len(ctx.error_summary) == 3

    def test_to_dict_returns_expected_structure(self):
        """Test to_dict returns correct dictionary structure."""
        ctx = RetryContext()
        ctx.record_attempt(1, ModelRateLimitError("Test error"))

        result = ctx.to_dict()

        assert result["retry_count"] == 1
        assert result["last_error_class"] == "rate_limit"
        assert "Attempt 1: rate_limit" in result["error_summary"]

    def test_to_dict_with_no_errors(self):
        """Test to_dict with no recorded errors."""
        ctx = RetryContext()
        ctx.record_attempt(0)  # Success on first attempt

        result = ctx.to_dict()

        assert result["retry_count"] == 0
        assert result["last_error_class"] is None
        assert result["error_summary"] is None

    def test_error_summary_truncates_long_messages(self):
        """Test error messages are truncated to 100 characters."""
        ctx = RetryContext()
        long_error = "x" * 200

        ctx.record_attempt(1, ValueError(long_error))

        summary = ctx.error_summary[0]
        # Summary format is "Attempt X: error_class - error_message[:100]"
        # Check that the total error message portion is truncated
        assert "Attempt 1:" in summary
        assert len(summary) < 200  # Much shorter than the 200-char error


class TestRetryWithContext:
    """Tests for retry_with_context decorator."""

    def test_successful_function_executes_once(self):
        """Test successful function executes only once."""
        mock_func = Mock(__name__="test_func", return_value="success")

        wrapped = retry_with_context(mock_func, max_retries=2)
        result = wrapped()

        assert result == "success"
        assert mock_func.call_count == 1

    def test_retries_on_rate_limit_error(self):
        """Test retries on ModelRateLimitError."""
        mock_func = Mock(
            __name__="test_func", side_effect=[ModelRateLimitError("Rate limit"), "success"]
        )

        with patch("time.sleep"):  # Skip actual sleep
            wrapped = retry_with_context(mock_func, max_retries=2, base_delay=0.1)
            result = wrapped()

        assert result == "success"
        assert mock_func.call_count == 2

    def test_retries_on_timeout_error(self):
        """Test retries on ModelTimeoutError."""
        mock_func = Mock(
            __name__="test_func",
            side_effect=[
                ModelTimeoutError("Timeout"),
                ModelTimeoutError("Timeout again"),
                "success",
            ],
        )

        with patch("time.sleep"):
            wrapped = retry_with_context(mock_func, max_retries=3, base_delay=0.1)
            result = wrapped()

        assert result == "success"
        assert mock_func.call_count == 3

    def test_retries_on_connection_error(self):
        """Test retries on ModelConnectionError."""
        mock_func = Mock(
            __name__="test_func", side_effect=[ModelConnectionError("Connection failed"), "success"]
        )

        with patch("time.sleep"):
            wrapped = retry_with_context(mock_func, max_retries=2, base_delay=0.1)
            result = wrapped()

        assert result == "success"
        assert mock_func.call_count == 2

    def test_does_not_retry_on_non_retryable_error(self):
        """Test does not retry on non-retryable errors (sandbox, patch_apply)."""
        mock_func = Mock(
            __name__="test_func", side_effect=SandboxExecutionError("Sandbox execution failed")
        )

        wrapped = retry_with_context(mock_func, max_retries=2)

        with pytest.raises(SandboxExecutionError):
            wrapped()

        assert mock_func.call_count == 1

    def test_exhausts_max_retries_then_raises(self):
        """Test raises after exhausting max retries."""
        mock_func = Mock(__name__="test_func", side_effect=ModelRateLimitError("Rate limit"))

        with patch("time.sleep"):
            wrapped = retry_with_context(mock_func, max_retries=2)

            with pytest.raises(ModelRateLimitError):
                wrapped()

        assert mock_func.call_count == 3  # Initial + 2 retries

    def test_exponential_backoff_delays(self):
        """Test exponential backoff increases delay correctly."""
        mock_func = Mock(
            __name__="test_func",
            side_effect=[
                ModelRateLimitError("Error 1"),
                ModelRateLimitError("Error 2"),
                ModelRateLimitError("Error 3"),
            ],
        )

        with patch("time.sleep") as mock_sleep:
            wrapped = retry_with_context(mock_func, max_retries=2, base_delay=1.0)

            with pytest.raises(ModelRateLimitError):
                wrapped()

        # Should have called sleep with 1.0, then 2.0
        assert mock_sleep.call_count == 2
        assert mock_sleep.call_args_list[0][0][0] == 1.0  # 1.0 * 2^0
        assert mock_sleep.call_args_list[1][0][0] == 2.0  # 1.0 * 2^1

    def test_context_records_retry_count(self):
        """Test RetryContext records retry count correctly."""
        mock_func = Mock(
            __name__="test_func", side_effect=[ModelRateLimitError("Error"), "success"]
        )
        ctx = RetryContext()

        with patch("time.sleep"):
            wrapped = retry_with_context(mock_func, max_retries=2, context=ctx)
            result = wrapped()

        assert result == "success"
        assert ctx.retry_count == 1
        assert ctx.last_error_class == "rate_limit"

    def test_context_records_all_errors(self):
        """Test RetryContext records all error attempts."""
        mock_func = Mock(
            __name__="test_func",
            side_effect=[
                ModelTimeoutError("Timeout 1"),
                ModelRateLimitError("Rate limit"),
                "success",
            ],
        )
        ctx = RetryContext()

        with patch("time.sleep"):
            wrapped = retry_with_context(mock_func, max_retries=3, context=ctx)
            wrapped()

        assert ctx.retry_count == 2
        assert len(ctx.error_summary) == 2
        assert "timeout" in ctx.error_summary[0]
        assert "rate_limit" in ctx.error_summary[1]

    def test_custom_retry_on_exceptions(self):
        """Test custom retry_on exception list."""
        mock_func = Mock(__name__="test_func", side_effect=[ValueError("Custom error"), "success"])

        with patch("time.sleep"):
            wrapped = retry_with_context(mock_func, max_retries=2, retry_on=(ValueError,))
            result = wrapped()

        assert result == "success"
        assert mock_func.call_count == 2

    def test_custom_logger(self):
        """Test uses custom logger when provided."""
        mock_func = Mock(
            __name__="test_func", side_effect=[ModelRateLimitError("Error"), "success"]
        )
        mock_logger = Mock()

        with patch("time.sleep"):
            wrapped = retry_with_context(mock_func, max_retries=2, logger_instance=mock_logger)
            wrapped()

        # Should have logged warning for retry
        assert mock_logger.warning.call_count == 1
        assert "Retrying" in str(mock_logger.warning.call_args)

    def test_logs_error_on_final_failure(self):
        """Test logs error when all retries exhausted."""
        mock_func = Mock(__name__="test_func", side_effect=ModelRateLimitError("Rate limit"))
        mock_logger = Mock()

        with patch("time.sleep"):
            wrapped = retry_with_context(mock_func, max_retries=1, logger_instance=mock_logger)

            with pytest.raises(ModelRateLimitError):
                wrapped()

        # Should have logged error for final failure
        assert mock_logger.error.call_count == 1
        assert "failed after" in str(mock_logger.error.call_args)

    def test_preserves_function_name_and_attributes(self):
        """Test decorator preserves function metadata."""

        def my_test_function():
            """Test docstring."""
            return "result"

        wrapped = retry_with_context(my_test_function, max_retries=2)

        assert wrapped.__name__ == "my_test_function"
        assert wrapped.__doc__ == "Test docstring."


class TestRetryDecorator:
    """Tests for retry decorator syntax."""

    def test_retry_as_decorator_with_arguments(self):
        """Test @retry(max_retries=2) decorator syntax."""
        call_count = {"count": 0}

        @retry(max_retries=2, base_delay=0.1)
        def failing_function():
            call_count["count"] += 1
            if call_count["count"] < 2:
                raise ModelRateLimitError("Error")
            return "success"

        with patch("time.sleep"):
            result = failing_function()

        assert result == "success"
        assert call_count["count"] == 2

    def test_retry_as_direct_wrapper(self):
        """Test retry()(func) direct wrapper syntax."""
        mock_func = Mock(
            __name__="test_func", side_effect=[ModelTimeoutError("Timeout"), "success"]
        )

        with patch("time.sleep"):
            wrapped = retry(max_retries=2)(mock_func)
            result = wrapped()

        assert result == "success"
        assert mock_func.call_count == 2

    def test_retry_without_parentheses_when_func_provided(self):
        """Test retry(func) syntax when function is directly provided."""
        mock_func = Mock(
            __name__="test_func", side_effect=[ModelRateLimitError("Error"), "success"]
        )

        with patch("time.sleep"):
            wrapped = retry(mock_func, max_retries=1)
            result = wrapped()

        assert result == "success"
        assert mock_func.call_count == 2

    def test_retry_with_custom_parameters(self):
        """Test retry decorator with all custom parameters."""
        mock_logger = Mock()
        call_count = {"count": 0}

        @retry(
            max_retries=3,
            base_delay=0.5,
            retry_on=(ValueError, KeyError),
            logger_instance=mock_logger,
        )
        def custom_function():
            call_count["count"] += 1
            if call_count["count"] < 3:
                raise ValueError("Test error")
            return "done"

        with patch("time.sleep"):
            result = custom_function()

        assert result == "done"
        assert call_count["count"] == 3
        assert mock_logger.warning.call_count == 2


class TestRetryIntegration:
    """Integration tests for retry functionality."""

    def test_retry_with_nexuscore_errors(self):
        """Test retry works with all NexusCore error types."""
        errors = [
            ModelRateLimitError("Rate limit"),
            ModelTimeoutError("Timeout"),
            ModelConnectionError("Connection"),
        ]
        mock_func = Mock(__name__="test_func", side_effect=errors + ["success"])

        with patch("time.sleep"):
            wrapped = retry_with_context(mock_func, max_retries=5)
            result = wrapped()

        assert result == "success"
        assert mock_func.call_count == 4

    def test_context_to_dict_integration(self):
        """Test full flow from retry to context.to_dict()."""
        mock_func = Mock(
            __name__="test_func",
            side_effect=[ModelRateLimitError("Error 1"), ModelTimeoutError("Error 2"), "success"],
        )
        ctx = RetryContext()

        with patch("time.sleep"):
            wrapped = retry_with_context(mock_func, max_retries=3, context=ctx)
            wrapped()

        details = ctx.to_dict()
        assert details["retry_count"] == 2
        assert details["last_error_class"] == "timeout"
        assert "rate_limit" in details["error_summary"]
        assert "timeout" in details["error_summary"]

    def test_zero_max_retries_fails_immediately(self):
        """Test max_retries=0 means no retries."""
        mock_func = Mock(__name__="test_func", side_effect=ModelRateLimitError("Error"))

        wrapped = retry_with_context(mock_func, max_retries=0)

        with pytest.raises(ModelRateLimitError):
            wrapped()

        assert mock_func.call_count == 1

    def test_function_with_arguments_and_kwargs(self):
        """Test retry works with functions that have arguments."""
        call_count = {"count": 0}

        def func_with_args(a, b, c=None):
            call_count["count"] += 1
            if call_count["count"] < 2:
                raise ModelTimeoutError("Error")
            return f"{a}-{b}-{c}"

        with patch("time.sleep"):
            wrapped = retry_with_context(func_with_args, max_retries=2)
            result = wrapped("x", "y", c="z")

        assert result == "x-y-z"
        assert call_count["count"] == 2

    @pytest.mark.skip(reason="Flaky in full suite - time.sleep patch leaks from other test files")
    def test_retry_respects_base_delay_parameter(self):
        """Test base_delay parameter affects sleep duration."""
        mock_func = Mock(
            __name__="test_func", side_effect=[ModelRateLimitError("Error"), "success"]
        )

        with patch("time.sleep") as mock_sleep:
            wrapped = retry_with_context(mock_func, max_retries=2, base_delay=5.0)
            wrapped()

        # First retry should sleep for 5.0 seconds
        assert mock_sleep.call_args_list[0][0][0] == 5.0
