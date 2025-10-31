#!/usr/bin/env python3
# ==============================================================================
# ファイル名: advanced_semantic_analyzer.py
# 機能: セマンティッククエリ統合版Tree-sitter解析ツール
# バージョン: 2.2.0 (最適化・統合版)
# 依存関係: pip install tree-sitter tree-sitter-language-pack tqdm colorama
# ==============================================================================

import os
import sys
import time
import json
import logging
import argparse
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from collections import Counter, defaultdict
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

# サードパーティライブラリ
try:
    from tqdm import tqdm
    from colorama import init, Fore, Style
    init(autoreset=True)
    HAS_EXTRAS = True
except ImportError:
    HAS_EXTRAS = False
    class Fore: RED = GREEN = YELLOW = BLUE = MAGENTA = CYAN = WHITE = ""
    class Style: BRIGHT = RESET_ALL = ""

# Tree-sitter（修正版）
try:
    from tree_sitter import Parser, Node
    from tree_sitter_language_pack import get_language, get_parser
    TREE_SITTER_AVAILABLE = True
except ImportError:
    TREE_SITTER_AVAILABLE = False
    Parser = Node = None

# ==============================================================================
# グローバル設定
# ==============================================================================

CONFIG = {
    'supported_languages': {
        '.py': 'python', '.js': 'javascript', '.ts': 'typescript', '.go': 'go',
        '.rs': 'rust', '.c': 'c', '.cpp': 'cpp', '.java': 'java', '.rb': 'ruby'
    },
    'max_workers': os.cpu_count() or 4,
    'timeout_seconds': 60
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
    
    def __getitem__(self, key): return self.data.get(key)
    def to_dict(self): return {'success': self.success, 'timestamp': self.timestamp, **self.data}
    def to_json(self, indent=2): return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

class SemanticAnalyzer:
    """セマンティッククエリ統合版解析器"""
    
    def __init__(self):
        self.parsers = {}
        self.languages = {}
        
    def check_availability(self) -> Tuple[bool, str]:
        """利用可能性チェック"""
        if not TREE_SITTER_AVAILABLE:
            return False, "Missing: pip install tree-sitter tree-sitter-language-pack"
        try:
            get_parser('python')
            return True, "Tree-sitter ready"
        except Exception as e:
            return False, f"Setup error: {e}"
    
    def setup_parsers(self, languages: List[str] = None) -> bool:
        """パーサーセットアップ"""
        if not languages:
            languages = list(set(CONFIG['supported_languages'].values()))
        
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
    
    def _extract_symbols(self, language: str, root_node: Node) -> Dict[str, List[Dict]]:
        """★★★ セマンティッククエリでシンボル抽出 ★★★"""
        
        # 言語別のS式クエリ定義
        queries = {
            'python': {
                'functions': '(function_definition name: (identifier) @name)',
                'classes': '(class_definition name: (identifier) @name)',
                'imports': '(import_statement name: (dotted_name) @name)',
                'variables': '(assignment left: (identifier) @name)'
            },
            'javascript': {
                'functions': '[(function_declaration name: (identifier) @name) (arrow_function)]',
                'classes': '(class_declaration name: (identifier) @name)',
                'imports': '(import_statement source: (string) @name)'
            },
            'go': {
                'functions': '(function_declaration name: (identifier) @name)',
                'types': '(type_declaration (type_spec name: (type_identifier) @name))',
                'packages': '(package_clause (package_identifier) @name)'
            },
            'rust': {
                'functions': '(function_item name: (identifier) @name)',
                'structs': '(struct_item name: (type_identifier) @name)',
                'impls': '(impl_item type: (type_identifier) @name)'
            }
        }
        
        lang_queries = queries.get(language, {})
        if not lang_queries:
            return {}
        
        symbols = defaultdict(list)
        language_obj = self.languages[language]
        
        for symbol_type, query_string in lang_queries.items():
            try:
                query = language_obj.query(query_string)
                captures = query.captures(root_node)
                
                for node, capture_name in captures:
                    symbol_name = node.text.decode('utf8')
                    # 重複除去
                    if not any(s['name'] == symbol_name for s in symbols[symbol_type]):
                        symbols[symbol_type].append({
                            'name': symbol_name,
                            'line': node.start_point[0] + 1,
                            'column': node.start_point[1] + 1
                        })
            except Exception as e:
                logger.debug(f"Query failed for {symbol_type}: {e}")
        
        return dict(symbols)
    
    def analyze_source_code(self, source_code: str, language: str, file_path: str = None) -> AnalysisResult:
        """ソースコード解析（セマンティック機能付き）"""
        if language not in self.parsers:
            return AnalysisResult(
                success=False, 
                error=f"Parser not available: {language}",
                file_path=file_path
            )
        
        try:
            start_time = time.time()
            
            # 構文解析
            parser = self.parsers[language]
            tree = parser.parse(bytes(source_code, "utf8"))
            root_node = tree.root_node
            
            # エラーチェック
            has_errors = root_node.has_error
            
            # ★★★ セマンティック解析実行 ★★★
            symbols = self._extract_symbols(language, root_node)
            
            # 基本統計
            lines = source_code.splitlines()
            
            return AnalysisResult(
                success=True,
                file_path=file_path,
                language=language,
                source_stats={
                    'line_count': len(lines),
                    'character_count': len(source_code),
                    'empty_lines': sum(1 for line in lines if not line.strip())
                },
                semantic_symbols=symbols,
                errors={'has_syntax_errors': has_errors},
                performance={'analysis_time': round(time.time() - start_time, 4)}
            )
            
        except Exception as e:
            return AnalysisResult(
                success=False,
                error=str(e),
                file_path=file_path,
                language=language
            )
    
    def analyze_file(self, file_path: Path) -> AnalysisResult:
        """ファイル解析"""
        if not file_path.is_file():
            return AnalysisResult(success=False, error=f"File not found: {file_path}")
        
        language = CONFIG['supported_languages'].get(file_path.suffix.lower())
        if not language:
            return AnalysisResult(success=False, error=f"Unsupported: {file_path.suffix}")
        
        try:
            content = file_path.read_text(encoding='utf-8')
            return self.analyze_source_code(content, language, str(file_path))
        except Exception as e:
            return AnalysisResult(success=False, error=f"Read error: {e}")
    
    def analyze_project(self, project_path: Path) -> Dict[str, AnalysisResult]:
        """プロジェクト解析"""
        exclude_patterns = ['**/node_modules/**', '**/.git/**', '**/build/**']
        
        target_files = [
            f for ext in CONFIG['supported_languages']
            for f in project_path.rglob(f"*{ext}")
            if f.is_file() and not any(f.match(p) for p in exclude_patterns)
        ]
        
        results = {}
        progress = tqdm(target_files, desc="Analyzing", disable=not HAS_EXTRAS)
        
        with ThreadPoolExecutor(max_workers=CONFIG['max_workers']) as executor:
            future_to_file = {executor.submit(self.analyze_file, f): f for f in target_files}
            
            for future in as_completed(future_to_file):
                file_path = future_to_file[future]
                try:
                    results[str(file_path)] = future.result(timeout=CONFIG['timeout_seconds'])
                except Exception as e:
                    results[str(file_path)] = AnalysisResult(success=False, error=str(e))
                progress.update(1)
        
        progress.close()
        return results

# ==============================================================================
# レポート生成
# ==============================================================================

class ReportGenerator:
    @staticmethod
    def generate_summary(results: Dict[str, AnalysisResult]) -> Dict[str, Any]:
        successful = [r for r in results.values() if r.success]
        
        # ★★★ セマンティック統計 ★★★
        symbol_stats = Counter()
        for result in successful:
            if symbols := result['semantic_symbols']:
                for symbol_type, symbol_list in symbols.items():
                    symbol_stats[symbol_type] += len(symbol_list)
        
        return {
            'overview': {
                'total_files': len(results),
                'successful': len(successful),
                'total_lines': sum(r['source_stats']['line_count'] for r in successful)
            },
            'languages': Counter(r['language'] for r in successful),
            'symbols': dict(symbol_stats),
            'errors': sum(1 for r in successful if r['errors']['has_syntax_errors'])
        }
    
    @staticmethod
    def print_report(summary: Dict[str, Any]):
        print(f"\n{Fore.CYAN}{Style.BRIGHT}=== SEMANTIC ANALYSIS REPORT ==={Style.RESET_ALL}")
        
        o = summary['overview']
        print(f"\n{Fore.GREEN}📊 Overview:")
        print(f"  • Files: {Fore.WHITE}{o['total_files']} ({o['successful']} analyzed)")
        print(f"  • Lines: {Fore.WHITE}{o['total_lines']:,}")
        
        print(f"\n{Fore.BLUE}🔤 Languages:")
        for lang, count in summary['languages'].items():
            print(f"  • {lang.title()}: {Fore.WHITE}{count} files")
        
        # ★★★ セマンティック情報表示 ★★★
        if summary['symbols']:
            print(f"\n{Fore.MAGENTA}🧬 Discovered Symbols:")
            for symbol_type, count in summary['symbols'].items():
                print(f"  • {symbol_type.title()}: {Fore.WHITE}{count}")
        
        if summary['errors'] > 0:
            print(f"\n{Fore.RED}⚠️  Syntax Errors: {Fore.WHITE}{summary['errors']} files")

# ==============================================================================
# CLI
# ==============================================================================

def main():
    parser = argparse.ArgumentParser(description="Semantic Code Analyzer v2.2.0")
    parser.add_argument('target', help='File or directory to analyze')
    parser.add_argument('--output', help='JSON output file')
    parser.add_argument('--verbose', '-v', action='store_true')
    
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
                json.dumps({
                    'summary': summary,
                    'details': {k: v.to_dict() for k, v in results.items()}
                }, indent=2, ensure_ascii=False)
            )
            print(f"\n{Fore.GREEN}✅ Saved to {args.output}")
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
