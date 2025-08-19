"""code_export_gui.py — importance‑aware export (ルール + 静的メタ解析)
Fully expanded script – 2025‑07‑23 rev‑6  (multi‑root + combine fix)
────────────────────────────────────────────────────────
* Layer‑① ルールベース（拡張子・パス・サイズ）
* Layer‑② 静的メタ解析（import 結合度 + LOC）
* **複数フォルダ選択** OK
* **combine_py バグ修正** ← ファイルが異なる root に属するとき `relative_to()` で ValueError が出ていた問題を解消
* exports/ 除外／Windows Path Limit 対策／99 MB 上限／Cancel／Progress はそのまま
"""
from __future__ import annotations
import ast
import datetime
import fnmatch
import os
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

# ───────────────────────────────────────── gitignore

def load_gitignore(root: Path) -> Set[str]:
    gi = root / ".gitignore"
    if not gi.exists():
        return set()
    return {
        line.strip()
        for line in gi.read_text("utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }

def path_is_ignored(path: Path, root: Path, patterns: Set[str]) -> bool:
    rel = path.relative_to(root)
    for pat in patterns:
        if pat.endswith("/") and fnmatch.fnmatch(f"{rel}/", pat):
            return True
        if fnmatch.fnmatch(str(rel), pat) or fnmatch.fnmatch(path.name, pat):
            return True
    return False

# ───────────────────────────────────────── static analysis

def build_import_map(root: Path, py_files: List[Path]) -> Dict[Path, Set[Path]]:
    module_of = {".".join(p.relative_to(root).with_suffix("").parts): p for p in py_files}
    mapping: Dict[Path, Set[Path]] = defaultdict(set)
    for pf in py_files:
        try:
            tree = ast.parse(pf.read_text("utf-8", "ignore"))
        except SyntaxError:
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
    patterns = load_gitignore(root)
    cap_total = TOTAL_SIZE_CAP_MB * 1024 * 1024
    cap_single = max_single_mb * 1024 * 1024

    cand: List[Path] = []
    entries = list(root.rglob("*"))
    for p in entries:
        if stop_event.is_set():
            break
        if any(p.is_relative_to(root / ig) for ig in DEFAULT_IGNORED_DIRS):
            continue
        if path_is_ignored(p, root, patterns):
            continue
        if p.is_file() and p.suffix.lower() in FILE_TYPES and p.stat().st_size <= cap_single:
            if os.name == "nt" and len(str(EXPORT_ROOT / p.relative_to(root))) > WIN_PATH_CAP:
                continue
            cand.append(p)

    py = [p for p in cand if p.suffix == ".py"]
    cent = degree_centrality(build_import_map(root, py))
    cand.sort(key=lambda p: file_score(p, root, cent), reverse=True)

    sel: List[Path] = []
    total = 0
    for i, p in enumerate(cand, 1):
        if stop_event.is_set():
            break
        progress(0.3 * i / len(cand))
        size = p.stat().st_size
        if total + size > cap_total:
            continue
        sel.append(p)
        total += size
    return sel

# ───────────────────────────────────────── helpers for export

def make_tree(root: Path, files: List[Path]) -> str:
    tree_dict: Dict[str, Dict] = {}
    for f in files:
        node = tree_dict
        for part in f.relative_to(root).parts:
            node = node.setdefault(part, {})
    lines = [f"./ ({root})"]
    def dfs(d: Dict[str, Dict], pref: str = ""):
        for i, k in enumerate(sorted(d)):
            conn = "└── " if i == len(d) - 1 else "├── "
            lines.append(f"{pref}{conn}{k}")
            if d[k]:
                dfs(d[k], pref + ("    " if i == len(d) - 1 else "│   "))
    dfs(tree_dict)
    return "\n".join(lines)

def def_class_only(path: Path) -> List[str]:
    return [
        f"{path.name}: {ln.strip()}"
        for ln in path.read_text("utf-8", "ignore").splitlines()
        if ln.lstrip().startswith(("def ", "class "))
    ]

# >>> FIXED: combine_py now handles files from multiple roots safely <<<

def combine_py(py_files: List[Tuple[Path, Path]], out_dir: Path):
    """py_files: list of (root, file)"""
    buf: List[str] = []
    idx = 1
    for rt, pf in py_files:
        try:
            rel = pf.relative_to(rt)
        except ValueError:
            rel = pf.name  # fallback
        buf.append(f"\n# === {rt.name}/{rel} ===")
        buf.extend(pf.read_text("utf-8", "ignore").splitlines())
        if len(buf) >= MAX_LINES_PER_FILE:
            (out_dir / f"combined_{idx}.py").write_text("\n".join(buf), "utf-8")
            buf, idx = [], idx + 1
    if buf:
        (out_dir / f"combined_{idx}.py").write_text("\n".join(buf), "utf-8")

# ───────────────────────────────────────── project export (multi‑root)

def export_multi(roots: List[Path], max_single_mb: int, progress: gr.Progress) -> Path:
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    session = EXPORT_ROOT / f"export_{ts}"
    session.mkdir(parents=True, exist_ok=True)

    all_files: List[Tuple[Path, Path]] = []  # (root, file)
    for idx, rt in enumerate(roots, 1):
        sub_prog = gr.Progress(track_tqdm=False)
        sub_files = collect_files(rt, max_single_mb, sub_prog)
        all_files.extend([(rt, f) for f in sub_files])
        progress(0.2 * idx / len(roots))

    if stop_event.is_set() or not all_files:
        raise RuntimeError("Cancelled or no files selected")

    tree_sections: List[str] = []
    summary_lines: List[str] = []
    py_files: List[Tuple[Path, Path]] = []

    for rt, f in all_files:
        dst = session / "source_code" / rt.name / f.relative_to(rt)
        if os.name == "nt" and len(str(dst)) > WIN_PATH_CAP:
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        try:
            dst.write_bytes(f.read_bytes())
        except OSError:
            continue
        if f.suffix == ".py":
            summary_lines.extend(def_class_only(f))
            py_files.append((rt, f))

    # structure texts
    for rt in roots:
        tree_sections.append(make_tree(rt, [f for r, f in all_files if r == rt]))
        tree_sections.append("")
    (session / "project_structure.txt").write_text("\n".join(tree_sections), "utf-8")
    (session / "summary_def_class.txt").write_text("\n".join(summary_lines), "utf-8")
    combine_py(py_files, session)

    zip_path = EXPORT_ROOT / f"source_{ts}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in session.rglob("*"):
            zf.write(f, arcname=f.relative_to(session))
    progress(1)
    return zip_path

# ───────────────────────────────────────── gradio callbacks

def run_export(roots_str: str, max_mb: int, cancelling: bool, progress=gr.Progress(track_tqdm=False)):
    if cancelling:
        return None, "⚠️ cancelling…", True
    stop_event.clear()
    roots = [Path(p.strip()).expanduser().resolve() for p in roots_str.splitlines() if p.strip()]
    if not roots:
        return None, "⚠️ select at least one folder", False
    try:
        zp = export_multi(roots, max_mb, progress)
        mb = zp.stat().st_size / (1024 * 1024)
        return str(zp), f"✅ Done: {mb:.1f} MB", False
    except Exception:
        return None, f"❌ {traceback.format_exc(limit=5)}", False

def cancel_export(_: bool):
    stop_event.set()
    return "⏹️ cancel signal", True


def browse_and_append(existing: str):
    try:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk()
        root.withdraw()
        path = filedialog.askdirectory(title="Select folder")
        root.destroy()
        if path:
            paths = existing.splitlines()
            if path not in paths:
                paths.append(path)
            return "\n".join(paths)
    except Exception:
        pass
    return existing

# ───────────────────────────────────────── UI
with gr.Blocks(title="Code Export (multi‑root)", css=".gr-button{min-width:6rem}") as demo:
    gr.Markdown("## 📦 Importance‑Aware Code Export (≤99 MB, multi‑root)")

    dirs_tb = gr.Textbox(label="Selected root directories (one per line)")
    browse_btn = gr.Button("📂 Browse & add")

    max_slider = gr.Slider(1, 50, value=10, step=1, label="Max single file size (MB)")

    with gr.Row():
        exp_btn = gr.Button("🚀 Export", variant="primary")
        cancel_btn = gr.Button("🛑 Cancel")

    zip_out = gr.File(label="ZIP")
    status = gr.Textbox(label="Status", lines=4)
    cancelling_state = gr.State(False)

    browse_btn.click(browse_and_append, inputs=[dirs_tb], outputs=[dirs_tb])
    exp_btn.click(run_export, inputs=[dirs_tb, max_slider, cancelling_state], outputs=[zip_out, status, cancelling_state])
    cancel_btn.click(cancel_export, inputs=[cancelling_state], outputs=[status, cancelling_state])

if __name__ == "__main__":
    demo.launch(inbrowser=True, allowed_paths=[str(EXPORT_ROOT)])
