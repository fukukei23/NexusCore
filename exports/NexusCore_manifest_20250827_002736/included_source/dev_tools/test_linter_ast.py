# main.py

from live_lint_checker import live_lint_checker
from tree_sitter_checker import print_syntax_tree

filepath = "test_code.py"  # チェック対象ファイル（別途用意）

def lint_callback(result: str):
    print("🔍 Lint結果:\n", result)

# Lintをリアルタイム監視で実行（ファイル変更を検知して実行）
live_lint_checker(filepath, lint_callback)

# tree-sitterでASTを出力
with open(filepath) as f:
    code = f.read()
    print("🌲 Tree-sitter構文:")
    print_syntax_tree(code)
