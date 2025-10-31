# ファイル名: code_export_gui.py / code_export_gui_fixed.py (共通)
# 目的: プロジェクト分析とエクスポートを行うための高機能なGradioベースGUIツール。
# 修正内容:
# - `_fixed`版の機能（進行度表示、命名規則プレビュー、エラー修正）を統合。
# - LLMが誤解しないよう、PROJECT_INFO.mdの生成ロジックを改善。
# - 「解析対象の概要」と「このパッケージの作成方法」を明確に分離。
# - GeminiモードとStandardモードでレポート内容が動的に変わるように修正。

from __future__ import annotations
import ast
import datetime
import fnmatch
import os
import re
import time
import traceback
import zipfile
from collections import defaultdict
from math import log2
from pathlib import Path
from threading import Event
from typing import List, Tuple, Dict, Set, Any
import gradio as gr

try:
    import networkx as nx
except ImportError:
    nx = None

# === CONFIG ===
FILE_TYPES: Tuple[str, ...] = (
    ".py", ".ipynb", ".md", ".txt", "package.json", ".json", ".yml", ".yaml", ".toml",
)
DEFAULT_IGNORED_DIRS = {
    ".git", "__pycache__", "node_modules", "dist", "build", ".venv", "myenv", "openenv",
    "exports", "htmlcov", "test_cache", ".pytest_cache", ".gradio"
}
DEFAULT_IGNORED_FILES = {
    '.env', 'secrets.json', 'config.local.json', '.DS_Store', '*.log',
    '*.exe', '*.dll', '*.so', '*.dylib', '*.lib'
}
EXPORT_DIR_NAME = "exports"

# === HELPER FUNCTIONS ===
def analyze_dependencies(directory: str, ignore_dirs: Set[str]) -> Dict[str, int]:
    dependencies: Dict[str, int] = defaultdict(int)
    py_files: List[str] = []
    for root, dirs, files in os.walk(directory):
        dirs[:] = [d for d in dirs if d not in ignore_dirs]
        for file in files:
            if file.endswith(".py"):
                py_files.append(os.path.join(root, file))
    
    for file_path in py_files:
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            tree = ast.parse(content)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        for path_to_check in py_files:
                            if alias.name in path_to_check.replace(os.sep, "."):
                                dependencies[path_to_check] += 1
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        for path_to_check in py_files:
                            if node.module in path_to_check.replace(os.sep, "."):
                                dependencies[path_to_check] += 1
        except Exception:
            continue
    return dependencies

def calculate_score(file_path: str, line_count: int, dependency_count: int) -> float:
    score = 0.0
    ext = os.path.splitext(file_path)[1]
    score += EXTENSION_WEIGHTS.get(ext, 0)
    normalized_path = file_path.replace(os.sep, "/")
    for path, weight in PATH_WEIGHTS.items():
        if path in normalized_path:
            score += weight
    if line_count >= MIN_LINES_FOR_DEPENDENCY:
        score += log2(1 + dependency_count)
    score += line_count * LINE_COUNT_WEIGHT
    return score

# --- 新しいPROJECT_INFO生成関数 (GUI版) ---
def generate_project_info_content(
    total_files: int,
    total_lines: int,
    stats: Dict[str, Dict[str, int]],
    export_type: str,
    max_size_mb: int,
    project_name: str
) -> str:
    """
    プロジェクト情報と解析パッケージに関するマークダウンコンテンツを生成する。
    """
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # --- セクション1: 解析対象プロジェクトの概要 ---
    project_summary = f"""# 📦 {project_name} プロジェクト解析パッケージ ({export_type})

## 1. 解析対象プロジェクトの概要 (`{project_name}`)

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
    size_info = f"**{export_type}のファイルサイズ上限 (~{max_size_mb}MB) を考慮**しつつ、" if export_type == "Gemini" else ""
    tool_name = "code_export_gui.py"
    package_info = f"""
---

## 2. この解析パッケージの作成方法について

このパッケージ（特に `COMBINED_CODE.py`）は、`{tool_name}` ツールによって、{size_info}以下の基準で重要と判断されたファイルを自動的に抽出し、結合したものです。

### 🎯 重要度判定基準
#### 拡張子重み
- `.py` ファイル: 3点（最重要）
- `.ipynb` ノートブック: 2点
- `.md` ドキュメント: 1点

#### パス重み
- `src/`, `app/`, `nexuscore/` フォルダ: +2点（重要）
- `tests/`, `docs/` フォルダ: -1点（補助）

#### 依存関係解析
- import結合度による中心性計算
- ファイル間の依存関係を重要度に反映

#### コード行数
- 空白やコメントを除いたコード行数が多いほど高評価
"""

    return f"{project_summary}\n## 📊 ファイル統計\n{stats_table}{package_info}"

# --- Core Logic for GUI ---
def export_project(project_dir_str: str, export_type: str, max_size_mb: int, progress=gr.Progress(track_tqdm=True)):
    project_dirs = [p.strip() for p in project_dir_str.splitlines() if p.strip()]
    if not project_dirs:
        return "Error: プロジェクトディレクトリが指定されていません。", "", None

    first_project_name = os.path.basename(project_dirs[0])
    output_dir = os.path.join(project_dirs[0], EXPORT_DIR_NAME)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    ignore_dirs = DEFAULT_IGNORED_DIRS
    max_size_bytes = max_size_mb * 1024 * 1024

    all_files_to_score = []
    total_files, total_lines, stats = 0, 0, defaultdict(lambda: {"files": 0, "lines": 0})

    for directory in progress.tqdm(project_dirs, desc="📊 Analyzing structure"):
        for root, dirs, files in os.walk(directory):
            dirs[:] = [d for d in dirs if d not in ignore_dirs]
            for file in files:
                file_path = os.path.join(root, file)
                total_files += 1
                ext = os.path.splitext(file)[1] or "No Ext"
                stats[ext]["files"] += 1
                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        line_count = len(f.readlines())
                    stats[ext]["lines"] += line_count
                    total_lines += line_count
                    if file.endswith(FILE_TYPES):
                        all_files_to_score.append(file_path)
                except Exception:
                    continue
    
    progress(0.4, desc="🔗 Analyzing dependencies...")
    dependencies = analyze_dependencies(project_dirs[0], ignore_dirs) # NOTE: Assuming main project is first

    progress(0.6, desc="🏆 Scoring files...")
    scores = {}
    for file_path in progress.tqdm(all_files_to_score, desc="Scoring"):
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
                line_count = len([line for line in lines if line.strip()])
            dep_count = dependencies.get(file_path, 0)
            scores[file_path] = calculate_score(file_path, line_count, dep_count)
        except Exception:
            continue
            
    sorted_files = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    
    progress(0.7, desc="Selecting top files based on size...")
    top_files = []
    current_size = 0
    for file_path, score in sorted_files:
        try:
            file_size = os.path.getsize(file_path)
            if current_size + file_size < max_size_bytes:
                top_files.append((file_path, score))
                current_size += file_size
        except OSError:
            continue

    progress(0.8, desc="📝 Generating project info...")
    project_info_content = generate_project_info_content(
        total_files, total_lines, stats, export_type, max_size_mb, first_project_name
    )

    progress(0.9, desc="📦 Creating ZIP file...")
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_filename_base = f"{first_project_name}_{export_type.lower()}_{timestamp}"
    zip_filepath = os.path.join(output_dir, f"{zip_filename_base}.zip")

    combined_code = ""
    with zipfile.ZipFile(zip_filepath, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("PROJECT_INFO.md", project_info_content)
        readme_content = f"# {first_project_name} Analysis Package ({export_type})\n\nGenerated for LLM analysis."
        zf.writestr("README.md", readme_content)
        
        for file_path, score in top_files:
            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                # 複数のルートディレクトリに対応するため、共通の基底パスを探す
                common_base = os.path.commonpath(project_dirs)
                relative_path = os.path.relpath(file_path, common_base)
                combined_code += f"# --- File: {relative_path.replace(os.sep, '/')}, Score: {score:.2f} ---\n"
                combined_code += content + "\n\n"
            except Exception as e:
                combined_code += f"# --- Error reading file: {file_path}, Error: {e} ---\n\n"
        zf.writestr("COMBINED_CODE.py", combined_code)

    return f"✅ Export complete! Saved to {zip_filepath}", project_info_content, zip_filepath

# --- UI Functions ---
def browse_and_append(existing_paths):
    try:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk()
        root.withdraw()
        path = filedialog.askdirectory(title="Select a project folder to add")
        root.destroy()
        if path:
            paths = existing_paths.splitlines()
            if path not in paths:
                paths.append(path)
            return "\n".join(paths)
    except Exception:
        pass # Tkinter not available
    return existing_paths

def get_naming_preview(dirs_str):
    dirs = [d.strip() for d in dirs_str.splitlines() if d.strip()]
    if not dirs:
        return "No directory selected."
    first_project_name = os.path.basename(dirs[0])
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"Standard: {first_project_name}_standard_{timestamp}.zip\nGemini: {first_project_name}_gemini_{timestamp}.zip"

# --- Gradio UI ---
with gr.Blocks(theme=gr.themes.Soft(), title="NexusCore Exporter") as demo:
    gr.Markdown("# NexusCore Project Exporter 🚀")
    gr.Markdown("Select project directories and export type to generate an analysis package for LLMs.")
    
    with gr.Row():
        project_dir_input = gr.Textbox(
            label="Project Directories (one per line)", 
            value=os.path.abspath(".."),
            lines=3
        )
        browse_button = gr.Button("📂 Add Folder")

    with gr.Row():
        export_type_radio = gr.Radio(
            ["Standard", "Gemini"], 
            label="Export Type", 
            value="Gemini",
            info="Gemini mode limits the combined code size to ~10MB."
        )
        max_size_slider = gr.Slider(
            1, 100, value=10, step=1, 
            label="Max Combined Code Size (MB)",
            info="Adjust the size limit for the combined code file."
        )

    with gr.Row():
        export_button = gr.Button("🚀 Export Project", variant="primary")
        naming_preview_button = gr.Button("📝 Preview Filename")

    status_output = gr.Textbox(label="Status", interactive=False)
    
    with gr.Accordion("📄 Export Details & Download", open=False) as details_accordion:
        project_info_output = gr.Markdown(label="Generated Project Info")
        zip_output_file = gr.File(label="Download Exported ZIP")

    with gr.Accordion("Filename Preview", open=False) as preview_accordion:
        naming_preview_output = gr.Textbox(label="Example Output Filenames", interactive=False)

    # --- Event Handlers ---
    browse_button.click(
        fn=browse_and_append,
        inputs=[project_dir_input],
        outputs=[project_dir_input]
    )

    naming_preview_button.click(
        fn=get_naming_preview,
        inputs=[project_dir_input],
        outputs=[naming_preview_output]
    ).then(lambda: gr.update(open=True), outputs=preview_accordion)

    export_button.click(
        fn=export_project,
        inputs=[project_dir_input, export_type_radio, max_size_slider],
        outputs=[status_output, project_info_output, zip_output_file]
    ).then(lambda: gr.update(open=True), outputs=details_accordion)

if __name__ == "__main__":
    print("🚀 Launching NexusCore Project Exporter GUI...")
    demo.launch()
