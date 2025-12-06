# ファイル名: project_structure_and_code_export.py
# 目的: プロジェクトの構造と主要なコードを分析し、基本的なエクスポートを行うためのコアツール。
# 修正内容:
# - LLMが誤解しないよう、PROJECT_INFO.mdの生成ロジックを改善。
# - 「解析対象の概要」と「このパッケージの作成方法」を明確に分離。
# - 元々のシンプルな分析ロジックは維持。

import os
import json
import zipfile
import fnmatch
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Tuple, Set, Any

# ===== チューニング設定 =====
MAX_FILE_SIZE_MB = 1
MAX_DEPTH = 10  # 階層の深さ制限を少し緩和
FILE_TYPES = ('.py', '.md', '.txt', 'package.json', '.json', '.yml', '.yaml', '.toml')
GITIGNORE_PATH = ".gitignore"

# ===== 除外対象（固定値） =====
DEFAULT_IGNORED_DIRS = {
    '.git', '.venv', '__pycache__', 'node_modules',
    'output', 'dist', 'build', 'sandbox_output', 'deploy_output',
    'myenv', 'openenv', 'exports', 'htmlcov', 'test_cache'
}
DEFAULT_IGNORED_FILES = {
    '.env', 'secrets.json', 'config.local.json', '.DS_Store', '*.log'
}

# ===== ユーティリティ関数 =====
def get_depth(path: str, base: str) -> int:
    return len(os.path.relpath(path, base).split(os.sep))

def load_gitignore(path: str = GITIGNORE_PATH) -> Tuple[Set[str], Set[str]]:
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

def is_ignored(path: str, base_path: str, ignored_dirs: Set[str], ignored_files: Set[str]) -> bool:
    rel_path = os.path.relpath(path, base_path)
    parts = rel_path.split(os.sep)
    # ディレクトリのチェック
    for i in range(len(parts)):
        sub_path = os.path.join(*parts[:i+1])
        if sub_path in ignored_dirs:
            return True
    # ファイルのチェック
    for pattern in ignored_files:
        if fnmatch.fnmatch(parts[-1], pattern):
            return True
    return False

def create_folder_structure_json(
    directory: str,
    base_path: str,
    ignored_dirs: Set[str],
    ignored_files: Set[str]
) -> Dict[str, Any]:
    name = os.path.basename(directory)
    if is_ignored(directory, base_path, ignored_dirs, set()):
        return None
    
    structure = {"name": name, "type": "folder", "children": []}
    if get_depth(directory, base_path) > MAX_DEPTH:
        return structure

    try:
        for item in sorted(os.listdir(directory)):
            item_path = os.path.join(directory, item)
            if is_ignored(item_path, base_path, ignored_dirs, ignored_files):
                continue

            if os.path.isdir(item_path):
                child_structure = create_folder_structure_json(item_path, base_path, ignored_dirs, ignored_files)
                if child_structure:
                    structure["children"].append(child_structure)
            else:
                structure["children"].append({"name": item, "type": "file"})
    except OSError:
        pass
    return structure

def create_folder_structure_md(
    directory: str,
    prefix: str,
    base_path: str,
    ignored_dirs: Set[str],
    ignored_files: Set[str]
) -> List[str]:
    lines = []
    if get_depth(directory, base_path) > MAX_DEPTH:
        return lines
        
    items = sorted(os.listdir(directory))
    for i, item in enumerate(items):
        item_path = os.path.join(directory, item)
        if is_ignored(item_path, base_path, ignored_dirs, ignored_files):
            continue

        is_last = i == (len(items) - 1)
        lines.append(prefix + ("└── " if is_last else "├── ") + item)
        
        if os.path.isdir(item_path):
            new_prefix = prefix + ("    " if is_last else "│   ")
            lines.extend(create_folder_structure_md(item_path, new_prefix, base_path, ignored_dirs, ignored_files))
    return lines

def combine_files(
    directory: str,
    ignored_dirs: Set[str],
    ignored_files: Set[str]
) -> str:
    combined_content = ""
    max_size = MAX_FILE_SIZE_MB * 1024 * 1024
    for root, dirs, files in os.walk(directory):
        dirs[:] = [d for d in dirs if d not in ignored_dirs and not is_ignored(os.path.join(root, d), directory, ignored_dirs, set())]
        for file in files:
            file_path = os.path.join(root, file)
            if file.endswith(FILE_TYPES) and not is_ignored(file_path, directory, ignored_dirs, ignored_files):
                try:
                    if os.path.getsize(file_path) > max_size:
                        continue
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                    relative_path = os.path.relpath(file_path, directory)
                    combined_content += f"# === {relative_path.replace(os.sep, '/')} ===\n"
                    combined_content += content + "\n\n"
                except Exception:
                    pass
    return combined_content

# --- 新しいPROJECT_INFO生成関数 ---
def generate_project_info_content(project_path: str, ignored_dirs: Set[str], ignored_files: Set[str]) -> str:
    """
    プロジェクトの統計情報を収集し、LLM向けのレポートを生成する。
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    total_files, total_lines, stats = 0, 0, {}

    for root, dirs, files in os.walk(project_path):
        dirs[:] = [d for d in dirs if d not in ignored_dirs]
        for file in files:
            if is_ignored(os.path.join(root, file), project_path, ignored_dirs, ignored_files):
                continue
            
            total_files += 1
            ext = os.path.splitext(file)[1] or "No Ext"
            stats.setdefault(ext, {"files": 0, "lines": 0})
            stats[ext]["files"] += 1
            try:
                with open(os.path.join(root, file), "r", encoding="utf-8", errors="ignore") as f:
                    lines = len(f.readlines())
                    stats[ext]["lines"] += lines
                    total_lines += lines
            except Exception:
                pass

    # --- セクション1: 解析対象プロジェクトの概要 ---
    project_summary = f"""# 📦 NexusCore プロジェクト解析パッケージ

## 1. 解析対象プロジェクトの概要 (`{os.path.basename(project_path)}`)

このパッケージは、「自己進化するAI開発エコシステム」である **NexusCore** プロジェクトの核心部分を抽出したものです。

- **プロジェクトの目的:** 専門的な役割を持つAIエージェント群が協調し、失敗から学び、その教訓を組織全体の知識として蓄積・進化させていく自己進化する開発エコシステム。
- **総ファイル数:** {total_files}
- **総コード行数:** {total_lines:,}行
- **エクスポート日時:** {timestamp}
"""

    # --- ファイル統計テーブルの生成 ---
    stats_table = "| 拡張子 | ファイル数 | コード行数 |\n|---|---|---|\n"
    sorted_stats = sorted(stats.items(), key=lambda item: item[1]['files'], reverse=True)
    for ext, data in sorted_stats:
        stats_table += f"| `{ext}` | {data['files']:,} | {data['lines']:,} |\n"
    stats_table += f"| **合計** | **{total_files:,}** | **{total_lines:,}** |\n"
    
    # --- セクション2: この解析パッケージの作成方法 ---
    package_info = f"""
---

## 2. この解析パッケージの作成方法について

このパッケージは、`project_structure_and_code_export.py` ツールによって生成されました。
このツールは、`.gitignore` と事前定義されたルールに基づき、プロジェクト内の関連ファイルを抽出し、単一のコードファイルに結合します。
"""

    return f"{project_summary}\n## 📊 ファイル統計\n{stats_table}{package_info}"


def main():
    PROJECT_PATH = "."
    OUTPUT_DIR = "exports"
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    project_name = os.path.basename(os.getcwd())

    STRUCTURE_JSON = os.path.join(OUTPUT_DIR, f"{project_name}_structure_{timestamp}.json")
    STRUCTURE_MD = os.path.join(OUTPUT_DIR, f"{project_name}_structure_{timestamp}.md")
    COMBINED_CODE = os.path.join(OUTPUT_DIR, f"{project_name}_combined_code_{timestamp}.py")
    PROJECT_INFO = os.path.join(OUTPUT_DIR, f"{project_name}_PROJECT_INFO_{timestamp}.md")
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
        f.write("\n".join(md_lines))
    print(f"✅ Markdown出力: {STRUCTURE_MD}")

    print("📝 プロジェクト情報を生成中...")
    project_info_content = generate_project_info_content(PROJECT_PATH, IGNORED_DIRS, IGNORED_FILES)
    with open(PROJECT_INFO, 'w', encoding='utf-8') as f:
        f.write(project_info_content)
    print(f"✅ プロジェクト情報出力: {PROJECT_INFO}")

    print("✍️ ファイル内容を結合中...")
    combined_content = combine_files(PROJECT_PATH, IGNORED_DIRS, IGNORED_FILES)
    with open(COMBINED_CODE, 'w', encoding='utf-8') as f:
        f.write(combined_content)
    print(f"✅ 結合コード出力: {COMBINED_CODE}")

    print("📦 ZIPファイルを作成中...")
    with zipfile.ZipFile(ARCHIVE_ZIP, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.write(STRUCTURE_JSON, os.path.basename(STRUCTURE_JSON))
        zf.write(STRUCTURE_MD, os.path.basename(STRUCTURE_MD))
        zf.write(COMBINED_CODE, os.path.basename(COMBINED_CODE))
        zf.write(PROJECT_INFO, os.path.basename(PROJECT_INFO))
    print(f"🎉 全ての処理が完了しました: {ARCHIVE_ZIP}")

if __name__ == "__main__":
    main()
