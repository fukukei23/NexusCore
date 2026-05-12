"""Sandbox configuration, resource limits, security checks, and policy loading."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

try:
    import resource
except ImportError:
    resource = None  # type: ignore[assignment]

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)

_MEMORY_LIMIT_MB = int(os.getenv("NEXUS_SANDBOX_MEMORY_MB", "512"))
_CPU_TIME_LIMIT_SEC = int(os.getenv("NEXUS_SANDBOX_CPU_SEC", "30"))

_FORBIDDEN_MODULE_NAMES = {"os", "subprocess", "shutil", "socket", "pathlib"}


def _apply_resource_limits() -> None:
    """サンドボックス実行時のリソース制限を適用する（POSIXのみ）。"""
    if os.name != "posix":
        return

    if resource is None:
        logger.debug("resource module is not available. Skipping resource limits.")
        return

    try:
        memory_limit_bytes = _MEMORY_LIMIT_MB * 1024 * 1024
        resource.setrlimit(resource.RLIMIT_AS, (memory_limit_bytes, memory_limit_bytes))

        resource.setrlimit(resource.RLIMIT_CPU, (_CPU_TIME_LIMIT_SEC, _CPU_TIME_LIMIT_SEC))

        logger.debug(
            f"Applied resource limits: memory={_MEMORY_LIMIT_MB}MB, cpu_time={_CPU_TIME_LIMIT_SEC}s"
        )
    except (OSError, ValueError) as e:
        logger.warning(f"Failed to apply resource limits: {e}")


def _check_forbidden_modules(code: str) -> None:
    """コード文字列内に危険なモジュールのインポートが含まれていないか検査する。"""
    from nexuscore.core.errors import SandboxSecurityError

    code_lower = code.lower()
    detected_modules = []

    for module_name in _FORBIDDEN_MODULE_NAMES:
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
    """sandbox_policy.yml を読み込んで辞書として返す。見つからない場合はデフォルト。"""
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
            "redact_env_vars": ["GLM_API_KEY", "MINIMAX_API_KEY", "GITHUB_TOKEN"],
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
