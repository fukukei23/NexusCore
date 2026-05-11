"""
Structured phase-logging helpers for authority_runner.

Extracted to keep the main module focused on orchestration flow
and to allow reuse from both primary and resume code paths.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Sequence

_logger = logging.getLogger(__name__)


def log_phase_start(phase: str, all_phases: Sequence[str]) -> None:
    idx = list(all_phases).index(phase) + 1 if phase in all_phases else "?"
    total = len(all_phases)
    _logger.info("[%s/%s] Phase: %s — starting", idx, total, phase)


def log_phase_done(phase: str, start_time: float) -> None:
    elapsed = time.monotonic() - start_time
    _logger.info("Phase: %s — done (%.1fs)", phase, elapsed)


def log_phase_pause(phase: str) -> None:
    _logger.info("Phase: %s — pausing before execution (stop_before)", phase)
