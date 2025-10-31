# tree_sitter_checker.py
import os
import json
from tree_sitter import Language, Parser

# ======== 言語ライブラリの読み込み ========
LIB_PATH = "build/my-languages.so"  # あらかじめビルドされていること
LANGUAGE_NAME = "python"

Language.build_library(
    # 出力先
    LIB_PATH,
    # 対象リポジトリ（必要な場合のみ）
    [
        'tree_sitter_languages/tree-sitter-python'
    ]
)

PY_LANGUAGE = Language(LIB_PATH, LANGUAGE_NAME)

# ======== AST パース関数 ========
def parse_code(code: str):
    parser = Parser()
    parser.set_language(PY_LANGUAGE)
    tree = parser.parse(bytes(code, "utf8"))
    
    def walk(node):
        return {
            "type": node.type,
            "start_point": node.start_point,
            "end_point": node.end_point,
            "children": [walk(child) for child in node.children]
        }

    root_node = tree.root_node
    return walk(root_node)

# ======== 簡易エラーチェック関数（例示用） ========
def find_syntax_errors(code: str):
    errors = []
    lines = code.splitlines()
    for i, line in enumerate(lines):
        if "??" in line:
            errors.append({"line": i + 1, "message": "無効なトークン '??' が含まれています。"})
    return errors

# ======== メイン実行部 ========
def main():
    input_code = os.environ.get("INPUT_CODE", "")

    if not input_code.strip():
        print(json.dumps({
            "result": "ERROR",
            "errors": [{"message": "コードが空です。"}],
            "ast": None
        }, ensure_ascii=False))
        return

    try:
        ast = parse_code(input_code)
        errors = find_syntax_errors(input_code)

        print(json.dumps({
            "result": "OK",
            "errors": errors,
            "ast": ast
        }, ensure_ascii=False))

    except Exception as e:
        print(json.dumps({
            "result": "ERROR",
            "errors": [{"message": str(e)}],
            "ast": None
        }, ensure_ascii=False))

if __name__ == "__main__":
    main()
