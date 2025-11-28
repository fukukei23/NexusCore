"""
ログ設定の共通ユーティリティ

すべてのログファイルを logs/ ディレクトリに統一して出力する。
"""

from __future__ import annotations

import logging
import os
from pathlib import Path


def get_logs_dir() -> Path:
    """
    ログディレクトリのパスを取得する。

    Returns:
        logs/ ディレクトリの Path オブジェクト（存在しない場合は作成）
    """
    project_root = Path(__file__).resolve().parent.parent.parent.parent
    logs_dir = project_root / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    return logs_dir


def setup_file_logging(
    log_filename: str,
    log_level: int = logging.INFO,
    format_string: str | None = None,
    logger_name: str | None = None,
) -> logging.Logger:
    """
    ファイルロギングを設定する。

    Args:
        log_filename: ログファイル名（例: "nexus_core_run.log"）
        log_level: ログレベル（デフォルト: logging.INFO）
        format_string: ログフォーマット文字列（デフォルト: 標準フォーマット）
        logger_name: ロガー名（デフォルト: None = root logger）

    Returns:
        設定された Logger インスタンス
    """
    logs_dir = get_logs_dir()
    log_path = logs_dir / log_filename

    if format_string is None:
        format_string = "%(asctime)s - %(levelname)-8s - %(name)-20s - %(message)s"

    logger = logging.getLogger(logger_name)
    logger.setLevel(log_level)

    # 既存の FileHandler を削除（重複防止）
    for handler in logger.handlers[:]:
        if isinstance(handler, logging.FileHandler):
            logger.removeHandler(handler)

    # FileHandler を追加
    file_handler = logging.FileHandler(log_path, mode='a', encoding='utf-8')
    file_handler.setLevel(log_level)
    file_handler.setFormatter(logging.Formatter(format_string))
    logger.addHandler(file_handler)

    return logger

