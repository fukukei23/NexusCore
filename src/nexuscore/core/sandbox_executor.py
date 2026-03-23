"""
NexusCore SaaS基盤 - サンドボックス実行の安定化

既存のサンドボックス実行モジュールを統合し、
タイムアウト制御、リトライ戦略、例外分類を追加。

既存の Orchestrator / NPE / Agents とは独立して動作する。
"""

from __future__ import annotations

import enum
import logging
import os
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    import resource
except ImportError:
    resource = None  # type: ignore

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore

logger = logging.getLogger(__name__)

# リソース制限の定数
_MEMORY_LIMIT_MB = 512
_CPU_TIME_LIMIT_SEC = 30

# 危険モジュールのブロックリスト
_FORBIDDEN_MODULE_NAMES = {"os", "subprocess", "shutil", "socket", "pathlib"}


def _apply_resource_limits() -> None:
    """
    サンドボックス実行時のリソース制限を適用する。

    Linux / POSIX 環境でのみ resource.setrlimit を使用して、
    メモリ上限とCPU時間上限を設定する。

    非POSIX環境やresourceモジュールが使用できない場合は、
    例外を投げずに静かに何もしない（サーバー全体が落ちないことを優先）。
    """
    if os.name != "posix":
        return

    if resource is None:
        logger.debug("resource module is not available. Skipping resource limits.")
        return

    try:
        # メモリ上限（仮想メモリ）: 512MB
        memory_limit_bytes = _MEMORY_LIMIT_MB * 1024 * 1024
        resource.setrlimit(resource.RLIMIT_AS, (memory_limit_bytes, memory_limit_bytes))

        # CPU時間上限: 30秒
        resource.setrlimit(resource.RLIMIT_CPU, (_CPU_TIME_LIMIT_SEC, _CPU_TIME_LIMIT_SEC))

        logger.debug(
            f"Applied resource limits: memory={_MEMORY_LIMIT_MB}MB, cpu_time={_CPU_TIME_LIMIT_SEC}s"
        )
    except (OSError, ValueError) as e:
        # リソース制限の設定に失敗しても、実行を続行する
        logger.warning(f"Failed to apply resource limits: {e}")


def _check_forbidden_modules(code: str) -> None:
    """
    コード文字列内に危険なモジュールのインポートが含まれていないか検査する。

    Args:
        code: 検査対象のコード文字列

    Raises:
        SandboxSecurityError: 禁止モジュールが検出された場合
    """
    from nexuscore.core.errors import SandboxSecurityError

    code_lower = code.lower()
    detected_modules = []

    for module_name in _FORBIDDEN_MODULE_NAMES:
        # import os, from os import, import os as などのパターンを検出
        patterns = [
            f"import {module_name}",
            f"from {module_name} import",
            f"import {module_name} as",
        ]
        for pattern in patterns:
            if pattern in code_lower:
                detected_modules.append(module_name)
                break

    if detected_modules:
        module_list = ", ".join(sorted(set(detected_modules)))
        logger.warning(f"Forbidden module usage detected: {module_list}")
        raise SandboxSecurityError(f"Forbidden module(s) detected in code: {module_list}")


def load_sandbox_policy(policy_path: str | None = None) -> dict[str, Any]:
    """
    sandbox_policy.yml を読み込んで辞書として返す。

    見つからない場合は安全側のデフォルトを返す。

    Args:
        policy_path: ポリシーファイルのパス（Noneの場合は環境変数またはデフォルト）

    Returns:
        ポリシー辞書
    """
    default: dict[str, Any] = {
        "resource_limits": {
            "cpu_time_seconds": 30,
            "wall_time_seconds": 60,
            "memory_mb": 1024,
            "disk_write_mb": 100,
        },
        "retry_policy": {
            "max_retries": 1,
            "retryable_errors": ["TimeoutError", "TransientSandboxError"],
        },
        "network": {
            "enabled": False,
            "allowlist": [],
            "denylist": [],
        },
        "filesystem": {
            "allowed_paths": ["/tmp/nexuscore_sandbox"],
            "read_only_paths": ["/usr/lib"],
            "forbidden_paths": ["/", "/etc", "/var", "/home"],
        },
        "python_runtime": {
            "forbidden_modules": ["os", "subprocess", "socket", "shutil"],
            "allowed_modules_extra": [],
        },
        "logging": {
            "level": "INFO",
            "redact_env_vars": ["OPENAI_API_KEY", "GITHUB_TOKEN"],
        },
    }

    if yaml is None:
        logger.warning("PyYAML is not installed. Using default sandbox policy.")
        return default

    path = (
        policy_path
        or os.getenv("NEXUSCORE_SANDBOX_POLICY", "sandbox_policy.yml")
        or "sandbox_policy.yml"
    )
    policy_file = Path(path)

    if not policy_file.exists():
        logger.debug(f"Sandbox policy file not found: {policy_file}. Using defaults.")
        return default

    try:
        with policy_file.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        # default に対して shallow merge する程度でよい
        if isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, dict) and key in default:
                    default[key].update(value)
                else:
                    default[key] = value
        return default
    except Exception as e:
        logger.warning(f"Failed to load sandbox policy from {policy_file}: {e}. Using defaults.")
        return default


class SandboxExceptionType(enum.Enum):
    """
    サンドボックス実行時の例外種別
    """

    RATE_LIMIT = "rate_limit"  # レート制限エラー
    TIMEOUT = "timeout"  # タイムアウト
    INVALID_OUTPUT = "invalid_output"  # 無効な出力
    EXECUTION_ERROR = "execution_error"  # 実行エラー（コンパイルエラー、テスト失敗など）
    NETWORK_ERROR = "network_error"  # 一時的なネットワークエラー


@dataclass
class SandboxResult:
    """
    サンドボックス実行結果
    """

    stdout: str
    stderr: str
    returncode: int
    timed_out: bool = False
    exception_type: SandboxExceptionType | None = None
    execution_time_sec: float = 0.0


class SandboxExecutor:
    """
    サンドボックス実行エグゼキューター

    タイムアウト制御、リトライ戦略、例外分類を提供。
    """

    def __init__(
        self,
        default_timeout_sec: int = 300,
        max_retries: int = 3,
        retry_delay_sec: float = 1.0,
        policy: dict[str, Any] | None = None,
    ):
        """
        Args:
            default_timeout_sec: デフォルトのタイムアウト（秒）
            max_retries: 最大リトライ回数
            retry_delay_sec: リトライ間隔（秒、指数バックオフの初期値）
            policy: サンドボックスポリシー（Noneの場合は sandbox_policy.yml から読み込む）
        """
        self.policy = policy or load_sandbox_policy()

        # ポリシーから値を取得（フォールバック付き）
        resource_limits = self.policy.get("resource_limits", {})
        retry_policy = self.policy.get("retry_policy", {})

        self.default_timeout_sec = resource_limits.get("wall_time_seconds", default_timeout_sec)
        self.max_retries = retry_policy.get("max_retries", max_retries)
        self.retry_delay_sec = retry_delay_sec

        # TODO: ファイルシステム制限や import 制限など、重い実装は将来の拡張ポイント
        # 現時点ではタイムアウト・リトライ・ログ出力のみ適用

    def run_in_sandbox(
        self,
        cmd: list[str],
        timeout_sec: int | None = None,
        cwd: str | Path | None = None,
        env: dict | None = None,
        retry_on_errors: bool = True,
    ) -> SandboxResult:
        """
        サンドボックスでコマンドを実行。

        Args:
            cmd: 実行コマンド（リスト形式）
            timeout_sec: タイムアウト（秒、Noneの場合はデフォルト値を使用）
            cwd: 作業ディレクトリ
            env: 環境変数
            retry_on_errors: エラー時にリトライするか（ロジック系の失敗はFalseに）

        Returns:
            SandboxResult

        Note:
            現在の実装はコマンド実行（subprocess.run）のため、
            Pythonコード文字列を直接受け取る構造ではない。
            危険モジュールの検出は、将来Pythonコード文字列を直接実行する機能が追加された場合に実装する。
            現時点では、リソース制限（メモリ・CPU時間）のみが適用される。
        """
        timeout = timeout_sec or self.default_timeout_sec
        last_exception: Exception | None = None

        for attempt in range(self.max_retries + 1):
            try:
                result = self._execute_once(cmd, timeout, cwd, env)
                return result

            except subprocess.TimeoutExpired as e:
                last_exception = e
                exception_type = SandboxExceptionType.TIMEOUT
                # サンドボックスログ（タイムアウト）
                self._log_sandbox_error(
                    None, exception_type, "Sandbox timed out", {"cmd": cmd, "timeout": timeout}
                )
                if not retry_on_errors or attempt >= self.max_retries:
                    return SandboxResult(
                        stdout="",
                        stderr=f"Timeout after {timeout} seconds",
                        returncode=-1,
                        timed_out=True,
                        exception_type=exception_type,
                    )
                # タイムアウトはリトライしない（時間がかかりすぎている）
                return SandboxResult(
                    stdout="",
                    stderr=f"Timeout after {timeout} seconds",
                    returncode=-1,
                    timed_out=True,
                    exception_type=exception_type,
                )

            except Exception as e:
                last_exception = e
                exception_type = self._classify_exception(e)

                # セキュリティエラーの場合は特別に処理
                from nexuscore.core.errors import SandboxSecurityError

                if isinstance(e, SandboxSecurityError):
                    # セキュリティエラーはリトライしない
                    self._log_sandbox_error(
                        None,
                        SandboxExceptionType.EXECUTION_ERROR,
                        f"Sandbox security violation: {str(e)[:200]}",
                        {"cmd": cmd},
                    )
                    return SandboxResult(
                        stdout="",
                        stderr=str(e),
                        returncode=-1,
                        exception_type=SandboxExceptionType.EXECUTION_ERROR,
                    )

                # サンドボックスログ（エラー）
                self._log_sandbox_error(
                    None, exception_type, f"Sandbox execution error: {str(e)[:200]}", {"cmd": cmd}
                )

                # ロジック系の失敗はリトライしない
                if exception_type == SandboxExceptionType.EXECUTION_ERROR:
                    return SandboxResult(
                        stdout="",
                        stderr=str(e),
                        returncode=-1,
                        exception_type=exception_type,
                    )

                # リトライ可能なエラー
                if retry_on_errors and attempt < self.max_retries:
                    delay = self.retry_delay_sec * (2**attempt)  # 指数バックオフ
                    logger.warning(
                        f"Sandbox execution failed (attempt {attempt + 1}/{self.max_retries + 1}): {e}. "
                        f"Retrying in {delay:.1f}s..."
                    )
                    time.sleep(delay)
                    continue

                # リトライ上限に達した
                return SandboxResult(
                    stdout="",
                    stderr=str(e),
                    returncode=-1,
                    exception_type=exception_type,
                )

        # ここには来ないはずだが、念のため
        return SandboxResult(
            stdout="",
            stderr=f"Max retries exceeded: {last_exception}",
            returncode=-1,
            exception_type=SandboxExceptionType.EXECUTION_ERROR,
        )

    def _execute_once(
        self,
        cmd: list[str],
        timeout_sec: int,
        cwd: str | Path | None,
        env: dict | None,
    ) -> SandboxResult:
        """
        1回の実行を実行（リトライなし）
        """
        start_time = time.time()

        try:
            # POSIX環境では、子プロセス開始前にリソース制限を適用
            preexec_fn = None
            if os.name == "posix":
                preexec_fn = _apply_resource_limits

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout_sec,
                cwd=cwd,
                env=env,
                preexec_fn=preexec_fn,
            )

            execution_time = time.time() - start_time

            return SandboxResult(
                stdout=result.stdout,
                stderr=result.stderr,
                returncode=result.returncode,
                timed_out=False,
                execution_time_sec=execution_time,
            )

        except subprocess.TimeoutExpired:
            execution_time = time.time() - start_time
            raise

        except Exception:
            execution_time = time.time() - start_time
            raise

    def _log_sandbox_error(
        self,
        run_db_id: int | None,
        error_type: SandboxExceptionType,
        message: str,
        payload: dict[str, Any] | None = None,
    ) -> None:
        """
        サンドボックスエラーを ExecutionLog に記録する（Flaskアプリコンテキストが存在する場合のみ）

        Args:
            run_db_id: Run.id（オプション）
            error_type: 例外種別
            message: メッセージ
            payload: 追加情報
        """
        try:
            from nexuscore.webapp.logging_service import log_execution_event
        except ImportError:
            # webapp がインストールされていない場合はスキップ（CLI実行時など）
            return
        except Exception:
            # インポートエラーは既存の処理を止めない
            return

        base_payload: dict[str, Any] = {"error_type": error_type.value}
        if payload:
            base_payload.update(payload)

        log_execution_event(
            run_id=run_db_id,
            source="SANDBOX",
            level="ERROR",
            message=message,
            payload=base_payload,
        )

    def _classify_exception(self, exception: Exception) -> SandboxExceptionType:
        """
        例外を分類
        """
        error_msg = str(exception).lower()

        # レート制限
        if any(
            keyword in error_msg
            for keyword in ["rate limit", "rate_limit", "429", "too many requests"]
        ):
            return SandboxExceptionType.RATE_LIMIT

        # ネットワークエラー
        if any(keyword in error_msg for keyword in ["connection", "network", "timeout", "dns"]):
            return SandboxExceptionType.NETWORK_ERROR

        # タイムアウト
        if "timeout" in error_msg:
            return SandboxExceptionType.TIMEOUT

        # 実行エラー（コンパイルエラー、テスト失敗など）
        return SandboxExceptionType.EXECUTION_ERROR


# グローバルインスタンス（必要に応じて使用）
_default_executor = SandboxExecutor()


def run_in_sandbox(
    cmd: list[str],
    timeout_sec: int = 300,
    cwd: str | Path | None = None,
    env: dict | None = None,
    retry_on_errors: bool = True,
) -> SandboxResult:
    """
    サンドボックスでコマンドを実行（簡易インターフェース）

    Args:
        cmd: 実行コマンド（リスト形式）
        timeout_sec: タイムアウト（秒）
        cwd: 作業ディレクトリ
        env: 環境変数
        retry_on_errors: エラー時にリトライするか

    Returns:
        SandboxResult
    """
    return _default_executor.run_in_sandbox(
        cmd=cmd,
        timeout_sec=timeout_sec,
        cwd=cwd,
        env=env,
        retry_on_errors=retry_on_errors,
    )
