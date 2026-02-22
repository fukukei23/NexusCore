"""
orchestrator/constants.py

Minimal authority-level constants for controlling how far an orchestration run is
allowed to proceed.

NOTE:
This module intentionally does NOT depend on `nexuscore.core.orchestrator` to
avoid importing frozen/core components at import time.
"""


class AuthorityLevel:
    """Authority (autonomy) level for orchestration execution."""

    HUMAN_CONTROLLED = 1
    PARTIALLY_AUTONOMOUS = 2
    FULLY_AUTONOMOUS = 3


