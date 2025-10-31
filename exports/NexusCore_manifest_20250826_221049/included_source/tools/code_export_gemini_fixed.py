# ======================================================================
# ファイル名: code_export_gemini_final.py
#
# 機能概要:
# Gemini / GPT-5 等の大規模言語モデル（LLM）に最適化した
# 「コード＋構造マニフェスト」エクスポーター（Gradio UI付き）。
# - Manifest選択時は「フォルダ展開＋ZIP」の両方を生成
# - 目標ZIPサイズのプロファイル制御（Gemini ≤10MB / GPT-5 ≤50MB / Custom）
# - ドライラン（プレビュー）＆詳細ログ（サイズ推移）
# - 主要コードを優先、二次候補の自動充填、索引ファイルでパディング
# - 既存エクスポートの保持・世代管理（最新N件を残す）
# - （任意）Windowsレジストリに直近設定を保存/復元
#
# 使用方法（操作ソフト）:
# - Python 3.9+（推奨 3.10+）
# - pip install gradio networkx  （networkxはインストール済みでなくても動作）
# - Git（任意, PROJECT_CHRONICLE.md 生成に利用）
# - VS Code など任意のエディタ（編集・実行用）
#
# 実行:
#   python code_export_gemini_final.py
#   → ブラウザが 127.0.0.1:7860 を開きます。
#
# 出力先:
#   <プロジェクトルート>/exports/
#   - <prefix>_gemini_YYYYMMDD_HHMMSS.zip
#   - <prefix>_manifest_YYYYMMDD_HHMMSS/ 以下に README.md / PROJECT_CHRONICLE.md /
#     CODE_STRUCTURE_MANIFEST.md / included_source/ を展開
#
# レジストリ（Windows任意）:
#   パス: HKEY_CURRENT_USER\Software\NexusCore\CodeExport
#   値  : LastProjectDir (SZ), LastProfile (SZ), LastSizeProfile (SZ), LastCustomMB (SZ)
#
# --- 更新履歴 ---
# 2025-08-26 rev7.0 (final):
#  - 改良修正案をすべて反映。UI/ログ/サイズ制御/出力保持/不具合修正を統合。
#  - 「Custom 目標サイズ (MB)」は Custom 選択時のみ活性化（可視）。
#  - 主要→二次→索引の三段充填で Gemini ≤10MB を安定達成（floor/target導入）。
#  - フォルダ展開＋ZIP を常に両生成（Manifest モード）。
#  - 詳細ログにサイズ推移（MB）を逐次表示。
#  - 旧出力の削除は世代保持（N件）に変更。誤削除抑止。
#  - Windowsレジストリへ直近設定の保存/復元を追加（任意）。
# 2025-08-26 rev6.5:
#  - ZIPサイズ急減問題の対策（二次候補＋索引パディング）。
# 2025-08-26 rev6.4:
#  - NameError（_copy_to_manifest_folder）修正、タイムスタンプ同期。
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
from collections import defaultdict
from math import log2
from pathlib import Path
from threading import Event
from typing import List, Tuple, Dict, Set, Any, Optional

import gradio as gr

try:
    import networkx as nx  # noqa: F401  # （将来の構造解析で使用）
except Exception:
    nx = None

# --- Windows Registry (optional) ----------------------------------------
WINREG_AVAILABLE = False
try:
    import winreg  # type: ignore
    WINREG_AVAILABLE = True
except Exception:
    pass

REG_ROOT = None
REG_PATH = r"Software\NexusCore\CodeExport"
if WINREG_AVAILABLE:
    REG_ROOT = winreg.HKEY_CURRENT_USER  # noqa: F401


def _reg_get(name: str, default: Optional[str] = None) -> Optional[str]:
    if not WINREG_AVAILABLE:
        return default
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH, 0, winreg.KEY_READ) as k:
            val, _ = winreg.QueryValueEx(k, name)
            return str(val)
    except Exception:
        return default


def _reg_set(name: str, value: str) -> None:
    if not WINREG_AVAILABLE:
        return
    try:
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, REG_PATH) as k:
            winreg.SetValueEx(k, name, 0, winreg.REG_SZ, str(value))
    except Exception:
        pass


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

MANIFEST_INCLUDED_FILES_MAX = 120
ALWAYS_INCLUDE_FILES = {"requirements.txt", "pyproject.toml", ".env.template", "package.json"}
KEEP_FILES = ALWAYS_INCLUDE_FILES

# ===== プロファイル別ルール =====
PROFILE_RULES = {
    "gemini_10mb": {
        "target_bytes": int(float(os.getenv("GEMINI_TARGET_MB", "9.8")) * MB),
        "floor_bytes": int(float(os.getenv("GEMINI_FLOOR_MB", "9.0")) * MB),
        "allow_site_packages": False,
        "fallback_binary_max_bytes": 128 * KB,
        # Geminiはノートブックや巨大アセットを極力抑制
        "extra_excludes": {
            "exported_projects", "evaluation", "history", "logs",
            "htmlcov", "htmlcov_agents", "htmlcov_detailed", "htmlcov_final", "htmlcov_full",
            "*.ipynb",
        },
        "secondary_dirs": ["app", "src", "tools", "templates", "static", "config", "data", "docs"],
        "secondary_exts": {".py", ".md", ".json", ".yml", ".yaml", ".toml", ".ini", ".cfg",
                           ".sql", ".html", ".css", ".js"},
    },
    "gpt5_50mb": {
        "target_bytes": 50 * MB,
        "floor_bytes": int(45 * MB),
        "allow_site_packages": True,
        "fallback_binary_max_bytes": 1 * MB,
        # GPT-5は.ipynb等も積極採用
        "extra_excludes": set(),
        "secondary_dirs": ["app", "src", "tools", "templates", "static", "config", "data", "docs"],
        "secondary_exts": {".md", ".json", ".yml", ".yaml", ".toml", ".cfg", ".ini", ".sql",
                           ".ipynb", ".html", ".css", ".js"},
    },
    "custom": {
        "target_bytes": 24 * MB,  # Default
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
PATH_WEIGHTS = {"src": 3, "app": 3, "lib": 2, "tools": 2, "tests": -1, "docs": -1}
MAX_LOG_LINES = 600
stop_event = Event()


# ======================================================================
# Git 年代記
# ======================================================================
class ChronicleGenerator:
    def __init__(self, roots: List[Path]):
        self.roots = roots
        self.primary_root = roots[0] if roots else Path(".")

    def generate(self) -> str:
        if not (self.primary_root / ".git").exists():
            return ""
        try:
            cmd = ["git", "log", "--date=short", "--pretty=format:%H %ad %s", "--no-merges", "--since=1.year.ago"]
            result = subprocess.run(cmd, cwd=self.primary_root, capture_output=True, text=True,
                                    encoding="utf-8", errors="ignore")
            if result.returncode != 0:
                return ""
            commits = [{"date": p[1], "subject": p[2]} for line in result.stdout.strip().split("\n")
                       if (p := line.split(" ", 2)) and len(p) == 3]
            weekly_commits: Dict[str, List[str]] = defaultdict(list)
            for commit in commits:
                commit_date = datetime.datetime.strptime(commit["date"], "%Y-%m-%d")
                week_start = commit_date - datetime.timedelta(days=commit_date.weekday())
                weekly_commits[week_start.strftime("%Y-%m-%d")].append(commit["subject"])
            md = ["# 📖 プロジェクト年代記 (AI-Generated)",
                  "\n**Git履歴に基づいてAIが自動生成した進化の記録です。**\n"]
            for week_start_str in sorted(weekly_commits.keys(), reverse=True)[:12]:
                subjects = weekly_commits[week_start_str]
                week_start_date = datetime.datetime.strptime(week_start_str, "%Y-%m-%d")
                md.append(f"---\n### EPOCH: {week_start_date.strftime('%Y年%m月%d日')} の週\n")
                md.extend([f"- {s}" for s in subjects[:3]])
                if len(subjects) > 3:
                    md.append(f"- ...他 {len(subjects) - 3} 件の改善")
                md.append("")
            return "\n".join(md)
        except Exception:
            return ""


# ======================================================================
# ユーティリティ
# ======================================================================
def sanitize_name(name: str) -> str:
    return re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name).strip("_") or "Unknown"


def generate_project_prefix(roots: List[Path]) -> str:
    if not roots:
        return "Export"
    names = [sanitize_name(r.name) for r in roots]
    return names[0] if len(names) == 1 else "-".join(names[:2]) + (f"-etc{len(names) - 2}" if len(names) > 2 else "")


def load_gitignore(root: Path) -> Set[str]:
    gi = root / ".gitignore"
    if not gi.exists():
        return set()
    return {line.strip() for line in gi.read_text("utf-8", "ignore").splitlines()
            if line.strip() and not line.strip().startswith("#")}.union(IGNORED_FILES_USER)


def path_is_ignored(path: Path, root: Path, export_root: Path, profile_key: str, user_patterns: Set[str]) -> bool:
    rules = PROFILE_RULES.get(profile_key, PROFILE_RULES["custom"])
    try:
        rel_path = path.relative_to(root)
    except Exception:
        return True
    parts_lower = [p.casefold() for p in rel_path.parts]
    if export_root in path.parents or path == export_root:
        return True
    if any(p in {d.casefold() for d in IGNORED_DIRS_USER} for p in parts_lower):
        return True
    if any(p in {d.casefold() for d in rules["extra_excludes"]} for p in parts_lower):
        return True
    if (not rules.get("allow_site_packages", True)) and ("site-packages" in parts_lower):
        return True
    path_str = str(rel_path).replace("\\", "/")
    return any(fnmatch.fnmatchcase(path_str.casefold(), pat.casefold())
               or fnmatch.fnmatchcase(rel_path.name.casefold(), pat.casefold())
               for pat in user_patterns)


def file_score(path: Path, root: Path) -> float:
    base = 0.0
    try:
        rel = path.relative_to(root)
        base += EXTENSION_WEIGHTS.get(path.suffix.lower(), 0)
        base += next((PATH_WEIGHTS[p] for p in rel.parts if p in PATH_WEIGHTS), 0)
        try:
            with path.open("r", encoding="utf-8", errors="ignore") as f:
                lines = sum(1 for _ in f)
        except Exception:
            lines = 0
        if lines > 0:
            base += min(log2(lines + 1) / 5, 3)
        score = base * (1 / (len(rel.parts) * 0.5 + 1))
    except (ValueError, OSError):
        score = base
    return score


def _is_binary(path: Path) -> bool:
    try:
        with open(path, "rb") as f:
            return b"\0" in f.read(1024)
    except Exception:
        return True


def _copy_to_manifest_folder(export_root_dir: Path, project_prefix: str, run_id: str,
                             roots: list[Path], picked: list[Tuple[Path, Path]],
                             chronicle_md: str, final_manifest: str, readme_md: str) -> Path:
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
            dest_path = included_dir / file_path.relative_to(root)
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(file_path, dest_path)
        except Exception:
            continue
    return manifest_dir


# ======================================================================
# メタデータ生成
# ======================================================================
def create_readme_md(project_prefix: str, profile_label: str, size_bytes: int) -> str:
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    size_mb = size_bytes / MB
    return (
        f"# {project_prefix} - AI Analysis Package\n\n"
        f"- Exported: {ts}\n"
        f"- Profile : {profile_label}\n"
        f"- Size    : {size_mb:.2f} MB\n\n"
        "## 推奨分析手順\n"
        "1. `PROJECT_CHRONICLE.md`（最近の変更点の流れ）\n"
        "2. `CODE_STRUCTURE_MANIFEST.md`（全体の構造把握）\n"
        "3. `included_source/`（主要コード群）\n"
    )


def create_code_structure_manifest_md(all_files: List[Tuple[Path, Path]],
                                      included_files: List[Tuple[Path, Path]],
                                      roots: List[Path]) -> str:
    manifest = ["# 🗺️ Code & Structure Manifest",
                "これはプロジェクト全体の構造と主要コンポーネントの概要を示す設計図です。"]
    included_paths = {p for _, p in included_files}
    primary_root = roots[0] if roots else Path(".")
    tree_dict: Dict[str, Any] = {}
    for r, f in all_files:
        try:
            rel_path = f.relative_to(primary_root) if f.is_relative_to(primary_root) else Path(r.name) / f.relative_to(r)
            node = tree_dict
            for part in rel_path.parts:
                node = node.setdefault(part, {})
        except Exception:
            continue
    lines = [f"{primary_root.name}/"]

    def build_tree(d, prefix: str = "", current_path: Path = Path()):
        items = sorted(d.keys())
        for i, name in enumerate(items):
            connector = "└── " if i == len(items) - 1 else "├── "
            mark = " [INCLUDED]" if (primary_root / current_path / name) in included_paths else ""
            lines.append(f"{prefix}{connector}{name}{mark}")
            if d[name]:
                build_tree(d[name], prefix + ("    " if i == len(items) - 1 else "│   "), current_path / name)

    build_tree(tree_dict)
    manifest.append("```\n" + "\n".join(lines) + "\n```")
    return "\n".join(manifest)


def build_code_reference_index(root: Path, picked_files: List[Tuple[Path, Path]], budget_bytes: int) -> Optional[str]:
    content = ["# 📚 CODE_REFERENCE_INDEX.md\n\n主要コードの抜粋索引です。\n"]
    current_size = 0
    for r, p in picked_files:
        try:
            if p.suffix.lower() != ".py":
                continue
            txt = p.read_text("utf-8", "ignore")[:8192]
            block = f"\n\n## {p.relative_to(r)}\n\n```python\n{txt}\n```\n"
            block_bytes = len(block.encode("utf-8"))
            if current_size + block_bytes > budget_bytes:
                break
            content.append(block)
            current_size += block_bytes
        except Exception:
            continue
    return "".join(content) if len(content) > 1 else None


# ======================================================================
# ファイル収集 & スコアリング
# ======================================================================
def collect_and_score_files(root: Path, profile_key: str, progress: gr.Progress) -> List[Tuple[float, Path]]:
    progress(0.05, desc=f"スキャン中: {root.name}")
    export_root = root / EXPORT_DIR_NAME
    patterns = load_gitignore(root)
    candidates: List[Path] = []
    try:
        all_entries = list(root.rglob("*"))
    except Exception:
        return []
    for p in all_entries:
        if stop_event.is_set():
            break
        if p.is_file() and not path_is_ignored(p, root, export_root, profile_key, patterns):
            candidates.append(p)
    if not candidates:
        return []
    scored_files = [(file_score(p, root) + (60 if p.name in KEEP_FILES and p.parent == root else 0), p) for p in candidates]
    scored_files.sort(key=lambda x: x[0], reverse=True)
    return scored_files


# ======================================================================
# エクスポート本体
# ======================================================================
def export_for_gemini(roots: List[Path], profile_name: str,
                      size_profile: str, custom_target_mb: float,
                      dry_run: bool, log_verbosity: str,
                      progress: gr.Progress) -> Tuple[List[Path], str]:
    progress(0, desc=f"エクスポート開始 ({profile_name})")

    log_buffer: List[str] = []
    _log_cnt = 0

    def log_step(msg: str):
        nonlocal _log_cnt
        if log_verbosity == "silent":
            return
        emit = (log_verbosity == "detail") or (_log_cnt % 10 == 0)
        if emit and len(log_buffer) < MAX_LOG_LINES:
            log_buffer.append(msg)
        elif len(log_buffer) == MAX_LOG_LINES:
            log_buffer.append("... (log truncated)")
        _log_cnt += 1

    if size_profile == "Gemini (≤10MB)":
        profile_key = "gemini_10mb"
    elif size_profile == "GPT-5 (≤50MB)":
        profile_key = "gpt5_50mb"
    else:
        profile_key = "custom"
    rules = PROFILE_RULES[profile_key].copy()
    if profile_key == "custom":
        rules["target_bytes"] = int((custom_target_mb or 24.0) * MB)
        rules["floor_bytes"] = int(rules["target_bytes"] * 0.85)

    project_prefix = generate_project_prefix(roots)
    base_root = roots[0]
    export_root_dir = base_root / EXPORT_DIR_NAME

    # 出力保持ポリシー（世代管理）
    if not dry_run:
        export_root_dir.mkdir(exist_ok=True)
        retention_patterns = {f"{project_prefix}_gemini_*.zip": 8, f"{project_prefix}_manifest_*": 10}
        for pattern, keep in retention_patterns.items():
            items = sorted(export_root_dir.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)
            for p in items[keep:]:
                try:
                    p.unlink() if p.is_file() else shutil.rmtree(p)
                except Exception:
                    pass

    all_scored = []
    for r in roots:
        all_scored.extend([(s, r, p) for s, p in collect_and_score_files(r, profile_key, progress)])
    all_scored.sort(key=lambda t: t[0], reverse=True)
    if not all_scored:
        raise RuntimeError("対象ファイルが見つかりませんでした。")

    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    chronicle_md = ChronicleGenerator(roots).generate()

    if PROFILES[profile_name]["mode"] == "manifest":
        picked: List[Tuple[Path, Path]] = []
        seen: Set[Path] = set()

        target_bytes = rules["target_bytes"]
        floor_bytes = rules["floor_bytes"]

        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            # 動的 README（サイズとプロファイルを埋込）
            readme_md = create_readme_md(project_prefix, size_profile, 0)
            zf.writestr("README.md", readme_md)
            if chronicle_md:
                zf.writestr("PROJECT_CHRONICLE.md", chronicle_md)

            def try_add(r: Path, p: Path) -> bool:
                if p in seen:
                    return False
                try:
                    arcname = Path("included_source") / p.relative_to(r)
                    zf.write(p, str(arcname))
                    picked.append((r, p))
                    seen.add(p)
                    log_step(f"+ {arcname} -> {buf.tell() / MB:.2f} MB")
                    return True
                except Exception:
                    return False

            # Phase 1: Primary assets
            for _, r, p in all_scored:
                if len(picked) >= MANIFEST_INCLUDED_FILES_MAX:
                    break
                if try_add(r, p) and buf.tell() >= target_bytes:
                    break

            # Phase 2: Secondary assets（小さい順）
            if buf.tell() < floor_bytes:
                secondary_cand = []
                for r in roots:
                    patterns = load_gitignore(r)
                    for d in rules["secondary_dirs"]:
                        base = r / d
                        if not base.exists():
                            continue
                        for p in base.rglob("*"):
                            if p.is_file() and not path_is_ignored(p, r, export_root_dir, profile_key, patterns):
                                if p.suffix.lower() in rules["secondary_exts"]:
                                    if not _is_binary(p) or p.stat().st_size <= rules["fallback_binary_max_bytes"]:
                                        secondary_cand.append((r, p))
                secondary_cand.sort(key=lambda x: x[1].stat().st_size)
                for r, p in secondary_cand:
                    if len(picked) >= MANIFEST_INCLUDED_FILES_MAX:
                        break
                    if buf.tell() >= floor_bytes:
                        break
                    try_add(r, p)

            # Phase 3: Padding with index
            if buf.tell() < floor_bytes:
                remaining_budget = floor_bytes - buf.tell()
                if remaining_budget > 256 * KB:
                    index_content = build_code_reference_index(base_root, picked, remaining_budget)
                    if index_content:
                        zf.writestr("CODE_REFERENCE_INDEX.md", index_content)
                        log_step(f"+ CODE_REFERENCE_INDEX.md -> {buf.tell() / MB:.2f} MB")

            final_manifest = create_code_structure_manifest_md([(r, p) for _, r, p in all_scored], picked, roots)
            zf.writestr("CODE_STRUCTURE_MANIFEST.md", final_manifest)

            # README を最終サイズで更新（追記）
            try:
                zf.writestr("README.md", create_readme_md(project_prefix, size_profile, buf.tell()))
            except Exception:
                pass

        if dry_run:
            preview = f"🔎 ドライラン結果: 推定ZIP {buf.tell() / MB:.2f} MB / 追加ファイル {len(picked)} 件"
            log_buffer.insert(0, preview)
            return [], "\n".join(log_buffer)

        zip_path = export_root_dir / f"{project_prefix}_gemini_{ts}.zip"
        with open(zip_path, "wb") as f:
            f.write(buf.getvalue())

        _copy_to_manifest_folder(export_root_dir, project_prefix, ts, roots, picked, chronicle_md, final_manifest,
                                 readme_md=create_readme_md(project_prefix, size_profile, buf.tell()))

        return [zip_path], "\n".join(log_buffer)

    # Structured / Legacy は将来拡張
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
        zip_paths, logs = export_for_gemini(roots, profile_name, size_profile, custom_target_mb, dry_run,
                                            log_verbosity, progress)
        if stop_event.is_set():
            return None, "⏹️ キャンセルされました。"
        total_mb = sum(p.stat().st_size for p in zip_paths) / MB if zip_paths else 0.0
        output_files_str = "\n".join([str(p) for p in zip_paths]) if zip_paths else "(ドライランのため出力なし)"
        hdr = f"✅ エクスポート完了" if not dry_run else "👁‍🗨 プレビュー完了"
        msg = f"{hdr} ({profile_name}, target={size_profile if size_profile!='Custom' else f'Custom {custom_target_mb:.1f}MB'})\n"
        msg += f"- {len(zip_paths)}個のZIP (合計 {total_mb:.2f} MB)\n\n出力先:\n{output_files_str}"
        if logs:
            msg += f"\n\n--- LOG ---\n{logs}"

        # 設定をレジストリへ保存（任意/Windowsのみ）
        try:
            if WINREG_AVAILABLE and roots:
                _reg_set("LastProjectDir", str(roots[0]))
                _reg_set("LastProfile", str(profile_name))
                _reg_set("LastSizeProfile", str(size_profile))
                _reg_set("LastCustomMB", str(custom_target_mb or ""))
        except Exception:
            pass

        return [str(p) for p in zip_paths] if zip_paths else None, msg
    except Exception as e:
        return None, f"❌ エラーが発生しました:\n{e}\n\n詳細:\n{traceback.format_exc(limit=3)}"


def create_interface():
    # 既定ディレクトリは CWD → レジストリ値があれば置換
    default_dir = str(Path.cwd())
    try:
        reg_dir = _reg_get("LastProjectDir")
        if reg_dir and Path(reg_dir).exists():
            default_dir = reg_dir
    except Exception:
        pass

    with gr.Blocks(title="Code Export for Gemini (Hybrid)", theme=gr.themes.Soft()) as demo:
        gr.Markdown("# 🤖 Gemini対応コードエクスポート (Manifest強化＋サイズプロファイル)")

        dirs_tb = gr.Textbox(label="📁 プロジェクトフォルダ", value=default_dir, lines=1)
        with gr.Row():
            profile_dd = gr.Dropdown(label="🎯 分析プロファイル",
                                     choices=list(PROFILES.keys()), value=DEFAULT_PROFILE)
            # 既定は Gemini（≤10MB）
            default_size_profile = _reg_get("LastSizeProfile", "Gemini (≤10MB)") or "Gemini (≤10MB)"
            size_profile_dd = gr.Dropdown(label="📦 アップロード先ターゲット（目標ZIPサイズ）",
                                          choices=["Gemini (≤10MB)", "GPT-5 (≤50MB)", "Custom"],
                                          value=default_size_profile)

        # Customのみ入力可
        default_custom_mb = float(_reg_get("LastCustomMB", "24.0") or 24.0)
        custom_target = gr.Number(label="Custom 目標サイズ (MB)", value=default_custom_mb, precision=1, visible=False)

        with gr.Row():
            dry_run_chk = gr.Checkbox(label="ドライラン（プレビューのみ）", value=False)
            verbose_log_chk = gr.Checkbox(label="詳細ログ（サイズ推移を表示）", value=False)

        def on_size_profile_change(sp):
            return gr.update(visible=(sp == "Custom"))

        size_profile_dd.change(on_size_profile_change, inputs=size_profile_dd, outputs=custom_target)

        with gr.Row():
            exp_btn = gr.Button("🚀 エクスポート開始", variant="primary", size="lg")
            cancel_btn = gr.Button("⏹️ キャンセル")
        zip_out = gr.File(label="📦 ダウンロード", file_count="multiple")
        status = gr.Textbox(label="📋 ステータス", lines=12, show_copy_button=True)

        export_event = exp_btn.click(
            fn=run_export_wrapper,
            inputs=[dirs_tb, profile_dd, size_profile_dd, custom_target, dry_run_chk, verbose_log_chk],
            outputs=[zip_out, status]
        )

        def on_cancel():
            stop_event.set()
            return "⏹️ キャンセル処理を開始しました。"

        cancel_btn.click(fn=on_cancel, cancels=[export_event], outputs=[status])
    return demo


if __name__ == "__main__":
    app = create_interface()
    # ローカルのみ解放（外部公開しない）
    app.launch(inbrowser=True, server_name="127.0.0.1", server_port=7860)
