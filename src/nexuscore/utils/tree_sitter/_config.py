import os
from typing import Any

CONFIG: dict[str, Any] = {
    "supported_languages": {
        ".py": "python",
        ".js": "javascript",
        ".ts": "typescript",
        ".go": "go",
        ".rs": "rust",
        ".c": "c",
        ".cpp": "cpp",
        ".java": "java",
        ".rb": "ruby",
    },
    "max_workers": int(os.getenv("NEXUS_TREESITTER_MAX_WORKERS", os.cpu_count() or 4)),
    "timeout_seconds": int(os.getenv("NEXUS_TREESITTER_TIMEOUT_SEC", 60)),
    "enable_cache": os.getenv("NEXUS_TREESITTER_ENABLE_CACHE", "1").lower() in ("1", "true", "yes"),
    "enable_profiling": os.getenv("NEXUS_TREESITTER_ENABLE_PROFILING", "0").lower() in ("1", "true", "yes"),
}

try:
    from tree_sitter import Node, Parser
    from tree_sitter_language_pack import get_language, get_parser

    TREE_SITTER_AVAILABLE = True
except ImportError:
    TREE_SITTER_AVAILABLE = False
    Parser = Node = None

try:
    from colorama import Fore, Style, init
    init(autoreset=True)
    HAS_EXTRAS = True
except ImportError:
    HAS_EXTRAS = False

    class Fore:  # type: ignore[no-redef]
        RED = GREEN = YELLOW = BLUE = MAGENTA = CYAN = WHITE = ""

    class Style:  # type: ignore[no-redef]
        BRIGHT = RESET_ALL = ""
