import os
import json
import zipfile
import fnmatch
from pathlib import Path
from datetime import datetime

# ===== チューニング設定 =====
MAX_FILE_SIZE_MB = 1
MAX_DEPTH = 5
FILE_TYPES = ('.py', '.md', '.txt', 'package.json')
GITIGNORE_PATH = ".gitignore"

# ===== 除外対象（固定値） =====
DEFAULT_IGNORED_DIRS = {
    '.git', '.venv', '__pycache__', 'node_modules',
    'output', 'dist', 'build', 'sandbox_output', 'deploy_output'
}
DEFAULT_IGNORED_FILES = {
    '.env', 'secrets.json', 'config.local.json', '.DS_Store', '*.log'
}

# ===== ユーティリティ関数 =====
def get_depth(path, base):
    return len(os.path.relpath(path, base).split(os.sep))

def load_gitignore(path=GITIGNORE_PATH):
    ignored_dirs, ignored_files = set(), set()
    if not os.path.exists(path):
        return ignored_dirs, ignored_files
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.endswith('/'):
                ignored_dirs.add(line.rstrip('/'))
            else:
                ignored_files.add(line)
    return ignored_dirs, ignored_files

def create_folder_structure_json(path, base_path, ignored_dirs, ignored_files):
    if get_depth(path, base_path) > MAX_DEPTH:
        return None
    result = {
        'name': os.path.basename(path),
        'type': 'folder',
        'children': []
    }
    for entry in sorted(os.listdir(path)):
        full_path = os.path.join(path, entry)
        if os.path.isdir(full_path):
            if entry in ignored_dirs:
                continue
            child = create_folder_structure_json(full_path, base_path, ignored_dirs, ignored_files)
            if child:
                result['children'].append(child)
        else:
            if entry in ignored_files or any(fnmatch.fnmatch(entry, pattern) for pattern in ignored_files):
                continue
            result['children'].append({'name': entry, 'type': 'file'})
    return result

def create_folder_structure_md(path, prefix, base_path, ignored_dirs, ignored_files):
    lines = []
    if get_depth(path, base_path) > MAX_DEPTH:
        return lines
    for i, entry in enumerate(sorted(os.listdir(path))):
        full_path = os.path.join(path, entry)
        if entry in ignored_dirs or entry in ignored_files or any(fnmatch.fnmatch(entry, pattern) for pattern in ignored_files):
            continue
        connector = "└── " if i == len(os.listdir(path)) - 1 else "├── "
        lines.append(prefix + connector + entry)
        if os.path.isdir(full_path):
            extension = "    " if i == len(os.listdir(path)) - 1 else "│   "
            lines.extend(create_folder_structure_md(full_path, prefix + extension, base_path, ignored_dirs, ignored_files))
    return lines

def combine_files(root_path, output_file, file_types, ignored_dirs, ignored_files):
    buffer = []
    for dirpath, _, filenames in os.walk(root_path):
        if any(part in ignored_dirs for part in dirpath.split(os.sep)):
            continue
        if get_depth(dirpath, root_path) > MAX_DEPTH:
            continue
        for filename in sorted(filenames):
            if filename in ignored_files or any(fnmatch.fnmatch(filename, pattern) for pattern in ignored_files):
                continue
            if not (filename.endswith(file_types) or filename in file_types):
                continue
            file_path = os.path.join(dirpath, filename)
            if os.path.getsize(file_path) > MAX_FILE_SIZE_MB * 1024 * 1024:
                continue
            rel_path = os.path.relpath(file_path, root_path)
            buffer.append(f"\n\n# === File: {rel_path} ===\n\n")
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    buffer.append(f.read())
            except Exception as e:
                buffer.append(f"[読み込みエラー: {e}]")
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(''.join(buffer))

def zip_outputs(output_dir, archive_name):
    with zipfile.ZipFile(archive_name, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(output_dir):
            for file in files:
                full_path = os.path.join(root, file)
                arcname = os.path.relpath(full_path, output_dir)
                zipf.write(full_path, arcname)

# ===== メイン処理 =====
if __name__ == "__main__":
    PROJECT_PATH = "./"
    OUTPUT_DIR = "output"
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    project_name = os.path.basename(os.getcwd())

    STRUCTURE_JSON = os.path.join(OUTPUT_DIR, f"{project_name}_structure_{timestamp}.json")
    STRUCTURE_MD = os.path.join(OUTPUT_DIR, f"{project_name}_structure_{timestamp}.md")
    COMBINED_CODE = os.path.join(OUTPUT_DIR, f"{project_name}_combined_{timestamp}.txt")
    ARCHIVE_ZIP = os.path.join(OUTPUT_DIR, f"{project_name}_bundle_{timestamp}.zip")

    print("🚀 .gitignoreを読み込み中...")
    gitignore_dirs, gitignore_files = load_gitignore()
    IGNORED_DIRS = DEFAULT_IGNORED_DIRS.union(gitignore_dirs)
    IGNORED_FILES = DEFAULT_IGNORED_FILES.union(gitignore_files)

    print("📁 ディレクトリ構造の解析を開始します...")
    structure = create_folder_structure_json(PROJECT_PATH, PROJECT_PATH, IGNORED_DIRS, IGNORED_FILES)
    with open(STRUCTURE_JSON, 'w', encoding='utf-8') as f:
        json.dump(structure, f, indent=4, ensure_ascii=False)
    print(f"✅ JSON出力: {STRUCTURE_JSON}")

    md_lines = create_folder_structure_md(PROJECT_PATH, "", PROJECT_PATH, IGNORED_DIRS, IGNORED_FILES)
    with open(STRUCTURE_MD, 'w', encoding='utf-8') as f:
        f.write('\n'.join(md_lines))
    print(f"✅ Markdown出力: {STRUCTURE_MD}")

    print("📦 ソース統合中...")
    combine_files(PROJECT_PATH, COMBINED_CODE, FILE_TYPES, IGNORED_DIRS, IGNORED_FILES)
    print(f"✅ 統合コード出力: {COMBINED_CODE}")

    print("🗜️ アーカイブ作成中...")
    zip_outputs(OUTPUT_DIR, ARCHIVE_ZIP)
    print(f"✅ zip出力完了: {ARCHIVE_ZIP}")

    print("\n🎉 すべての処理が完了しました。")
