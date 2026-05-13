from collections import Counter
from typing import Any

from nexuscore.analyzer.unified_analyzer import AnalysisResult
from nexuscore.utils.tree_sitter._config import Fore, Style


class ReportGenerator:
    @staticmethod
    def generate_summary(results: dict[str, AnalysisResult]) -> dict[str, Any]:
        successful = [r for r in results.values() if r.success]

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

        if summary["symbols"]:
            print(f"\n{Fore.MAGENTA}🧬 Discovered Symbols:")
            for symbol_type, count in summary["symbols"].items():
                print(f"  • {symbol_type.title()}: {Fore.WHITE}{count}")

        if summary["errors"] > 0:
            print(f"\n{Fore.RED}⚠️  Syntax Errors: {Fore.WHITE}{summary['errors']} files")
