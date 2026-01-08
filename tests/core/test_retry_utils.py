"""
Tests for retry utilities with exponential backoff

指数バックオフリトライロジックの信頼性を保証するテスト群
"""
import pytest
import time
from unittest.mock import Mock, patch
import nexuscore.core.retry_utils as retry_utils_module
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


@pytest.fixture(autouse=True)
def _no_real_sleep(monkeypatch):
    """
    テストが実時間に依存しないように、retry_utils 内の time.sleep を常に無効化する。

    - テスト品質ルール（time.sleep 禁止）遵守
    - CI でのフレーク（タイミング依存）抑制
    """
    monkeypatch.setattr(retry_utils_module.time, "sleep", lambda _: None)


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
        """指数バックオフの遅延（sleep呼び出し）が正しいことを確認"""
        with patch.object(retry_utils_module.time, "sleep") as sleep_mock:
            @retry(max_retries=2, base_delay=0.2)
            def timed_function():
                raise ModelTimeoutError("Timeout")

            with pytest.raises(ModelTimeoutError):
                timed_function()

            # max_retries=2 なので sleep は 2 回（0.2, 0.4）
            delays = [c.args[0] for c in sleep_mock.call_args_list]
            assert delays == [pytest.approx(0.2), pytest.approx(0.4)]

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
        """非常に短い遅延でも、sleep呼び出しが正しいことを確認"""
        call_count = 0

        with patch.object(retry_utils_module.time, "sleep") as sleep_mock:
            @retry(max_retries=2, base_delay=0.01)
            def fast_retry():
                nonlocal call_count
                call_count += 1
                if call_count < 3:
                    raise ModelTimeoutError("Timeout")
                return "success"

            result = fast_retry()

            assert result == "success"
            assert call_count == 3
            delays = [c.args[0] for c in sleep_mock.call_args_list]
            assert delays == [pytest.approx(0.01), pytest.approx(0.02)]

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
        """Backoff 戦略は意味論レベル（3.3.3）: sleep が段階的に増える"""
        with patch.object(retry_utils_module.time, "sleep") as sleep_mock:
            @retry(max_retries=2, base_delay=0.2)
            def backoff_test():
                raise ModelRateLimitError("Rate limit")

            with pytest.raises(ModelRateLimitError):
                backoff_test()

            delays = [c.args[0] for c in sleep_mock.call_args_list]
            assert len(delays) == 2
            assert delays[1] > delays[0]


class TestClassificationFailureFallback:
    """分類処理が壊れてもリトライが暴走しないことを固定するテスト"""

    def test_classify_error_raises_treated_as_non_retryable(self, monkeypatch):
        """classify_error が例外を投げても、非リトライ扱いで即座に失敗する"""
        def _broken_classify_error(_exc):  # noqa: ANN001 - テスト用
            raise RuntimeError("classification boom")

        monkeypatch.setattr(retry_utils_module, "classify_error", _broken_classify_error)

        def always_timeout():
            raise ModelTimeoutError("Timeout")

        wrapped = retry_with_context(
            always_timeout,
            max_retries=2,
            base_delay=0.2,
            retry_on=(),  # isinstance(e, retry_on) を必ず False にする
            context=None,  # 失敗時ログ用 classify_error 呼び出しを避ける
        )

        with patch.object(retry_utils_module.time, "sleep") as sleep_mock:
            with pytest.raises(ModelTimeoutError):
                wrapped()
            assert sleep_mock.call_count == 0

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
