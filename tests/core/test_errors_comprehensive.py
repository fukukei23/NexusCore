"""
Comprehensive tests for errors module.

Tests custom exception classes, error classification, and
HTTP error conversion.
"""

import pytest

from nexuscore.core.errors import (
    InvalidModelOutputError,
    ModelConnectionError,
    ModelRateLimitError,
    ModelTimeoutError,
    NexusCoreError,
    PatchApplyError,
    SandboxExecutionError,
    SandboxSecurityError,
    UnexpectedSystemError,
    classify_error,
    convert_http_error_to_nexus_error,
)


class TestCustomExceptions:
    """Tests for custom exception classes."""

    def test_nexuscore_error_is_base_exception(self):
        """Test NexusCoreError is base for all custom exceptions."""
        error = NexusCoreError("Test error")
        assert isinstance(error, Exception)
        assert str(error) == "Test error"

    def test_model_rate_limit_error(self):
        """Test ModelRateLimitError can be raised and caught."""
        with pytest.raises(ModelRateLimitError) as exc_info:
            raise ModelRateLimitError("Rate limit exceeded")

        assert "Rate limit exceeded" in str(exc_info.value)
        assert isinstance(exc_info.value, NexusCoreError)

    def test_model_timeout_error(self):
        """Test ModelTimeoutError can be raised and caught."""
        with pytest.raises(ModelTimeoutError) as exc_info:
            raise ModelTimeoutError("Request timed out")

        assert "timed out" in str(exc_info.value)
        assert isinstance(exc_info.value, NexusCoreError)

    def test_model_connection_error(self):
        """Test ModelConnectionError can be raised and caught."""
        with pytest.raises(ModelConnectionError) as exc_info:
            raise ModelConnectionError("Connection failed")

        assert "Connection failed" in str(exc_info.value)
        assert isinstance(exc_info.value, NexusCoreError)

    def test_invalid_model_output_error(self):
        """Test InvalidModelOutputError can be raised and caught."""
        with pytest.raises(InvalidModelOutputError) as exc_info:
            raise InvalidModelOutputError("Invalid JSON output")

        assert "Invalid JSON" in str(exc_info.value)
        assert isinstance(exc_info.value, NexusCoreError)

    def test_sandbox_execution_error(self):
        """Test SandboxExecutionError can be raised and caught."""
        with pytest.raises(SandboxExecutionError) as exc_info:
            raise SandboxExecutionError("Test execution failed")

        assert "execution failed" in str(exc_info.value)
        assert isinstance(exc_info.value, NexusCoreError)

    def test_sandbox_security_error(self):
        """Test SandboxSecurityError can be raised and caught."""
        with pytest.raises(SandboxSecurityError) as exc_info:
            raise SandboxSecurityError("Security violation")

        assert "Security violation" in str(exc_info.value)
        assert isinstance(exc_info.value, NexusCoreError)

    def test_patch_apply_error(self):
        """Test PatchApplyError can be raised and caught."""
        with pytest.raises(PatchApplyError) as exc_info:
            raise PatchApplyError("Patch application failed")

        assert "Patch application failed" in str(exc_info.value)
        assert isinstance(exc_info.value, NexusCoreError)

    def test_unexpected_system_error(self):
        """Test UnexpectedSystemError can be raised and caught."""
        with pytest.raises(UnexpectedSystemError) as exc_info:
            raise UnexpectedSystemError("Unexpected error occurred")

        assert "Unexpected error" in str(exc_info.value)
        assert isinstance(exc_info.value, NexusCoreError)


class TestClassifyErrorNexusCoreExceptions:
    """Tests for classify_error with NexusCore exceptions."""

    def test_classify_model_rate_limit_error(self):
        """Test classify_error identifies ModelRateLimitError."""
        error = ModelRateLimitError("Rate limit")
        result = classify_error(error)
        assert result == "rate_limit"

    def test_classify_model_timeout_error(self):
        """Test classify_error identifies ModelTimeoutError."""
        error = ModelTimeoutError("Timeout")
        result = classify_error(error)
        assert result == "timeout"

    def test_classify_model_connection_error(self):
        """Test classify_error identifies ModelConnectionError."""
        error = ModelConnectionError("Connection lost")
        result = classify_error(error)
        assert result == "connection"

    def test_classify_invalid_model_output_error(self):
        """Test classify_error identifies InvalidModelOutputError."""
        error = InvalidModelOutputError("Invalid output")
        result = classify_error(error)
        assert result == "invalid_output"

    def test_classify_sandbox_execution_error(self):
        """Test classify_error identifies SandboxExecutionError."""
        error = SandboxExecutionError("Execution failed")
        result = classify_error(error)
        assert result == "sandbox"

    def test_classify_patch_apply_error(self):
        """Test classify_error identifies PatchApplyError."""
        error = PatchApplyError("Patch failed")
        result = classify_error(error)
        assert result == "patch_apply"

    def test_classify_generic_nexuscore_error(self):
        """Test classify_error returns 'unexpected' for generic NexusCoreError."""
        error = NexusCoreError("Generic error")
        result = classify_error(error)
        assert result == "unexpected"


class TestClassifyErrorHTTPErrors:
    """Tests for classify_error with HTTP and network errors."""

    def test_classify_429_rate_limit_error(self):
        """Test classify_error identifies 429 rate limit errors."""
        error = Exception("HTTP 429: Too Many Requests")
        result = classify_error(error)
        assert result == "rate_limit"

    def test_classify_rate_limit_by_message(self):
        """Test classify_error identifies rate limit from message."""
        error = Exception("Rate limit exceeded, please retry")
        result = classify_error(error)
        assert result == "rate_limit"

    def test_classify_timeout_error_by_message(self):
        """Test classify_error identifies timeout from message."""
        error = Exception("Request timeout after 30 seconds")
        result = classify_error(error)
        assert result == "timeout"

    def test_classify_timeout_error_by_type_name(self):
        """Test classify_error identifies timeout from exception type."""

        class TimeoutException(Exception):
            pass

        error = TimeoutException("Connection timed out")
        result = classify_error(error)
        assert result == "timeout"

    def test_classify_connection_error_by_message(self):
        """Test classify_error identifies connection errors from message."""
        error = Exception("Connection refused")
        result = classify_error(error)
        assert result == "connection"

    def test_classify_network_error(self):
        """Test classify_error identifies network errors."""
        error = Exception("Network error occurred")
        result = classify_error(error)
        assert result == "connection"

    def test_classify_dns_error(self):
        """Test classify_error identifies DNS resolution errors."""
        error = Exception("Failed to resolve DNS")
        result = classify_error(error)
        assert result == "connection"

    def test_classify_connection_error_by_type_name(self):
        """Test classify_error identifies connection from exception type."""

        class ConnectionError(Exception):
            pass

        error = ConnectionError("Failed to connect")
        result = classify_error(error)
        assert result == "connection"


class TestClassifyErrorJSONErrors:
    """Tests for classify_error with JSON parsing errors."""

    def test_classify_json_decode_error(self):
        """Test classify_error identifies JSON decode errors."""
        error = Exception("Failed to decode JSON response")
        result = classify_error(error)
        assert result == "invalid_output"

    def test_classify_json_parse_error(self):
        """Test classify_error identifies JSON parse errors."""
        error = Exception("JSON parse error at line 5")
        result = classify_error(error)
        assert result == "invalid_output"

    def test_classify_invalid_format_error(self):
        """Test classify_error identifies invalid format errors."""
        error = Exception("Invalid format in response")
        result = classify_error(error)
        assert result == "invalid_output"

    def test_classify_json_error_by_type_name(self):
        """Test classify_error identifies JSON errors from type name."""

        class JSONDecodeError(Exception):
            pass

        error = JSONDecodeError("Cannot decode")
        result = classify_error(error)
        assert result == "invalid_output"


class TestClassifyErrorSandboxErrors:
    """Tests for classify_error with sandbox-related errors."""

    def test_classify_sandbox_error_by_message(self):
        """Test classify_error identifies sandbox errors from message."""
        error = Exception("Sandbox execution failed")
        result = classify_error(error)
        assert result == "sandbox"

    def test_classify_subprocess_error(self):
        """Test classify_error identifies subprocess errors."""
        error = Exception("Subprocess failed to execute")
        result = classify_error(error)
        assert result == "sandbox"

    def test_classify_execution_failed_error(self):
        """Test classify_error identifies execution failures."""
        error = Exception("Command execution failed with code 1")
        result = classify_error(error)
        assert result == "sandbox"


class TestClassifyErrorPatchErrors:
    """Tests for classify_error with patch-related errors."""

    def test_classify_patch_error_by_message(self):
        """Test classify_error identifies patch errors from message."""
        error = Exception("Failed to apply patch")
        result = classify_error(error)
        assert result == "patch_apply"

    def test_classify_diff_error(self):
        """Test classify_error identifies diff application errors."""
        error = Exception("Diff application failed")
        result = classify_error(error)
        assert result == "patch_apply"


class TestClassifyErrorUnexpected:
    """Tests for classify_error with unexpected/unknown errors."""

    def test_classify_unknown_error_returns_unexpected(self):
        """Test classify_error returns 'unexpected' for unknown errors."""
        error = Exception("Some random error")
        result = classify_error(error)
        assert result == "unexpected"

    def test_classify_value_error_returns_unexpected(self):
        """Test classify_error returns 'unexpected' for ValueError."""
        error = ValueError("Invalid value")
        result = classify_error(error)
        assert result == "unexpected"

    def test_classify_key_error_returns_unexpected(self):
        """Test classify_error returns 'unexpected' for KeyError."""
        error = KeyError("missing_key")
        result = classify_error(error)
        assert result == "unexpected"


class TestConvertHTTPErrorToNexusError:
    """Tests for convert_http_error_to_nexus_error function."""

    def test_convert_rate_limit_error(self):
        """Test converts rate limit error to ModelRateLimitError."""
        http_error = Exception("HTTP 429: Rate limit exceeded")

        result = convert_http_error_to_nexus_error(http_error)

        assert isinstance(result, ModelRateLimitError)
        assert "Rate limit error" in str(result)
        assert "429" in str(result)

    def test_convert_timeout_error(self):
        """Test converts timeout error to ModelTimeoutError."""
        http_error = Exception("Request timed out")

        result = convert_http_error_to_nexus_error(http_error)

        assert isinstance(result, ModelTimeoutError)
        assert "Timeout error" in str(result)

    def test_convert_connection_error(self):
        """Test converts connection error to ModelConnectionError."""
        http_error = Exception("Connection refused")

        result = convert_http_error_to_nexus_error(http_error)

        assert isinstance(result, ModelConnectionError)
        assert "Connection error" in str(result)

    def test_convert_invalid_output_error(self):
        """Test converts JSON error to InvalidModelOutputError."""
        http_error = Exception("Invalid JSON response")

        result = convert_http_error_to_nexus_error(http_error)

        assert isinstance(result, InvalidModelOutputError)
        assert "Invalid model output" in str(result)

    def test_convert_sandbox_error(self):
        """Test converts sandbox error to SandboxExecutionError."""
        http_error = Exception("Sandbox execution failed")

        result = convert_http_error_to_nexus_error(http_error)

        assert isinstance(result, SandboxExecutionError)
        assert "Sandbox execution error" in str(result)

    def test_convert_patch_error(self):
        """Test converts patch error to PatchApplyError."""
        http_error = Exception("Patch application failed")

        result = convert_http_error_to_nexus_error(http_error)

        assert isinstance(result, PatchApplyError)
        assert "Patch apply error" in str(result)

    def test_convert_unexpected_error(self):
        """Test converts unknown error to UnexpectedSystemError."""
        http_error = ValueError("Some random error")

        result = convert_http_error_to_nexus_error(http_error)

        assert isinstance(result, UnexpectedSystemError)
        assert "Unexpected error" in str(result)
        assert "ValueError" in str(result)

    def test_convert_preserves_original_message(self):
        """Test conversion preserves original error message."""
        original_message = "Original error details: API key invalid"
        http_error = Exception(original_message)

        result = convert_http_error_to_nexus_error(http_error)

        assert original_message in str(result)

    def test_convert_includes_error_type_name(self):
        """Test conversion includes original exception type name."""

        class CustomHTTPError(Exception):
            pass

        http_error = CustomHTTPError("Custom error")

        result = convert_http_error_to_nexus_error(http_error)

        assert "CustomHTTPError" in str(result)


class TestErrorClassificationIntegration:
    """Integration tests for error classification and conversion."""

    def test_classify_and_convert_rate_limit(self):
        """Test full flow: classify then convert rate limit error."""
        error = Exception("HTTP 429: Too many requests")

        error_class = classify_error(error)
        converted = convert_http_error_to_nexus_error(error)

        assert error_class == "rate_limit"
        assert isinstance(converted, ModelRateLimitError)

    def test_classify_and_convert_timeout(self):
        """Test full flow: classify then convert timeout error."""
        error = Exception("Connection timed out after 30s")

        error_class = classify_error(error)
        converted = convert_http_error_to_nexus_error(error)

        assert error_class == "timeout"
        assert isinstance(converted, ModelTimeoutError)

    def test_classify_nexuscore_errors_directly(self):
        """Test NexusCore errors are classified without conversion."""
        errors = [
            (ModelRateLimitError("Test"), "rate_limit"),
            (ModelTimeoutError("Test"), "timeout"),
            (ModelConnectionError("Test"), "connection"),
            (InvalidModelOutputError("Test"), "invalid_output"),
            (SandboxExecutionError("Test"), "sandbox"),
            (PatchApplyError("Test"), "patch_apply"),
        ]

        for error, expected_class in errors:
            result = classify_error(error)
            assert result == expected_class

    def test_case_insensitive_classification(self):
        """Test classification is case-insensitive."""
        errors = [
            Exception("TIMEOUT occurred"),
            Exception("Timeout occurred"),
            Exception("timeout occurred"),
        ]

        for error in errors:
            result = classify_error(error)
            assert result == "timeout"

    def test_multiple_keywords_in_error_message(self):
        """Test classification when multiple keywords present."""
        # "timeout" is checked before "connection" in classify_error
        error = Exception("Connection timeout while connecting to server")

        result = classify_error(error)

        # Should classify as timeout (checked first in the code)
        assert result == "timeout"

    def test_converted_errors_are_catchable_as_nexuscore_error(self):
        """Test converted errors can be caught as NexusCoreError."""
        http_error = Exception("Rate limit exceeded")
        converted = convert_http_error_to_nexus_error(http_error)

        assert isinstance(converted, NexusCoreError)

        # Should be catchable as base class
        try:
            raise converted
        except NexusCoreError as e:
            assert "Rate limit" in str(e)

    def test_all_custom_exceptions_inherit_from_base(self):
        """Test all custom exceptions inherit from NexusCoreError."""
        exception_classes = [
            ModelRateLimitError,
            ModelTimeoutError,
            ModelConnectionError,
            InvalidModelOutputError,
            SandboxExecutionError,
            SandboxSecurityError,
            PatchApplyError,
            UnexpectedSystemError,
        ]

        for exc_class in exception_classes:
            error = exc_class("Test")
            assert isinstance(error, NexusCoreError)
            assert isinstance(error, Exception)
