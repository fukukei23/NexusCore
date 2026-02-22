#!/usr/bin/env python3
# ==============================================================================
# ファイル名: src/nexuscore/analyzer/unified_analyzer.py
# 機能: Tree-sitterによる完全な構文解析とセマンティック解析（フル機能版）
# バージョン: 5.4.0 (統合・最終安定版)
# 作成日: 2025-08-04
# ==============================================================================

import hashlib
import json
import logging
import os
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

# --- サードパーティライブラリ ---
try:
    from tqdm import tqdm

    HAS_TQDM = True
except ImportError:
    HAS_TQDM = False

try:
    from colorama import Fore, Style, init

    init(autoreset=True)
    HAS_COLORAMA = True
except ImportError:
    HAS_COLORAMA = False

    class Fore:
        RED = GREEN = YELLOW = BLUE = MAGENTA = CYAN = WHITE = ""

    class Style:
        BRIGHT = RESET_ALL = ""


try:
    import speech_recognition as sr

    HAS_SPEECH = True
except ImportError:
    HAS_SPEECH = False

try:
    from tree_sitter import Node, Query
    from tree_sitter_language_pack import get_language, get_parser

    TREE_SITTER_AVAILABLE = True
except ImportError:
    Node = Query = None
    TREE_SITTER_AVAILABLE = False

# ==============================================================================
# グローバル設定とロギング
# ==============================================================================
CONFIG = {
    "cache_dir": Path.home() / ".nexuscore" / "cache",
    "log_level": logging.INFO,
    "supported_languages": {
        ".py": "python",
        ".js": "javascript",
    },
    "cache_version": 1,  # キャッシュフォーマットのバージョン（schema_version として使用）
    "analyzer_version": "0.1.0",  # アナライザーのバージョン
    # 環境変数によるキャッシュ制御
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


def setup_logging(log_level=logging.INFO):
    """CONFIG の log_level を用いたシンプルなロガー初期化ヘルパー。"""
    logging.basicConfig(
        level=log_level, format="%(asctime)s - %(levelname)s - %(message)s", stream=sys.stdout
    )
    return logging.getLogger("NexusCoreAnalyzer")


logger = setup_logging(CONFIG["log_level"])

# ==============================================================================
# コア機能クラス
# ==============================================================================


class AnalysisResult:
    def __init__(self, success: bool = False, **kwargs):
        self.success = success
        self.timestamp = datetime.now().isoformat()
        self.data = kwargs

    def __getitem__(self, key):
        return self.data.get(key)

    def to_dict(self) -> dict[str, Any]:
        return {"success": self.success, "timestamp": self.timestamp, **self.data}

    def to_json(self, indent=2) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)


class TreeSitterEngine:
    """Tree-sitterベースのコア解析エンジン"""

    def __init__(self, config: dict[str, Any] = None):
        self.config = {**CONFIG, **(config or {})}
        self.parsers = {}
        self.languages = {}
        self.cache_dir = self.config.get("cache_dir", Path("./cache"))
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def setup_parsers(self, languages: list[str] = None) -> bool:
        if not TREE_SITTER_AVAILABLE:
            return False
        languages_to_load = languages or list(set(self.config["supported_languages"].values()))
        for lang in languages_to_load:
            try:
                if lang not in self.parsers:
                    self.languages[lang] = get_language(lang)
                    self.parsers[lang] = get_parser(lang)
            except Exception as e:
                logger.warning(f"Failed to load parser for {lang}: {e}")
        return len(self.parsers) > 0

    def analyze_source(
        self, source_code: str, language: str, file_path: str = None
    ) -> AnalysisResult:
        if language not in self.parsers:
            return AnalysisResult(success=False, error=f"Parser not available for '{language}'")
        try:
            parser = self.parsers[language]
            tree = parser.parse(bytes(source_code, "utf8"))
            root_node = tree.root_node
            semantic_info = self._extract_semantic_info(language, root_node)
            return AnalysisResult(
                success=not root_node.has_error,
                file_path=file_path,
                language=language,
                semantic_info=semantic_info,
                errors={"has_syntax_errors": root_node.has_error},
            )
        except Exception as e:
            return AnalysisResult(success=False, error=str(e), file_path=file_path)

    def _extract_semantic_info(self, language: str, root_node: Node) -> dict[str, Any]:
        """マルチキャプチャ・クエリと手動探索フォールバックを組み合わせた解析ロジック。

        Query 失敗時（言語 pack 不整合やクエリ構文エラーなど）は manual パスにフォールバックする。
        """
        info = defaultdict(list)

        query_string = """
            (function_definition name: (identifier) @function.name) @function.definition
            (class_definition name: (identifier) @class.name) @class.definition
            (call function: (identifier) @call.name) @call.expression
            (call function: (attribute attribute: (identifier) @call.name)) @call.expression
        """

        try:
            # メインパス: 効率的なマルチキャプチャ・クエリ
            query = Query(self.languages[language], query_string)
            captures = query.captures(root_node)

            node_to_captures = defaultdict(dict)
            for node, name in captures:
                node_to_captures[node.id][name] = node

            # あなたの優れたロジック: まずクラス定義をすべて特定
            class_names = {
                parts["class.name"].text.decode("utf8")
                for parts in node_to_captures.values()
                if "class.definition" in parts and "class.name" in parts
            }

            for node_id, captured_parts in node_to_captures.items():
                if "function.definition" in captured_parts and "function.name" in captured_parts:
                    info["definitions"].append(
                        {
                            "name": captured_parts["function.name"].text.decode("utf8"),
                            "type": "function",
                            "line": captured_parts["function.definition"].start_point[0] + 1,
                        }
                    )
                elif "class.definition" in captured_parts and "class.name" in captured_parts:
                    info["definitions"].append(
                        {
                            "name": captured_parts["class.name"].text.decode("utf8"),
                            "type": "class",
                            "line": captured_parts["class.definition"].start_point[0] + 1,
                        }
                    )
                elif "call.expression" in captured_parts and "call.name" in captured_parts:
                    call_name = captured_parts["call.name"].text.decode("utf8")
                    # あなたの優れたロジック: クラスのインスタンス化を除外
                    if call_name in class_names:
                        continue
                    call_node = captured_parts["call.expression"]
                    scope_name = self._find_scope_name(call_node)
                    info["calls"].append(
                        {
                            "name": call_name,
                            "type": "call",
                            "line": call_node.start_point[0] + 1,
                            "scope": scope_name,
                        }
                    )
        except Exception as e:
            # フォールバックパス: 堅牢な手動探索。言語 pack 不整合や Query 構文エラーに備える。
            logger.warning(f"Query failed in {language}: {e}. Falling back to manual extraction.")
            self._manual_extract(root_node, info)

        # 統計情報生成機能の統合
        definitions = info.get("definitions", [])
        calls = info.get("calls", [])
        info["statistics"] = {
            "total_definitions": len(definitions),
            "total_calls": len(calls),
            "functions_count": len([d for d in definitions if d["type"] == "function"]),
            "classes_count": len([d for d in definitions if d["type"] == "class"]),
        }

        return dict(info)

    def _find_scope_name(self, node: Node) -> str:
        """指定されたノードの親を辿り、スコープ名を返す"""
        current = node.parent
        while current:
            if current.type in ["function_definition", "class_definition"]:
                name_node = current.child_by_field_name("name")
                if name_node:
                    return name_node.text.decode("utf8")
            current = current.parent
        return "global"

    def _manual_extract(self, node: Node, info: defaultdict):
        """手動での情報抽出（フォールバック用）。info は definitions/calls のリストを持つ dict。"""
        if node.type in ["function_definition", "class_definition"]:
            name_node = node.child_by_field_name("name")
            if name_node:
                info["definitions"].append(
                    {
                        "name": name_node.text.decode("utf8"),
                        "type": node.type,
                        "line": node.start_point[0] + 1,
                    }
                )
        elif node.type == "call":
            func_node = node.child_by_field_name("function")
            if func_node:
                name_node = (
                    func_node
                    if func_node.type == "identifier"
                    else func_node.child_by_field_name("attribute")
                )
                if name_node:
                    class_names = {
                        d["name"] for d in info["definitions"] if d.get("type") == "class"
                    }
                    call_name = name_node.text.decode("utf8")
                    if call_name not in class_names:
                        info["calls"].append(
                            {
                                "name": call_name,
                                "type": "call",
                                "line": node.start_point[0] + 1,
                                "scope": self._find_scope_name(node),
                            }
                        )
        # TODO: 他の構文要素の抽出は必要に応じて拡張する
        for child in node.children:
            self._manual_extract(child, info)


# ==============================================================================
# キャッシュ層
# ==============================================================================


class AnalyzerCache:
    """
    解析結果のキャッシュマネージャー

    プロジェクト単位でキャッシュを管理し、ファイル内容のハッシュベースで
    差分検出を行い、変更のないファイルは再解析をスキップする。
    """

    def __init__(self, project_root: Path, cache_dir: Path | None = None):
        """
        Args:
            project_root: プロジェクトのルートディレクトリ
            cache_dir: キャッシュディレクトリ（None の場合は project_root/.nexuscache）
        """
        self.project_root = Path(project_root).resolve()

        # 環境変数からキャッシュディレクトリを取得（優先順位: 引数 > 環境変数 > デフォルト）
        if cache_dir is None and CONFIG.get("cache_dir_env"):
            cache_dir = Path(CONFIG["cache_dir_env"])

        self.cache_dir = cache_dir or (self.project_root / ".nexuscache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_file = (
            self.cache_dir / "unified_analyzer.json"
        )  # 要件に合わせて unified_analyzer.json に変更
        self.cache_data: dict[str, Any] = {}
        self.cache_version = CONFIG["cache_version"]

    def _compute_file_hash(self, file_path: Path) -> str:
        """ファイル内容のハッシュを計算（sha256: プレフィックス付き）"""
        try:
            content = file_path.read_bytes()
            hash_hex = hashlib.sha256(content).hexdigest()
            return f"sha256:{hash_hex}"  # 要件に合わせて sha256: プレフィックスを付与
        except Exception as e:
            logger.warning(f"Failed to compute hash for {file_path}: {e}")
            return ""

    def load_cache(self) -> bool:
        """
        キャッシュファイルを読み込む

        Returns:
            キャッシュの読み込みに成功したか
        """
        if not self.cache_file.exists():
            logger.debug(f"Cache file not found: {self.cache_file}")
            return False

        try:
            with open(self.cache_file, encoding="utf-8") as f:
                data = json.load(f)

            # バージョンチェック（schema_version または version をチェック）
            schema_version = data.get("schema_version") or data.get("version")
            if schema_version != self.cache_version:
                logger.info(
                    f"Cache version mismatch (expected {self.cache_version}, got {schema_version}). Rebuilding cache."
                )
                return False

            # analyzer_version のチェック（オプション）
            analyzer_version = data.get("analyzer_version")
            expected_version = CONFIG.get("analyzer_version", "0.1.0")
            if analyzer_version and analyzer_version != expected_version:
                logger.info(
                    f"Analyzer version mismatch (expected {expected_version}, got {analyzer_version}). Rebuilding cache."
                )
                return False

            self.cache_data = data
            logger.debug(
                f"Loaded cache from {self.cache_file} ({len(data.get('files', {}))} files)"
            )
            return True
        except Exception as e:
            logger.warning(f"Failed to load cache from {self.cache_file}: {e}")
            return False

    def save_cache(self, file_results: dict[str, dict[str, Any]]):
        """
        キャッシュファイルに保存（atomic rename を使用）

        Args:
            file_results: {file_path: {hash, result, ...}} の形式
        """
        try:
            # 既存のキャッシュデータから created_at を取得（存在する場合）
            created_at = self.cache_data.get("created_at") or datetime.now().isoformat()
            updated_at = datetime.now().isoformat()

            cache_data = {
                "schema_version": self.cache_version,  # 要件に合わせて schema_version に変更
                "analyzer_version": CONFIG.get("analyzer_version", "0.1.0"),
                "created_at": created_at,
                "updated_at": updated_at,
                "project_root": str(self.project_root),
                "files": file_results,
            }

            # atomic rename を使用して保存

            temp_file = self.cache_file.with_suffix(".tmp")

            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(cache_data, f, indent=2, ensure_ascii=False)

            # atomic rename で上書き
            temp_file.replace(self.cache_file)

            # キャッシュデータも更新
            self.cache_data = cache_data

            logger.debug(f"Saved cache to {self.cache_file} ({len(file_results)} files)")
        except Exception as e:
            logger.warning(f"Failed to save cache to {self.cache_file}: {e}")

    def get_cached_result(self, file_path: Path, current_hash: str) -> dict[str, Any] | None:
        """
        キャッシュから結果を取得

        Args:
            file_path: ファイルパス（project_root からの相対パス）
            current_hash: 現在のファイル内容のハッシュ

        Returns:
            キャッシュされた結果（存在する場合）、または None
        """
        if not self.cache_data:
            return None

        # プロジェクトルートからの相対パスに変換
        try:
            rel_path = str(file_path.relative_to(self.project_root))
        except ValueError:
            # プロジェクト外のファイルはキャッシュしない
            return None

        cached_file = self.cache_data.get("files", {}).get(rel_path)
        if not cached_file:
            return None

        # ハッシュが一致するか確認（sha256: プレフィックスを考慮）
        cached_hash = cached_file.get("hash", "")
        # 両方のハッシュからプレフィックスを正規化
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
        """
        ファイルを解析する必要があるか判定

        Args:
            file_path: ファイルパス

        Returns:
            (should_analyze, current_hash) のタプル
        """
        if not file_path.is_file():
            return False, None

        current_hash = self._compute_file_hash(file_path)
        if not current_hash:
            return True, None  # ハッシュ計算失敗時は解析する

        cached_result = self.get_cached_result(file_path, current_hash)
        if cached_result is not None:
            return False, current_hash  # キャッシュヒット

        return True, current_hash  # キャッシュミス、解析が必要

    def update_cache_entry(self, file_path: Path, file_hash: str, result: dict[str, Any]):
        """
        キャッシュエントリを更新（メモリ内）

        Args:
            file_path: ファイルパス
            file_hash: ファイル内容のハッシュ
            result: 解析結果
        """
        try:
            rel_path = str(file_path.relative_to(self.project_root))
        except ValueError:
            return

        if "files" not in self.cache_data:
            self.cache_data["files"] = {}

        self.cache_data["files"][rel_path] = {
            "hash": f"sha256:{file_hash}" if not file_hash.startswith("sha256:") else file_hash,
            "result": result,
            "last_analyzed": datetime.now().isoformat(),  # 要件に合わせて last_analyzed に変更
        }

    def clear_cache(self):
        """キャッシュをクリア"""
        if self.cache_file.exists():
            self.cache_file.unlink()
        self.cache_data = {}
        logger.info(f"Cache cleared: {self.cache_file}")


# ==============================================================================
# UnifiedAnalyzer クラス（プロジェクト全体の解析を統合）
# ==============================================================================


class UnifiedAnalyzer:
    """
    プロジェクト全体の解析を統合するクラス

    キャッシュ機能付きで、変更のないファイルは再解析をスキップする。
    """

    def __init__(self, project_root: Path, use_cache: bool = None, config: dict[str, Any] = None):
        """
        Args:
            project_root: プロジェクトのルートディレクトリ
            use_cache: キャッシュを使用するか（None の場合は CONFIG から読み込み）
            config: 追加の設定
        """
        self.project_root = Path(project_root).resolve()
        self.config = {**CONFIG, **(config or {})}
        self.use_cache = use_cache if use_cache is not None else self.config["enable_cache"]

        self.engine = TreeSitterEngine(self.config)

        # キャッシュディレクトリの決定（環境変数または config から取得）
        cache_dir = None
        if self.use_cache:
            # 環境変数から取得（優先）
            if CONFIG.get("cache_dir_env"):
                cache_dir = Path(CONFIG["cache_dir_env"])
            # config から取得
            elif self.config.get("cache_dir"):
                cache_dir = Path(self.config["cache_dir"])

        self.cache = AnalyzerCache(self.project_root, cache_dir) if self.use_cache else None

        # 統計情報
        self.stats = {"total_files": 0, "cached_files": 0, "analyzed_files": 0, "failed_files": 0}

    def setup(self, languages: list[str] = None) -> bool:
        """パーサーをセットアップ"""
        return self.engine.setup_parsers(languages)

    def _get_target_files(self, exclude_patterns: list[str] = None) -> list[Path]:
        """
        解析対象のファイルリストを取得

        Args:
            exclude_patterns: 除外パターンのリスト

        Returns:
            解析対象ファイルのリスト
        """
        if exclude_patterns is None:
            exclude_patterns = [
                "**/node_modules/**",
                "**/.git/**",
                "**/build/**",
                "**/__pycache__/**",
                "**/.nexuscache/**",
            ]

        target_files = []
        for ext, lang in self.config["supported_languages"].items():
            for file_path in self.project_root.rglob(f"*{ext}"):
                if not file_path.is_file():
                    continue

                # 除外パターンチェック
                if any(file_path.match(p) for p in exclude_patterns):
                    continue

                target_files.append(file_path)

        return target_files

    def run(self, exclude_patterns: list[str] = None) -> dict[str, Any]:
        """
        プロジェクト全体を解析するメインメソッド

        Args:
            exclude_patterns: 除外パターンのリスト

        Returns:
            解析結果の辞書
        """
        start_time = datetime.now()

        # キャッシュを読み込み
        if self.cache:
            self.cache.load_cache()

            # RESET_CACHE 環境変数が設定されている場合はキャッシュをクリア
            if CONFIG.get("reset_cache", False):
                logger.info("RESET_CACHE environment variable is set. Clearing cache.")
                self.cache.clear_cache()

        # 対象ファイルを取得
        target_files = self._get_target_files(exclude_patterns)
        self.stats["total_files"] = len(target_files)

        logger.info(
            f"Analyzing {len(target_files)} files in {self.project_root} (cache: {'enabled' if self.use_cache else 'disabled'})"
        )

        results: list[AnalysisResult] = []
        files_to_analyze: list[Path] = []
        file_hashes: dict[Path, str] = {}

        # 差分検出: 変更のないファイルはキャッシュから取得
        for file_path in target_files:
            if self.cache:
                should_analyze, file_hash = self.cache.should_analyze_file(file_path)
                file_hashes[file_path] = file_hash or ""

                if not should_analyze:
                    # キャッシュから結果を取得
                    cached_result = self.cache.get_cached_result(file_path, file_hash)
                    if cached_result:
                        # AnalysisResult オブジェクトを再構築
                        result = AnalysisResult(**cached_result)
                        results.append(result)
                        self.stats["cached_files"] += 1
                        continue

            files_to_analyze.append(file_path)

        # 変更のあるファイル・新規ファイルを解析
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

                    # キャッシュに保存
                    if self.cache and file_path in file_hashes:
                        result_dict = result.to_dict()
                        self.cache.update_cache_entry(
                            file_path, file_hashes[file_path], result_dict
                        )
                else:
                    self.stats["failed_files"] += 1
                    results.append(result)  # 失敗した結果も含める

            except Exception as e:
                logger.warning(f"Failed to analyze {file_path}: {e}")
                self.stats["failed_files"] += 1
                results.append(
                    AnalysisResult(success=False, error=str(e), file_path=str(file_path))
                )

        # キャッシュを保存
        if self.cache and files_to_analyze:
            # キャッシュデータを構築
            cache_entries = {}
            for file_path, file_hash in file_hashes.items():
                if file_hash:
                    try:
                        rel_path = str(file_path.relative_to(self.project_root))
                        cached_result = self.cache.get_cached_result(file_path, file_hash)
                        if cached_result:
                            cache_entries[rel_path] = {"hash": file_hash, "result": cached_result}
                    except ValueError:
                        pass

            # 新しく解析したファイルを追加
            for result in results:
                if result.success and result.data.get("file_path"):
                    result_file_path = Path(result.data["file_path"])
                    if result_file_path in file_hashes:
                        file_hash = file_hashes[result_file_path]
                        if file_hash:
                            try:
                                rel_path = str(result_file_path.relative_to(self.project_root))
                                cache_entries[rel_path] = {
                                    "hash": file_hash,
                                    "result": result.to_dict(),
                                }
                            except ValueError:
                                pass

            self.cache.save_cache(cache_entries)

        # 統計情報をログ出力
        elapsed = (datetime.now() - start_time).total_seconds()
        logger.info(
            f"Analysis complete: {self.stats['total_files']} files, "
            f"{self.stats['analyzed_files']} analyzed, {self.stats['cached_files']} cached, "
            f"{self.stats['failed_files']} failed, {elapsed:.2f}s elapsed"
        )

        if self.cache:
            logger.info(f"Cache file: {self.cache.cache_file}")

        # 結果を返す
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


# ==============================================================================
# 下位互換性インターフェースとCLI
# ==============================================================================


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
    except Exception as e:
        return {"error": f"Failed to read file: {e}", "success": False}


if __name__ == "__main__":
    # このモジュールはライブラリ利用を想定。CLI は別エントリポイント推奨。
    print("This module is intended to be used as a library. For CLI, use the main entry point.")
