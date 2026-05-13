from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path


class NexusCoreLogger:
    """標準ロガーファクトリー"""

    _configured = False
    _log_dir: Path | None = None

    @classmethod
    def get_logger(cls, name: str, audit: bool = False) -> logging.Logger:
        """
        標準ロガーを取得

        Args:
            name: モジュール名（常に __name__ を使用）
            audit: True の場合、監査ログも有効化

        Returns:
            設定済みの Logger インスタンス

        Usage:
            from nexuscore.logging_standard import get_logger
            logger = get_logger(__name__)
        """
        # 初回設定
        if not cls._configured:
            cls._setup_root_config()
            cls._configured = True

        # nexuscore. プレフィックスを付与
        logger = logging.getLogger(f"nexuscore.{name}")

        # 監査ログが必要な場合は追加ハンドラーを設定
        if audit and not cls._has_audit_handler(logger):
            cls._add_audit_handler(logger)

        return logger

    @classmethod
    def _setup_root_config(cls):
        """ルートロガーの初期設定"""
        root_logger = logging.getLogger("nexuscore")
        root_logger.setLevel(logging.INFO)
        root_logger.propagate = False  # 重複ログ防止

        # ログディレクトリの取得
        cls._log_dir = cls._get_logs_dir()
        cls._log_dir.mkdir(parents=True, exist_ok=True)

        # コンソールハンドラー
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(cls._get_formatter())
        root_logger.addHandler(console_handler)

        # ファイルハンドラー（ローテーション付き）
        file_handler = RotatingFileHandler(
            cls._log_dir / "nexuscore.log", maxBytes=10 * 1024 * 1024, backupCount=5  # 10MB
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(cls._get_formatter(verbose=True))
        root_logger.addHandler(file_handler)

    @staticmethod
    def _get_formatter(verbose: bool = False) -> logging.Formatter:
        """ログフォーマッターを取得"""
        if verbose:
            return logging.Formatter(
                "%(asctime)s [%(levelname)8s] %(name)s (%(filename)s:%(lineno)d) - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        else:
            return logging.Formatter(
                "%(asctime)s [%(levelname)s] %(name)s - %(message)s", datefmt="%H:%M:%S"
            )

    @staticmethod
    def _get_logs_dir() -> Path:
        """ログディレクトリのパスを取得"""
        # 環境変数で上書き可能
        import os

        log_dir_env = os.getenv("NEXUS_LOG_DIR")
        if log_dir_env:
            return Path(log_dir_env)

        # デフォルト: プロジェクトルート/logs
        project_root = Path(__file__).parent.parent
        return project_root / "logs"

    @staticmethod
    def _has_audit_handler(logger: logging.Logger) -> bool:
        """監査ハンドラーが既に追加されているかチェック"""
        return any(
            isinstance(h, logging.FileHandler) and "audit" in str(h.baseFilename)
            for h in logger.handlers
        )

    @classmethod
    def _add_audit_handler(cls, logger: logging.Logger):
        """監査ログ用の追加ハンドラーを設定"""
        audit_file = cls._log_dir / "audit.jsonl"  # type: ignore[operator]
        audit_handler = RotatingFileHandler(
            audit_file, maxBytes=50 * 1024 * 1024, backupCount=10  # 50MB
        )
        audit_handler.setLevel(logging.INFO)

        # JSON形式のフォーマッター（簡易版）
        audit_handler.setFormatter(
            logging.Formatter(
                '{"timestamp": "%(asctime)s", "level": "%(levelname)s", '
                '"module": "%(name)s", "message": "%(message)s"}',
                datefmt="%Y-%m-%dT%H:%M:%S",
            )
        )
        logger.addHandler(audit_handler)


# エイリアス（簡潔な利用のため）
get_logger = NexusCoreLogger.get_logger
