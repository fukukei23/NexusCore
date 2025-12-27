"""
Tests for error classification system

エラー分類ロジックの正確性を保証するテスト群（リトライ戦略の基盤）
"""
import pytest
from src.nexuscore.core.errors import (
    NexusCoreError,
    ModelRateLimitError,
    ModelTimeoutError,
    ModelConnectionError,
    InvalidModelOutputError,
    SandboxExecutionError,
    PatchApplyError,
    UnexpectedSystemError,
    classify_error,
    convert_http_error_to_nexus_error,
)


class TestErrorClassification:
    """classify_error() のテスト群"""

    # ==============================================================================
    # カスタム例外の分類テスト
    # ==============================================================================

    def test_classify_rate_limit_error(self):
        """ModelRateLimitError の分類テスト"""
        exc = ModelRateLimitError("Rate limit exceeded")
        assert classify_error(exc) == "rate_limit"

    def test_classify_timeout_error(self):
        """ModelTimeoutError の分類テスト"""
        exc = ModelTimeoutError("Request timed out after 30s")
        assert classify_error(exc) == "timeout"

    def test_classify_connection_error(self):
        """ModelConnectionError の分類テスト"""
        exc = ModelConnectionError("DNS resolution failed")
        assert classify_error(exc) == "connection"

    def test_classify_invalid_output_error(self):
        """InvalidModelOutputError の分類テスト"""
        exc = InvalidModelOutputError("JSON parse failed")
        assert classify_error(exc) == "invalid_output"

    def test_classify_sandbox_error(self):
        """SandboxExecutionError の分類テスト"""
        exc = SandboxExecutionError("Test execution failed")
        assert classify_error(exc) == "sandbox"

    def test_classify_patch_apply_error(self):
        """PatchApplyError の分類テスト"""
        exc = PatchApplyError("Patch application failed")
        assert classify_error(exc) == "patch_apply"

    def test_classify_base_nexus_error(self):
        """基底クラス NexusCoreError の分類テスト"""
        exc = NexusCoreError("Some generic error")
        assert classify_error(exc) == "unexpected"

    def test_classify_unexpected_system_error(self):
        """UnexpectedSystemError の分類テスト"""
        exc = UnexpectedSystemError("Unexpected error occurred")
        assert classify_error(exc) == "unexpected"

    # ==============================================================================
    # エラーメッセージからの分類テスト（一般的な例外）
    # ==============================================================================

    def test_classify_rate_limit_from_message_429(self):
        """エラーメッセージ内の '429' から rate_limit を分類"""
        exc = Exception("HTTP 429: Rate limit exceeded")
        assert classify_error(exc) == "rate_limit"

    def test_classify_rate_limit_from_message_text(self):
        """エラーメッセージ内の 'rate limit' から分類"""
        exc = Exception("API rate limit exceeded, please retry later")
        assert classify_error(exc) == "rate_limit"

    def test_classify_timeout_from_message(self):
        """エラーメッセージ内の 'timeout' から分類"""
        exc = Exception("Connection timeout after 60s")
        assert classify_error(exc) == "timeout"

    def test_classify_timed_out_from_message(self):
        """エラーメッセージ内の 'timed out' から分類"""
        exc = Exception("Request timed out")
        assert classify_error(exc) == "timeout"

    def test_classify_connection_from_message(self):
        """エラーメッセージ内の 'connection' から分類"""
        exc = Exception("Connection refused by server")
        assert classify_error(exc) == "connection"

    def test_classify_network_from_message(self):
        """エラーメッセージ内の 'network' から分類"""
        exc = Exception("Network unreachable")
        assert classify_error(exc) == "connection"

    def test_classify_dns_from_message(self):
        """エラーメッセージ内の 'dns' から分類"""
        exc = Exception("DNS resolution failed for api.openai.com")
        assert classify_error(exc) == "connection"

    def test_classify_json_parse_error(self):
        """JSON パースエラーを invalid_output として分類（型名に json を含む必要がある）"""
        # 型名に 'json' が含まれ、かつメッセージにもキーワードが必要
        class JSONParseError(Exception):
            pass

        exc = JSONParseError("Failed to parse JSON: unexpected token at position 42")
        assert classify_error(exc) == "invalid_output"

    def test_classify_json_decode_error(self):
        """JSON デコードエラーを invalid_output として分類"""
        class JSONDecodeError(Exception):
            pass

        exc = JSONDecodeError("Failed to decode JSON response")
        assert classify_error(exc) == "invalid_output"

    def test_classify_generic_json_error_as_unexpected(self):
        """一般的な Exception での JSON エラーは unexpected として分類"""
        # 型名に json/parse が含まれない場合は unexpected
        exc = Exception("JSON parse error: invalid syntax")
        assert classify_error(exc) == "unexpected"

    def test_classify_sandbox_from_message(self):
        """エラーメッセージ内の 'sandbox' から分類"""
        exc = Exception("Sandbox execution failed with exit code 1")
        assert classify_error(exc) == "sandbox"

    def test_classify_subprocess_from_message(self):
        """エラーメッセージ内の 'subprocess' から分類"""
        exc = Exception("subprocess execution failed")
        assert classify_error(exc) == "sandbox"

    def test_classify_patch_from_message(self):
        """エラーメッセージ内の 'patch' から分類"""
        exc = Exception("Failed to apply patch: hunk #1 FAILED")
        assert classify_error(exc) == "patch_apply"

    def test_classify_diff_from_message(self):
        """エラーメッセージ内の 'diff' から分類"""
        exc = Exception("Diff application failed")
        assert classify_error(exc) == "patch_apply"

    # ==============================================================================
    # 例外型名からの分類テスト
    # ==============================================================================

    def test_classify_from_exception_type_timeout(self):
        """例外型名に 'Timeout' が含まれる場合の分類"""
        class CustomTimeoutError(Exception):
            pass

        exc = CustomTimeoutError("Custom timeout")
        assert classify_error(exc) == "timeout"

    def test_classify_from_exception_type_connection(self):
        """例外型名に 'Connection' が含まれる場合の分類"""
        class ConnectionRefusedError(Exception):
            pass

        exc = ConnectionRefusedError("Connection refused")
        assert classify_error(exc) == "connection"

    # ==============================================================================
    # デフォルト動作のテスト
    # ==============================================================================

    def test_classify_unknown_error_as_unexpected(self):
        """未知のエラーは 'unexpected' として分類"""
        exc = ValueError("Some random value error")
        assert classify_error(exc) == "unexpected"

    def test_classify_key_error_as_unexpected(self):
        """KeyError は 'unexpected' として分類"""
        exc = KeyError("missing_key")
        assert classify_error(exc) == "unexpected"

    def test_classify_attribute_error_as_unexpected(self):
        """AttributeError は 'unexpected' として分類"""
        exc = AttributeError("'NoneType' object has no attribute 'value'")
        assert classify_error(exc) == "unexpected"


class TestConvertHttpErrorToNexusError:
    """convert_http_error_to_nexus_error() のテスト群"""

    def test_convert_rate_limit_error(self):
        """HTTP 429 エラーを ModelRateLimitError に変換"""
        http_error = Exception("HTTP 429: Too Many Requests")
        nexus_error = convert_http_error_to_nexus_error(http_error)

        assert isinstance(nexus_error, ModelRateLimitError)
        assert "Rate limit error" in str(nexus_error)
        assert "429" in str(nexus_error)

    def test_convert_timeout_error(self):
        """タイムアウトエラーを ModelTimeoutError に変換"""
        http_error = Exception("Request timeout after 30s")
        nexus_error = convert_http_error_to_nexus_error(http_error)

        assert isinstance(nexus_error, ModelTimeoutError)
        assert "Timeout error" in str(nexus_error)

    def test_convert_connection_error(self):
        """接続エラーを ModelConnectionError に変換"""
        http_error = Exception("Connection failed: DNS resolution error")
        nexus_error = convert_http_error_to_nexus_error(http_error)

        assert isinstance(nexus_error, ModelConnectionError)
        assert "Connection error" in str(nexus_error)

    def test_convert_invalid_output_error(self):
        """JSON パースエラーを InvalidModelOutputError に変換（型名に json を含む必要）"""
        class JSONParseError(Exception):
            pass

        http_error = JSONParseError("JSON decode error: invalid syntax at position 10")
        nexus_error = convert_http_error_to_nexus_error(http_error)

        assert isinstance(nexus_error, InvalidModelOutputError)
        assert "Invalid model output" in str(nexus_error)

    def test_convert_invalid_model_output_directly(self):
        """InvalidModelOutputError を直接変換"""
        http_error = InvalidModelOutputError("Model returned invalid JSON")
        nexus_error = convert_http_error_to_nexus_error(http_error)

        assert isinstance(nexus_error, InvalidModelOutputError)
        assert "Invalid model output" in str(nexus_error)

    def test_convert_sandbox_error(self):
        """サンドボックスエラーを SandboxExecutionError に変換"""
        http_error = Exception("Sandbox execution failed with code 1")
        nexus_error = convert_http_error_to_nexus_error(http_error)

        assert isinstance(nexus_error, SandboxExecutionError)
        assert "Sandbox execution error" in str(nexus_error)

    def test_convert_patch_error(self):
        """パッチ適用エラーを PatchApplyError に変換"""
        http_error = Exception("Failed to apply patch: hunk failed")
        nexus_error = convert_http_error_to_nexus_error(http_error)

        assert isinstance(nexus_error, PatchApplyError)
        assert "Patch apply error" in str(nexus_error)

    def test_convert_unexpected_error(self):
        """未知のエラーを UnexpectedSystemError に変換"""
        http_error = ValueError("Some unexpected value error")
        nexus_error = convert_http_error_to_nexus_error(http_error)

        assert isinstance(nexus_error, UnexpectedSystemError)
        assert "Unexpected error" in str(nexus_error)
        assert "ValueError" in str(nexus_error)

    def test_convert_preserves_original_message(self):
        """元のエラーメッセージが保持されることを確認"""
        original_message = "Original error message with details"
        http_error = Exception(original_message)
        nexus_error = convert_http_error_to_nexus_error(http_error)

        assert original_message in str(nexus_error)


class TestCustomExceptionHierarchy:
    """カスタム例外の継承関係のテスト"""

    def test_all_custom_exceptions_inherit_from_base(self):
        """すべてのカスタム例外が NexusCoreError を継承していることを確認"""
        assert issubclass(ModelRateLimitError, NexusCoreError)
        assert issubclass(ModelTimeoutError, NexusCoreError)
        assert issubclass(ModelConnectionError, NexusCoreError)
        assert issubclass(InvalidModelOutputError, NexusCoreError)
        assert issubclass(SandboxExecutionError, NexusCoreError)
        assert issubclass(PatchApplyError, NexusCoreError)
        assert issubclass(UnexpectedSystemError, NexusCoreError)

    def test_base_exception_inherits_from_exception(self):
        """NexusCoreError が Exception を継承していることを確認"""
        assert issubclass(NexusCoreError, Exception)

    def test_can_catch_all_nexus_errors(self):
        """すべての NexusCore エラーを NexusCoreError で捕捉できることを確認"""
        errors = [
            ModelRateLimitError("test"),
            ModelTimeoutError("test"),
            ModelConnectionError("test"),
            InvalidModelOutputError("test"),
            SandboxExecutionError("test"),
            PatchApplyError("test"),
            UnexpectedSystemError("test"),
        ]

        for error in errors:
            try:
                raise error
            except NexusCoreError:
                pass  # Successfully caught
            except Exception:
                pytest.fail(f"{type(error).__name__} should be catchable as NexusCoreError")


class TestEdgeCases:
    """エッジケースのテスト"""

    def test_classify_empty_message_error(self):
        """空のメッセージのエラーを分類"""
        exc = Exception("")
        # デフォルトで 'unexpected' になる
        assert classify_error(exc) == "unexpected"

    def test_classify_error_with_mixed_keywords(self):
        """複数のキーワードが含まれる場合、最初にマッチしたもので分類"""
        # 'rate limit' が先に評価される
        exc = Exception("HTTP 429: rate limit exceeded due to timeout")
        assert classify_error(exc) == "rate_limit"

    def test_classify_case_insensitive(self):
        """大文字小文字を区別せずに分類"""
        exc = Exception("TIMEOUT ERROR")
        assert classify_error(exc) == "timeout"

    def test_convert_already_nexus_error(self):
        """既に NexusCore 例外の場合でも変換可能"""
        original = ModelRateLimitError("Original rate limit error")
        converted = convert_http_error_to_nexus_error(original)

        # 再度変換されても rate_limit として分類される
        assert isinstance(converted, ModelRateLimitError)

    def test_classify_error_with_newlines(self):
        """改行を含むエラーメッセージの分類"""
        exc = Exception("Error occurred:\nTimeout after 30s\nPlease retry")
        assert classify_error(exc) == "timeout"

    def test_classify_error_with_special_characters(self):
        """特殊文字を含むエラーメッセージの分類"""
        exc = Exception("Error: connection failed [errno 111] @host:port")
        assert classify_error(exc) == "connection"
