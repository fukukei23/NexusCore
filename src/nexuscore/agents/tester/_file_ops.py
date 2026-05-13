from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def resolve_test_file_path(project_root: Path, target_file_path: str) -> Path:
    path = Path(target_file_path)
    parts = list(path.parts)
    if "src" in parts:
        idx = parts.index("src")
        parts = parts[idx + 1:]
    elif "nexuscore" in parts:
        idx = parts.index("nexuscore")
        parts = parts[idx:]

    if parts[0] != "tests":
        parts = ["tests"] + parts

    filename = parts[-1]
    if not filename.startswith("test_"):
        parts[-1] = f"test_{filename}"

    return project_root / Path(*parts)


def write_test_file(test_file_path: Path, test_code: str) -> None:
    test_file_path.parent.mkdir(parents=True, exist_ok=True)
    if test_file_path.exists():
        logger.info("Overwriting existing test file: %s", test_file_path)
    test_file_path.write_text(test_code, encoding="utf-8")
    logger.info("Test file written: %s", test_file_path)


def infer_module_name_from_path(file_path: str) -> str:
    return Path(file_path).stem
