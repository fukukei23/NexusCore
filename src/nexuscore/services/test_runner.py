from __future__ import annotations

import logging
import os
import shlex
import subprocess
from pathlib import Path
from typing import Any

try:
    from nexuscore.core.sandbox_executor import SandboxResult, run_in_sandbox

    HAS_SANDBOX = True
except ImportError:
    HAS_SANDBOX = False
    run_in_sandbox = None
    SandboxResult = None

logger = logging.getLogger(__name__)


def run_tests(
    project_path: Path,
    retry_context: Any | None = None,
) -> tuple[bool, str]:
    """
    プロジェクト配下でテストコマンドを実行する。
    デフォルトは pytest。環境変数 NEXUS_SELF_HEALING_TEST_CMD で上書き可能。

    Args:
        project_path: プロジェクトパス
        retry_context: RetryContext インスタンス（retry_count と error_class を記録）

    Returns:
        (成功フラグ, 出力文字列)
    """
    cmd_str = os.getenv("NEXUS_SELF_HEALING_TEST_CMD", "pytest -q")
    logger.info(f"Running tests with command: {cmd_str} (cwd={project_path})")

    if HAS_SANDBOX and run_in_sandbox:
        return _run_via_sandbox(cmd_str, project_path, retry_context)
    else:
        return _run_via_subprocess(cmd_str, project_path)


def _run_via_sandbox(
    cmd_str: str,
    project_path: Path,
    retry_context: Any | None,
) -> tuple[bool, str]:
    cmd_list = cmd_str.split()
    if not cmd_list:
        cmd_list = ["pytest", "-q"]

    timeout_sec = int(os.getenv("NEXUS_SANDBOX_TIMEOUT_SEC", "300"))

    try:
        result: SandboxResult = run_in_sandbox(
            cmd=cmd_list,
            timeout_sec=timeout_sec,
            cwd=str(project_path),
            retry_on_errors=True,
        )

        if retry_context and result.exception_type:
            from nexuscore.core.errors import SandboxExecutionError

            error = SandboxExecutionError(f"Sandbox execution failed: {result.stderr}")
            retry_context.record_attempt(
                attempt=0,
                error=error if result.returncode != 0 else None,
            )

        success = result.returncode == 0 and not result.timed_out
        output = result.stdout + result.stderr if result.stderr else result.stdout
        return success, output

    except Exception as e:  # noqa: BLE001
        msg = f"Exception while running tests: {e}"
        logger.error(msg, exc_info=True)
        if retry_context:
            retry_context.record_attempt(attempt=0, error=e)
        return False, msg


def _run_via_subprocess(cmd_str: str, project_path: Path) -> tuple[bool, str]:
    try:
        cmd_list = shlex.split(cmd_str)
        if not cmd_list:
            cmd_list = ["pytest", "-q"]
        proc = subprocess.run(
            cmd_list,
            cwd=str(project_path),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        output = proc.stdout
        success = proc.returncode == 0
        return success, output
    except (subprocess.SubprocessError, OSError) as e:
        msg = f"Exception while running tests: {e}"
        logger.error(msg, exc_info=True)
        return False, msg
