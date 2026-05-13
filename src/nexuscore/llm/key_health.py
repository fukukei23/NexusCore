from __future__ import annotations

import logging
import os
from dataclasses import dataclass

logger = logging.getLogger("KeyHealth")

KNOWN_KEYS: tuple[tuple[str, str], ...] = (
    ("OPENAI_API_KEY", "openai"),
    ("ANTHROPIC_API_KEY", "anthropic"),
    ("GEMINI_API_KEY", "google"),
    ("GLM_API_KEY", "glm"),
    ("MINIMAX_API_KEY", "minimax"),
    ("DEEPSEEK_API_KEY", "deepseek"),
    ("KIMI_API_KEY", "moonshot"),
    ("PERPLEXITY_API_KEY", "perplexity"),
)

PLACEHOLDERS = frozenset({"", "your-api-key", "xxx", "changeme", "sk-xxx", "placeholder"})


@dataclass
class KeyReport:
    provider: str
    env_var: str
    status: str  # ok / missing / placeholder / duplicate
    key_length: int = 0


def check_all_keys() -> list[KeyReport]:
    reports: list[KeyReport] = []
    seen_hashes: dict[int, str] = {}

    for env_var, provider in KNOWN_KEYS:
        val = os.getenv(env_var, "")
        if not val or val.strip().lower() in PLACEHOLDERS:
            reports.append(KeyReport(provider, env_var, "missing"))
            continue

        val_hash = hash(val)
        if val_hash in seen_hashes:
            reports.append(KeyReport(provider, env_var, "duplicate", len(val)))
            logger.warning(
                "[KeyHealth] %s shares value with %s", env_var, seen_hashes[val_hash]
            )
        else:
            seen_hashes[val_hash] = env_var
            reports.append(KeyReport(provider, env_var, "ok", len(val)))

    return reports


def log_key_health() -> None:
    """Log key health summary at startup."""
    reports = check_all_keys()
    for r in reports:
        if r.status == "ok":
            logger.info("[KeyHealth] %s: OK (length=%d)", r.provider, r.key_length)
        else:
            logger.warning(
                "[KeyHealth] %s (%s): %s", r.provider, r.env_var, r.status
            )


__all__ = ["KeyReport", "check_all_keys", "log_key_health"]
