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
from typing import Optional, List, Dict, Any

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore

logger = logging.getLogger(__name__)


def load_sandbox_policy(policy_path: str | None = None) -> Dict[str, Any]:
    """
    sandbox_policy.yml を読み込んで辞書として返す。

    見つからない場合は安全側のデフォルトを返す。

    Args:
        policy_path: ポリシーファイルのパス（Noneの場合は環境変数またはデフォルト）

    Returns:
        ポリシー辞書
    """
    default = {
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

    path = policy_path or os.getenv("NEXUSCORE_SANDBOX_POLICY", "sandbox_policy.yml")
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
    exception_type: Optional[SandboxExceptionType] = None
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
        policy: Dict[str, Any] | None = None,
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
        cmd: List[str],
        timeout_sec: Optional[int] = None,
        cwd: Optional[str | Path] = None,
        env: Optional[dict] = None,
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
        """
        timeout = timeout_sec or self.default_timeout_sec
        last_exception: Optional[Exception] = None

        for attempt in range(self.max_retries + 1):
            try:
                result = self._execute_once(cmd, timeout, cwd, env)
                return result

            except subprocess.TimeoutExpired as e:
                last_exception = e
                exception_type = SandboxExceptionType.TIMEOUT
                # サンドボックスログ（タイムアウト）
                self._log_sandbox_error(None, exception_type, "Sandbox timed out", {"cmd": cmd, "timeout": timeout})
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

                # サンドボックスログ（エラー）
                self._log_sandbox_error(None, exception_type, f"Sandbox execution error: {str(e)[:200]}", {"cmd": cmd})

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
                    delay = self.retry_delay_sec * (2 ** attempt)  # 指数バックオフ
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
        cmd: List[str],
        timeout_sec: int,
        cwd: Optional[str | Path],
        env: Optional[dict],
    ) -> SandboxResult:
        """
        1回の実行を実行（リトライなし）
        """
        start_time = time.time()

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout_sec,
                cwd=cwd,
                env=env,
            )

            execution_time = time.time() - start_time

            return SandboxResult(
                stdout=result.stdout,
                stderr=result.stderr,
                returncode=result.returncode,
                timed_out=False,
                execution_time_sec=execution_time,
            )

        except subprocess.TimeoutExpired as e:
            execution_time = time.time() - start_time
            raise

        except Exception as e:
            execution_time = time.time() - start_time
            raise

    def _log_sandbox_error(
        self,
        run_db_id: Optional[int],
        error_type: SandboxExceptionType,
        message: str,
        payload: Optional[Dict[str, Any]] = None,
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

        base_payload: Dict[str, Any] = {"error_type": error_type.value}
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
        if any(keyword in error_msg for keyword in ["rate limit", "rate_limit", "429", "too many requests"]):
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
    cmd: List[str],
    timeout_sec: int = 300,
    cwd: Optional[str | Path] = None,
    env: Optional[dict] = None,
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

