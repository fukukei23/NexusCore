from __future__ import annotations

import logging
import os
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

try:
    from dotenv import find_dotenv, load_dotenv
except ImportError:  # pragma: no cover - optional dependency
    find_dotenv = None  # type: ignore[assignment]
    load_dotenv = None  # type: ignore[assignment]

_ENV_LOADED = False
_LOGGER = logging.getLogger("LLMRouterConfig")


def _bool_from_env(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def ensure_env_loaded() -> str | None:
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

    if load_dotenv is not None:
        for candidate in candidates:
            try:
                if candidate.is_file():
                    load_dotenv(candidate, override=False)
                    os.environ["NEXUSCORE_ENV_LOADED"] = str(candidate.resolve())
                    _ENV_LOADED = True
                    return os.getenv("NEXUSCORE_ENV_LOADED")
            except Exception:  # pragma: no cover - defensive
                continue

        if not _ENV_LOADED and find_dotenv is not None:
            auto = find_dotenv(usecwd=True)
            if auto:
                load_dotenv(auto, override=False)
                os.environ["NEXUSCORE_ENV_LOADED"] = auto
                _ENV_LOADED = True
                return os.getenv("NEXUSCORE_ENV_LOADED")
    else:
        _LOGGER.warning("[ENV] python-dotenv is not installed; skipping automatic .env loading.")

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
    _sync_env_var("GLM_API_KEY", ["ZHIPU_API_KEY", "GLM_KEY"])
    _sync_env_var("MINIMAX_API_KEY", ["MINIMAX_KEY"])


@dataclass(frozen=True)
class LLMRouterConfig:
    glm_api_key: str | None
    minimax_api_key: str | None
    request_timeout: float
    dry_run: bool
    real_calls_enabled: bool

    @classmethod
    def from_env(cls) -> LLMRouterConfig:
        ensure_env_loaded()
        synchronize_aliases()

        glm_key = os.getenv("GLM_API_KEY")
        minimax_key = os.getenv("MINIMAX_API_KEY")

        timeout = float(os.getenv("NEXUS_REQUEST_TIMEOUT_SEC", "120") or 120)
        dry_run = _bool_from_env(os.getenv("LLM_DRY_RUN"), False)
        real_calls = _bool_from_env(os.getenv("NEXUS_REAL_CALLS"), False)

        if not real_calls and any([glm_key, minimax_key]):
            # Auto-enable real calls if API keys are present.
            os.environ["NEXUS_REAL_CALLS"] = "1"
            real_calls = True

        os.environ.setdefault("NEXUS_REQUEST_TIMEOUT_SEC", str(timeout))

        return cls(
            glm_api_key=glm_key,
            minimax_api_key=minimax_key,
            request_timeout=timeout,
            dry_run=dry_run,
            real_calls_enabled=real_calls,
        )
