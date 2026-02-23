"""
Webapp用のロギングプロバイダー実装

Core層のlogging_interfaceを実装し、既存のDB拡張ロガーをラップする。
これにより、Core層がWebapp層に直接依存せずにDB logging機能を利用できる。
"""

from pathlib import Path
from typing import Any

from nexuscore.core.logging_interface import LoggingProvider


class WebappLoggingProvider(LoggingProvider):
    """
    WebappのDB拡張ロガーをラップするプロバイダー

    既存の db_logger.enhance_log_transaction() をアダプターとして
    利用し、Core層からの呼び出しを可能にする。
    """

    def enhance_transaction(self, log_data: dict[str, Any], log_file: Path) -> None:
        """
        既存のDB拡張ロガーを呼び出す

        Args:
            log_data: ログデータ
            log_file: ログファイルパス
        """
        # Webapp層の具体的な実装を呼び出す
        # （ここでのみWebapp層へのインポートが発生）
        from nexuscore.webapp.db_logger import enhance_log_transaction

        enhance_log_transaction(log_data, log_file)

    def get_provider_name(self) -> str:
        return "WebappDBProvider"
