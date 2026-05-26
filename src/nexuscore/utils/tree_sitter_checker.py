#!/usr/bin/env python3
# ==============================================================================
# ファイル名: tree_sitter_checker.py
# 機能: セマンティッククエリ統合版Tree-sitter解析ツール
# バージョン: 2.3.0 (split: analyzer + report + config extracted)
# 依存関係: pip install tree-sitter tree-sitter-language-pack tqdm colorama
# ==============================================================================

import argparse
import json
import sys
from pathlib import Path

from nexuscore.utils.tree_sitter._config import CONFIG, Fore, HAS_EXTRAS, TREE_SITTER_AVAILABLE, Style
from nexuscore.utils.tree_sitter._analyzer import SemanticAnalyzer
from nexuscore.utils.tree_sitter._report import ReportGenerator
from nexuscore.analyzer.unified_analyzer import AnalysisResult  # noqa: F401 — legacy re-export

import logging as _logging
_logger = _logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Semantic Code Analyzer v2.3.0")
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
