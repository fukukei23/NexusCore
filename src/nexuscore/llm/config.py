"""
Configuration helpers for LLMRouter.

This module centralizes .env loading, environment-variable synchronization,
and typed access to runtime settings so that the router itself can focus on
provider logic.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

try:
    from dotenv import find_dotenv, load_dotenv
except ImportError:  # pragma: no cover - optional dependency
    find_dotenv = None  # type: ignore[assignment]
    load_dotenv = None  # type: ignore[assignment]

_ENV_LOADED = False
_LOGGER = logging.getLogger("LLMRouterConfig")


def _bool_from_env(value: Optional[str], default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def ensure_env_loaded() -> Optional[str]:
    """
    Load environment variables from the nearest .env file (if python-dotenv is available).
    Only runs once per process.
    """
    global _ENV_LOADED
    if _ENV_LOADED:
        return os.getenv("NEXUSCORE_ENV_LOADED")

    env_file = os.getenv("NEXUSCORE_ENV_FILE")
    candidates: list[Path] = []
    if env_file:
        candidates.append(Path(env_file))

    current = Path(__file__).resolve()
    candidates.extend(
        [
            current.parents[3] / ".env",
            current.parents[2] / ".env",
            current.parents[1] / ".env",
        ]
    )

    if load_dotenv:
        for candidate in candidates:
            try:
                if candidate.is_file():
                    load_dotenv(candidate, override=False)
                    os.environ["NEXUSCORE_ENV_LOADED"] = str(candidate.resolve())
                    _ENV_LOADED = True
                    return os.getenv("NEXUSCORE_ENV_LOADED")
            except Exception:  # pragma: no cover - defensive
                continue

        if not _ENV_LOADED and find_dotenv:
            auto = find_dotenv(usecwd=True)
            if auto:
                load_dotenv(auto, override=False)
                os.environ["NEXUSCORE_ENV_LOADED"] = auto
                _ENV_LOADED = True
                return os.getenv("NEXUSCORE_ENV_LOADED")
    else:
        _LOGGER.warning(
            "[ENV] python-dotenv is not installed; skipping automatic .env loading."
        )

    _ENV_LOADED = True
    return os.getenv("NEXUSCORE_ENV_LOADED")


def _sync_env_var(target: str, aliases: Iterable[str]) -> None:
    if os.getenv(target):
        return
    for alias in aliases:
        value = os.getenv(alias)
        if value:
            os.environ[target] = value
            _LOGGER.info("ENV sync: %s was missing. Using value from %s.", target, alias)
            break


def synchronize_aliases() -> None:
    """Align legacy/custom environment variables with canonical names."""
    _sync_env_var("GEMINI_API_KEY", ["GEMINI_API_KEY_AGENT_A", "GEMINI_API_KEY_AGENT_B"])
    _sync_env_var("DEEPSEEK_API_KEY", ["DEEPSEEK_KEY", "DEEPSEEK"])
    _sync_env_var("KIMI_API_KEY", ["MOONSHOT_API_KEY", "MOONSHOT"])


@dataclass(frozen=True)
class LLMRouterConfig:
    openai_api_key: Optional[str]
    gemini_api_key: Optional[str]
    deepseek_api_key: Optional[str]
    kimi_api_key: Optional[str]
    request_timeout: float
    dry_run: bool
    real_calls_enabled: bool

    @classmethod
    def from_env(cls) -> "LLMRouterConfig":
        ensure_env_loaded()
        synchronize_aliases()

        openai_key = os.getenv("OPENAI_API_KEY")
        gemini_key = os.getenv("GEMINI_API_KEY")
        deepseek_key = os.getenv("DEEPSEEK_API_KEY")
        kimi_key = os.getenv("KIMI_API_KEY")

        timeout = float(os.getenv("NEXUS_REQUEST_TIMEOUT_SEC", "120") or 120)
        dry_run = _bool_from_env(os.getenv("LLM_DRY_RUN"), False)
        real_calls = _bool_from_env(os.getenv("NEXUS_REAL_CALLS"), False)

        if not real_calls and any([openai_key, gemini_key, deepseek_key, kimi_key]):
            # Auto-enable real calls if API keys are present.
            os.environ["NEXUS_REAL_CALLS"] = "1"
            real_calls = True

        os.environ.setdefault("NEXUS_REQUEST_TIMEOUT_SEC", str(timeout))

        return cls(
            openai_api_key=openai_key,
            gemini_api_key=gemini_key,
            deepseek_api_key=deepseek_key,
            kimi_api_key=kimi_key,
            request_timeout=timeout,
            dry_run=dry_run,
            real_calls_enabled=real_calls,
        )
