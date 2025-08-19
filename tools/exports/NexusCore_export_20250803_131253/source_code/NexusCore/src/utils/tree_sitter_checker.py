# tree_sitter_checker.py
from tree_sitter import Language, Parser
import os

# 絶対パス指定（Windows環境対応）
base_dir = os.path.dirname(os.path.abspath(__file__))
lib_path = os.path.abspath(os.path.join(base_dir, "..", "..", "build", "my-languages.so"))

# Python用の言語を読み込み
PY_LANGUAGE = Language(lib_path, 'python')

# Tree-sitter構文解析を実行
def print_syntax_tree(code: str):
    parser = Parser()
    parser.set_language(PY_LANGUAGE)
    tree = parser.parse(bytes(code, "utf8"))
    print(tree.root_node.sexp())
    return tree.root_node.sexp()
