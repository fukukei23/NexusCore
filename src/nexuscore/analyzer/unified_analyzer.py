#!/usr/bin/env python3
"""Unified project-wide analyzer with hash-based caching."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from ._cache import AnalyzerCache
from ._config import CONFIG, TREE_SITTER_AVAILABLE, logger
from ._engine import AnalysisResult, TreeSitterEngine


class UnifiedAnalyzer:
    """プロジェクト全体の解析を統合するクラス（キャッシュ機能付き）。"""

    def __init__(
        self,
        project_root: Path,
        use_cache: bool | None = None,
        config: dict[str, Any] | None = None,
    ):
        self.project_root = Path(project_root).resolve()
        self.config = {**CONFIG, **(config or {})}
        self.use_cache = use_cache if use_cache is not None else self.config["enable_cache"]

        self.engine = TreeSitterEngine(self.config)

        cache_dir = None
        if self.use_cache:
            if CONFIG.get("cache_dir_env"):
                cache_dir = Path(CONFIG["cache_dir_env"])
            elif self.config.get("cache_dir"):
                cache_dir = Path(self.config["cache_dir"])

        self.cache = AnalyzerCache(self.project_root, cache_dir) if self.use_cache else None
        self.stats = {"total_files": 0, "cached_files": 0, "analyzed_files": 0, "failed_files": 0}

    def setup(self, languages: list[str] | None = None) -> bool:
        return self.engine.setup_parsers(languages)

    def _get_target_files(self, exclude_patterns: list[str] | None = None) -> list[Path]:
        if exclude_patterns is None:
            exclude_patterns = [
                "**/node_modules/**",
                "**/.git/**",
                "**/build/**",
                "**/__pycache__/**",
                "**/.nexuscache/**",
            ]

        target_files = []
        for ext, _lang in self.config["supported_languages"].items():
            for file_path in self.project_root.rglob(f"*{ext}"):
                if not file_path.is_file():
                    continue
                if any(file_path.match(p) for p in exclude_patterns):
                    continue
                target_files.append(file_path)
        return target_files

    def run(self, exclude_patterns: list[str] | None = None) -> dict[str, Any]:
        start_time = datetime.now()

        if self.cache:
            self.cache.load_cache()
            if CONFIG.get("reset_cache", False):
                logger.info("RESET_CACHE environment variable is set. Clearing cache.")
                self.cache.clear_cache()

        target_files = self._get_target_files(exclude_patterns)
        self.stats["total_files"] = len(target_files)

        logger.info(
            "Analyzing %d files in %s (cache: %s)",
            len(target_files), self.project_root,
            "enabled" if self.use_cache else "disabled",
        )

        results: list[AnalysisResult] = []
        files_to_analyze: list[Path] = []
        file_hashes: dict[Path, str] = {}

        for file_path in target_files:
            if self.cache:
                should_analyze, file_hash = self.cache.should_analyze_file(file_path)
                file_hashes[file_path] = file_hash or ""

                if not should_analyze:
                    cached_result = self.cache.get_cached_result(file_path, file_hash or "")
                    if cached_result:
                        result = AnalysisResult(**cached_result)
                        results.append(result)
                        self.stats["cached_files"] += 1
                        continue

            files_to_analyze.append(file_path)

        for file_path in files_to_analyze:
            try:
                language = self.config["supported_languages"].get(file_path.suffix.lower())
                if not language:
                    continue

                content = file_path.read_text(encoding="utf-8")
                result = self.engine.analyze_source(content, language, str(file_path))

                if result.success:
                    results.append(result)
                    self.stats["analyzed_files"] += 1
                    if self.cache and file_path in file_hashes:
                        result_dict = result.to_dict()
                        self.cache.update_cache_entry(file_path, file_hashes[file_path], result_dict)
                else:
                    self.stats["failed_files"] += 1
                    results.append(result)
            except (OSError, UnicodeDecodeError) as e:
                logger.warning("Failed to analyze %s: %s", file_path, e)
                self.stats["failed_files"] += 1
                results.append(
                    AnalysisResult(success=False, error=str(e), file_path=str(file_path))
                )

        if self.cache and files_to_analyze:
            self._save_analysis_cache(files_to_analyze, results, file_hashes)

        elapsed = (datetime.now() - start_time).total_seconds()
        logger.info(
            "Analysis complete: %d files, %d analyzed, %d cached, %d failed, %.2fs elapsed",
            self.stats["total_files"], self.stats["analyzed_files"],
            self.stats["cached_files"], self.stats["failed_files"], elapsed,
        )

        if self.cache:
            logger.info("Cache file: %s", self.cache.cache_file)

        return {
            "files": {r.data.get("file_path", "unknown"): r.to_dict() for r in results},
            "stats": self.stats.copy(),
            "cache_info": (
                {
                    "enabled": self.use_cache,
                    "cache_file": str(self.cache.cache_file) if self.cache else None,
                    "cache_hits": self.stats["cached_files"],
                    "cache_misses": self.stats["analyzed_files"],
                }
                if self.use_cache
                else None
            ),
        }

    def _save_analysis_cache(
        self, files_to_analyze: list[Path], results: list,
        file_hashes: dict[Path, str],
    ) -> None:
        """分析結果をキャッシュに保存する。"""
        cache_entries: dict[str, dict] = {}
        for file_path, file_hash in file_hashes.items():
            if file_hash:
                try:
                    rel_path = str(file_path.relative_to(self.project_root))
                    cached_result = self.cache.get_cached_result(file_path, file_hash)
                    if cached_result:
                        cache_entries[rel_path] = {"hash": file_hash, "result": cached_result}
                except ValueError:
                    pass

        for result in results:
            if result.success and result.data.get("file_path"):
                result_file_path = Path(result.data["file_path"])
                file_hash = file_hashes.get(result_file_path)
                if file_hash:
                    try:
                        rel_path = str(result_file_path.relative_to(self.project_root))
                        cache_entries[rel_path] = {"hash": file_hash, "result": result.to_dict()}
                    except ValueError:
                        pass

        self.cache.save_cache(cache_entries)


# --- Legacy compatibility interface ---

def check_tree_sitter_availability():
    if not TREE_SITTER_AVAILABLE:
        return False, "Missing: pip install tree-sitter tree-sitter-language-pack"
    return True, "Tree-sitter ready"


def print_syntax_tree(source_code, language="python"):
    engine = TreeSitterEngine()
    if not engine.setup_parsers([language]):
        return {"error": "Setup failed", "success": False}
    result = engine.analyze_source(source_code, language)
    return result.to_dict()


def analyze_python_file(file_path):
    path_obj = Path(file_path)
    if not path_obj.exists():
        return {"error": f"File not found: {file_path}", "success": False}
    try:
        content = path_obj.read_text(encoding="utf-8")
        return print_syntax_tree(content, "python")
    except (OSError, UnicodeDecodeError) as e:
        return {"error": f"Failed to read file: {e}", "success": False}


# --- Re-exports for backward compatibility ---
__all__ = [
    "UnifiedAnalyzer",
    "AnalysisResult",
    "AnalyzerCache",
    "TreeSitterEngine",
    "CONFIG",
    "TREE_SITTER_AVAILABLE",
    "check_tree_sitter_availability",
    "print_syntax_tree",
    "analyze_python_file",
]
