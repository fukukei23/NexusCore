"""
NexusCore カスタム例外クラス

Self-Healing 実行中の LLM 呼び出し & sandbox 実行で発生する例外を分類し、
Retry 戦略を決定するために使用する。
"""

from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)


class NexusCoreError(Exception):
    """Base class for NexusCore-specific errors."""
    pass


class ModelRateLimitError(NexusCoreError):
    """LLM API のレートリミット（429）"""
    pass


class ModelTimeoutError(NexusCoreError):
    """LLM 応答タイムアウト"""
    pass


class ModelConnectionError(NexusCoreError):
    """ネットワーク系の一時的なエラー"""
    pass


class InvalidModelOutputError(NexusCoreError):
    """LLM 出力が期待する JSON/構造になっていない"""
    pass


class SandboxExecutionError(NexusCoreError):
    """テスト実行・コード実行系のエラー"""
    pass


class PatchApplyError(NexusCoreError):
    """patch_applier の適用失敗"""
    pass


class UnexpectedSystemError(NexusCoreError):
    """想定外の例外ラッパ"""
    pass


def classify_error(exc: Exception) -> str:
    """
    例外からエラー種別を分類する。

    Args:
        exc: 発生した例外

    Returns:
        エラー種別文字列:
        - 'rate_limit': レートリミット
        - 'timeout': タイムアウト
        - 'connection': ネットワーク接続エラー
        - 'invalid_output': LLM 出力が不正
        - 'sandbox': サンドボックス実行エラー
        - 'patch_apply': パッチ適用エラー
        - 'unexpected': 想定外のエラー
    """
    # NexusCore カスタム例外の場合は直接判定
    if isinstance(exc, ModelRateLimitError):
        return "rate_limit"
    if isinstance(exc, ModelTimeoutError):
        return "timeout"
    if isinstance(exc, ModelConnectionError):
        return "connection"
    if isinstance(exc, InvalidModelOutputError):
        return "invalid_output"
    if isinstance(exc, SandboxExecutionError):
        return "sandbox"
    if isinstance(exc, PatchApplyError):
        return "patch_apply"
    if isinstance(exc, NexusCoreError):
        return "unexpected"

    # HTTP エラーの判定
    error_str = str(exc).lower()
    error_type = type(exc).__name__.lower()

    # レートリミット（429）
    if "429" in error_str or "rate limit" in error_str or "ratelimit" in error_type:
        return "rate_limit"

    # タイムアウト
    if "timeout" in error_str or "timeout" in error_type or "timed out" in error_str:
        return "timeout"

    # 接続エラー
    if any(keyword in error_str for keyword in ["connection", "connect", "network", "dns", "resolve"]):
        return "connection"
    if any(keyword in error_type for keyword in ["Connection", "Connect", "Network"]):
        return "connection"

    # JSON パースエラー（LLM 出力が不正）
    # メッセージまたは型名にJSON/parseキーワードが含まれる場合
    has_json_in_message = any(keyword in error_str for keyword in ["json", "parse", "decode", "invalid format"])
    has_json_in_type = any(keyword in error_type for keyword in ["json", "parse", "decode"])
    if has_json_in_message or has_json_in_type:
        return "invalid_output"

    # サンドボックス関連
    if any(keyword in error_str for keyword in ["sandbox", "subprocess", "execution failed"]):
        return "sandbox"

    # パッチ適用関連
    if any(keyword in error_str for keyword in ["patch", "apply", "diff"]):
        return "patch_apply"

    # デフォルト: 想定外
    return "unexpected"


def convert_http_error_to_nexus_error(exc: Exception) -> NexusCoreError:
    """
    HTTP エラーや SDK エラーを NexusCore カスタム例外に変換する。

    Args:
        exc: 発生した例外

    Returns:
        NexusCore カスタム例外
    """
    error_class = classify_error(exc)
    error_str = str(exc)
    error_type = type(exc).__name__

    if error_class == "rate_limit":
        return ModelRateLimitError(f"Rate limit error: {error_str}")
    elif error_class == "timeout":
        return ModelTimeoutError(f"Timeout error: {error_str}")
    elif error_class == "connection":
        return ModelConnectionError(f"Connection error: {error_str}")
    elif error_class == "invalid_output":
        return InvalidModelOutputError(f"Invalid model output: {error_str}")
    elif error_class == "sandbox":
        return SandboxExecutionError(f"Sandbox execution error: {error_str}")
    elif error_class == "patch_apply":
        return PatchApplyError(f"Patch apply error: {error_str}")
    else:
        return UnexpectedSystemError(f"Unexpected error ({error_type}): {error_str}")
