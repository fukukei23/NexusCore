#!/usr/bin/env python3
# ==============================================================================
# ファイル名: advanced_semantic_analyzer.py
# 機能: セマンティッククエリ統合版Tree-sitter解析ツール
# バージョン: 2.2.0 (最適化・統合版)
# 依存関係: pip install tree-sitter tree-sitter-language-pack tqdm colorama
# ==============================================================================

import argparse
import hashlib
import json
import logging
import os
import sys
import time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from concurrent.futures import TimeoutError as FutureTimeoutError
from datetime import datetime
from pathlib import Path
from typing import Any

# サードパーティライブラリ
try:
    from colorama import Fore, Style, init
    from tqdm import tqdm

    init(autoreset=True)
    HAS_EXTRAS = True
except ImportError:
    HAS_EXTRAS = False

    class Fore:  # type: ignore[no-redef]
        RED = GREEN = YELLOW = BLUE = MAGENTA = CYAN = WHITE = ""

    class Style:  # type: ignore[no-redef]
        BRIGHT = RESET_ALL = ""


# Tree-sitter（修正版）
try:
    from tree_sitter import Node, Parser
    from tree_sitter_language_pack import get_language, get_parser

    TREE_SITTER_AVAILABLE = True
except ImportError:
    TREE_SITTER_AVAILABLE = False
    Parser = Node = None

# ==============================================================================
# グローバル設定
# ==============================================================================

# 環境変数から設定を読み込み
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
    "enable_profiling": os.getenv("NEXUS_TREESITTER_ENABLE_PROFILING", "0").lower()
    in ("1", "true", "yes"),
}

logger = logging.getLogger(__name__)

# ==============================================================================
# メインクラス
# ==============================================================================


class AnalysisResult:
    """解析結果データクラス"""

    def __init__(self, success: bool = False, **kwargs):
        self.success = success
        self.timestamp = datetime.now().isoformat()
        self.data = kwargs

    def __getitem__(self, key):
        return self.data.get(key)

    def to_dict(self):
        return {"success": self.success, "timestamp": self.timestamp, **self.data}

    def to_json(self, indent=2):
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)


class SemanticAnalyzer:
    """
    セマンティッククエリ統合版解析器

    最適化機能:
    - キャッシュ: ファイル内容のハッシュベースキャッシュ（プロセス内）
    - 並列処理: ThreadPoolExecutor による並列解析（環境変数 NEXUS_TREESITTER_MAX_WORKERS で制御）
    - タイムアウト: ファイル単位のタイムアウト（環境変数 NEXUS_TREESITTER_TIMEOUT_SEC で制御）
    - プロファイリング: 解析時間の統計（環境変数 NEXUS_TREESITTER_ENABLE_PROFILING で有効化）
    """

    def __init__(self, enable_cache: bool | None = None):
        """
        Args:
            enable_cache: キャッシュを有効にするか（None の場合は CONFIG から読み込み）
        """
        self.parsers: dict[str, Any] = {}
        self.languages: dict[str, Any] = {}
        # TODO: キャッシュ機能 - ファイルパス × 内容ハッシュをキーに解析結果をキャッシュ
        self._cache_enabled = enable_cache if enable_cache is not None else CONFIG["enable_cache"]
        self._cache: dict[str, AnalysisResult] = {}
        # TODO: プロファイリング統計 - 解析時間の集計
        self._profiling_stats: dict[str, Any] = {
            "total_files": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "total_time": 0.0,
            "file_times": [],
        }

    def check_availability(self) -> tuple[bool, str]:
        """利用可能性チェック"""
        if not TREE_SITTER_AVAILABLE:
            return False, "Missing: pip install tree-sitter tree-sitter-language-pack"
        try:
            get_parser("python")
            return True, "Tree-sitter ready"
        except Exception as e:
            return False, f"Setup error: {e}"

    def setup_parsers(self, languages: list[str] | None = None) -> bool:
        """パーサーセットアップ"""
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
            except Exception as e:
                logger.warning(f"Failed to load {lang}: {e}")

        logger.info(f"Loaded parsers: {list(self.parsers.keys())}")
        return len(self.parsers) > 0

    def _extract_symbols(self, language: str, root_node: Node) -> dict[str, list[dict]]:
        """★★★ セマンティッククエリでシンボル抽出 ★★★"""

        # 言語別のS式クエリ定義
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
                    # 重複除去
                    if not any(s["name"] == symbol_name for s in symbols[symbol_type]):
                        symbols[symbol_type].append(
                            {
                                "name": symbol_name,
                                "line": node.start_point[0] + 1,
                                "column": node.start_point[1] + 1,
                            }
                        )
            except Exception as e:
                logger.debug(f"Query failed for {symbol_type}: {e}")

        return dict(symbols)

    def _compute_content_hash(self, source_code: str) -> str:
        """ファイル内容のハッシュを計算"""
        return hashlib.sha256(source_code.encode("utf-8")).hexdigest()

    def _get_cache_key(self, file_path: str, content_hash: str) -> str:
        """キャッシュキーを生成"""
        return f"{file_path}:{content_hash}"

    def analyze_source_code(
        self, source_code: str, language: str, file_path: str | None = None
    ) -> AnalysisResult:
        """
        ソースコード解析（セマンティック機能付き）

        TODO: ボトルネック候補
        - Tree-sitter の parse() 呼び出し（I/O バウンド）
        - _extract_symbols() のクエリ実行（計算バウンド）
        """
        if language not in self.parsers:
            return AnalysisResult(
                success=False, error=f"Parser not available: {language}", file_path=file_path
            )

        # TODO: キャッシュチェック - 同じファイル内容ならキャッシュから返す
        cache_key = None
        if self._cache_enabled and file_path:
            content_hash = self._compute_content_hash(source_code)
            cache_key = self._get_cache_key(file_path, content_hash)
            if cache_key in self._cache:
                self._profiling_stats["cache_hits"] += 1
                logger.debug(f"Cache hit: {file_path}")
                return self._cache[cache_key]
            self._profiling_stats["cache_misses"] += 1

        try:
            start_time = time.time()

            # TODO: 構文解析 - Tree-sitter の parse() がボトルネックになる可能性
            parser = self.parsers[language]
            tree = parser.parse(bytes(source_code, "utf8"))
            root_node = tree.root_node

            # エラーチェック
            has_errors = root_node.has_error

            # TODO: セマンティック解析 - クエリ実行が計算バウンド
            symbols = self._extract_symbols(language, root_node)

            # 基本統計
            lines = source_code.splitlines()

            analysis_time = time.time() - start_time

            result = AnalysisResult(
                success=True,
                file_path=file_path,
                language=language,
                source_stats={
                    "line_count": len(lines),
                    "character_count": len(source_code),
                    "empty_lines": sum(1 for line in lines if not line.strip()),
                },
                semantic_symbols=symbols,
                errors={"has_syntax_errors": has_errors},
                performance={"analysis_time": round(analysis_time, 4)},
            )

            # TODO: キャッシュ保存 - 成功した解析結果をキャッシュに保存
            if self._cache_enabled and cache_key:
                self._cache[cache_key] = result

            # TODO: プロファイリング統計 - 解析時間を記録
            if CONFIG["enable_profiling"]:
                self._profiling_stats["file_times"].append(analysis_time)
                self._profiling_stats["total_time"] += analysis_time

            return result

        except Exception as e:
            logger.warning(f"Analysis failed for {file_path}: {e}")
            return AnalysisResult(
                success=False, error=str(e), file_path=file_path, language=language
            )

    def analyze_file(self, file_path: Path) -> AnalysisResult:
        """
        ファイル解析

        TODO: ボトルネック候補
        - ファイル I/O（read_text）
        - 大きなファイルの読み込み時間
        """
        if not file_path.is_file():
            return AnalysisResult(success=False, error=f"File not found: {file_path}")

        language = CONFIG["supported_languages"].get(file_path.suffix.lower())
        if not language:
            return AnalysisResult(success=False, error=f"Unsupported: {file_path.suffix}")

        try:
            # TODO: ファイル I/O - 大きなファイルで時間がかかる可能性
            content = file_path.read_text(encoding="utf-8")
            return self.analyze_source_code(content, language, str(file_path))
        except Exception as e:
            logger.warning(f"File read error for {file_path}: {e}")
            return AnalysisResult(success=False, error=f"Read error: {e}")

    def analyze_project(self, project_path: Path) -> dict[str, AnalysisResult]:
        """
        プロジェクト解析

        TODO: ボトルネック候補
        - ファイルリスト取得（rglob）
        - 並列処理のオーバーヘッド
        - タイムアウト処理
        """
        start_time = time.time()
        exclude_patterns = ["**/node_modules/**", "**/.git/**", "**/build/**"]

        # TODO: ファイルリスト取得 - 大量ファイルで時間がかかる可能性
        target_files = [
            f
            for ext in CONFIG["supported_languages"]
            for f in project_path.rglob(f"*{ext}")
            if f.is_file() and not any(f.match(p) for p in exclude_patterns)
        ]

        self._profiling_stats["total_files"] = len(target_files)

        if CONFIG["enable_profiling"]:
            logger.info(f"Analyzing {len(target_files)} files with {CONFIG['max_workers']} workers")

        results = {}
        progress = tqdm(target_files, desc="Analyzing", disable=not HAS_EXTRAS)

        # TODO: 並列処理 - ThreadPoolExecutor のオーバーヘッドとワーカー数の最適化
        with ThreadPoolExecutor(max_workers=CONFIG["max_workers"]) as executor:
            future_to_file = {executor.submit(self.analyze_file, f): f for f in target_files}

            for future in as_completed(future_to_file):
                file_path = future_to_file[future]
                try:
                    # TODO: タイムアウト処理 - 1ファイルあたりのタイムアウトを設定
                    results[str(file_path)] = future.result(timeout=CONFIG["timeout_seconds"])
                except FutureTimeoutError:
                    logger.warning(f"Timeout analyzing {file_path} (>{CONFIG['timeout_seconds']}s)")
                    results[str(file_path)] = AnalysisResult(
                        success=False,
                        error=f"Timeout after {CONFIG['timeout_seconds']}s",
                        file_path=str(file_path),
                    )
                except Exception as e:
                    logger.warning(f"Error analyzing {file_path}: {e}")
                    results[str(file_path)] = AnalysisResult(
                        success=False, error=str(e), file_path=str(file_path)
                    )
                progress.update(1)

        progress.close()

        # TODO: プロファイリング統計 - 解析完了後の統計をログ出力
        if CONFIG["enable_profiling"]:
            total_time = time.time() - start_time
            avg_time = total_time / len(target_files) if target_files else 0
            cache_hit_rate = (
                self._profiling_stats["cache_hits"]
                / (self._profiling_stats["cache_hits"] + self._profiling_stats["cache_misses"])
                if (self._profiling_stats["cache_hits"] + self._profiling_stats["cache_misses"]) > 0
                else 0
            )
            logger.info(
                f"Analysis complete: {len(target_files)} files, "
                f"{total_time:.2f}s total, {avg_time:.4f}s avg/file, "
                f"cache hit rate: {cache_hit_rate:.1%}"
            )

        return results

    def get_profiling_stats(self) -> dict[str, Any]:
        """プロファイリング統計を取得"""
        stats = self._profiling_stats.copy()
        if stats["file_times"]:
            stats["avg_file_time"] = sum(stats["file_times"]) / len(stats["file_times"])
            stats["min_file_time"] = min(stats["file_times"])
            stats["max_file_time"] = max(stats["file_times"])
        return stats

    def clear_cache(self):
        """キャッシュをクリア"""
        self._cache.clear()
        logger.debug("Cache cleared")


# ==============================================================================
# レポート生成
# ==============================================================================


class ReportGenerator:
    @staticmethod
    def generate_summary(results: dict[str, AnalysisResult]) -> dict[str, Any]:
        successful = [r for r in results.values() if r.success]

        # ★★★ セマンティック統計 ★★★
        symbol_stats: Counter[str] = Counter()
        for result in successful:
            if symbols := result["semantic_symbols"]:
                for symbol_type, symbol_list in symbols.items():
                    symbol_stats[symbol_type] += len(symbol_list)

        return {
            "overview": {
                "total_files": len(results),
                "successful": len(successful),
                "total_lines": sum(r["source_stats"]["line_count"] for r in successful),
            },
            "languages": Counter(r["language"] for r in successful),
            "symbols": dict(symbol_stats),
            "errors": sum(1 for r in successful if r["errors"]["has_syntax_errors"]),
        }

    @staticmethod
    def print_report(summary: dict[str, Any]):
        print(f"\n{Fore.CYAN}{Style.BRIGHT}=== SEMANTIC ANALYSIS REPORT ==={Style.RESET_ALL}")

        o = summary["overview"]
        print(f"\n{Fore.GREEN}📊 Overview:")
        print(f"  • Files: {Fore.WHITE}{o['total_files']} ({o['successful']} analyzed)")
        print(f"  • Lines: {Fore.WHITE}{o['total_lines']:,}")

        print(f"\n{Fore.BLUE}🔤 Languages:")
        for lang, count in summary["languages"].items():
            print(f"  • {lang.title()}: {Fore.WHITE}{count} files")

        # ★★★ セマンティック情報表示 ★★★
        if summary["symbols"]:
            print(f"\n{Fore.MAGENTA}🧬 Discovered Symbols:")
            for symbol_type, count in summary["symbols"].items():
                print(f"  • {symbol_type.title()}: {Fore.WHITE}{count}")

        if summary["errors"] > 0:
            print(f"\n{Fore.RED}⚠️  Syntax Errors: {Fore.WHITE}{summary['errors']} files")


# ==============================================================================
# CLI
# ==============================================================================


def main():
    parser = argparse.ArgumentParser(description="Semantic Code Analyzer v2.2.0")
    parser.add_argument("target", help="File or directory to analyze")
    parser.add_argument("--output", help="JSON output file")
    parser.add_argument("--verbose", "-v", action="store_true")

    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)

    analyzer = SemanticAnalyzer()
    if not analyzer.setup_parsers():
        print(f"{Fore.RED}❌ Parser setup failed")
        return 1

    target = Path(args.target)

    if target.is_file():
        result = analyzer.analyze_file(target)
        print(result.to_json())
    elif target.is_dir():
        results = analyzer.analyze_project(target)
        summary = ReportGenerator.generate_summary(results)
        ReportGenerator.print_report(summary)

        if args.output:
            Path(args.output).write_text(
                json.dumps(
                    {"summary": summary, "details": {k: v.to_dict() for k, v in results.items()}},
                    indent=2,
                    ensure_ascii=False,
                )
            )
            print(f"\n{Fore.GREEN}✅ Saved to {args.output}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
