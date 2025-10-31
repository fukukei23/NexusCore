#!/usr/bin/env python3
# ==============================================================================
# ファイル名: src/nexuscore/analyzer/unified_analyzer.py
# 機能: Tree-sitterによる完全な構文解析とセマンティック解析（フル機能版）
# バージョン: 5.4.0 (統合・最終安定版)
# 作成日: 2025-08-04
# ==============================================================================

import os
import sys
import json
import logging
import argparse
from pathlib import Path
from typing import Dict, List, Any
from collections import Counter, defaultdict
from datetime import datetime

# --- サードパーティライブラリ ---
try:
    from tqdm import tqdm
    HAS_TQDM = True
except ImportError:
    HAS_TQDM = False

try:
    from colorama import init, Fore, Style
    init(autoreset=True)
    HAS_COLORAMA = True
except ImportError:
    HAS_COLORAMA = False
    class Fore: RED = GREEN = YELLOW = BLUE = MAGENTA = CYAN = WHITE = ""
    class Style: BRIGHT = RESET_ALL = ""

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
    'cache_dir': Path.home() / ".nexuscore" / "cache",
    'log_level': logging.INFO,
    'supported_languages': { '.py': 'python', '.js': 'javascript', }
}
def setup_logging(log_level=logging.INFO):
    logging.basicConfig(level=log_level, format='%(asctime)s - %(levelname)s - %(message)s', stream=sys.stdout)
    return logging.getLogger("NexusCoreAnalyzer")
logger = setup_logging(CONFIG['log_level'])

# ==============================================================================
# コア機能クラス
# ==============================================================================

class AnalysisResult:
    def __init__(self, success: bool = False, **kwargs):
        self.success = success; self.timestamp = datetime.now().isoformat(); self.data = kwargs
    def __getitem__(self, key): return self.data.get(key)
    def to_dict(self) -> Dict[str, Any]: return {'success': self.success, 'timestamp': self.timestamp, **self.data}
    def to_json(self, indent=2) -> str: return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

class TreeSitterEngine:
    """Tree-sitterベースのコア解析エンジン"""
    def __init__(self, config: Dict[str, Any] = None):
        self.config = {**CONFIG, **(config or {})}
        self.parsers = {}
        self.languages = {}
        self.cache_dir = self.config.get('cache_dir', Path('./cache'))
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def setup_parsers(self, languages: List[str] = None) -> bool:
        if not TREE_SITTER_AVAILABLE: return False
        languages_to_load = languages or list(set(self.config['supported_languages'].values()))
        for lang in languages_to_load:
            try:
                if lang not in self.parsers:
                    self.languages[lang] = get_language(lang)
                    self.parsers[lang] = get_parser(lang)
            except Exception as e:
                logger.warning(f"Failed to load parser for {lang}: {e}")
        return len(self.parsers) > 0

    def analyze_source(self, source_code: str, language: str, file_path: str = None) -> AnalysisResult:
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
                errors={'has_syntax_errors': root_node.has_error}
            )
        except Exception as e:
            return AnalysisResult(success=False, error=str(e), file_path=file_path)

    def _extract_semantic_info(self, language: str, root_node: Node) -> Dict[str, Any]:
        """マルチキャプチャ・クエリと手動探索フォールバックを組み合わせた最終版ロジック"""
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
                parts['class.name'].text.decode('utf8')
                for parts in node_to_captures.values()
                if 'class.definition' in parts and 'class.name' in parts
            }

            for node_id, captured_parts in node_to_captures.items():
                if 'function.definition' in captured_parts and 'function.name' in captured_parts:
                    info['definitions'].append({'name': captured_parts['function.name'].text.decode('utf8'), 'type': 'function', 'line': captured_parts['function.definition'].start_point[0] + 1})
                elif 'class.definition' in captured_parts and 'class.name' in captured_parts:
                     info['definitions'].append({'name': captured_parts['class.name'].text.decode('utf8'), 'type': 'class', 'line': captured_parts['class.definition'].start_point[0] + 1})
                elif 'call.expression' in captured_parts and 'call.name' in captured_parts:
                    call_name = captured_parts['call.name'].text.decode('utf8')
                    # あなたの優れたロジック: クラスのインスタンス化を除外
                    if call_name in class_names:
                        continue
                    call_node = captured_parts['call.expression']
                    scope_name = self._find_scope_name(call_node)
                    info['calls'].append({'name': call_name, 'type': 'call', 'line': call_node.start_point[0] + 1, 'scope': scope_name})
        except Exception as e:
            # フォールバックパス: 堅牢な手動探索
            logger.warning(f"Query failed in {language}: {e}. Falling back to manual extraction.")
            self._manual_extract(root_node, info)
            
        # 統計情報生成機能の統合
        definitions = info.get('definitions', [])
        calls = info.get('calls', [])
        info['statistics'] = {
            'total_definitions': len(definitions),
            'total_calls': len(calls),
            'functions_count': len([d for d in definitions if d['type'] == 'function']),
            'classes_count': len([d for d in definitions if d['type'] == 'class'])
        }

        return dict(info)

    def _find_scope_name(self, node: Node) -> str:
        """指定されたノードの親を辿り、スコープ名を返す"""
        current = node.parent
        while current:
            if current.type in ['function_definition', 'class_definition']:
                name_node = current.child_by_field_name('name')
                if name_node:
                    return name_node.text.decode('utf8')
            current = current.parent
        return "global"

    def _manual_extract(self, node: Node, info: defaultdict):
        """手動での情報抽出（フォールバック用）"""
        if node.type in ['function_definition', 'class_definition']:
            name_node = node.child_by_field_name('name')
            if name_node:
                info['definitions'].append({'name': name_node.text.decode('utf8'), 'type': node.type, 'line': node.start_point[0] + 1})
        elif node.type == 'call':
            func_node = node.child_by_field_name('function')
            if func_node:
                name_node = func_node if func_node.type == 'identifier' else func_node.child_by_field_name('attribute')
                if name_node:
                    class_names = {d['name'] for d in info['definitions'] if d.get('type') == 'class'}
                    call_name = name_node.text.decode('utf8')
                    if call_name not in class_names:
                        info['calls'].append({'name': call_name, 'type': 'call', 'line': node.start_point[0] + 1, 'scope': self._find_scope_name(node)})
        for child in node.children:
            self._manual_extract(child, info)

# ==============================================================================
# 下位互換性インターフェースとCLI
# ==============================================================================

def check_tree_sitter_availability():
    if not TREE_SITTER_AVAILABLE:
        return False, "Missing: pip install tree-sitter tree-sitter-language-pack"
    return True, "Tree-sitter ready"

def print_syntax_tree(source_code, language='python'):
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
        content = path_obj.read_text(encoding='utf-8')
        return print_syntax_tree(content, 'python')
    except Exception as e:
        return {"error": f"Failed to read file: {e}", "success": False}

if __name__ == '__main__':
    # (CLI実行部分は省略し、テスト実行を推奨)
    print("This module is intended to be used as a library. For CLI, use the main entry point.")
