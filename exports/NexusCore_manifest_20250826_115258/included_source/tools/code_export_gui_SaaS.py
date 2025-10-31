# ======================================================================
# code_export_gui_SaaS.py — SaaS向けプロファイル切替 + .env.redacted 生成
# プロファイル: Safe Share / Repro Build / Audit Pack
# 2025-08-09 v1
# ======================================================================

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
    import networkx as nx
except ImportError:
    nx = None

# --- ベースの除外（ユーザ最終リスト） ---
BASE_IGNORED_DIRS = {
    ".git", "__pycache__", "node_modules", "dist", "build", ".venv", "venv",
    ".idea", ".vscode", ".mypy_cache", ".pytest_cache", "htmlcov", ".gradio", "exports",
    "openenv", "myenv", "old_tool",
    "quality_loop_test_sandbox", "result_images", "sandbox_repo", "scripts", "output",
    "patch_history", "policy_test_sandbox", "project_structure_export", "quality_gate_test_sandbox",
    "test_cache",
}
BASE_IGNORED_FILES = {
    ".coverage", ".env", ".env.template", ".gitattributes", ".gitignore", ".nexus_context.json",
    ".python-version", "nexus_api_server.log", "nexus_core_run.log", "orchestrator_test.log",
    "quality_gate_test_run.log", "OpenCodeInterpreter.code-workspace", "launch.bat", "launch_all.ps1",
    "launch_dev.ps1", "LICENSE", "project_chronicle.jsonl", "project_structure.json",
    "fix_imports.py", "gradio_app.py", "main_cli.py", "project_structure_and_code_export.py",
    "pytest.ini", "vscode-extension.zip",
}

# --- プロファイル定義 ---
PROFILES = {
    "Safe Share": {
        "keep": {
            "requirements.txt", "pyproject.toml", "project_structure.json",
            ".env.template", "README.md", "ARCHITECTURE.md",
            "openapi.yaml", "openapi.json",
        },
        "include_dirs": set(),  # 追加取り込み無し
    },
    "Repro Build": {
        "keep": {
            "requirements.txt", "pyproject.toml", ".env.template", "README.md",
            "poetry.lock", "Pipfile.lock", "uv.lock",
            "Dockerfile", "docker-compose.yml",
            "Makefile", "Justfile",
            "alembic.ini", "project_structure.json",
        },
        "include_dirs": {"migrations", "infra", "deploy", "k8s", "helm"},
    },
    "Audit Pack": {
        "keep": {
            "requirements.txt", "pyproject.toml", ".env.template", "README.md",
            "poetry.lock", "Pipfile.lock", "uv.lock",
            "Dockerfile", "docker-compose.yml",
            "Makefile", "Justfile",
            "openapi.yaml", "openapi.json", "THIRD_PARTY_NOTICES.md",
            "project_structure.json",
        },
        "include_dirs": {"migrations", "infra", "deploy", "k8s", "helm", ".github/workflows"},
    },
}
DEFAULT_PROFILE = "Safe Share"  # 起動デフォルト

FILE_TYPES: Tuple[str, ...] = (
    ".py", ".ipynb", ".md", ".txt", "package.json", ".json", ".yml", ".yaml", ".toml",
)

MAX_LINES_PER_FILE = 10_000
TOTAL_SIZE_CAP_MB = 99
WIN_PATH_CAP = 250
EXPORT_ROOT = Path("./exports").resolve()
EXPORT_ROOT.mkdir(exist_ok=True)

EXT_WEIGHT = {".py": 3, ".ipynb": 2, ".md": 1}
PATH_WEIGHT = {"src": 2, "app": 2, "lib": 1, "tests": -1, "docs": -1}

stop_event = Event()

def sanitize_name(name: str) -> str:
    invalid_chars = r'[<>:"/\\|?*\x00-\x1f]'
    s = re.sub(invalid_chars, '_', name)
    s = re.sub(r'_+', '_', s).strip('_') or "Unknown"
    return s[:50]

def generate_project_prefix(roots: List[Path]) -> str:
    if not roots: return "Export"
    names = [sanitize_name(r.name) for r in roots]
    if len(names) == 1: return names[0]
    return "-".join(names) if len(names) <= 3 else f"{'-'.join(names[:2])}-etc{len(names)-2}"

def load_gitignore(root: Path) -> Set[str]:
    gi = root / ".gitignore"
    if not gi.exists(): return set()
    return {
        line.strip()
        for line in gi.read_text("utf-8", errors="ignore").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }

def should_force_include(path: Path, keep_set: Set[str]) -> bool:
    return path.is_file() and (path.name in keep_set)

def path_is_ignored(path: Path, root: Path, patterns: Set[str], include_dirs: Set[str]) -> bool:
    if EXPORT_ROOT in path.parents or path == EXPORT_ROOT:
        return True
    # include_dirs は除外を打ち消す（優先許可）
    for inc in include_dirs:
        try:
            if (root / inc) in path.parents:
                return False
        except Exception:
            pass
    # ユーザの除外
    for d in BASE_IGNORED_DIRS:
        try:
            if (root / d) in path.parents:
                return True
        except Exception:
            pass
    try:
        rel = path.relative_to(root)
    except ValueError:
        return True
    for pat in patterns:
        if pat.endswith("/") and fnmatch.fnmatch(f"{rel}/", pat):
            return True
        if fnmatch.fnmatch(str(rel), pat) or fnmatch.fnmatch(path.name, pat):
            return True
    if path.is_file() and path.name in BASE_IGNORED_FILES:
        return True
    return False

def build_import_map(root: Path, py_files: List[Path], progress: gr.Progress) -> Dict[Path, Set[Path]]:
    progress(0.35, desc="import依存解析中...")
    module_of = {".".join(p.relative_to(root).with_suffix("").parts): p for p in py_files}
    mapping: Dict[Path, Set[Path]] = defaultdict(set)
    for i, pf in enumerate(py_files):
        if stop_event.is_set(): break
        try:
            tree = ast.parse(pf.read_text("utf-8", errors="ignore"))
        except (SyntaxError, UnicodeDecodeError):
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for a in node.names:
                    tgt = module_of.get(a.name.split(".")[0])
                    if tgt: mapping[pf].add(tgt)
            elif isinstance(node, ast.ImportFrom) and node.module:
                tgt = module_of.get(node.module.split(".")[0])
                if tgt: mapping[pf].add(tgt)
        if i % 10 == 0 and py_files:
            progress(0.35 + (0.1 * i / len(py_files)), desc=f"import解析中... ({i+1}/{len(py_files)})")
    return mapping

def degree_centrality(mapping: Dict[Path, Set[Path]]) -> Dict[Path, float]:
    if not nx: return {k: float(len(v)) for k, v in mapping.items()}
    g = nx.DiGraph()
    for s, tgts in mapping.items():
        for t in tgts: g.add_edge(s, t)
    return nx.degree_centrality(g)

def loc_count(path: Path) -> int:
    try: return sum(1 for _ in path.open("r", encoding="utf-8", errors="ignore"))
    except Exception: return 0

def file_score(path: Path, root: Path, cent: Dict[Path, float]) -> float:
    score = EXT_WEIGHT.get(path.suffix.lower(), 0)
    score += next((PATH_WEIGHT[p] for p in path.parts if p in PATH_WEIGHT), 0)
    score += cent.get(path, 0) * 5
    lines = loc_count(path)
    if lines: score += min(log2(lines + 1) / 5, 3)
    return score

def write_redacted_env(src_env: Path, out_dir: Path):
    """値を '****' にマスクした .env.redacted を出力"""
    try:
        lines = src_env.read_text("utf-8", errors="ignore").splitlines()
        out = []
        for ln in lines:
            if not ln or ln.strip().startswith("#") or "=" not in ln:
                out.append(ln); continue
            k, v = ln.split("=", 1)
            out.append(f"{k}=****")
        (out_dir / ".env.redacted").write_text("\n".join(out), "utf-8")
    except Exception:
        pass

def collect_files(root: Path, max_single_mb: int, progress: gr.Progress, keep_set: Set[str], include_dirs: Set[str]) -> List[Path]:
    progress(0.05, desc=f"スキャン中... ({root.name})")
    patterns = load_gitignore(root)
    cap_total = TOTAL_SIZE_CAP_MB * 1024 * 1024
    cap_single = max_single_mb * 1024 * 1024
    cand: List[Path] = []

    progress(0.1, desc="一覧取得...")
    try:
        entries = list(root.rglob("*"))
    except (PermissionError, FileNotFoundError):
        return []

    total_entries = len(entries)
    for i, p in enumerate(entries):
        if stop_event.is_set(): break

        if should_force_include(p, keep_set):
            cand.append(p)
        else:
            if not path_is_ignored(p, root, patterns, include_dirs):
                if p.is_file() and (p.suffix.lower() in FILE_TYPES) and (p.stat().st_size <= cap_single):
                    if os.name == "nt":
                        try:
                            potential = EXPORT_ROOT / p.relative_to(root)
                            if len(str(potential)) > WIN_PATH_CAP:
                                p = None
                        except ValueError:
                            p = None
                    if p is not None:
                        cand.append(p)

        if i % 100 == 0 and total_entries:
            progress(0.1 + (0.15 * i / total_entries), desc=f"収集中... ({len(cand)}件)")

    if not cand: return []

    progress(0.3, desc="重要度計算...")
    py = [p for p in cand if p.suffix == ".py"]
    cent = degree_centrality(build_import_map(root, py, progress)) if py else {}

    progress(0.5, desc="重要度ソート...")
    cand.sort(key=lambda p: file_score(p, root, cent), reverse=True)

    # KEEP → .py → その他（合計サイズ内）
    progress(0.6, desc="選別中...")
    sel: List[Path] = []
    total = 0

    for group in [
        [x for x in cand if x.name in keep_set],
        [x for x in cand if x.suffix == ".py" and x.name not in keep_set],
        [x for x in cand if x not in sel and x.name not in keep_set],
    ]:
        for i, p in enumerate(group):
            if stop_event.is_set(): break
            size = p.stat().st_size
            if total + size > cap_total: continue
            if p not in sel:
                sel.append(p); total += size
        if stop_event.is_set(): break

    progress(0.8, desc=f"選別完了: {len(sel)}件")
    return sel

def make_tree(root: Path, files: List[Path]) -> str:
    tree_dict: Dict[str, Dict] = {}
    for f in files:
        try: rel = f.relative_to(root)
        except ValueError: continue
        node = tree_dict
        for part in rel.parts: node = node.setdefault(part, {})
    lines = [f"./ ({root.name})"]
    def dfs(d: Dict[str, Dict], pref=""):
        items = sorted(d.keys())
        for i, k in enumerate(items):
            conn = "└── " if i == len(items)-1 else "├── "
            lines.append(f"{pref}{conn}{k}")
            if d[k]:
                dfs(d[k], pref + ("    " if i == len(items)-1 else "│   "))
    dfs(tree_dict)
    return "\n".join(lines)

def combine_py(py_files: List[Tuple[Path, Path]], out_dir: Path, progress: gr.Progress):
    if not py_files: return
    progress(0.85, desc="Python統合中...")
    buf: List[str] = []; idx = 1
    for i, (rt, pf) in enumerate(py_files):
        if stop_event.is_set(): break
        try: rel = pf.relative_to(rt)
        except ValueError: rel = Path(pf.name)
        buf.append(f"\n# === {rt.name}/{rel} ===")
        try:
            content = pf.read_text("utf-8", errors="ignore"); buf.extend(content.splitlines())
        except Exception:
            buf.append("# 読み込み失敗")
        if len(buf) >= MAX_LINES_PER_FILE:
            (out_dir / f"combined_{idx}.py").write_text("\n".join(buf), "utf-8", errors="ignore")
            buf, idx = [], idx + 1
        if i % 5 == 0:
            progress(0.85 + (0.05 * i / len(py_files)), desc=f"統合中... ({i+1}/{len(py_files)})")
    if buf:
        (out_dir / f"combined_{idx}.py").write_text("\n".join(buf), "utf-8", errors="ignore")

def export_multi(roots: List[Path], max_single_mb: int, progress: gr.Progress, profile: str, redact_env: bool) -> Path:
    progress(0, desc=f"エクスポート開始（{profile}）...")
    time.sleep(0.2)
    project_prefix = generate_project_prefix(roots)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    session = EXPORT_ROOT / f"{project_prefix}_{profile.replace(' ', '')}_{ts}"
    session.mkdir(parents=True, exist_ok=True)

    prof_def = PROFILES.get(profile, PROFILES[DEFAULT_PROFILE])
    keep_set: Set[str] = set(prof_def["keep"])
    include_dirs: Set[str] = set(prof_def["include_dirs"])

    all_files: List[Tuple[Path, Path]] = []
    for idx, rt in enumerate(roots, 1):
        if stop_event.is_set(): raise RuntimeError("キャンセルされました")
        progress(0.1 * idx / len(roots), desc=f"フォルダ解析中... ({rt.name})")
        class SubProgress:
            def __call__(self, value, desc=""):
                progress(0.1 * (idx - 1) / len(roots) + value * 0.7 / len(roots), desc=desc)
        sub_files = collect_files(rt, max_single_mb, SubProgress(), keep_set, include_dirs)
        all_files.extend([(rt, f) for f in sub_files])

        # .env.redacted 生成（任意）
        if redact_env and (rt / ".env").exists():
            try:
                write_redacted_env(rt / ".env", session)
            except Exception:
                pass

    if stop_event.is_set() or not all_files:
        raise RuntimeError("キャンセル or 対象なし")

    progress(0.82, desc="コピー中...")
    tree_sections: List[str] = []
    py_files: List[Tuple[Path, Path]] = []

    info_header = [
        f"=== {project_prefix} Export ({profile}) ===",
        f"エクスポート日時: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"対象フォルダ数: {len(roots)}",
        "対象フォルダ:",
        *[f"  - {root}" for root in roots],
        f"総ファイル数: {len(all_files)}",
        "",
        "KEEP: " + ", ".join(sorted(keep_set)),
        "include_dirs: " + (", ".join(sorted(include_dirs)) if include_dirs else "(なし)"),
        "注意: .env は常に除外。必要時は .env.redacted を利用。",
    ]

    total_files = len(all_files)
    for file_idx, (rt, f) in enumerate(all_files):
        if stop_event.is_set(): break
        try: dst = session / "source_code" / rt.name / f.relative_to(rt)
        except ValueError: continue
        if os.name == "nt" and len(str(dst)) > WIN_PATH_CAP: continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        try: dst.write_bytes(f.read_bytes())
        except (OSError, PermissionError): continue
        if f.suffix == ".py":
            py_files.append((rt, f))
        if file_idx % 10 == 0:
            progress(0.82 + (0.03 * file_idx / total_files), desc=f"コピー中... ({file_idx+1}/{total_files})")

    progress(0.88, desc="構造生成中...")
    for rt in roots:
        root_files = [f for r, f in all_files if r == rt]
        if root_files:
            tree_sections.append(make_tree(rt, root_files))
            tree_sections.append("")
    (session / "project_info.txt").write_text("\n".join(info_header), "utf-8")
    (session / "project_structure.txt").write_text("\n".join(tree_sections), "utf-8")

    if py_files:
        combine_py(py_files, session, progress)

    progress(0.95, desc="ZIP作成中...")
    zip_path = EXPORT_ROOT / f"{project_prefix}_{profile.replace(' ', '')}_{ts}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in session.rglob("*"):
            if f.is_file():
                try: zf.write(f, arcname=f.relative_to(session))
                except Exception: continue

    progress(1.0, desc="完了")
    time.sleep(0.3)
    return zip_path

# --- Gradio UI ---
def run_export(roots_str: str, max_mb: int, profile: str, redact_env: bool, cancelling: bool, progress=gr.Progress(track_tqdm=True)):
    if cancelling: return None, "⚠️ キャンセル中...", True
    stop_event.clear()
    roots_list = [p.strip() for p in roots_str.splitlines() if p.strip()]
    if not roots_list: return None, "⚠️ 少なくとも1つのフォルダを指定してください", False
    roots = []
    for path_str in roots_list:
        try:
            path = Path(path_str).expanduser().resolve()
            if not path.exists(): return None, f"⚠️ 存在しません: {path_str}", False
            if not path.is_dir(): return None, f"⚠️ フォルダではありません: {path_str}", False
            roots.append(path)
        except Exception:
            return None, f"⚠️ 無効なパス: {path_str}", False
    try:
        progress(0, desc="準備中...")
        zp = export_multi(roots, max_mb, progress, profile, redact_env)
        mb = zp.stat().st_size / (1024 * 1024)
        prefix = generate_project_prefix(roots)
        msg = f"""✅ エクスポート完了 ({profile})
プロジェクト: {prefix}
ファイルサイズ: {mb:.1f} MB
出力: {zp}
"""
        return str(zp), msg, False
    except Exception as e:
        return None, f"❌ エラー:\n{str(e)}\n\n詳細:\n{traceback.format_exc(limit=3)}", False

def cancel_export(_: bool):
    stop_event.set()
    return "⏹️ キャンセル信号を送信しました", True

def browse_and_append(existing: str):
    try:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk(); root.withdraw(); root.attributes('-topmost', True)
        path = filedialog.askdirectory(title="プロジェクトフォルダを選択")
        root.destroy()
        if path:
            paths = [p.strip() for p in existing.splitlines() if p.strip()]
            if path not in paths: paths.append(path)
            return "\n".join(paths)
    except Exception:
        pass
    return existing

def preview_output(roots_str: str, profile: str):
    roots_list = [p.strip() for p in roots_str.splitlines() if p.strip()]
    if not roots_list: return "⚠️ フォルダを指定してください"
    try:
        prefix = generate_project_prefix([Path(p) for p in roots_list])
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        keep_set = PROFILES.get(profile, PROFILES[DEFAULT_PROFILE])["keep"]
        include_dirs = PROFILES.get(profile, PROFILES[DEFAULT_PROFILE])["include_dirs"]
        return f"""📋 出力プレビュー

📁 セッションフォルダ: {prefix}_{profile.replace(' ', '')}_{ts}/
📦 ZIP: {prefix}_{profile.replace(' ', '')}_{ts}.zip

プロファイル: {profile}
KEEP: {", ".join(sorted(keep_set)) if keep_set else "(なし)"}
include_dirs: {", ".join(sorted(include_dirs)) if include_dirs else "(なし)"}
"""
    except Exception as e:
        return f"⚠️ プレビュー生成エラー: {str(e)}"

def create_interface():
    with gr.Blocks(title="Code Export (SaaS Profiles)", css=".gr-button{min-width:6rem} .gr-textbox{font-family:monospace}", theme=gr.themes.Soft()) as demo:
        gr.Markdown("## 🧩 SaaS向けコードエクスポート — プロファイル切替 / .env.redacted対応")
        with gr.Row():
            with gr.Column(scale=3):
                dirs_tb = gr.Textbox(label="📁 プロジェクトフォルダ（1行=1フォルダ）", lines=3)
            with gr.Column(scale=1):
                browse_btn = gr.Button("📂 参照して追加", size="sm")
        with gr.Row():
            profile_dd = gr.Dropdown(choices=list(PROFILES.keys()), value=DEFAULT_PROFILE, label="プロファイル")
            redact_ck = gr.Checkbox(value=True, label=".env.redacted を生成（値マスク）")
        with gr.Row():
            preview_btn = gr.Button("👁️ 出力プレビュー", variant="secondary", size="sm")
        naming_preview = gr.Textbox(label="📋 プレビュー", lines=7, interactive=False, visible=False)
        with gr.Row():
            max_slider = gr.Slider(minimum=1, maximum=50, value=10, step=1, label="🔧 単一ファイル最大 (MB)")
        gr.Markdown("### 🚀 実行")
        with gr.Row():
            exp_btn = gr.Button("▶️ エクスポート開始", variant="primary", size="lg")
            cancel_btn = gr.Button("⏹️ キャンセル", variant="secondary")
        gr.Markdown("### 📤 結果")
        zip_out = gr.File(label="📦 ZIP")
        status = gr.Textbox(label="📋 ステータス", lines=8, max_lines=15, show_copy_button=True)
        cancelling_state = gr.State(False)

        browse_btn.click(fn=browse_and_append, inputs=[dirs_tb], outputs=[dirs_tb])
        preview_btn.click(fn=preview_output, inputs=[dirs_tb, profile_dd], outputs=[naming_preview]).then(
            fn=lambda: gr.update(visible=True), outputs=[naming_preview]
        )
        exp_btn.click(
            fn=run_export,
            inputs=[dirs_tb, max_slider, profile_dd, redact_ck, cancelling_state],
            outputs=[zip_out, status, cancelling_state],
            show_progress="full"
        )
        cancel_btn.click(fn=cancel_export, inputs=[cancelling_state], outputs=[status, cancelling_state])
        demo.queue(default_concurrency_limit=1, max_size=10)
    return demo

if __name__ == "__main__":
    print("🧩 Code Export GUI (SaaS Profiles) 起動")
    print(f"📁 EXPORT_ROOT: {EXPORT_ROOT}")
    create_interface().launch(inbrowser=True, allowed_paths=[str(EXPORT_ROOT)], server_name="127.0.0.1", server_port=7861, share=False)
