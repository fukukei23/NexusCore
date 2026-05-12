"""Shared configuration and tree-sitter availability for the analyzer package."""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from typing import Any

# --- tree-sitter optional dependency ---
try:
    from tree_sitter import Node, Query
    from tree_sitter_language_pack import get_language, get_parser

    TREE_SITTER_AVAILABLE = True
except ImportError:
    Node = Query = None
    TREE_SITTER_AVAILABLE = False

# --- Global config ---
CONFIG: dict[str, Any] = {
    "cache_dir": Path.home() / ".nexuscore" / "cache",
    "log_level": logging.INFO,
    "supported_languages": {
        ".py": "python",
        ".js": "javascript",
    },
    "cache_version": 1,
    "analyzer_version": "0.1.0",
    "enable_cache": os.getenv(
        "NEXUS_UNIFIED_ANALYZER_ENABLE_CACHE", os.getenv("NEXUS_ANALYZER_ENABLE_CACHE", "1")
    ).lower()
    not in ("0", "false", "no"),
    "cache_dir_env": os.getenv(
        "NEXUS_UNIFIED_ANALYZER_CACHE_DIR", os.getenv("NEXUS_ANALYZER_CACHE_DIR")
    ),
    "reset_cache": os.getenv("NEXUS_UNIFIED_ANALYZER_RESET_CACHE", "").lower()
    in ("1", "true", "yes"),
}


def setup_logging(log_level: int = logging.INFO) -> logging.Logger:
    logging.basicConfig(
        level=log_level, format="%(asctime)s - %(levelname)s - %(message)s", stream=sys.stdout
    )
    return logging.getLogger("NexusCoreAnalyzer")


logger = setup_logging(CONFIG["log_level"])
