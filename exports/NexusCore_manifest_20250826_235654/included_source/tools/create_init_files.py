# C:\Users\USER\tools\OpenCodeInterpreter\create_init_files.py

import os

# Pythonパッケージとして扱うべきディレクトリのリスト
# 今後、新しいモジュールフォルダを追加した場合は、このリストに追加してください。
PACKAGE_DIRS = [
    "src",
    "src/core",
    "agents",
    "utils"
]

def initialize_project_structure():
    """
    プロジェクト内の指定されたディレクトリに__init__.pyファイルを作成し、
    Pythonパッケージとして認識できるようにします。
    """
    project_root = os.path.dirname(os.path.abspath(__file__))
    print(f"プロジェクトルート: {project_root}")
    print("プロジェクトのパッケージ構造を初期化します...")
    print("-" * 30)

    for dir_path in PACKAGE_DIRS:
        full_path = os.path.join(project_root, dir_path)
        init_file = os.path.join(full_path, "__init__.py")

        # ディレクトリが存在するかチェック
        if not os.path.isdir(full_path):
            print(f"⚠️  警告: ディレクトリ '{dir_path}' が見つかりません。スキップします。")
            continue

        # __init__.pyファイルが存在しない場合に作成
        if not os.path.exists(init_file):
            print(f"✅  '{init_file}' を作成しました。")
            with open(init_file, "w") as f:
                # このファイルは空で問題ありません。
                # パッケージであることを示すマーカーとして機能します。
                pass
        else:
            print(f"ℹ️   '{init_file}' は既に存在します。")

    print("-" * 30)
    print("\n初期化が完了しました。")
    print("再度 `python main_cli.py execute ...` を実行してみてください。")


if __name__ == "__main__":
    initialize_project_structure()
