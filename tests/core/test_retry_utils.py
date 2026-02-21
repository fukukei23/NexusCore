"""
Tests for retry utilities with exponential backoff

指数バックオフリトライロジックの信頼性を保証するテスト群
"""
import pytest
import time
from unittest.mock import Mock, patch
from nexuscore.core.retry_utils import (
    retry,
    retry_with_context,
    RetryContext,
)
from nexuscore.core.errors import (
    ModelRateLimitError,
    ModelTimeoutError,
    ModelConnectionError,
    InvalidModelOutputError,
    SandboxExecutionError,
)


class TestRetryContext:
    """RetryContext のテスト群"""

    def test_initial_state(self):
        """初期状態のテスト"""
        context = RetryContext()
        assert context.retry_count == 0
        assert context.last_error_class is None
        assert context.error_summary == []

    def test_record_attempt_without_error(self):
        """エラーなし試行の記録テスト"""
        context = RetryContext()
        context.record_attempt(0)  # 初回試行 (0-indexed)

        assert context.retry_count == 0
        assert context.last_error_class is None
        assert context.error_summary == []

    def test_record_attempt_with_error(self):
        """エラーあり試行の記録テスト"""
        context = RetryContext()
        error = ModelTimeoutError("Timeout after 30s")
        context.record_attempt(1, error)  # 2回目の試行 = 1回リトライ

        assert context.retry_count == 1
        assert context.last_error_class == "timeout"
        assert len(context.error_summary) == 1
        assert "Attempt 1" in context.error_summary[0]
        assert "timeout" in context.error_summary[0]

    def test_record_multiple_attempts(self):
        """複数回の試行記録テスト"""
        context = RetryContext()

        context.record_attempt(0)  # 初回成功
        context.record_attempt(1, ModelRateLimitError("Rate limit"))  # 2回目失敗
        context.record_attempt(2, ModelTimeoutError("Timeout"))  # 3回目失敗

        assert context.retry_count == 2
        assert context.last_error_class == "timeout"
        assert len(context.error_summary) == 2

    def test_to_dict(self):
        """辞書変換のテスト"""
        context = RetryContext()
        context.record_attempt(1, ModelRateLimitError("Rate limit"))
        context.record_attempt(2, ModelTimeoutError("Timeout"))

        result = context.to_dict()

        assert result["retry_count"] == 2
        assert result["last_error_class"] == "timeout"
        assert "Attempt 1" in result["error_summary"]
        assert "Attempt 2" in result["error_summary"]

    def test_to_dict_no_errors(self):
        """エラーなしの辞書変換テスト"""
        context = RetryContext()
        context.record_attempt(0)  # 初回成功

        result = context.to_dict()

        assert result["retry_count"] == 0
        assert result["last_error_class"] is None
        assert result["error_summary"] is None


class TestRetryDecorator:
    """retry デコレータのテスト群"""

    def test_success_on_first_attempt(self):
        """初回試行で成功する場合のテスト"""
        call_count = 0

        @retry(max_retries=2)
        def successful_function():
            nonlocal call_count
            call_count += 1
            return "success"

        result = successful_function()
        assert result == "success"
        assert call_count == 1  # 1回だけ呼ばれる

    def test_success_after_one_retry(self):
        """1回リトライ後に成功する場合のテスト"""
        call_count = 0

        @retry(max_retries=2, base_delay=0.1)
        def flaky_function():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ModelTimeoutError("Timeout on API call")
            return "success"

        result = flaky_function()
        assert result == "success"
        assert call_count == 2  # 2回目で成功

    def test_success_after_two_retries(self):
        """2回リトライ後に成功するテスト"""
        call_count = 0

        @retry(max_retries=3, base_delay=0.1)
        def very_flaky_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ModelConnectionError("Connection failed")
            return "success"

        result = very_flaky_function()
        assert result == "success"
        assert call_count == 3  # 3回目で成功

    def test_max_retries_exhausted(self):
        """最大リトライ回数を超えた場合のテスト"""
        call_count = 0

        @retry(max_retries=2, base_delay=0.1)
        def always_failing_function():
            nonlocal call_count
            call_count += 1
            raise ModelRateLimitError("Rate limit exceeded")

        with pytest.raises(ModelRateLimitError):
            always_failing_function()

        assert call_count == 3  # max_retries=2 なので計3回試行 (0, 1, 2)

    def test_exponential_backoff_delays(self):
        """指数バックオフの遅延が正しいことを確認"""
        call_times = []

        @retry(max_retries=2, base_delay=0.2)
        def timed_function():
            call_times.append(time.time())
            raise ModelTimeoutError("Timeout")

        with pytest.raises(ModelTimeoutError):
            timed_function()

        # 遅延の確認（0.2s、0.4s の指数バックオフ）
        assert len(call_times) == 3
        delay_1 = call_times[1] - call_times[0]
        delay_2 = call_times[2] - call_times[1]

        # 許容誤差を考慮して検証
        assert 0.15 < delay_1 < 0.35, f"First delay should be ~0.2s, got {delay_1:.3f}s"
        assert 0.30 < delay_2 < 0.60, f"Second delay should be ~0.4s, got {delay_2:.3f}s"

    def test_non_retryable_error_not_retried(self):
        """リトライ対象外のエラーでは即座に失敗するテスト"""
        call_count = 0

        @retry(max_retries=3, base_delay=0.1)
        def non_retryable_error():
            nonlocal call_count
            call_count += 1
            raise ValueError("This is not a retryable error")

        with pytest.raises(ValueError):
            non_retryable_error()

        assert call_count == 1  # リトライせず即座に失敗

    def test_invalid_model_output_error_is_retried(self):
        """InvalidModelOutputError はリトライ可能（Spec 3.3.1）"""
        call_count = 0
        max_retries = 3

        @retry(max_retries=2, base_delay=0.1)
        def invalid_output():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise InvalidModelOutputError("Model returned invalid JSON")
            return "success"

        result = invalid_output()
        assert result == "success"
        assert call_count == 2  # リトライ後に成功

    def test_sandbox_error_not_retried(self):
        """SandboxExecutionError はリトライされないテスト"""
        call_count = 0

        @retry(max_retries=3, base_delay=0.1)
        def sandbox_fail():
            nonlocal call_count
            call_count += 1
            raise SandboxExecutionError("Test failed")

        with pytest.raises(SandboxExecutionError):
            sandbox_fail()

        assert call_count == 1  # リトライせず即座に失敗

    def test_decorator_without_parentheses(self):
        """括弧なしのデコレータ使用テスト"""
        call_count = 0

        @retry
        def simple_function():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ModelTimeoutError("Timeout")
            return "success"

        result = simple_function()
        assert result == "success"
        assert call_count == 2

    def test_custom_retry_on_exceptions(self):
        """カスタムリトライ対象例外のテスト"""
        call_count = 0

        @retry(max_retries=2, base_delay=0.1, retry_on=(ValueError,))
        def custom_retryable():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ValueError("Custom retryable error")
            return "success"

        result = custom_retryable()
        assert result == "success"
        assert call_count == 2

    def test_return_value_preservation(self):
        """戻り値が正しく保持されることを確認"""
        @retry(max_retries=2, base_delay=0.1)
        def return_dict():
            return {"status": "ok", "value": 42}

        result = return_dict()
        assert result == {"status": "ok", "value": 42}

    def test_function_with_arguments(self):
        """引数を持つ関数のテスト"""
        call_count = 0

        @retry(max_retries=2, base_delay=0.1)
        def add_numbers(a, b, c=0):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ModelTimeoutError("Timeout")
            return a + b + c

        result = add_numbers(10, 20, c=5)
        assert result == 35
        assert call_count == 2


class TestRetryWithContext:
    """retry_with_context のテスト群"""

    def test_context_tracks_successful_attempt(self):
        """成功時の context 記録テスト"""
        context = RetryContext()

        def successful_func():
            return "success"

        wrapped = retry_with_context(successful_func, max_retries=2, base_delay=0.1, context=context)
        result = wrapped()

        assert result == "success"
        assert context.retry_count == 0
        assert context.last_error_class is None

    def test_context_tracks_retry_attempts(self):
        """リトライ試行の context 記録テスト"""
        context = RetryContext()
        call_count = 0

        def flaky_func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ModelTimeoutError("Timeout")
            return "success"

        wrapped = retry_with_context(flaky_func, max_retries=2, base_delay=0.1, context=context)
        result = wrapped()

        assert result == "success"
        assert context.retry_count == 1  # 1回リトライ（計2回試行）
        assert context.last_error_class == "timeout"
        assert len(context.error_summary) == 1

    def test_context_tracks_all_failures(self):
        """すべての失敗を context が記録するテスト"""
        context = RetryContext()
        call_count = 0

        def always_failing():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ModelRateLimitError("Rate limit 1")
            elif call_count == 2:
                raise ModelTimeoutError("Timeout 2")
            else:
                raise ModelConnectionError("Connection 3")

        wrapped = retry_with_context(always_failing, max_retries=2, base_delay=0.1, context=context)

        with pytest.raises(ModelConnectionError):
            wrapped()

        assert context.retry_count == 2
        assert context.last_error_class == "connection"
        assert len(context.error_summary) == 3  # 3回すべて記録

    def test_context_to_dict_integration(self):
        """context.to_dict() の統合テスト"""
        context = RetryContext()
        call_count = 0

        def multi_retry():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ModelTimeoutError("Timeout")
            return "success"

        wrapped = retry_with_context(multi_retry, max_retries=3, base_delay=0.1, context=context)
        result = wrapped()

        assert result == "success"

        details = context.to_dict()
        assert details["retry_count"] == 2
        assert details["last_error_class"] == "timeout"
        # Attempt indexing is 0-based: Attempt 0 (fail), Attempt 1 (fail), Attempt 2 (success)
        # Only failures are recorded in error_summary
        assert "Attempt 0" in details["error_summary"]
        assert "Attempt 1" in details["error_summary"]

    def test_without_context_still_works(self):
        """context なしでも動作することを確認"""
        call_count = 0

        def flaky():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ModelTimeoutError("Timeout")
            return "success"

        wrapped = retry_with_context(flaky, max_retries=2, base_delay=0.1)
        result = wrapped()

        assert result == "success"
        assert call_count == 2

    def test_custom_logger(self):
        """カスタムロガーのテスト"""
        mock_logger = Mock()
        call_count = 0

        def flaky_with_log():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ModelTimeoutError("Timeout")
            return "success"

        wrapped = retry_with_context(
            flaky_with_log,
            max_retries=2,
            base_delay=0.1,
            logger_instance=mock_logger
        )
        result = wrapped()

        assert result == "success"
        assert mock_logger.warning.called  # ログが呼ばれたことを確認


class TestEdgeCases:
    """エッジケースのテスト"""

    def test_max_retries_zero(self):
        """max_retries=0 の場合のテスト"""
        call_count = 0

        @retry(max_retries=0, base_delay=0.1)
        def no_retry():
            nonlocal call_count
            call_count += 1
            raise ModelTimeoutError("Timeout")

        with pytest.raises(ModelTimeoutError):
            no_retry()

        assert call_count == 1  # リトライなし、1回だけ試行

    def test_very_short_delay(self):
        """非常に短い遅延のテスト"""
        call_count = 0

        @retry(max_retries=2, base_delay=0.01)
        def fast_retry():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ModelTimeoutError("Timeout")
            return "success"

        start = time.time()
        result = fast_retry()
        duration = time.time() - start

        assert result == "success"
        assert call_count == 3
        # 総遅延時間が短いことを確認 (0.01 + 0.02 = 0.03秒)
        assert duration < 0.5

    def test_mixed_retryable_and_non_retryable_errors(self):
        """リトライ可能・不可能エラーの混在テスト"""
        call_count = 0

        @retry(max_retries=3, base_delay=0.1)
        def mixed_errors():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ModelTimeoutError("Retryable timeout")
            else:
                raise ValueError("Non-retryable error")

        with pytest.raises(ValueError):
            mixed_errors()

        assert call_count == 2  # 1回リトライ後、非リトライエラーで停止

    def test_exception_chain_preserved(self):
        """例外チェーンが保持されることを確認"""
        @retry(max_retries=1, base_delay=0.1)
        def chained_exception():
            try:
                raise ValueError("Original error")
            except ValueError as e:
                raise ModelTimeoutError("Wrapped error") from e

        with pytest.raises(ModelTimeoutError) as exc_info:
            chained_exception()

        # 元の例外が保持されていることを確認
        assert exc_info.value.__cause__ is not None
        assert isinstance(exc_info.value.__cause__, ValueError)


class TestSpec33RetryControlPolicy:
    """Spec 3.3: Retry / Failure Control Policy のテスト"""

    def test_retryable_rate_limit(self):
        """rate_limit はリトライ可能（3.3.1）"""
        call_count = 0

        @retry(max_retries=2, base_delay=0.1)
        def rate_limit_func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ModelRateLimitError("Rate limit exceeded")
            return "success"

        result = rate_limit_func()
        assert result == "success"
        assert call_count == 2

    def test_retryable_timeout(self):
        """timeout はリトライ可能（3.3.1）"""
        call_count = 0

        @retry(max_retries=2, base_delay=0.1)
        def timeout_func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ModelTimeoutError("Timeout")
            return "success"

        result = timeout_func()
        assert result == "success"
        assert call_count == 2

    def test_retryable_connection(self):
        """connection はリトライ可能（3.3.1）"""
        call_count = 0

        @retry(max_retries=2, base_delay=0.1)
        def connection_func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ModelConnectionError("Connection failed")
            return "success"

        result = connection_func()
        assert result == "success"
        assert call_count == 2

    def test_retryable_invalid_output(self):
        """invalid_output はリトライ可能（3.3.1）"""
        call_count = 0

        @retry(max_retries=2, base_delay=0.1)
        def invalid_output_func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise InvalidModelOutputError("Invalid JSON")
            return "success"

        result = invalid_output_func()
        assert result == "success"
        assert call_count == 2

    def test_non_retryable_sandbox(self):
        """sandbox はリトライ不可（3.3.1）"""
        call_count = 0

        @retry(max_retries=3, base_delay=0.1)
        def sandbox_func():
            nonlocal call_count
            call_count += 1
            raise SandboxExecutionError("Sandbox failed")

        with pytest.raises(SandboxExecutionError):
            sandbox_func()

        assert call_count == 1  # リトライせず即座に失敗

    def test_non_retryable_patch_apply(self):
        """patch_apply はリトライ不可（3.3.1）"""
        from nexuscore.core.errors import PatchApplyError

        call_count = 0

        @retry(max_retries=3, base_delay=0.1)
        def patch_func():
            nonlocal call_count
            call_count += 1
            raise PatchApplyError("Patch failed")

        with pytest.raises(PatchApplyError):
            patch_func()

        assert call_count == 1  # リトライせず即座に失敗

    def test_non_retryable_unexpected(self):
        """unexpected はリトライ禁止（3.3.4）"""
        from nexuscore.core.errors import UnexpectedSystemError

        call_count = 0

        @retry(max_retries=3, base_delay=0.1)
        def unexpected_func():
            nonlocal call_count
            call_count += 1
            raise UnexpectedSystemError("Unexpected error")

        with pytest.raises(UnexpectedSystemError):
            unexpected_func()

        assert call_count == 1  # リトライせず即座に失敗

    def test_retry_finiteness_guarantee(self):
        """リトライの有限性保証（3.3.2 SHALL要件）"""
        call_count = 0

        @retry(max_retries=2, base_delay=0.1)
        def always_fail():
            nonlocal call_count
            call_count += 1
            raise ModelRateLimitError("Always fail")

        with pytest.raises(ModelRateLimitError):
            always_fail()

        # max_retries=2 なので、初回 + 2回リトライ = 3回試行で終了
        assert call_count == 3
        # 無限ループに陥らないことを確認（有限回数で終了）

    def test_backoff_strategy_semantic_level(self):
        """Backoff 戦略は意味論レベル（3.3.3）"""
        call_times = []

        @retry(max_retries=2, base_delay=0.2)
        def backoff_test():
            call_times.append(time.time())
            raise ModelRateLimitError("Rate limit")

        with pytest.raises(ModelRateLimitError):
            backoff_test()

        # 増加型待機戦略: リトライ回数の増加に応じて待機時間が延長される
        assert len(call_times) == 3
        delay_1 = call_times[1] - call_times[0]
        delay_2 = call_times[2] - call_times[1]

        # 意味論レベル: delay_2 > delay_1（段階的に延長）
        assert delay_2 > delay_1, f"Backoff should increase: {delay_1:.3f}s -> {delay_2:.3f}s"

    def test_logger_none_safety(self):
        """logger が None でも落ちない（実装要件）"""
        call_count = 0

        @retry(max_retries=2, base_delay=0.1, logger_instance=None)
        def logger_test():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ModelTimeoutError("Timeout")
            return "success"

        # logger_instance=None でも動作する（内部でデフォルトロガーを使用）
        result = logger_test()
        assert result == "success"
        assert call_count == 2


# ==============================================================================
# Batch 0 Mini: Characterization Tests with Mock Sleep (Deterministic)
# ==============================================================================

class TestRetryCharacterizationDeterministic:
    """
    Characterization tests using mock_sleep fixture for deterministic testing.

    Purpose:
    - Record existing behavior (As-is)
    - No real time.sleep execution
    - Verify sleep call count and arguments
    - Subject to replacement in future refactoring

    Note: These tests document current behavior, not necessarily desired behavior.
    """

    @pytest.mark.characterization
    def test_ch_retry_01_initial_success_no_retry(self, mock_sleep):
        """
        CH-RETRY-01: 初回成功ならretryしない

        現状動作:
        - attempt=1 で成功
        - sleep呼び出し回数 = 0
        - context.retry_count = 0

        将来置換前提: retry メカニズムの変更時に更新する
        """
        call_count = 0
        context = RetryContext()

        def successful_func():
            nonlocal call_count
            call_count += 1
            return "success"

        wrapped = retry_with_context(
            successful_func,
            max_retries=2,
            base_delay=1.0,
            context=context
        )
        result = wrapped()

        # 検証: 初回成功
        assert result == "success"
        assert call_count == 1

        # 検証: sleep未呼び出し
        assert mock_sleep.call_count == 0

        # 検証: context記録
        assert context.retry_count == 0
        assert context.last_error_class is None

    @pytest.mark.characterization
    def test_ch_retry_02_one_failure_then_success(self, mock_sleep):
        """
        CH-RETRY-02: 1回失敗→次成功

        現状動作:
        - attempt=2 で成功（0回目失敗、1回目成功）
        - sleep呼び出し回数 = 1
        - sleep引数 = base_delay × 2^0 = 1.0
        - context.retry_count = 1

        将来置換前提: retry メカニズムの変更時に更新する
        """
        call_count = 0
        context = RetryContext()

        def flaky_func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ModelTimeoutError("Timeout on first attempt")
            return "success"

        wrapped = retry_with_context(
            flaky_func,
            max_retries=2,
            base_delay=1.0,
            context=context
        )
        result = wrapped()

        # 検証: 2回目で成功
        assert result == "success"
        assert call_count == 2

        # 検証: sleep呼び出し回数と引数
        assert mock_sleep.call_count == 1
        # sleep(1.0) が呼ばれる（attempt=0 なので delay=1.0×2^0=1.0）
        assert mock_sleep.call_args_list[0][0][0] == 1.0

        # 検証: context記録
        assert context.retry_count == 1
        assert context.last_error_class == "timeout"
        assert len(context.error_summary) == 1

    @pytest.mark.characterization
    def test_ch_retry_03_max_retries_reached_failure_not_suppressed(self, mock_sleep):
        """
        CH-RETRY-03: 上限到達で停止し、失敗が握りつぶされない

        現状動作:
        - max_retries=2 → 計3回試行（attempt=0,1,2）
        - sleep呼び出し回数 = 2（attempt=0,1 後）
        - sleep引数 = [1.0, 2.0]（指数バックオフ）
        - 最後の例外が re-raise される
        - context.retry_count = 2

        将来置換前提: retry メカニズムの変更時に更新する
        """
        call_count = 0
        context = RetryContext()

        def always_failing():
            nonlocal call_count
            call_count += 1
            raise ModelRateLimitError(f"Rate limit on attempt {call_count}")

        wrapped = retry_with_context(
            always_failing,
            max_retries=2,
            base_delay=1.0,
            context=context
        )

        # 検証: 例外が re-raise される
        with pytest.raises(ModelRateLimitError) as exc_info:
            wrapped()

        # 検証: 3回試行
        assert call_count == 3

        # 検証: sleep呼び出し回数と引数（指数バックオフ）
        assert mock_sleep.call_count == 2
        # sleep(1.0) が呼ばれる（attempt=0 なので delay=1.0×2^0=1.0）
        assert mock_sleep.call_args_list[0][0][0] == 1.0
        # sleep(2.0) が呼ばれる（attempt=1 なので delay=1.0×2^1=2.0）
        assert mock_sleep.call_args_list[1][0][0] == 2.0

        # 検証: context記録
        assert context.retry_count == 2
        assert context.last_error_class == "rate_limit"
        assert len(context.error_summary) == 3

        # 検証: 例外メッセージが保持されている
        assert "Rate limit" in str(exc_info.value)


# ==============================================================================
# Batch 0 Mini: Must Not Tests (Contract Enforcement)
# ==============================================================================

class TestRetryMustNotContracts:
    """
    Must Not tests enforcing critical invariants.

    Purpose:
    - Enforce MN-RETRY-01/02/03 invariants
    - Prevent catastrophic failures (infinite loops, resource exhaustion)
    - These are CONTRACT tests, not characterization tests
    """

    @pytest.mark.contract
    def test_mn_retry_01_classifier_exception_stops_retry(self, mock_sleep):
        """
        MN-RETRY-01: classifierが例外を投げたらリトライ継続してはならない

        契約:
        - classify_error() が例外を投げた場合、should_retry = False
        - sleep呼び出し = 0回
        - 追加attempt = 0回（初回のみ）
        - 元の例外が re-raise される

        根拠: retry_utils.py:139-148（classifier例外の捕捉と should_retry=False 設定）
        """
        from unittest.mock import patch, Mock

        call_count = 0
        classify_error_call_count = 0

        def flaky_func():
            nonlocal call_count
            call_count += 1
            raise ValueError("Test error")

        def broken_classifier(exc):
            """分類処理中に例外を投げる classifier"""
            nonlocal classify_error_call_count
            classify_error_call_count += 1
            raise RuntimeError("Classifier is broken")

        # classify_error をモックして例外を投げる
        with patch('nexuscore.core.retry_utils.classify_error', side_effect=broken_classifier):
            wrapped = retry_with_context(
                flaky_func,
                max_retries=3,  # 最大3回リトライ可能だが...
                base_delay=1.0
            )

            # 検証: 元の例外が re-raise される
            with pytest.raises(ValueError) as exc_info:
                wrapped()

        # 検証: 初回のみ試行（リトライなし）
        assert call_count == 1

        # 検証: sleep未呼び出し（リトライしていない）
        assert mock_sleep.call_count == 0

        # 検証: classify_error が1回だけ呼ばれた（リトライ判定時）
        assert classify_error_call_count == 1

        # 検証: 元の例外が保持されている
        assert "Test error" in str(exc_info.value)

    @pytest.mark.contract
    def test_mn_retry_02_max_retries_upper_bound_enforced(self, mock_sleep):
        """
        MN-RETRY-02: 最大試行上限を超えてattemptしてはならない

        契約:
        - max_retries=N → 最大 N+1 回試行
        - 無限ループに陥らない
        - 有限回数で終了する

        根拠: retry_utils.py:101（ループ回数制限）, retry_utils.py:155（停止条件）
        """
        call_count = 0

        def always_failing():
            nonlocal call_count
            call_count += 1
            raise ModelTimeoutError(f"Attempt {call_count}")

        wrapped = retry_with_context(
            always_failing,
            max_retries=5,  # 最大5回リトライ → 計6回試行
            base_delay=1.0
        )

        with pytest.raises(ModelTimeoutError):
            wrapped()

        # 検証: 6回試行で停止（max_retries=5 なので 5+1=6）
        assert call_count == 6

        # 検証: sleep呼び出し回数 = 5回（attempt=0,1,2,3,4 後）
        assert mock_sleep.call_count == 5

    @pytest.mark.contract
    def test_mn_retry_03_non_retryable_error_immediate_stop(self, mock_sleep):
        """
        MN-RETRY-03: non-retryable判定をリトライしてはならない

        契約:
        - classify_error() が "sandbox", "patch_apply", "unexpected" を返す場合
        - または retry_on に含まれない例外の場合
        - should_retry = False
        - sleep呼び出し = 0回
        - 即座に例外を re-raise

        根拠: retry_utils.py:120-121, 126-127, 137-138（should_retry=False設定）
        """
        call_count = 0

        # Case 1: SandboxExecutionError（non-retryable）
        def sandbox_fail():
            nonlocal call_count
            call_count += 1
            raise SandboxExecutionError("Sandbox failed")

        wrapped = retry_with_context(
            sandbox_fail,
            max_retries=3,
            base_delay=1.0
        )

        with pytest.raises(SandboxExecutionError):
            wrapped()

        # 検証: 初回のみ試行（リトライなし）
        assert call_count == 1

        # 検証: sleep未呼び出し
        assert mock_sleep.call_count == 0

        # Case 2: retry_on に含まれない一般的な例外（ValueError）
        mock_sleep.reset_mock()  # モックをリセット
        call_count = 0

        def value_error_fail():
            nonlocal call_count
            call_count += 1
            raise ValueError("Not retryable")

        wrapped2 = retry_with_context(
            value_error_fail,
            max_retries=3,
            base_delay=1.0,
            retry_on=(ModelTimeoutError,)  # ValueError は含まれない
        )

        with pytest.raises(ValueError):
            wrapped2()

        # 検証: 初回のみ試行（リトライなし）
        assert call_count == 1

        # 検証: sleep未呼び出し
        assert mock_sleep.call_count == 0
