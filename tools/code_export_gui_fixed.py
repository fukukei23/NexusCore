"""code_export_gui_fixed.py — importance-aware export with folder-named outputs (ERROR FIXED)

エラー修正版 - 2025-08-03 rev-9 (sub_progress parameter conflict fixed)

────────────────────────────────────────────────────

* Layer-① ルールベース（拡張子・パス・サイズ）
* Layer-② 静的メタ解析（import 結合度 + LOC）
* **複数フォルダ選択** OK
* **進行度表示機能** - 各処理段階を視覚化
* **フォルダ名識別** - 出力ファイル名に分析対象フォルダ名を含める
* **引数競合エラー修正** NEW - sub_progress関数の引数処理を修正

使用方法:
1. (venv) 環境で実行: python code_export_gui_fixed.py
2. ブラウザで http://127.0.0.1:7860 にアクセス
3. プロジェクトフォルダに C:/Users/USER/tools/NexusCore を指定
4. エクスポート開始で進行度を確認しながら処理実行

"""

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
from typing import List, Tuple, Dict, Set

import gradio as gr

try:
    import networkx as nx  # optional – centrality calc
except ImportError:
    nx = None

# === CONFIG ===
FILE_TYPES: Tuple[str, ...] = (
    ".py", ".ipynb", ".md", ".txt", "package.json", ".json", ".yml", ".yaml", ".toml",
)

DEFAULT_IGNORED_DIRS = {
    ".git", "__pycache__", "node_modules", "venv", ".venv", "dist", "build", ".idea", ".vscode",
}

MAX_LINES_PER_FILE = 10_000
TOTAL_SIZE_CAP_MB = 99
WIN_PATH_CAP = 250  # safe margin under MAX_PATH 260
EXPORT_ROOT = Path("./exports").resolve()
EXPORT_ROOT.mkdir(exist_ok=True)
DEFAULT_IGNORED_DIRS.add(EXPORT_ROOT.name)

EXT_WEIGHT = {".py": 3, ".ipynb": 2, ".md": 1}
PATH_WEIGHT = {"src": 2, "app": 2, "lib": 1, "tests": -1, "docs": -1}

stop_event = Event()

# ───────────────────────────────────────── naming helpers
def sanitize_name(name: str) -> str:
    """ファイル名として安全な文字列に変換"""
    invalid_chars = r'[<>:"/\\|?*\x00-\x1f]'
    sanitized = re.sub(invalid_chars, '_', name)
    sanitized = re.sub(r'_+', '_', sanitized)
    sanitized = sanitized.strip('_')
    if not sanitized:
        sanitized = "Unknown"
    if len(sanitized) > 50:
        sanitized = sanitized[:50]
    return sanitized

def generate_project_prefix(roots: List[Path]) -> str:
    """分析対象フォルダ名から出力ファイル名のプレフィックスを生成"""
    if not roots:
        return "Export"
    folder_names = [sanitize_name(root.name) for root in roots]
    if len(folder_names) == 1:
        return folder_names[0]
    if len(folder_names) <= 3:
        return "-".join(folder_names)
    else:
        return f"{'-'.join(folder_names[:2])}-etc{len(folder_names)-2}"

# ───────────────────────────────────────── gitignore
def load_gitignore(root: Path) -> Set[str]:
    gi = root / ".gitignore"
    if not gi.exists():
        return set()
    return {
        line.strip()
        for line in gi.read_text("utf-8", errors="ignore").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }

def path_is_ignored(path: Path, root: Path, patterns: Set[str]) -> bool:
    try:
        rel = path.relative_to(root)
    except ValueError:
        return True
    for pat in patterns:
        if pat.endswith("/") and fnmatch.fnmatch(f"{rel}/", pat):
            return True
        if fnmatch.fnmatch(str(rel), pat) or fnmatch.fnmatch(path.name, pat):
            return True
    return False

# ───────────────────────────────────────── static analysis
def build_import_map(root: Path, py_files: List[Path], progress: gr.Progress) -> Dict[Path, Set[Path]]:
    progress(0.35, desc="import依存関係を解析中...")
    module_of = {".".join(p.relative_to(root).with_suffix("").parts): p for p in py_files}
    mapping: Dict[Path, Set[Path]] = defaultdict(set)
    for i, pf in enumerate(py_files):
        if stop_event.is_set():
            break
        try:
            tree = ast.parse(pf.read_text("utf-8", errors="ignore"))
        except (SyntaxError, UnicodeDecodeError):
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for a in node.names:
                    tgt = module_of.get(a.name.split(".")[0])
                    if tgt:
                        mapping[pf].add(tgt)
            elif isinstance(node, ast.ImportFrom) and node.module:
                tgt = module_of.get(node.module.split(".")[0])
                if tgt:
                    mapping[pf].add(tgt)
        if i % 10 == 0:
            progress(0.35 + (0.1 * i / len(py_files)), desc=f"import解析中... ({i+1}/{len(py_files)})")
    return mapping

def degree_centrality(mapping: Dict[Path, Set[Path]]) -> Dict[Path, float]:
    if not nx:
        return {k: len(v) for k, v in mapping.items()}
    g = nx.DiGraph()
    for s, tgts in mapping.items():
        for t in tgts:
            g.add_edge(s, t)
    return nx.degree_centrality(g)

# ───────────────────────────────────────── scoring helpers
def loc_count(path: Path) -> int:
    try:
        return sum(1 for _ in path.open("r", encoding="utf-8", errors="ignore"))
    except Exception:
        return 0

def file_score(path: Path, root: Path, cent: Dict[Path, float]) -> float:
    score = EXT_WEIGHT.get(path.suffix.lower(), 0)
    score += next((PATH_WEIGHT[p] for p in path.parts if p in PATH_WEIGHT), 0)
    score += cent.get(path, 0) * 5
    lines = loc_count(path)
    if lines:
        score += min(log2(lines + 1) / 5, 3)
    return score

# ───────────────────────────────────────── file collection
def collect_files(root: Path, max_single_mb: int, progress: gr.Progress) -> List[Path]:
    progress(0.05, desc=f"フォルダをスキャン中... ({root.name})")
    patterns = load_gitignore(root)
    cap_total = TOTAL_SIZE_CAP_MB * 1024 * 1024
    cap_single = max_single_mb * 1024 * 1024
    cand: List[Path] = []

    progress(0.1, desc="ファイル一覧を取得中...")
    try:
        entries = list(root.rglob("*"))
    except (PermissionError, FileNotFoundError):
        return []
    total_entries = len(entries)
    for i, p in enumerate(entries):
        if stop_event.is_set():
            break
        if any(p.is_relative_to(root / ig) for ig in DEFAULT_IGNORED_DIRS if (root / ig).exists()):
            continue
        if path_is_ignored(p, root, patterns):
            continue
        if (p.is_file() and 
            p.suffix.lower() in FILE_TYPES and 
            p.stat().st_size <= cap_single):
            if os.name == "nt" and len(str(EXPORT_ROOT / p.relative_to(root))) > WIN_PATH_CAP:
                continue
            cand.append(p)
        if i % 100 == 0:
            progress(0.1 + (0.15 * i / total_entries), desc=f"ファイル収集中... ({len(cand)}件)")
    if not cand:
        return []
    progress(0.3, desc="重要度を計算中...")
    py = [p for p in cand if p.suffix == ".py"]
    if py:
        cent = degree_centrality(build_import_map(root, py, progress))
    else:
        cent = {}
    progress(0.5, desc="ファイルを重要度順にソート中...")
    cand.sort(key=lambda p: file_score(p, root, cent), reverse=True)
    progress(0.6, desc="サイズ制限内でファイルを選択中...")
    sel: List[Path] = []
    total = 0
    for i, p in enumerate(cand):
        if stop_event.is_set():
            break
        size = p.stat().st_size
        if total + size > cap_total:
            continue
        sel.append(p)
        total += size
        if i % 50 == 0:
            progress(0.6 + (0.2 * i / len(cand)), desc=f"ファイル選択中... ({len(sel)}件)")
    progress(0.8, desc=f"ファイル収集完了: {len(sel)}件")
    return sel

# ───────────────────────────────────────── helpers for export
def make_tree(root: Path, files: List[Path]) -> str:
    tree_dict: Dict[str, Dict] = {}
    for f in files:
        try:
            rel_path = f.relative_to(root)
        except ValueError:
            continue
        node = tree_dict
        for part in rel_path.parts:
            node = node.setdefault(part, {})
    lines = [f"./ ({root.name})"]
    def dfs(d: Dict[str, Dict], pref: str = ""):
        items = sorted(d.keys())
        for i, k in enumerate(items):
            conn = "└── " if i == len(items) - 1 else "├── "
            lines.append(f"{pref}{conn}{k}")
            if d[k]:
                extension = "    " if i == len(items) - 1 else "│   "
                dfs(d[k], pref + extension)
    dfs(tree_dict)
    return "\n".join(lines)

def def_class_only(path: Path) -> List[str]:
    try:
        lines = path.read_text("utf-8", errors="ignore").splitlines()
        return [
            f"{path.name}: {ln.strip()}"
            for ln in lines
            if ln.lstrip().startswith(("def ", "class "))
        ]
    except Exception:
        return []

def combine_py(py_files: List[Tuple[Path, Path]], out_dir: Path, progress: gr.Progress):
    if not py_files:
        return
    progress(0.85, desc="Pythonファイルを統合中...")
    buf: List[str] = []
    idx = 1
    for i, (rt, pf) in enumerate(py_files):
        if stop_event.is_set():
            break
        try:
            rel = pf.relative_to(rt)
        except ValueError:
            rel = Path(pf.name)
        buf.append(f"\n# === {rt.name}/{rel} ===")
        try:
            content = pf.read_text("utf-8", errors="ignore")
            buf.extend(content.splitlines())
        except Exception:
            buf.append("# エラー: ファイルを読み込めませんでした")
        if len(buf) >= MAX_LINES_PER_FILE:
            output_file = out_dir / f"combined_{idx}.py"
            output_file.write_text("\n".join(buf), "utf-8", errors="ignore")
            buf, idx = [], idx + 1
        if i % 5 == 0:
            progress(0.85 + (0.05 * i / len(py_files)), desc=f"Python統合中... ({i+1}/{len(py_files)})")
    if buf:
        output_file = out_dir / f"combined_{idx}.py"
        output_file.write_text("\n".join(buf), "utf-8", errors="ignore")

# ───────────────────────────────────────── 修正されたプロキシ
class ProgressProxy:
    def __init__(self, main_progress: gr.Progress, scale_factor: float, offset: float):
        self.main_progress = main_progress
        self.scale_factor = scale_factor
        self.offset = offset
    def __call__(self, *args, **kwargs):
        value = 0.0
        desc = ""
        if args:
            value = float(args[0])
        if 'desc' in kwargs:
            desc = kwargs['desc']
        elif len(args) > 1:
            desc = str(args[1])
        scaled_value = self.offset + (value * self.scale_factor)
        try:
            self.main_progress(scaled_value, desc=desc)
        except Exception:
            self.main_progress(scaled_value)

# ───────────────────────────────────────── project export (multi-root)
def export_multi(roots: List[Path], max_single_mb: int, progress: gr.Progress) -> Path:
    progress(0, desc="エクスポートを開始中...")
    time.sleep(0.2)
    project_prefix = generate_project_prefix(roots)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    session = EXPORT_ROOT / f"{project_prefix}_export_{ts}"
    session.mkdir(parents=True, exist_ok=True)

    all_files: List[Tuple[Path, Path]] = []
    for idx, rt in enumerate(roots, 1):
        if stop_event.is_set():
            raise RuntimeError("エクスポートがキャンセルされました")
        progress(0.1 * idx / len(roots), desc=f"フォルダ解析中... ({rt.name})")
        scale_factor = 0.8 / len(roots)
        offset = 0.1 * (idx - 1) / len(roots)
        sub_progress = ProgressProxy(progress, scale_factor, offset)
        sub_files = collect_files(rt, max_single_mb, sub_progress)
        all_files.extend([(rt, f) for f in sub_files])

    if stop_event.is_set() or not all_files:
        raise RuntimeError("キャンセルされたか、処理対象ファイルがありません")

    progress(0.82, desc="ファイルをコピー中...")
    tree_sections: List[str] = []
    summary_lines: List[str] = []
    py_files: List[Tuple[Path, Path]] = []

    info_header = [
        f"=== {project_prefix} プロジェクト解析結果 ===",
        f"エクスポート日時: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"分析対象フォルダ数: {len(roots)}",
        f"分析対象フォルダ:",
        *[f"  - {root}" for root in roots],
        f"総ファイル数: {len(all_files)}",
        "",
    ]

    total_files = len(all_files)
    for file_idx, (rt, f) in enumerate(all_files):
        if stop_event.is_set():
            break
        try:
            dst = session / "source_code" / rt.name / f.relative_to(rt)
        except ValueError:
            continue
        if os.name == "nt" and len(str(dst)) > WIN_PATH_CAP:
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        try:
            dst.write_bytes(f.read_bytes())
        except (OSError, PermissionError):
            continue
        if f.suffix == ".py":
            summary_lines.extend(def_class_only(f))
            py_files.append((rt, f))
        if file_idx % 10 == 0:
            progress(0.82 + (0.03 * file_idx / total_files),
                    desc=f"ファイルコピー中... ({file_idx+1}/{total_files})")

    progress(0.88, desc="プロジェクト構造を生成中...")
    for rt in roots:
        root_files = [f for r, f in all_files if r == rt]
        if root_files:
            tree_sections.append(make_tree(rt, root_files))
            tree_sections.append("")

    (session / "project_info.txt").write_text("\n".join(info_header), "utf-8")
    (session / "project_structure.txt").write_text("\n".join(tree_sections), "utf-8")
    (session / "summary_def_class.txt").write_text("\n".join(summary_lines), "utf-8")

    if py_files:
        combine_py(py_files, session, progress)

    progress(0.95, desc="ZIPアーカイブを作成中...")
    zip_path = EXPORT_ROOT / f"{project_prefix}_source_{ts}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in session.rglob("*"):
            if f.is_file():
                try:
                    zf.write(f, arcname=f.relative_to(session))
                except Exception:
                    continue

    progress(1.0, desc="エクスポート完了!")
    time.sleep(0.3)
    return zip_path

# ───────────────────────────────────────── gradio callbacks
def run_export(roots_str: str, max_mb: int, cancelling: bool, progress=gr.Progress(track_tqdm=True)):
    if cancelling:
        return None, "⚠️ キャンセル中...", True
    stop_event.clear()
    roots_list = [p.strip() for p in roots_str.splitlines() if p.strip()]
    if not roots_list:
        return None, "⚠️ 少なくとも1つのフォルダを選択してください", False
    roots = []
    for path_str in roots_list:
        try:
            path = Path(path_str).expanduser().resolve()
            if not path.exists():
                return None, f"⚠️ フォルダが存在しません: {path_str}", False
            if not path.is_dir():
                return None, f"⚠️ フォルダではありません: {path_str}", False
            roots.append(path)
        except Exception:
            return None, f"⚠️ 無効なパス: {path_str}", False
    try:
        progress(0, desc="エクスポートを準備中...")
        zp = export_multi(roots, max_mb, progress)
        mb = zp.stat().st_size / (1024 * 1024)
        project_prefix = generate_project_prefix(roots)
        success_msg = f"""✅ エクスポート完了!
プロジェクト: {project_prefix}
ファイルサイズ: {mb:.1f} MB
出力場所: {zp}
処理フォルダ数: {len(roots)}

分析対象フォルダ:
{chr(10).join(f"  📁 {root.name} ({root})" for root in roots)}"""
        return str(zp), success_msg, False
    except Exception as e:
        error_msg = f"""❌ エラーが発生しました:
{str(e)}

詳細:
{traceback.format_exc(limit=3)}"""
        return None, error_msg, False

def cancel_export(_: bool):
    stop_event.set()
    return "⏹️ キャンセル信号を送信しました", True

def browse_and_append(existing: str):
    try:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        path = filedialog.askdirectory(title="プロジェクトフォルダを選択")
        root.destroy()
        if path:
            paths = [p.strip() for p in existing.splitlines() if p.strip()]
            if path not in paths:
                paths.append(path)
            return "\n".join(paths)
    except Exception:
        pass
    return existing

def show_naming_preview(roots_str: str):
    roots_list = [p.strip() for p in roots_str.splitlines() if p.strip()]
    if not roots_list:
        return "⚠️ フォルダを選択してください"
    try:
        roots = [Path(p).name for p in roots_list]
        prefix = generate_project_prefix([Path(p) for p in roots_list])
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        preview = f"""📋 ファイル名プレビュー:

📁 エクスポートフォルダ: {prefix}_export_{ts}/
📦 ZIPファイル: {prefix}_source_{ts}.zip

🎯 分析対象フォルダ ({len(roots)}個):
{chr(10).join(f"  • {folder}" for folder in roots)}"""
        return preview
    except Exception as e:
        return f"⚠️ プレビュー生成エラー: {str(e)}"

# ───────────────────────────────────────── UI
def create_interface():
    with gr.Blocks(
        title="Code Export (Error Fixed)",
        css=".gr-button{min-width:6rem} .gr-textbox{font-family:monospace}",
        theme=gr.themes.Soft()
    ) as demo:
        gr.Markdown("""
        ## 📦 重要度認識コードエクスポートツール (エラー修正版)

        **機能**: プロジェクトの重要なファイルを自動判定し、**フォルダ名付き**で統合エクスポート  
        **修正**: sub_progress引数競合エラーを完全修正  
        **制限**: 合計99MB以下、単一ファイル最大50MB  
        **対応**: 複数フォルダ同時処理、リアルタイム進行度表示、**分析対象フォルダ名を含むファイル名**
        """)
        with gr.Row():
            with gr.Column(scale=3):
                dirs_tb = gr.Textbox(
                    label="📁 選択されたプロジェクトフォルダ (1行につき1つ)",
                    placeholder="例: C:/Users/USER/tools/NexusCore\n例: /home/user/project",
                    lines=3
                )
            with gr.Column(scale=1):
                browse_btn = gr.Button("📂 参照して追加", size="sm")
        with gr.Row():
            preview_btn = gr.Button("👁️ ファイル名プレビュー", variant="secondary", size="sm")
        naming_preview = gr.Textbox(
            label="📋 出力ファイル名プレビュー",
            lines=4,
            interactive=False,
            visible=False
        )
        with gr.Row():
            max_slider = gr.Slider(minimum=1, maximum=50, value=10, step=1, label="🔧 単一ファイル最大サイズ (MB)")
        gr.Markdown("### 🚀 実行")
        with gr.Row():
            exp_btn = gr.Button("▶️ エクスポート開始", variant="primary", size="lg")
            cancel_btn = gr.Button("⏹️ キャンセル", variant="secondary")
        gr.Markdown("### 📤 結果")
        zip_out = gr.File(label="📦 エクスポートファイル (ZIP)")
        status = gr.Textbox(label="📋 ステータス", lines=8, max_lines=15, show_copy_button=True)
        cancelling_state = gr.State(False)
        browse_btn.click(fn=browse_and_append, inputs=[dirs_tb], outputs=[dirs_tb])
        preview_btn.click(fn=show_naming_preview, inputs=[dirs_tb], outputs=[naming_preview]).then(
            fn=lambda: gr.update(visible=True), outputs=[naming_preview]
        )
        exp_btn.click(
            fn=run_export, inputs=[dirs_tb, max_slider, cancelling_state],
            outputs=[zip_out, status, cancelling_state],
            show_progress="full"
        )
        cancel_btn.click(fn=cancel_export, inputs=[cancelling_state], outputs=[status, cancelling_state])
        demo.queue(default_concurrency_limit=1, max_size=10)
    return demo

if __name__ == "__main__":
    print("🚀 Code Export GUI (Error Fixed) を起動中...")
    print(f"📁 エクスポート先: {EXPORT_ROOT}")
    demo = create_interface()
    demo.launch(inbrowser=True, allowed_paths=[str(EXPORT_ROOT)], server_name="127.0.0.1", server_port=7860, share=False)
