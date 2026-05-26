import hashlib
import logging
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from concurrent.futures import TimeoutError as FutureTimeoutError
from pathlib import Path
from typing import Any

from nexuscore.analyzer.unified_analyzer import AnalysisResult
from nexuscore.utils.tree_sitter import _config as _cfg

CONFIG = _cfg.CONFIG
HAS_EXTRAS = _cfg.HAS_EXTRAS

if HAS_EXTRAS:
    from tqdm import tqdm
else:
    tqdm = None

if _cfg.TREE_SITTER_AVAILABLE:
    from tree_sitter_language_pack import get_language, get_parser

logger = logging.getLogger(__name__)


class SemanticAnalyzer:
    """
    セマンティッククエリ統合版解析器

    最適化機能:
    - キャッシュ: ファイル内容のハッシュベースキャッシュ（プロセス内）
    - 並列処理: ThreadPoolExecutor による並列解析
    - タイムアウト: ファイル単位のタイムアウト
    - プロファイリング: 解析時間の統計
    """

    def __init__(self, enable_cache: bool | None = None):
        self.parsers: dict[str, Any] = {}
        self.languages: dict[str, Any] = {}
        self._cache_enabled = enable_cache if enable_cache is not None else CONFIG["enable_cache"]
        self._cache: dict[str, AnalysisResult] = {}
        self._profiling_stats: dict[str, Any] = {
            "total_files": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "total_time": 0.0,
            "file_times": [],
        }

    def check_availability(self) -> tuple[bool, str]:
        if not _cfg.TREE_SITTER_AVAILABLE:
            return False, "Missing: pip install tree-sitter tree-sitter-language-pack"
        try:
            get_parser("python")
            return True, "Tree-sitter ready"
        except Exception as e:  # noqa: BLE001 — tree-sitter native library errors
            return False, f"Setup error: {e}"

    def setup_parsers(self, languages: list[str] | None = None) -> bool:
        if not languages:
            languages = list(set(CONFIG["supported_languages"].values()))

        available, message = self.check_availability()
        if not available:
            logger.error(message)
            return False

        for lang in languages:
            try:
                self.languages[lang] = get_language(lang)
                self.parsers[lang] = get_parser(lang)
            except Exception as e:  # noqa: BLE001 — tree-sitter native library errors
                logger.warning("Failed to load %s: %s", lang, e)

        logger.info("Loaded parsers: %s", list(self.parsers.keys()))
        return len(self.parsers) > 0

    def _extract_symbols(self, language: str, root_node) -> dict[str, list[dict]]:
        queries = {
            "python": {
                "functions": "(function_definition name: (identifier) @name)",
                "classes": "(class_definition name: (identifier) @name)",
                "imports": "(import_statement name: (dotted_name) @name)",
                "variables": "(assignment left: (identifier) @name)",
            },
            "javascript": {
                "functions": "[(function_declaration name: (identifier) @name) (arrow_function)]",
                "classes": "(class_declaration name: (identifier) @name)",
                "imports": "(import_statement source: (string) @name)",
            },
            "go": {
                "functions": "(function_declaration name: (identifier) @name)",
                "types": "(type_declaration (type_spec name: (type_identifier) @name))",
                "packages": "(package_clause (package_identifier) @name)",
            },
            "rust": {
                "functions": "(function_item name: (identifier) @name)",
                "structs": "(struct_item name: (type_identifier) @name)",
                "impls": "(impl_item type: (type_identifier) @name)",
            },
        }

        lang_queries = queries.get(language, {})
        if not lang_queries:
            return {}

        symbols: dict[str, list[dict]] = defaultdict(list)
        language_obj = self.languages[language]

        for symbol_type, query_string in lang_queries.items():
            try:
                query = language_obj.query(query_string)
                captures = query.captures(root_node)

                for node, _capture_name in captures:
                    symbol_name = node.text.decode("utf8")
                    if not any(s["name"] == symbol_name for s in symbols[symbol_type]):
                        symbols[symbol_type].append(
                            {"name": symbol_name, "line": node.start_point[0] + 1, "column": node.start_point[1] + 1}
                        )
            except Exception as e:  # noqa: BLE001 — tree-sitter query API errors
                logger.debug("Query failed for %s: %s", symbol_type, e)

        return dict(symbols)

    def _compute_content_hash(self, source_code: str) -> str:
        return hashlib.sha256(source_code.encode("utf-8")).hexdigest()

    def _get_cache_key(self, file_path: str, content_hash: str) -> str:
        return f"{file_path}:{content_hash}"

    def analyze_source_code(self, source_code: str, language: str, file_path: str | None = None) -> AnalysisResult:
        if language not in self.parsers:
            return AnalysisResult(success=False, error=f"Parser not available: {language}", file_path=file_path)

        cache_key = None
        if self._cache_enabled and file_path:
            content_hash = self._compute_content_hash(source_code)
            cache_key = self._get_cache_key(file_path, content_hash)
            if cache_key in self._cache:
                self._profiling_stats["cache_hits"] += 1
                logger.debug("Cache hit: %s", file_path)
                return self._cache[cache_key]
            self._profiling_stats["cache_misses"] += 1

        try:
            start_time = time.time()
            parser = self.parsers[language]
            tree = parser.parse(bytes(source_code, "utf8"))
            root_node = tree.root_node
            has_errors = root_node.has_error
            symbols = self._extract_symbols(language, root_node)
            lines = source_code.splitlines()
            analysis_time = time.time() - start_time

            result = AnalysisResult(
                success=True,
                file_path=file_path,
                language=language,
                source_stats={"line_count": len(lines), "character_count": len(source_code),
                              "empty_lines": sum(1 for line in lines if not line.strip())},
                semantic_symbols=symbols,
                errors={"has_syntax_errors": has_errors},
                performance={"analysis_time": round(analysis_time, 4)},
            )

            if self._cache_enabled and cache_key:
                self._cache[cache_key] = result

            if CONFIG["enable_profiling"]:
                self._profiling_stats["file_times"].append(analysis_time)
                self._profiling_stats["total_time"] += analysis_time

            return result
        except Exception as e:  # noqa: BLE001 — tree-sitter parse errors
            logger.warning("Analysis failed for %s: %s", file_path, e)
            return AnalysisResult(success=False, error=str(e), file_path=file_path, language=language)

    def analyze_file(self, file_path: Path) -> AnalysisResult:
        if not file_path.is_file():
            return AnalysisResult(success=False, error=f"File not found: {file_path}")
        language = CONFIG["supported_languages"].get(file_path.suffix.lower())
        if not language:
            return AnalysisResult(success=False, error=f"Unsupported: {file_path.suffix}")
        try:
            content = file_path.read_text(encoding="utf-8")
            return self.analyze_source_code(content, language, str(file_path))
        except (OSError, UnicodeDecodeError, RuntimeError) as e:
            logger.warning("File read error for %s: %s", file_path, e)
            return AnalysisResult(success=False, error=f"Read error: {e}")

    def analyze_project(self, project_path: Path) -> dict[str, AnalysisResult]:
        start_time = time.time()
        exclude_patterns = ["**/node_modules/**", "**/.git/**", "**/build/**"]

        target_files = [
            f for ext in CONFIG["supported_languages"]
            for f in project_path.rglob(f"*{ext}")
            if f.is_file() and not any(f.match(p) for p in exclude_patterns)
        ]

        self._profiling_stats["total_files"] = len(target_files)

        if CONFIG["enable_profiling"]:
            logger.info("Analyzing %d files with %d workers", len(target_files), CONFIG["max_workers"])

        results = {}
        progress = tqdm(target_files, desc="Analyzing", disable=not HAS_EXTRAS) if HAS_EXTRAS else target_files

        with ThreadPoolExecutor(max_workers=CONFIG["max_workers"]) as executor:
            future_to_file = {executor.submit(self.analyze_file, f): f for f in target_files}

            for future in as_completed(future_to_file):
                file_path = future_to_file[future]
                try:
                    results[str(file_path)] = future.result(timeout=CONFIG["timeout_seconds"])
                except FutureTimeoutError:
                    logger.warning("Timeout analyzing %s (>%ds)", file_path, CONFIG["timeout_seconds"])
                    results[str(file_path)] = AnalysisResult(
                        success=False, error=f"Timeout after {CONFIG['timeout_seconds']}s", file_path=str(file_path),
                    )
                except Exception as e:  # noqa: BLE001 — concurrent worker errors
                    logger.warning("Error analyzing %s: %s", file_path, e)
                    results[str(file_path)] = AnalysisResult(success=False, error=str(e), file_path=str(file_path))
                if HAS_EXTRAS:
                    progress.update(1)  # type: ignore[union-attr]

        if HAS_EXTRAS:
            progress.close()  # type: ignore[union-attr]

        if CONFIG["enable_profiling"]:
            total_time = time.time() - start_time
            avg_time = total_time / len(target_files) if target_files else 0
            hits = self._profiling_stats["cache_hits"]
            misses = self._profiling_stats["cache_misses"]
            cache_hit_rate = hits / (hits + misses) if (hits + misses) > 0 else 0
            logger.info(
                "Analysis complete: %d files, %.2fs total, %.4fs avg/file, cache hit rate: %.1%%",
                len(target_files), total_time, avg_time, cache_hit_rate,
            )

        return results

    def get_profiling_stats(self) -> dict[str, Any]:
        stats = self._profiling_stats.copy()
        if stats["file_times"]:
            stats["avg_file_time"] = sum(stats["file_times"]) / len(stats["file_times"])
            stats["min_file_time"] = min(stats["file_times"])
            stats["max_file_time"] = max(stats["file_times"])
        return stats

    def clear_cache(self):
        self._cache.clear()
        logger.debug("Cache cleared")
