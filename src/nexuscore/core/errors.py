from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class NexusCoreError(Exception):
    """NexusCore 全例外の基底クラス。

    全てのカスタム例外はこのクラスを継承する。
    """

    pass


class ModelRateLimitError(NexusCoreError):
    """LLM API レートリミット（HTTP 429）。

    一時的エラー。Exponential backoff で最大5回リトライ。
    """

    pass


class ModelTimeoutError(NexusCoreError):
    """LLM 応答タイムアウト。

    一時的エラー。Linear backoff（10秒固定）で最大3回リトライ。
    """

    pass


class ModelConnectionError(NexusCoreError):
    """ネットワーク接続の一時的エラー。

    一時的エラー。Exponential backoff で最大3回リトライ。
    """

    pass


class InvalidModelOutputError(NexusCoreError):
    """LLM 出力が期待する JSON/構造になっていない。

    一時的エラー。Linear backoff（5秒固定）で最大3回リトライ。
    """

    pass


class SandboxExecutionError(NexusCoreError):
    """テスト実行・コード実行系のエラー。

    非リトライ可能。即座に abort。
    """

    pass


class SandboxSecurityError(NexusCoreError):
    """サンドボックスセキュリティ違反。

    禁止モジュールの利用など。非リトライ可能。即座に abort。
    """

    pass


class PatchApplyError(NexusCoreError):
    """パッチ適用失敗。

    非リトライ可能。即座に abort。
    """

    pass


class UnexpectedSystemError(NexusCoreError):
    """想定外の例外ラッパ。

    非リトライ可能。即座に abort。
    """

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

    分類不能エラー時のフォールバック（3.4.2）:
        - 分類処理中の例外は捕捉し、'unexpected' を返す
        - すべての入力に対して少なくとも 'unexpected' を返すことを保証
    """
    # Step 1: 入力検証（3.4.3）
    if exc is None:
        logger.warning(
            "classify_error received None. Treating as unclassifiable error.", exc_info=False
        )
        return "unexpected"

    try:
        # Phase 1: NexusCore カスタム例外の場合は直接判定
        if isinstance(exc, ModelRateLimitError):
            result = "rate_limit"
        elif isinstance(exc, ModelTimeoutError):
            result = "timeout"
        elif isinstance(exc, ModelConnectionError):
            result = "connection"
        elif isinstance(exc, InvalidModelOutputError):
            result = "invalid_output"
        elif isinstance(exc, SandboxExecutionError):
            result = "sandbox"
        elif isinstance(exc, PatchApplyError):
            result = "patch_apply"
        elif isinstance(exc, NexusCoreError):
            result = "unexpected"
        else:
            # Phase 2: メッセージと型名からの推論
            try:
                error_str = str(exc).lower()
                error_type = type(exc).__name__.lower()
            except Exception as e:  # noqa: BLE001 — error object stringification can fail in unexpected ways
                # エラーオブジェクトの文字列化に失敗した場合
                logger.warning(
                    f"Failed to stringify error object (type: {type(exc).__name__}). "
                    f"Reason: {e}. Treating as unclassifiable error.",
                    exc_info=False,
                )
                return "unexpected"

            # レートリミット（429）
            if "429" in error_str or "rate limit" in error_str or "ratelimit" in error_type:
                result = "rate_limit"
            # タイムアウト
            elif "timeout" in error_str or "timeout" in error_type or "timed out" in error_str:
                result = "timeout"
            # 接続エラー
            elif any(
                keyword in error_str
                for keyword in ["connection", "connect", "network", "dns", "resolve"]
            ):
                result = "connection"
            elif any(keyword in error_type for keyword in ["connection", "connect", "network"]):
                result = "connection"
            # JSON パースエラー（LLM 出力が不正）
            # メッセージまたは型名にJSON/parseキーワードが含まれる場合（OR論理）
            elif any(
                keyword in error_str for keyword in ["json", "parse", "decode", "invalid format"]
            ) or any(keyword in error_type for keyword in ["json", "parse", "decode"]):
                result = "invalid_output"
            # サンドボックス関連
            elif any(
                keyword in error_str for keyword in ["sandbox", "subprocess", "execution failed"]
            ):
                result = "sandbox"
            # パッチ適用関連
            elif any(keyword in error_str for keyword in ["patch", "apply", "diff"]):
                result = "patch_apply"
            # デフォルト: 想定外
            else:
                result = "unexpected"

        # Step 2: 分類結果をログに記録（5.3 AU-1）
        logger.info(f"Error classified as '{result}': {type(exc).__name__} - {str(exc)[:200]}")

        # 分類結果が定義済みカテゴリに含まれているか検証（3.4.1）
        valid_categories = {
            "rate_limit",
            "timeout",
            "connection",
            "invalid_output",
            "sandbox",
            "patch_apply",
            "unexpected",
        }
        if result not in valid_categories:
            # Step 2: 分類不能エラーのログ記録（3.4.2 Step 2）
            logger.warning(
                f"classify_error returned invalid category '{result}'. "
                f"Original error: {type(exc).__name__} - {str(exc)[:200]}. "
                f"Falling back to 'unexpected'."
            )
            result = "unexpected"

        return result

    except Exception as classification_error:  # noqa: BLE001 — classification error fallback (3.4.3)
        # Step 2: 分類処理中の例外を捕捉（3.4.3）
        logger.warning(
            f"Exception occurred during error classification. "
            f"Original error: {type(exc).__name__} - {str(exc)[:200]}. "
            f"Classification error: {type(classification_error).__name__} - {str(classification_error)}. "
            f"Treating as unclassifiable error.",
            exc_info=True,
        )
        # Step 1: 安全な分類結果の返却（3.4.2 Step 1）
        return "unexpected"


def convert_http_error_to_nexus_error(exc: Exception) -> NexusCoreError:
    """
    HTTP エラーや SDK エラーを NexusCore カスタム例外に変換する。

    Args:
        exc: 発生した例外

    Returns:
        NexusCore カスタム例外

    分類不能エラー時のフォールバック（3.4.2）:
        - 分類不能エラーは UnexpectedSystemError として変換
        - 元のエラー情報を保持
    """
    try:
        error_class = classify_error(exc)
        try:
            error_str = str(exc) if exc is not None else "None"
        except Exception:  # noqa: BLE001 — エラーオブジェクトの文字列化に失敗した場合
            error_str = f"<unstringifiable {type(exc).__name__ if exc is not None else 'None'}>"
        try:
            error_type = type(exc).__name__ if exc is not None else "NoneType"
        except Exception:  # noqa: BLE001 — type().__name__への安全なアクセス
            error_type = "Unknown"

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
            # Step 3: 上位へのエラー伝播（3.4.2 Step 3）
            # unexpected 系の標準エラーとして上位レイヤーへ伝播
            return UnexpectedSystemError(f"Unexpected error ({error_type}): {error_str}")
    except Exception as conversion_error:  # noqa: BLE001 — 変換処理中の例外を捕捉（3.4.3）
        # 変換処理中の例外を捕捉（3.4.3）
        logger.warning(
            f"Exception occurred during error conversion. "
            f"Original error: {type(exc).__name__ if exc is not None else 'None'}. "
            f"Conversion error: {type(conversion_error).__name__} - {str(conversion_error)}. "
            f"Falling back to UnexpectedSystemError.",
            exc_info=True,
        )
        # Step 3: 安全な例外として伝播（3.4.2 Step 3）
        try:
            error_str = str(exc) if exc is not None else "None"
        except Exception:  # noqa: BLE001 — エラーオブジェクトの文字列化に失敗した場合
            error_str = f"<unstringifiable {type(exc).__name__ if exc is not None else 'None'}>"
        try:
            error_type = type(exc).__name__ if exc is not None else "NoneType"
        except Exception:  # noqa: BLE001 — type().__name__への安全なアクセス
            error_type = "Unknown"
        return UnexpectedSystemError(f"Unclassifiable error ({error_type}): {error_str}")
