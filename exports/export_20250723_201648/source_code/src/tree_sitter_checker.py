# tree_sitter_checker.py

from tree_sitter import Language, Parser

# 一度だけビルドすればOK（初回起動時）
Language.build_library(
    'build/my-languages.so',
    ['tree-sitter-python']  # git clone したリポジトリのパス（必須）
)

PY_LANGUAGE = Language('build/my-languages.so', 'python')
parser = Parser()
parser.set_language(PY_LANGUAGE)

def print_syntax_tree(code: str):
    tree = parser.parse(bytes(code, "utf8"))
    print(tree.root_node.sexp())
