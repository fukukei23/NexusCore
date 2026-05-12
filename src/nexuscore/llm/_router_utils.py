# =============================================================================
# Shared utilities for LLMRouter and RoutedLLM
# =============================================================================

from __future__ import annotations


def estimate_tokens(text: str) -> int:
    """Rough token count estimate (chars / 3)."""
    if not text:
        return 0
    return (len(text) + 2) // 3
