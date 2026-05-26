from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from ._config import CONFIG, logger


class AnalyzerCache:
    """
    Hash-based cache manager for analysis results.

    Detects unchanged files via content hash and skips re-analysis.
    """

    def __init__(self, project_root: Path, cache_dir: Path | None = None):
        self.project_root = Path(project_root).resolve()

        if cache_dir is None and CONFIG.get("cache_dir_env"):
            cache_dir = Path(CONFIG["cache_dir_env"])

        self.cache_dir = cache_dir or (self.project_root / ".nexuscache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_file = self.cache_dir / "unified_analyzer.json"
        self.cache_data: dict[str, Any] = {}
        self.cache_version = CONFIG["cache_version"]

    def _compute_file_hash(self, file_path: Path) -> str:
        try:
            content = file_path.read_bytes()
            hash_hex = hashlib.sha256(content).hexdigest()
            return f"sha256:{hash_hex}"
        except OSError as e:
            logger.warning("Failed to compute hash for %s: %s", file_path, e)
            return ""

    def load_cache(self) -> bool:
        if not self.cache_file.exists():
            logger.debug("Cache file not found: %s", self.cache_file)
            return False

        try:
            with open(self.cache_file, encoding="utf-8") as f:
                data = json.load(f)

            schema_version = data.get("schema_version") or data.get("version")
            if schema_version != self.cache_version:
                logger.info(
                    "Cache version mismatch (expected %s, got %s). Rebuilding cache.",
                    self.cache_version, schema_version,
                )
                return False

            analyzer_version = data.get("analyzer_version")
            expected_version = CONFIG.get("analyzer_version", "0.1.0")
            if analyzer_version and analyzer_version != expected_version:
                logger.info(
                    "Analyzer version mismatch (expected %s, got %s). Rebuilding cache.",
                    expected_version, analyzer_version,
                )
                return False

            self.cache_data = data
            logger.debug(
                "Loaded cache from %s (%d files)",
                self.cache_file, len(data.get("files", {})),
            )
            return True
        except (OSError, json.JSONDecodeError, ValueError) as e:
            logger.warning("Failed to load cache from %s: %s", self.cache_file, e)
            return False

    def save_cache(self, file_results: dict[str, dict[str, Any]]):
        try:
            created_at = self.cache_data.get("created_at") or datetime.now().isoformat()
            updated_at = datetime.now().isoformat()

            cache_data = {
                "schema_version": self.cache_version,
                "analyzer_version": CONFIG.get("analyzer_version", "0.1.0"),
                "created_at": created_at,
                "updated_at": updated_at,
                "project_root": str(self.project_root),
                "files": file_results,
            }

            temp_file = self.cache_file.with_suffix(".tmp")
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(cache_data, f, indent=2, ensure_ascii=False)
            temp_file.replace(self.cache_file)
            self.cache_data = cache_data
            logger.debug("Saved cache to %s (%d files)", self.cache_file, len(file_results))
        except OSError as e:
            logger.warning("Failed to save cache to %s: %s", self.cache_file, e)

    def get_cached_result(self, file_path: Path, current_hash: str) -> dict[str, Any] | None:
        if not self.cache_data:
            return None

        try:
            rel_path = str(file_path.relative_to(self.project_root))
        except ValueError:
            return None

        cached_file = self.cache_data.get("files", {}).get(rel_path)
        if not cached_file:
            return None

        cached_hash = cached_file.get("hash", "")
        cached_hash_normalized = cached_hash.replace("sha256:", "") if cached_hash else ""
        current_hash_normalized = current_hash.replace("sha256:", "") if current_hash else ""

        if (
            cached_hash_normalized
            and current_hash_normalized
            and cached_hash_normalized == current_hash_normalized
        ):
            return cached_file.get("result")

        return None

    def should_analyze_file(self, file_path: Path) -> tuple[bool, str | None]:
        if not file_path.is_file():
            return False, None

        current_hash = self._compute_file_hash(file_path)
        if not current_hash:
            return True, None

        cached_result = self.get_cached_result(file_path, current_hash)
        if cached_result is not None:
            return False, current_hash

        return True, current_hash

    def update_cache_entry(self, file_path: Path, file_hash: str, result: dict[str, Any]):
        try:
            rel_path = str(file_path.relative_to(self.project_root))
        except ValueError:
            return

        if "files" not in self.cache_data:
            self.cache_data["files"] = {}

        self.cache_data["files"][rel_path] = {
            "hash": f"sha256:{file_hash}" if not file_hash.startswith("sha256:") else file_hash,
            "result": result,
            "last_analyzed": datetime.now().isoformat(),
        }

    def clear_cache(self):
        if self.cache_file.exists():
            self.cache_file.unlink()
        self.cache_data = {}
        logger.info("Cache cleared: %s", self.cache_file)
