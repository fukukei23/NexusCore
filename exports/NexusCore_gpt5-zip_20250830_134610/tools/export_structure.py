# ファイル名: export_structure.py
# メモ:
# - 指定フォルダのディレクトリ構造をツリー形式でテキスト出力
# - 出力先フォルダ「project_structure_export」を自動作成し、
#   解析したフォルダ名を使ったファイル名「<foldername>_folder_structure.txt」で保存
# - 除外ディレクトリもカスタマイズ可能
# - 使い方: python export_structure.py [対象ディレクトリ（省略時はカレント）]

import os
import sys

EXCLUDE_DIRS = {'.git', '__pycache__', '.venv', 'venv', '.idea', '.mypy_cache', '.pytest_cache', '.DS_Store'}

def print_tree(root, prefix="", file=sys.stdout):
    entries = sorted([e for e in os.listdir(root) if e not in EXCLUDE_DIRS])
    for i, entry in enumerate(entries):
        path = os.path.join(root, entry)
        connector = "└── " if i == len(entries) - 1 else "├── "
        print(prefix + connector + entry, file=file)
        if os.path.isdir(path):
            extension = "    " if i == len(entries) - 1 else "│   "
            print_tree(path, prefix + extension, file=file)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        target_dir = os.path.abspath(sys.argv[1])
    else:
        target_dir = os.getcwd()

    # 解析したフォルダ名を取得
    folder_name = os.path.basename(os.path.normpath(target_dir))

    # 出力用フォルダを作成
    export_dir = "project_structure_export"
    os.makedirs(export_dir, exist_ok=True)

    # 出力ファイル名（例: myproject_folder_structure.txt）
    output_file = os.path.join(export_dir, f"{folder_name}_folder_structure.txt")

    with open(output_file, "w", encoding="utf-8") as f:
        print(f"{folder_name}/", file=f)
        print_tree(target_dir, file=f)

    print(f"フォルダ構造を {output_file} に出力しました。")
