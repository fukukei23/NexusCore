"""
LLM call fallback chain management.

When a provider returns 429 (rate limit), this module tracks cooldown state
per provider and selects the next available candidate from the fallback list.
Designed to prevent cascading stub-mode degradation on rate-limited providers.
"""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass, field

logger = logging.getLogger("LLMFallback")


@dataclass
class RateLimitEntry:
    """Per-provider rate limit tracking."""

    last_429_at: float = 0.0
    cooldown_sec: float = 60.0

    @property
    def in_cooldown(self) -> bool:
        return (time.time() - self.last_429_at) < self.cooldown_sec


@dataclass
class FallbackTracker:
    """Tracks 429 state per provider and determines fallback eligibility."""

    providers: dict[str, RateLimitEntry] = field(default_factory=dict)
    max_fallbacks: int = 3

    def record_429(self, provider: str) -> None:
        if provider not in self.providers:
            cooldown = float(os.getenv("NEXUS_429_COOLDOWN_SEC", "60"))
            self.providers[provider] = RateLimitEntry(cooldown_sec=cooldown)
        self.providers[provider].last_429_at = time.time()
        logger.warning("[Fallback] 429 recorded for provider=%s", provider)

    def should_skip(self, provider: str) -> bool:
        entry = self.providers.get(provider)
        return entry.in_cooldown if entry else False

    def next_candidate(self, candidates: list[str], family_fn) -> str | None:
        """Return first candidate whose provider is NOT in cooldown."""
        for c in candidates:
            if not self.should_skip(family_fn(c)):
                return c
        return None


__all__ = ["FallbackTracker", "RateLimitEntry"]
