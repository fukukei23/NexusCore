"""
ロギングプロバイダーインターフェース

Core層とWebapp層の依存関係を切り離すための抽象化層。
Core/NPE層はこのインターフェースのみに依存し、Webapp層の具体的な実装は
実行時に依存性注入される。これにより循環インポートを回避し、CLI実行時に
Webappが不要になる。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any


class LoggingProvider(ABC):
    """
    ロギング拡張のための抽象インターフェース

    Core層はこのインターフェースのみに依存し、具体的な実装
    （Webapp DBロガー等）は実行時に注入される。
    """

    @abstractmethod
    def enhance_transaction(self, log_data: dict[str, Any], log_file: Path) -> None:
        """
        ログトランザクションの拡張処理

        Args:
            log_data: ログデータ（dict形式）
            log_file: ログファイルパス
        """
        pass

    @abstractmethod
    def get_provider_name(self) -> str:
        """プロバイダー名を返す（デバッグ用）"""
        pass


class NoOpLoggingProvider(LoggingProvider):
    """
    何もしないロギングプロバイダー（CLI/テスト用のデフォルト）

    Webapp が利用できない環境（CLI実行、単体テスト等）では
    このプロバイダーが使用され、ファイルログのみが記録される。
    """

    def enhance_transaction(self, log_data: dict[str, Any], log_file: Path) -> None:
        # 何もしない（ファイルログのみで十分）
        pass

    def get_provider_name(self) -> str:
        return "NoOpProvider"


# グローバルプロバイダーレジストリ
_logging_provider: LoggingProvider | None = None


def register_logging_provider(provider: LoggingProvider) -> None:
    """
    ロギングプロバイダーを登録する

    Webappの初期化時に呼び出され、DB拡張ロガーを登録する。
    CLI実行時は呼び出されず、デフォルトのNoOpProviderが使用される。

    Args:
        provider: ロギングプロバイダーの実装

    Example:
        from nexuscore.webapp.logging_provider import WebappLoggingProvider
        from nexuscore.core.logging_interface import register_logging_provider

        # Webapp初期化時
        register_logging_provider(WebappLoggingProvider())
    """
    global _logging_provider
    _logging_provider = provider
    print(f"[LoggingProvider] Registered: {provider.get_provider_name()}")


def get_logging_provider() -> LoggingProvider:
    """
    現在のロギングプロバイダーを取得

    Returns:
        登録されたプロバイダー、または NoOpProvider（デフォルト）
    """
    global _logging_provider
    if _logging_provider is None:
        _logging_provider = NoOpLoggingProvider()
    return _logging_provider
