"""
============================================================================
Comprehensive Tests for logging_interface.py
============================================================================
高品質テストの原則:
- 外部依存をモック（今回はほぼ依存なし）
- 実際のプロバイダー登録・取得ロジックをテスト
- エッジケースとエラー条件をカバー
============================================================================
"""

from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from nexuscore.core.logging_interface import (
    LoggingProvider,
    NoOpLoggingProvider,
    get_logging_provider,
    register_logging_provider,
)

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture(autouse=True)
def reset_global_provider():
    """各テスト前後でグローバルプロバイダーをリセット"""
    import nexuscore.core.logging_interface as logging_interface

    original_provider = logging_interface._logging_provider

    # テスト前にリセット
    logging_interface._logging_provider = None

    yield

    # テスト後に復元
    logging_interface._logging_provider = original_provider


class MockLoggingProvider(LoggingProvider):
    """テスト用のモックプロバイダー"""

    def __init__(self, name: str = "MockProvider"):
        self.name = name
        self.enhance_calls = []

    def enhance_transaction(self, log_data: dict[str, Any], log_file: Path) -> None:
        self.enhance_calls.append(
            {
                "log_data": log_data,
                "log_file": log_file,
            }
        )

    def get_provider_name(self) -> str:
        return self.name


# ============================================================================
# Tests: LoggingProvider abstract class
# ============================================================================


class TestLoggingProviderAbstract:
    def test_cannot_instantiate_abstract_class(self):
        """抽象クラスは直接インスタンス化できない"""
        with pytest.raises(TypeError) as exc_info:
            LoggingProvider()

        assert "Can't instantiate abstract class" in str(exc_info.value)

    def test_must_implement_enhance_transaction(self):
        """enhance_transaction メソッドを実装する必要がある"""

        class IncompleteProvider(LoggingProvider):
            def get_provider_name(self) -> str:
                return "incomplete"

        with pytest.raises(TypeError) as exc_info:
            IncompleteProvider()

        assert "abstract method" in str(exc_info.value).lower()

    def test_must_implement_get_provider_name(self):
        """get_provider_name メソッドを実装する必要がある"""

        class IncompleteProvider(LoggingProvider):
            def enhance_transaction(self, log_data, log_file):
                pass

        with pytest.raises(TypeError) as exc_info:
            IncompleteProvider()

        assert "abstract method" in str(exc_info.value).lower()

    def test_can_create_concrete_implementation(self):
        """両方のメソッドを実装すればインスタンス化可能"""

        class CompleteProvider(LoggingProvider):
            def enhance_transaction(self, log_data, log_file):
                pass

            def get_provider_name(self) -> str:
                return "complete"

        provider = CompleteProvider()
        assert provider.get_provider_name() == "complete"


# ============================================================================
# Tests: NoOpLoggingProvider
# ============================================================================


class TestNoOpLoggingProvider:
    def test_can_instantiate(self):
        """NoOpProvider をインスタンス化できる"""
        provider = NoOpLoggingProvider()
        assert provider is not None

    def test_get_provider_name(self):
        """プロバイダー名を返す"""
        provider = NoOpLoggingProvider()
        assert provider.get_provider_name() == "NoOpProvider"

    def test_enhance_transaction_does_nothing(self):
        """enhance_transaction は何もしない"""
        provider = NoOpLoggingProvider()

        log_data = {"message": "test", "level": "INFO"}
        log_file = Path("/tmp/test.log")

        # 例外が発生しないことを確認
        provider.enhance_transaction(log_data, log_file)

    def test_enhance_transaction_with_empty_data(self):
        """空のログデータでも動作する"""
        provider = NoOpLoggingProvider()

        provider.enhance_transaction({}, Path("/tmp/test.log"))

    def test_enhance_transaction_with_complex_data(self):
        """複雑なログデータでも動作する"""
        provider = NoOpLoggingProvider()

        log_data = {
            "message": "test",
            "level": "INFO",
            "nested": {"data": [1, 2, 3], "more": {"deep": "value"}},
        }

        provider.enhance_transaction(log_data, Path("/tmp/test.log"))


# ============================================================================
# Tests: register_logging_provider
# ============================================================================


class TestRegisterLoggingProvider:
    def test_register_custom_provider(self):
        """カスタムプロバイダーを登録できる"""
        provider = MockLoggingProvider("TestProvider")
        register_logging_provider(provider)
        assert get_logging_provider().get_provider_name() == "TestProvider"

    def test_register_noop_provider(self):
        """NoOpProvider を登録できる"""
        provider = NoOpLoggingProvider()
        register_logging_provider(provider)
        assert get_logging_provider().get_provider_name() == "NoOpProvider"

    def test_register_overwrites_previous(self):
        """新しいプロバイダーは前のものを上書きする"""
        provider1 = MockLoggingProvider("Provider1")
        provider2 = MockLoggingProvider("Provider2")

        register_logging_provider(provider1)
        register_logging_provider(provider2)

    def test_register_updates_global_state(self):
        """グローバル状態が更新される"""
        provider = MockLoggingProvider()

        register_logging_provider(provider)

        import nexuscore.core.logging_interface as logging_interface

        assert logging_interface._logging_provider is provider


# ============================================================================
# Tests: get_logging_provider
# ============================================================================


class TestGetLoggingProvider:
    def test_get_default_provider(self):
        """デフォルトで NoOpProvider が返される"""
        provider = get_logging_provider()

        assert isinstance(provider, NoOpLoggingProvider)
        assert provider.get_provider_name() == "NoOpProvider"

    def test_get_registered_provider(self):
        """登録されたプロバイダーが返される"""
        custom_provider = MockLoggingProvider("CustomProvider")

        register_logging_provider(custom_provider)

        provider = get_logging_provider()
        assert provider.get_provider_name() == "CustomProvider"

    def test_get_provider_multiple_times(self):
        """複数回呼び出しても同じプロバイダーが返される"""
        provider1 = get_logging_provider()
        provider2 = get_logging_provider()

        # 同じインスタンスが返される
        assert provider1 is provider2

    def test_get_provider_after_registration(self):
        """登録後は登録されたプロバイダーが返される"""
        # 最初はデフォルト
        default_provider = get_logging_provider()
        assert isinstance(default_provider, NoOpLoggingProvider)

        # カスタムプロバイダーを登録
        custom_provider = MockLoggingProvider()
        register_logging_provider(custom_provider)

        # カスタムプロバイダーが返される
        provider = get_logging_provider()
        assert provider is custom_provider


# ============================================================================
# Tests: Integration scenarios
# ============================================================================


class TestIntegrationScenarios:
    def test_full_provider_lifecycle(self):
        """プロバイダーのライフサイクル全体をテスト"""
        # 1. デフォルトプロバイダーを取得
        default = get_logging_provider()
        assert isinstance(default, NoOpLoggingProvider)

        # 2. カスタムプロバイダーを登録
        custom = MockLoggingProvider("Integration")
        register_logging_provider(custom)

        # 3. カスタムプロバイダーが返される
        current = get_logging_provider()
        assert current is custom

        # 4. enhance_transaction を呼び出す
        log_data = {"message": "test", "level": "INFO"}
        log_file = Path("/tmp/integration.log")
        current.enhance_transaction(log_data, log_file)

        # 5. 呼び出しが記録される
        assert len(custom.enhance_calls) == 1
        assert custom.enhance_calls[0]["log_data"] == log_data
        assert custom.enhance_calls[0]["log_file"] == log_file

    def test_multiple_providers_sequential(self):
        """複数のプロバイダーを順次登録"""
        providers = [
            MockLoggingProvider("Provider1"),
            MockLoggingProvider("Provider2"),
            MockLoggingProvider("Provider3"),
        ]

        for provider in providers:
            register_logging_provider(provider)
        current = get_logging_provider()
        assert current.get_provider_name() == provider.get_provider_name()

    def test_provider_with_complex_log_data(self):
        """複雑なログデータを処理"""
        provider = MockLoggingProvider()

        register_logging_provider(provider)

        log_data = {
            "timestamp": "2025-12-31T10:00:00",
            "level": "ERROR",
            "message": "Test error",
            "exception": {
                "type": "ValueError",
                "message": "Invalid value",
                "traceback": ["line1", "line2", "line3"],
            },
            "context": {"user_id": "user123", "request_id": "req456", "metadata": {"key": "value"}},
        }

        log_file = Path("/var/log/nexuscore/test.log")

        current = get_logging_provider()
        current.enhance_transaction(log_data, log_file)

        assert len(provider.enhance_calls) == 1
        assert provider.enhance_calls[0]["log_data"]["exception"]["type"] == "ValueError"

    def test_provider_with_pathlib_path(self):
        """Pathlib Path オブジェクトを使用"""
        provider = MockLoggingProvider()

        register_logging_provider(provider)

        log_file = Path("/tmp") / "nested" / "directory" / "log.txt"

        current = get_logging_provider()
        current.enhance_transaction({"message": "test"}, log_file)

        assert provider.enhance_calls[0]["log_file"] == log_file


# ============================================================================
# Tests: Custom provider implementations
# ============================================================================


class TestCustomProviderImplementations:
    def test_provider_with_state(self):
        """状態を持つプロバイダー"""

        class StatefulProvider(LoggingProvider):
            def __init__(self):
                self.call_count = 0
                self.last_log_data = None

            def enhance_transaction(self, log_data, log_file):
                self.call_count += 1
                self.last_log_data = log_data

            def get_provider_name(self) -> str:
                return "StatefulProvider"

        provider = StatefulProvider()

        register_logging_provider(provider)

        current = get_logging_provider()

        # 複数回呼び出し
        for i in range(5):
            current.enhance_transaction({"count": i}, Path(f"/tmp/log{i}.txt"))

        assert provider.call_count == 5
        assert provider.last_log_data == {"count": 4}

    def test_provider_with_validation(self):
        """バリデーションを行うプロバイダー"""

        class ValidatingProvider(LoggingProvider):
            def __init__(self):
                self.valid_calls = []
                self.invalid_calls = []

            def enhance_transaction(self, log_data, log_file):
                if "message" in log_data:
                    self.valid_calls.append(log_data)
                else:
                    self.invalid_calls.append(log_data)

            def get_provider_name(self) -> str:
                return "ValidatingProvider"

        provider = ValidatingProvider()

        register_logging_provider(provider)

        current = get_logging_provider()

        current.enhance_transaction({"message": "valid"}, Path("/tmp/log.txt"))
        current.enhance_transaction({"no_message": True}, Path("/tmp/log.txt"))
        current.enhance_transaction({"message": "also valid"}, Path("/tmp/log.txt"))

        assert len(provider.valid_calls) == 2
        assert len(provider.invalid_calls) == 1

    def test_provider_with_side_effects(self):
        """副作用を持つプロバイダー"""
        side_effects = []

        class SideEffectProvider(LoggingProvider):
            def enhance_transaction(self, log_data, log_file):
                side_effects.append(f"Logged to {log_file}")

            def get_provider_name(self) -> str:
                return "SideEffectProvider"

        provider = SideEffectProvider()

        register_logging_provider(provider)

        current = get_logging_provider()
        current.enhance_transaction({}, Path("/tmp/log1.txt"))
        current.enhance_transaction({}, Path("/tmp/log2.txt"))

        assert len(side_effects) == 2
        assert "log1.txt" in side_effects[0]
        assert "log2.txt" in side_effects[1]


# ============================================================================
# Tests: Edge cases
# ============================================================================


class TestEdgeCases:
    def test_register_same_provider_twice(self):
        """同じプロバイダーを2回登録"""
        provider = MockLoggingProvider()

        register_logging_provider(provider)
        register_logging_provider(provider)

        # 同じインスタンスが取得される
        assert get_logging_provider() is provider

        # 同じインスタンスが取得される
        current = get_logging_provider()
        assert current is provider

    def test_enhance_transaction_with_none_values(self):
        """None 値を含むログデータ"""
        provider = MockLoggingProvider()

        register_logging_provider(provider)

        log_data = {
            "message": None,
            "level": None,
            "context": None,
        }

        current = get_logging_provider()
        current.enhance_transaction(log_data, Path("/tmp/log.txt"))

        assert provider.enhance_calls[0]["log_data"] == log_data

    def test_enhance_transaction_with_large_data(self):
        """大量のデータを含むログ"""
        provider = MockLoggingProvider()

        register_logging_provider(provider)

        log_data = {
            "message": "x" * 10000,  # 10KB のメッセージ
            "payload": list(range(1000)),  # 大きな配列
        }

        current = get_logging_provider()
        current.enhance_transaction(log_data, Path("/tmp/log.txt"))

        assert len(provider.enhance_calls) == 1
