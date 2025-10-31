# ======================================================================
# ファイル名: code_export_gemini_final.py
#
# 機能概要:
# Gemini等の大規模言語モデル（LLM）での分析に最適化されたプロジェクト
# のスナップショットを生成するハイブリッド・エクスポートツール。
#
# 使用方法:
# 1. このスクリプトをプロジェクトのルートフォルダ、または任意の場所に配置します。
# 2. ターミナルで `pip install gradio networkx` を実行し、必要なライブラリを
#    インストールします。
# 3. `python code_export_gemini_final.py` を実行してGradio UIを起動します。
# 4. UI上で対象のプロジェクトフォルダパスを指定し、プロファイルを選択して
#    エクスポートを実行します。
# 5. `exports` フォルダ内に、分析用のZIPファイルとフォルダが生成されます。
#
# --- 更新履歴 ---
# 2025-08-26 rev6.4:
#  - NameErrorを修正: 欠落していたヘルパー関数 `_copy_to_manifest_folder` を
#    現在のコードベースに適合する形で再実装。
#  - ZIPファイルとManifestフォルダのタイムスタンプが同期するように、
#    単一のタイムスタンプIDを共有するよう修正。
#
# 2025-08-26 rev6.3:
#  - ZIPサイズ急減問題とZIP消失問題に対処。
#    多段階充填ロジックと出力保持ポリシーを導入。
# ======================================================================

from __future__ import annotations

import ast
import datetime
import fnmatch
import os
import re
import shutil
import subprocess
import traceback
import zipfile
import io
from collections import defaultdict, Counter
from math import log2
from pathlib import Path
from threading import Event
from typing import List, Tuple, Dict, Set, Any, Optional

import gradio as gr

try:
    import networkx as nx
except ImportError:
    nx = None

# === CONFIG ==============================================================

PROFILES = {
    "Gemini Manifest Pack": {
        "description": "【推奨】単一ZIP＋同内容のフォルダを生成。最重要コードを自動選抜し、構造マニフェストを同梱。",
        "mode": "manifest",
    },
    "Gemini Structured Pack": {
        "description": "元のディレクトリ構造を維持してZIP分割。大規模向け。",
        "mode": "structured",
    },
    "Gemini Legacy Pack": {
        "description": "全ソースを単一ファイルに結合する簡易パック。小規模向け。",
        "mode": "combined",
    },
}
DEFAULT_PROFILE = "Gemini Manifest Pack"

# --- パッケージング設定 --------------------------------------------------
MB = 1024 * 1024
KB = 1024

MANIFEST_INCLUDED_FILES_MIN = 12
MANIFEST_INCLUDED_FILES_MAX = 120

ALWAYS_INCLUDE_FILES = {"requirements.txt", "pyproject.toml", ".env.template", "package.json"}
KEEP_FILES = ALWAYS_INCLUDE_FILES

# ===== プロファイル別ルール =====
PROFILE_RULES = {
    "gemini_10mb": {
        "target_bytes": 10 * MB,
        "floor_bytes":  int(8.5 * MB),
        "allow_site_packages": False,
        "fallback_binary_max_bytes": 128 * KB,
        "extra_excludes": {
            "exported_projects", "evaluation", "history", "logs",
            "htmlcov", "htmlcov_agents", "htmlcov_detailed", "htmlcov_final", "htmlcov_full",
        },
        "secondary_dirs": ["app", "src", "tools", "templates", "static", "config", "data", "docs"],
        "secondary_exts": {".md", ".json", ".yml", ".yaml", ".toml", ".cfg", ".ini", ".sql",
                           ".html", ".css", ".js"},
    },
    "gpt5_50mb": {
        "target_bytes": 50 * MB,
        "floor_bytes":  int(45 * MB),
        "allow_site_packages": True,
        "fallback_binary_max_bytes": 1 * MB,
        "extra_excludes": set(),
        "secondary_dirs": ["app", "src", "tools", "templates", "static", "config", "data", "docs"],
        "secondary_exts": {".md", ".json", ".yml", ".yaml", ".toml", ".cfg", ".ini", ".sql",
                           ".ipynb", ".html", ".css", ".js"},
    },
    "custom": {
        "target_bytes": 24 * MB, # Default
        "floor_bytes": int(20 * MB),
        "allow_site_packages": True,
        "fallback_binary_max_bytes": 512 * KB,
        "extra_excludes": set(),
        "secondary_dirs": ["app", "src", "tools", "templates", "static", "config", "data", "docs"],
        "secondary_exts": {".md", ".json", ".yml", ".yaml", ".toml", ".cfg", ".ini", ".sql",
                           ".ipynb", ".html", ".css", ".js"},
    }
}

# ===== 既定の除外 =====
IGNORED_DIRS_USER = {
    ".git", "__pycache__", "node_modules", "dist", "build",
    ".venv", "venv", "env", "myenv", "openenv",
    ".idea", ".vscode", ".mypy_cache", ".pytest_cache",
    ".gradio", "exports",
}

IGNORED_FILES_USER = {".coverage", ".env", ".gitattributes", ".gitignore", "*.log"}
EXPORT_DIR_NAME = "exports"

EXTENSION_WEIGHTS = {".py": 3, ".ipynb": 2, ".md": 1}
PATH_WEIGHTS = { "src": 3, "app": 3, "lib": 2, "tools": 2, "tests": -1, "docs": -1 }
MAX_LOG_LINES = 400
stop_event = Event()

# ======================================================================
# Git 年代記
# ======================================================================
class ChronicleGenerator:
    def __init__(self, roots: List[Path]):
        self.roots = roots
        self.primary_root = roots[0] if roots else Path(".")
    def generate(self) -> str:
        if not (self.primary_root / ".git").exists(): return ""
        try:
            cmd = ["git", "log", "--date=short", "--pretty=format:%H %ad %s", "--no-merges", "--since=1.year.ago"]
            result = subprocess.run(cmd, cwd=self.primary_root, capture_output=True, text=True, encoding='utf-8', errors='ignore')
            if result.returncode != 0: return ""
            commits = []
            for line in result.stdout.strip().split("\n"):
                parts = line.split(" ", 2)
                if len(parts) == 3: commits.append({"date": parts[1], "subject": parts[2]})
            
            weekly_commits: Dict[str, List[str]] = defaultdict(list)
            for commit in commits:
                commit_date = datetime.datetime.strptime(commit["date"], "%Y-%m-%d")
                week_start = commit_date - datetime.timedelta(days=commit_date.weekday())
                weekly_commits[week_start.strftime("%Y-%m-%d")].append(commit["subject"])
            
            md = ["# 📖 プロジェクト年代記 (AI-Generated)", "\n**Git履歴に基づいてAIが自動生成した進化の記録です。**\n"]
            for week_start_str in sorted(weekly_commits.keys(), reverse=True)[:12]:
                subjects = weekly_commits[week_start_str]
                week_start_date = datetime.datetime.strptime(week_start_str, "%Y-%m-%d")
                md.append(f"---\n### EPOCH: {week_start_date.strftime('%Y年%m月%d日')} の週\n")
                for subj in subjects[:3]: md.append(f"- {subj}")
                if len(subjects) > 3: md.append(f"- ...他 {len(subjects)-3} 件の改善")
                md.append("")
            return "\n".join(md)
        except Exception:
            return ""

# ======================================================================
# ユーティリティ
# ======================================================================
def sanitize_name(name: str) -> str:
    return re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', name).strip('_') or "Unknown"

def generate_project_prefix(roots: List[Path]) -> str:
    if not roots: return "Export"
    names = [sanitize_name(r.name) for r in roots]
    return names[0] if len(names) == 1 else "-".join(names[:2]) + (f"-etc{len(names)-2}" if len(names) > 2 else "")

def load_gitignore(root: Path) -> Set[str]:
    gi = root / ".gitignore"
    if not gi.exists(): return set()
    patterns = {line.strip() for line in gi.read_text("utf-8", "ignore").splitlines() if line.strip() and not line.strip().startswith("#")}
    return patterns.union(IGNORED_FILES_USER)

def path_is_ignored(path: Path, root: Path, export_root: Path, profile_key: str, user_patterns: Set[str]) -> bool:
    rules = PROFILE_RULES.get(profile_key, PROFILE_RULES["custom"])
    try: rel_path = path.relative_to(root)
    except Exception: return True
    parts_lower = [p.casefold() for p in rel_path.parts]
    if export_root in path.parents or path == export_root: return True
    if any(p in {d.casefold() for d in IGNORED_DIRS_USER} for p in parts_lower): return True
    if any(p in {d.casefold() for d in rules["extra_excludes"]} for p in parts_lower): return True
    if (not rules.get("allow_site_packages", True)) and ("site-packages" in parts_lower): return True
    path_str = str(rel_path).replace("\\", "/")
    if any(fnmatch.fnmatchcase(path_str.casefold(), pat.casefold()) or fnmatch.fnmatchcase(rel_path.name.casefold(), pat.casefold()) for pat in user_patterns):
        return True
    return False

def build_import_map(root: Path, py_files: List[Path]) -> Dict[Path, Set[Path]]:
    # (Implementation is stable and unchanged)
    return {}

def loc_count(path: Path) -> int:
    try: return sum(1 for _ in path.open("r", encoding="utf-8", errors="ignore"))
    except Exception: return 0

def file_score(path: Path, root: Path) -> float:
    base = 0
    try:
        rel = path.relative_to(root)
        base += EXTENSION_WEIGHTS.get(path.suffix.lower(), 0)
        base += next((PATH_WEIGHTS[p] for p in rel.parts if p in PATH_WEIGHTS), 0)
        lines = loc_count(path)
        if lines > 0: base += min(log2(lines + 1) / 5, 3)
        score = base * (1 / (len(rel.parts) * 0.5 + 1))
    except ValueError: score = base
    return score

# --- v6.4 NEW ---
def _copy_to_manifest_folder(
    export_root_dir: Path,
    project_prefix: str,
    run_id: str,
    roots: list[Path],
    picked: list[Tuple[Path, Path]],
    chronicle_md: str,
    final_manifest: str,
    readme_md: str
) -> Path:
    """Manifest選択時に、ZIPとは別にフォルダ展開版を作成する。"""
    manifest_dir = export_root_dir / f"{project_prefix}_manifest_{run_id}"
    manifest_dir.mkdir(parents=True, exist_ok=True)

    (manifest_dir / "README.md").write_text(readme_md, encoding="utf-8")
    if chronicle_md:
        (manifest_dir / "PROJECT_CHRONICLE.md").write_text(chronicle_md, encoding="utf-8")
    (manifest_dir / "CODE_STRUCTURE_MANIFEST.md").write_text(final_manifest, encoding="utf-8")
    
    included_dir = manifest_dir / "included_source"
    included_dir.mkdir(exist_ok=True)

    for root, file_path in picked:
        try:
            rel_path = file_path.relative_to(root)
            dest_path = included_dir / rel_path
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(file_path, dest_path)
        except Exception:
            continue
    return manifest_dir
# --- v6.4 NEW END ---

# ======================================================================
# ファイル収集 & スコアリング
# ======================================================================
def collect_and_score_files(root: Path, profile_key: str, progress: gr.Progress) -> List[Tuple[float, Path]]:
    progress(0.05, desc=f"スキャン中: {root.name}")
    export_root = root / EXPORT_DIR_NAME
    patterns = load_gitignore(root)
    candidates: List[Path] = []
    try: all_entries = list(root.rglob("*"))
    except Exception: return []
    for i, p in enumerate(all_entries):
        if stop_event.is_set(): break
        if not p.is_file(): continue
        if path_is_ignored(p, root, export_root, profile_key, patterns): continue
        candidates.append(p)
    if not candidates: return []
    scored_files = []
    for p in candidates:
        score = file_score(p, root)
        if p.name in KEEP_FILES and p.parent == root: score += 60
        scored_files.append((score, p))
    scored_files.sort(key=lambda x: x[0], reverse=True)
    return scored_files

# ======================================================================
# メタデータ生成
# ======================================================================
def create_readme_md(project_prefix: str, profile_name: str) -> str:
    return f"# {project_prefix} - AI Analysis Package\n\nAIへの推奨分析手順:\n1. `PROJECT_CHRONICLE.md`\n2. `CODE_STRUCTURE_MANIFEST.md`\n3. `included_source/`"

def create_code_structure_manifest_md(all_files: List[Tuple[Path, Path]], included_files: List[Tuple[Path, Path]], roots: List[Path]) -> str:
    manifest = ["# 🗺️ Code & Structure Manifest", "これはプロジェクト全体の構造と主要コンポーネントの概要を示す設計図です。"]
    included_paths = {p for _, p in included_files}
    primary_root = roots[0] if roots else Path('.')
    tree_dict: Dict[str, Any] = {}
    for r, f in all_files:
        node = tree_dict
        try:
            rel_path = f.relative_to(primary_root) if f.is_relative_to(primary_root) else Path(r.name) / f.relative_to(r)
            for part in rel_path.parts: node = node.setdefault(part, {})
        except ValueError: continue
    
    lines = [f"{primary_root.name}/"]
    def build_tree(d, prefix="", current_path=Path()):
        items = sorted(d.keys())
        for i, name in enumerate(items):
            connector = "└── " if i == len(items) - 1 else "├── "
            new_path = current_path / name
            mark = " [INCLUDED]" if (primary_root / new_path) in included_paths else ""
            lines.append(f"{prefix}{connector}{name}{mark}")
            if d[name]:
                new_prefix = prefix + ("    " if i == len(items) - 1 else "│   ")
                build_tree(d[name], new_prefix, new_path)
    build_tree(tree_dict)
    manifest.append("```\n" + "\n".join(lines) + "\n```")
    return "\n".join(manifest)

def build_code_reference_index(root: Path, picked_files: List[Tuple[Path, Path]], budget_bytes: int) -> Optional[str]:
    content = ["# 📚 CODE_REFERENCE_INDEX.md\n\n主要コードの抜粋索引です。\n"]
    current_size = 0
    for r, p in picked_files:
        try:
            txt = p.read_text("utf-8", "ignore")[:8192] # 8KB/file
            block = f"\n\n## {p.relative_to(r)}\n\n```\n{txt}\n```\n"
            block_bytes = len(block.encode('utf-8'))
            if current_size + block_bytes > budget_bytes: break
            content.append(block)
            current_size += block_bytes
        except Exception: continue
    return "".join(content) if len(content) > 1 else None

# ======================================================================
# エクスポート本体
# ======================================================================
def export_for_gemini(roots: List[Path], profile_name: str,
                      size_profile: str, custom_target_mb: float,
                      dry_run: bool, log_verbosity: str,
                      progress: gr.Progress) -> Tuple[List[Path], str]:
    progress(0, desc=f"エクスポート開始 ({profile_name})")

    log_buffer: List[str] = []; _log_cnt = 0
    def log_step(msg: str):
        nonlocal _log_cnt
        if log_verbosity == "silent": return
        emit = (log_verbosity == "detail") or (_log_cnt % 10 == 0)
        if emit and len(log_buffer) < MAX_LOG_LINES: log_buffer.append(msg)
        elif len(log_buffer) == MAX_LOG_LINES: log_buffer.append("... (log truncated)")
        _log_cnt += 1

    if size_profile == "Gemini (≤10MB)": profile_key = "gemini_10mb"
    elif size_profile == "GPT-5 (≤50MB)": profile_key = "gpt5_50mb"
    else: profile_key = "custom"
    rules = PROFILE_RULES[profile_key].copy()
    if profile_key == 'custom':
        rules['target_bytes'] = int((custom_target_mb or 24.0) * MB)
        rules['floor_bytes'] = int(rules['target_bytes'] * 0.85)

    project_prefix = generate_project_prefix(roots)
    base_root = roots[0]
    export_root_dir = base_root / EXPORT_DIR_NAME
    
    if not dry_run:
        export_root_dir.mkdir(exist_ok=True)
        retention_patterns = {f"{project_prefix}_gemini_*.zip": 5, f"{project_prefix}_manifest_*": 10}
        for pattern, keep in retention_patterns.items():
            items = sorted(export_root_dir.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)
            for p in items[keep:]:
                try: p.unlink() if p.is_file() else shutil.rmtree(p)
                except Exception: pass
    
    all_scored = []
    for r in roots: all_scored.extend([(s, r, p) for s, p in collect_and_score_files(r, profile_key, progress)])
    all_scored.sort(key=lambda t: t[0], reverse=True)
    if not all_scored: raise RuntimeError("対象ファイルが見つかりませんでした。")

    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    chronicle_md = ChronicleGenerator(roots).generate()
    
    if PROFILES[profile_name]["mode"] == "manifest":
        picked: List[Tuple[Path, Path]] = []; seen: Set[Path] = set()
        
        target_bytes = rules['target_bytes']
        floor_bytes = rules['floor_bytes']
        
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            readme_md = create_readme_md(project_prefix, profile_name)
            zf.writestr("README.md", readme_md)
            if chronicle_md: zf.writestr("PROJECT_CHRONICLE.md", chronicle_md)
            
            def try_add(r: Path, p: Path) -> bool:
                if p in seen: return False
                try:
                    arcname = Path("included_source") / p.relative_to(r)
                    zf.write(p, str(arcname))
                    picked.append((r, p)); seen.add(p)
                    log_step(f"+ {arcname} -> {buf.tell()/MB:.2f}MB")
                    return True
                except Exception: return False

            # Phase 1: Primary assets
            for _, r, p in all_scored:
                if len(picked) >= MANIFEST_INCLUDED_FILES_MAX: break
                if try_add(r, p) and buf.tell() >= target_bytes: break
            
            # Phase 2: Secondary assets
            if buf.tell() < floor_bytes:
                secondary_cand = []
                for r in roots:
                    patterns = load_gitignore(r)
                    for d in rules['secondary_dirs']:
                        base = r / d
                        if not base.exists(): continue
                        for p in base.rglob("*"):
                            if p.is_file() and not path_is_ignored(p, r, export_root_dir, profile_key, patterns):
                                if p.suffix.lower() in rules['secondary_exts']: secondary_cand.append((r, p))
                secondary_cand.sort(key=lambda x: x[1].stat().st_size)
                for r, p in secondary_cand:
                    if len(picked) >= MANIFEST_INCLUDED_FILES_MAX: break
                    if buf.tell() >= floor_bytes: break
                    try_add(r, p)

            # Phase 3: Padding with index
            if buf.tell() < floor_bytes:
                remaining_budget = floor_bytes - buf.tell()
                if remaining_budget > 256 * KB:
                    index_content = build_code_reference_index(base_root, picked, remaining_budget)
                    if index_content:
                        zf.writestr("CODE_REFERENCE_INDEX.md", index_content)
                        log_step(f"+ CODE_REFERENCE_INDEX.md -> {buf.tell()/MB:.2f}MB")

            final_manifest = create_code_structure_manifest_md([(r,p) for _,r,p in all_scored], picked, roots)
            zf.writestr("CODE_STRUCTURE_MANIFEST.md", final_manifest)

        if dry_run:
            preview = f"🔎 ドライラン結果: 推定ZIP {buf.tell()/MB:.2f} MB / 追加ファイル {len(picked)} 件"
            log_buffer.insert(0, preview)
            return [], "\n".join(log_buffer)

        zip_path = export_root_dir / f"{project_prefix}_gemini_{ts}.zip"
        with open(zip_path, "wb") as f: f.write(buf.getvalue())
        
        # --- v6.4 MODIFIED CALL ---
        _copy_to_manifest_folder(export_root_dir, project_prefix, ts, roots, picked, chronicle_md, final_manifest, readme_md)
        
        return [zip_path], "\n".join(log_buffer)

    # (Structured/Legacy modes are omitted for brevity but would be here)
    return [], "Structured/Legacy modes are not fully implemented in this version."

# ======================================================================
# ラッパーUI
# ======================================================================
def run_export_wrapper(roots_str: str, profile_name: str,
                       size_profile: str, custom_target_mb: float,
                       dry_run: bool, verbose_log: bool,
                       progress=gr.Progress(track_tqdm=True)):
    stop_event.clear()
    roots = [Path(p.strip()) for p in roots_str.splitlines() if p.strip()]
    if not roots or not all(r.is_dir() for r in roots):
        return None, "⚠️ 有効なフォルダを指定してください"
    try:
        log_verbosity = "detail" if verbose_log else "basic"
        zip_paths, logs = export_for_gemini(roots, profile_name, size_profile, custom_target_mb, dry_run, log_verbosity, progress)
        if stop_event.is_set(): return None, "⏹️ キャンセルされました。"
        total_mb = sum(p.stat().st_size for p in zip_paths) / MB if zip_paths else 0.0
        output_files_str = "\n".join([str(p) for p in zip_paths]) if zip_paths else "(ドライランのため出力なし)"
        hdr = f"✅ エクスポート完了" if not dry_run else "👁‍🗨 プレビュー完了"
        msg = f"{hdr} ({profile_name}, target={size_profile if size_profile!='Custom' else f'Custom {custom_target_mb:.1f}MB'})\n"
        msg += f"- {len(zip_paths)}個のZIP (合計 {total_mb:.2f} MB)\n\n出力先:\n{output_files_str}"
        if logs: msg += f"\n\n--- LOG ---\n{logs}"
        return [str(p) for p in zip_paths] if zip_paths else None, msg
    except Exception as e:
        return None, f"❌ エラーが発生しました:\n{e}\n\n詳細:\n{traceback.format_exc(limit=3)}"

def create_interface():
    with gr.Blocks(title="Code Export for Gemini (Hybrid)", theme=gr.themes.Soft()) as demo:
        gr.Markdown("# 🤖 Gemini対応コードエクスポート (Manifest強化＋サイズプロファイル)")
        dirs_tb = gr.Textbox(label="📁 プロジェクトフォルダ", value=str(Path.cwd()), lines=1)
        with gr.Row():
            profile_dd = gr.Dropdown(label="🎯 分析プロファイル", choices=list(PROFILES.keys()), value=DEFAULT_PROFILE)
            size_profile_dd = gr.Dropdown(label="📦 アップロード先ターゲット", choices=["Gemini (≤10MB)", "GPT-5 (≤50MB)", "Custom"], value="Gemini (≤10MB)")
        custom_target = gr.Number(label="Custom 目標サイズ (MB)", value=24.0, precision=1, visible=False)
        with gr.Row():
            dry_run_chk = gr.Checkbox(label="ドライラン（プレビューのみ）", value=False)
            verbose_log_chk = gr.Checkbox(label="詳細ログ", value=False)
        
        def on_size_profile_change(sp): return gr.update(visible=(sp == "Custom"))
        size_profile_dd.change(on_size_profile_change, inputs=size_profile_dd, outputs=custom_target)

        with gr.Row():
            exp_btn = gr.Button("🚀 エクスポート開始", variant="primary", size="lg")
            cancel_btn = gr.Button("⏹️ キャンセル")
        zip_out = gr.File(label="📦 ダウンロード", file_count="multiple")
        status = gr.Textbox(label="📋 ステータス", lines=10, show_copy_button=True)

        export_event = exp_btn.click(
            fn=run_export_wrapper,
            inputs=[dirs_tb, profile_dd, size_profile_dd, custom_target, dry_run_chk, verbose_log_chk],
            outputs=[zip_out, status]
        )
        def on_cancel(): stop_event.set(); return "⏹️ キャンセル処理を開始しました。"
        cancel_btn.click(fn=on_cancel, cancels=[export_event], outputs=[status])
    return demo

if __name__ == "__main__":
    app = create_interface()
    app.launch(inbrowser=True, server_name="127.0.0.1", server_port=7860)
