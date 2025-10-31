# build_tree_sitter.py

from tree_sitter import Language
import os

os.makedirs("build", exist_ok=True)

Language.build_library(
    # 出力先ファイル
    'build/my-languages.so',

    # 対象とする構文定義リポジトリ（すでにクローン済み）
    [
        'tree_sitter_languages/tree-sitter-python',
    ]
)

print("✅ Tree-sitterライブラリのビルド完了：build/my-languages.so")
