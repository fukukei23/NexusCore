from __future__ import annotations

import enum
import logging
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from nexuscore.core.sandbox._config import (  # noqa: F401 — legacy re-exports
    _CPU_TIME_LIMIT_SEC,
    _MEMORY_LIMIT_MB,
    _apply_resource_limits,
    _check_forbidden_modules,
    load_sandbox_policy,
)

logger = logging.getLogger(__name__)


class SandboxExceptionType(enum.Enum):
    """サンドボックス実行時の例外種別"""

    RATE_LIMIT = "rate_limit"
    TIMEOUT = "timeout"
    INVALID_OUTPUT = "invalid_output"
    EXECUTION_ERROR = "execution_error"
    NETWORK_ERROR = "network_error"


@dataclass
class SandboxResult:
    """サンドボックス実行結果"""

    stdout: str
    stderr: str
    returncode: int
    timed_out: bool = False
    exception_type: SandboxExceptionType | None = None
    execution_time_sec: float = 0.0


class SandboxExecutor:
    """サンドボックス実行エグゼキューター（タイムアウト制御、リトライ戦略、例外分類）。"""

    def __init__(
        self,
        default_timeout_sec: int = 300,
        max_retries: int = 3,
        retry_delay_sec: float = 1.0,
        policy: dict[str, Any] | None = None,
    ):
        self.policy = policy or load_sandbox_policy()

        resource_limits = self.policy.get("resource_limits", {})
        retry_policy = self.policy.get("retry_policy", {})

        self.default_timeout_sec = resource_limits.get("wall_time_seconds", default_timeout_sec)
        self.max_retries = retry_policy.get("max_retries", max_retries)
        self.retry_delay_sec = retry_delay_sec

    def run_in_sandbox(
        self,
        cmd: list[str],
        timeout_sec: int | None = None,
        cwd: str | Path | None = None,
        env: dict | None = None,
        retry_on_errors: bool = True,
    ) -> SandboxResult:
        """サンドボックスでコマンドを実行。"""
        timeout = timeout_sec or self.default_timeout_sec
        last_exception: Exception | None = None

        for attempt in range(self.max_retries + 1):
            try:
                result = self._execute_once(cmd, timeout, cwd, env)
                return result

            except subprocess.TimeoutExpired as e:
                last_exception = e
                exception_type = SandboxExceptionType.TIMEOUT
                self._log_sandbox_error(
                    None, exception_type, "Sandbox timed out", {"cmd": cmd, "timeout": timeout}
                )
                if not retry_on_errors or attempt >= self.max_retries:
                    return SandboxResult(
                        stdout="", stderr=f"Timeout after {timeout} seconds",
                        returncode=-1, timed_out=True, exception_type=exception_type,
                    )
                return SandboxResult(
                    stdout="", stderr=f"Timeout after {timeout} seconds",
                    returncode=-1, timed_out=True, exception_type=exception_type,
                )

            except Exception as e:  # noqa: BLE001 — sandbox error classification after specific TimeoutExpired catch
                last_exception = e
                exception_type = self._classify_exception(e)

                from nexuscore.core.errors import SandboxSecurityError

                if isinstance(e, SandboxSecurityError):
                    self._log_sandbox_error(
                        None, SandboxExceptionType.EXECUTION_ERROR,
                        f"Sandbox security violation: {str(e)[:200]}", {"cmd": cmd},
                    )
                    return SandboxResult(
                        stdout="", stderr=str(e), returncode=-1,
                        exception_type=SandboxExceptionType.EXECUTION_ERROR,
                    )

                self._log_sandbox_error(
                    None, exception_type, f"Sandbox execution error: {str(e)[:200]}", {"cmd": cmd}
                )

                if exception_type == SandboxExceptionType.EXECUTION_ERROR:
                    return SandboxResult(
                        stdout="", stderr=str(e), returncode=-1, exception_type=exception_type,
                    )

                if retry_on_errors and attempt < self.max_retries:
                    delay = self.retry_delay_sec * (2**attempt)
                    logger.warning(
                        f"Sandbox execution failed (attempt {attempt + 1}/{self.max_retries + 1}): {e}. "
                        f"Retrying in {delay:.1f}s..."
                    )
                    time.sleep(delay)
                    continue

                return SandboxResult(
                    stdout="", stderr=str(e), returncode=-1, exception_type=exception_type,
                )

        return SandboxResult(
            stdout="", stderr=f"Max retries exceeded: {last_exception}",
            returncode=-1, exception_type=SandboxExceptionType.EXECUTION_ERROR,
        )

    def _execute_once(
        self,
        cmd: list[str],
        timeout_sec: int,
        cwd: str | Path | None,
        env: dict | None,
    ) -> SandboxResult:
        """1回の実行（リトライなし）。"""
        import os

        start_time = time.time()

        try:
            preexec_fn = None
            if os.name == "posix":
                preexec_fn = _apply_resource_limits

            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=timeout_sec,
                cwd=cwd, env=env, preexec_fn=preexec_fn,
            )

            execution_time = time.time() - start_time

            return SandboxResult(
                stdout=result.stdout, stderr=result.stderr,
                returncode=result.returncode, timed_out=False,
                execution_time_sec=execution_time,
            )

        except subprocess.TimeoutExpired:
            raise

        except Exception:  # noqa: BLE001 — re-raise pattern for unknown subprocess errors
            raise

    def _log_sandbox_error(
        self,
        run_db_id: int | None,
        error_type: SandboxExceptionType,
        message: str,
        payload: dict[str, Any] | None = None,
    ) -> None:
        """サンドボックスエラーを ExecutionLog に記録する。"""
        try:
            from nexuscore.webapp.logging_service import log_execution_event
        except ImportError:
            return
        except Exception:  # noqa: BLE001 — モジュール初期化エラー等の追加キャッチ
            return

        base_payload: dict[str, Any] = {"error_type": error_type.value}
        if payload:
            base_payload.update(payload)

        log_execution_event(
            run_id=run_db_id, source="SANDBOX", level="ERROR",
            message=message, payload=base_payload,
        )

    def _classify_exception(self, exception: Exception) -> SandboxExceptionType:
        """例外を分類。"""
        error_msg = str(exception).lower()

        if any(
            keyword in error_msg
            for keyword in ["rate limit", "rate_limit", "429", "too many requests"]
        ):
            return SandboxExceptionType.RATE_LIMIT

        if any(keyword in error_msg for keyword in ["connection", "network", "timeout", "dns"]):
            return SandboxExceptionType.NETWORK_ERROR

        if "timeout" in error_msg:
            return SandboxExceptionType.TIMEOUT

        return SandboxExceptionType.EXECUTION_ERROR


_default_executor = SandboxExecutor()


def run_in_sandbox(
    cmd: list[str],
    timeout_sec: int = 300,
    cwd: str | Path | None = None,
    env: dict | None = None,
    retry_on_errors: bool = True,
) -> SandboxResult:
    """サンドボックスでコマンドを実行（簡易インターフェース）。"""
    return _default_executor.run_in_sandbox(
        cmd=cmd, timeout_sec=timeout_sec, cwd=cwd, env=env, retry_on_errors=retry_on_errors,
    )
