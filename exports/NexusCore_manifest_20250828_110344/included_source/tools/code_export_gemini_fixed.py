# -*- coding: utf-8 -*-
# File: tools/code_export_gemini_fixed.py
# Version: all-py-first v7.3
# Date: 2025-08-28
# Purpose: NexusCore Export Tool for Gemini (≤10MB), GPT-5 (≤50MB), and Custom profiles
# Notes:
#  - Prioritizes collecting as many .py files as possible (all-py-first) for Gemini.
#  - Also includes config/docs (toml/yaml/json/ini/cfg/md/rst/txt) as profile allows.
#  - Generates both a manifest folder and a ZIP (either/both selectable).
#  - Dry-run preview with size progression log.
#  - Always writes a log to logs/, and also mirrors the log into exports/ when outputs are created.
#  - Avoids Windows MAX_PATH by flattening overly deep paths with hashed middle segments.

import argparse
import hashlib
import io
import os
import re
import shutil
import sys
import zipfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, List, Tuple

# ---------------- Console-safe printing ----------------
def _sanitize_console_text(s: str, stream=None) -> str:
    stream = stream or sys.stdout
    enc = getattr(stream, "encoding", None) or "utf-8"
    return str(s).encode(enc, errors="replace").decode(enc)

def cprint(msg: str = "", *, stream=None, end: str = "\n"):
    stream = stream or sys.stdout
    stream.write(_sanitize_console_text(msg, stream=stream) + end)
    try:
        stream.flush()
    except Exception:
        pass

USE_EMOJI = not (os.name == "nt")
ICON = {
    "ok":      "✅ " if USE_EMOJI else "[OK] ",
    "fail":    "❌ " if USE_EMOJI else "[FAIL] ",
    "preview": "👁‍🗨 " if USE_EMOJI else "[Preview] ",
    "rocket":  "🚀 " if USE_EMOJI else "[Run] ",
    "pick":    "🔎 " if USE_EMOJI else "[Pick] ",
    "box":     "📦 " if USE_EMOJI else "[Out] ",
    "memo":    "📝 " if USE_EMOJI else "[Log] ",
}

# ---------------- Profiles ----------------
PROFILES = {
    "gemini-10": {
        "target_mb": 9.5,
        "max_files": 5000,
        "include_exts": {".py", ".md", ".rst", ".txt"},  # all-py-first + docs
        "include_configs": set(),  # keep lean
        "per_file_soft_limit_mb": 3.0,
        "exclude_globs": [
            "**/__pycache__/**", "**/.mypy_cache/**", "**/.pytest_cache/**",
            "**/.git/**", "**/.github/**", "**/.venv/**", "env/**", "venv/**",
            "**/*.whl", "**/*.zip", "**/*.7z", "**/*.tar", "**/*.gz",
            "**/*.png", "**/*.jpg", "**/*.jpeg", "**/*.gif", "**/*.svg",
            "tools/exports/**", "exports/**", "logs/**",
            "**/tree_sitter_languages/**", "**/parser.c",  # huge C sources
            "**/vscode-extension.zip", "**/node_modules/**",
            "**/*.pdf", "**/*.pptx", "**/*.docx",
        ],
    },
    "gpt5-50": {
        "target_mb": 49.5,
        "max_files": 5000,
        "include_exts": {
            ".py", ".ipynb",
            ".toml", ".yaml", ".yml", ".json", ".ini", ".cfg",
            ".md", ".rst", ".txt",
            ".proto", ".graphql",
        },
        "include_configs": {".toml", ".yaml", ".yml", ".json", ".ini", ".cfg"},
        "per_file_soft_limit_mb": 8.0,
        "exclude_globs": [
            "**/__pycache__/**", "**/.mypy_cache/**", "**/.pytest_cache/**",
            "**/.git/**", "**/.github/**", "**/.venv/**", "env/**", "venv/**",
            "**/*.whl", "**/*.7z", "**/*.tar", "**/*.gz",
            "**/*.png", "**/*.jpg", "**/*.jpeg", "**/*.gif", "**/*.svg",
            "tools/exports/**", "exports/**", "logs/**",
            "**/vscode-extension.zip", "**/parser.c",
            "**/node_modules/**", "**/*.pdf", "**/*.pptx", "**/*.docx",
        ],
    },
    "custom": {
        "target_mb": 24.0,
        "max_files": 5000,
        "include_exts": {".py", ".md", ".rst", ".txt", ".toml", ".yaml", ".yml", ".json"},
        "include_configs": {".toml", ".yaml", ".yml", ".json"},
        "per_file_soft_limit_mb": 6.0,
        "exclude_globs": [
            "**/__pycache__/**", "**/.git/**", "**/.venv/**",
            "exports/**", "logs/**",
        ],
    },
}

# Extension priority (lower is higher priority)
EXT_PRIORITY = {
    ".py": 0,
    ".toml": 1, ".yaml": 1, ".yml": 1, ".json": 1, ".ini": 1, ".cfg": 1,
    ".md": 2, ".rst": 2, ".txt": 2,
    ".ipynb": 3,
    ".proto": 4, ".graphql": 4,
}

TEXT_LIKE_RATIO = {
    ".py": 0.55, ".md": 0.6, ".rst": 0.6, ".txt": 0.6,
    ".toml": 0.55, ".yaml": 0.55, ".yml": 0.55, ".json": 0.6, ".ini": 0.55, ".cfg": 0.55,
    ".ipynb": 0.85,  # often already large
    ".proto": 0.55, ".graphql": 0.55,
}

# ---------------- Utilities ----------------
def to_mb(num_bytes: int) -> float:
    return round(num_bytes / (1024 * 1024), 2)

def estimate_zip_mb(p: Path) -> float:
    ext = p.suffix.lower()
    ratio = TEXT_LIKE_RATIO.get(ext, 0.9)
    try:
        sz = p.stat().st_size
    except Exception:
        return 0.0
    return round((sz * ratio) / (1024 * 1024), 2)

def _hash(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8", errors="ignore")).hexdigest()[:10]

def shorten_deep_relpath(rel: Path, max_len: int = 200) -> Path:
    """
    For Windows MAX_PATH safety: if the relative path string is too long,
    compress middle segments using a hash. Keeps top-2 and last-1 segments.
    """
    s = str(rel).replace("\\", "/")
    if len(s) <= max_len:
        return rel
    parts = s.split("/")
    if len(parts) <= 3:
        # nothing much to shorten; hash the base name
        base = parts[-1]
        stem, dot, suf = base.partition(".")
        base_short = (stem[:16] + "-" + _hash(s)) + (dot + suf if dot else "")
        return Path("/".join(parts[:-1] + [base_short]))
    head = "/".join(parts[:2])
    tail = parts[-1]
    mid = "/".join(parts[2:-1])
    mid_hash = _hash(mid)
    new_s = f"{head}/__{mid_hash}__/__flat__/{tail}"
    return Path(new_s)

def should_exclude(p: Path, exclude_globs: List[str]) -> bool:
    s = str(p).replace("\\", "/")
    for pat in exclude_globs:
        if Path().glob:  # dummy to keep linter calm
            pass
        # emulate glob pattern with PurePath.match
        if Path(s).match(pat):
            return True
    return False

def list_candidates(roots: List[str], profile: dict, max_files: int) -> List[Path]:
    exts = set(profile["include_exts"]) | set(profile.get("include_configs", set()))
    excl = profile["exclude_globs"]
    files: List[Path] = []
    seen = set()

    for r in roots:
        root = Path(r).resolve()
        if not root.exists():
            continue
        for p in root.rglob("*"):
            if not p.is_file():
                continue
            if p.suffix.lower() not in exts:
                continue
            if should_exclude(p, excl):
                continue
            key = str(p.resolve())
            if key in seen:
                continue
            seen.add(key)
            files.append(p)

    # sort by priority then recently modified, keeping .py first
    def _key(p: Path):
        prio = EXT_PRIORITY.get(p.suffix.lower(), 99)
        try:
            mtime = -p.stat().st_mtime  # newer first
        except Exception:
            mtime = 0
        return (prio, mtime, str(p).lower())

    files.sort(key=_key)
    if len(files) > max_files:
        files = files[:max_files]
    return files

@dataclass
class PickResult:
    picked: List[Tuple[Path, float]]  # (path, est_zip_mb)
    est_total_mb: float

def pick_files_for_target(files: List[Path], target_mb: float, per_file_soft_limit_mb: float) -> PickResult:
    picked: List[Tuple[Path, float]] = []
    total = 0.0
    for p in files:
        est = estimate_zip_mb(p)
        if est <= 0:
            continue
        if est > per_file_soft_limit_mb:
            # very large single file -> skip softly
            continue
        if total + est > target_mb * 1.02:  # small 2% buffer
            continue
        picked.append((p, est))
        total = round(total + est, 2)
        if total >= target_mb * 0.995:  # close enough
            break
    return PickResult(picked, total)

def compute_rel(p: Path, roots: List[str]) -> Path:
    for r in roots:
        try:
            rel = p.resolve().relative_to(Path(r).resolve())
            return rel
        except Exception:
            continue
    return Path(p.name)

def copy_manifest(picked: List[Tuple[Path, float]], roots: List[str], out_dir: Path) -> List[Tuple[Path, Path]]:
    out_dir.mkdir(parents=True, exist_ok=True)
    mapping: List[Tuple[Path, Path]] = []
    for p, _ in picked:
        rel = compute_rel(p, roots)
        rel = shorten_deep_relpath(rel, max_len=180)
        dest = out_dir / "included_source" / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        try:
            shutil.copy2(p, dest)
        except FileNotFoundError:
            # Fallback: copy with shorter filename only
            safe = dest.parent / (p.stem[:20] + "_" + _hash(str(p)) + p.suffix)
            shutil.copy2(p, safe)
            dest = safe
        mapping.append((p, dest))
    return mapping

def write_manifest_readme(manifest_dir: Path, args, picked_map: List[Tuple[Path, Path]], est_total_mb: float, ts: str):
    readme = manifest_dir / "README_MANIFEST.md"
    lines = []
    lines.append(f"# NexusCore Export Manifest")
    lines.append("")
    lines.append(f"- Date: {ts}")
    lines.append(f"- Profile: {args.profile}")
    lines.append(f"- Target: {args.target_mb} MB")
    lines.append(f"- Roots: {', '.join(args.roots)}")
    lines.append(f"- Emit ZIP: {args.emit_zip} / Emit Folder: {args.emit_folder} / Dry-run: {args.dry_run}")
    lines.append(f"- Estimated ZIP Size: {est_total_mb} MB")
    lines.append("")
    lines.append("## Suggested Entry Points / Registry (auto-detected)")
    REG_HINTS = [
        "orchestrator.py", "core/orchestrator.py",
        "routes.py", "app/routes.py",
        "main.py", "main_cli.py", "run.py",
        "wsgi.py", "asgi.py", "server.py",
        "run_*", "start_*",
    ]
    found = []
    for src, dst in picked_map:
        rp = str(dst).replace("\\", "/")
        name = rp.split("/")[-1].lower()
        for h in REG_HINTS:
            # naive contains/glob-ish
            if h.replace("*", "") in name:
                found.append(rp)
                break
    if found:
        for f in sorted(set(found)):
            lines.append(f"- `{f}`")
    else:
        lines.append("- (No obvious entries found; check included_source/)")

    lines.append("")
    lines.append("## How to Use")
    lines.append("1. Upload the generated ZIP to the target model (Gemini/GPT-5) as needed.")
    lines.append("2. For Gemini packs, keep under ~10MB; for GPT-5 packs, under ~50MB.")
    lines.append("3. If using the Web UI: `python tools/nexus_export_ui.py` (browser auto-open).")
    lines.append("4. If using CLI directly (examples):")
    lines.append("   - Gemini: `python tools/code_export_gemini_fixed.py --profile gemini-10 --emit-zip --emit-folder`")
    lines.append("   - GPT-5 : `python tools/code_export_gemini_fixed.py --profile gpt5-50 --emit-zip --emit-folder`")
    lines.append("")
    lines.append("## Notes")
    lines.append("- Windows long path is mitigated by flattening deep paths via hashed middle segments.")
    lines.append("- Logs are written to `logs/` and mirrored into this manifest directory.")

    readme.write_text("\n".join(lines), encoding="utf-8")

def write_text_log(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", errors="replace")

def mirror_log_to_exports(log_path: Path, manifest_dir: Path | None, exports_dir: Path):
    try:
        # copy to exports root
        dst = exports_dir / log_path.name
        if log_path.exists():
            shutil.copy2(log_path, dst)
        # and also into manifest dir if exists
        if manifest_dir and manifest_dir.exists():
            shutil.copy2(log_path, manifest_dir / log_path.name)
    except Exception:
        pass

def zip_dir(src_dir: Path, zip_path: Path):
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for p in src_dir.rglob("*"):
            if p.is_file():
                zf.write(p, p.relative_to(src_dir))

def export_main(args):
    profile = PROFILES.get(args.profile, PROFILES["gemini-10"]).copy()
    if args.target_mb:
        profile["target_mb"] = float(args.target_mb)
    target_mb = profile["target_mb"]
    max_files = int(args.max_files or profile.get("max_files", 5000))
    per_file_soft_limit_mb = float(profile.get("per_file_soft_limit_mb", 6.0))

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    exports_dir = Path(args.exports_dir).resolve()
    logs_dir = Path(args.logs_dir).resolve()
    manifest_dir = exports_dir / f"NexusCore_manifest_{ts}"
    zip_path = exports_dir / f"NexusCore_{args.profile.replace('-', '')}_{ts}.zip"
    log_path = logs_dir / f"NexusCore_export_{'dryrun' if args.dry_run else 'run'}_{ts}.txt"

    # Collect
    files = list_candidates(args.roots, profile, max_files=max_files)

    # Pick
    pick = pick_files_for_target(files, target_mb=target_mb, per_file_soft_limit_mb=per_file_soft_limit_mb)

    # Build size-progress log text
    lines = []
    hdr = f"{ICON['preview'] if args.dry_run else ICON['pick']}Pick Result: est ZIP {pick.est_total_mb} MB / {len(pick.picked)} files"
    lines.append(hdr)
    acc = 0.0
    for src, est in pick.picked:
        acc = round(acc + est, 2)
        rel = compute_rel(src, args.roots)
        lines.append(f"+ included_source/{rel} -> {acc:.2f} MB ( +{est:.2f} )")

    # If dry-run: only write log and exit
    if args.dry_run:
        write_text_log(log_path, "\n".join(lines))
        mirror_log_to_exports(log_path, None, exports_dir)
        cprint(f"{ICON['preview']}プレビュー完了 ({args.profile}, target={target_mb}MB)")
        cprint(f"{ICON['memo']}Log:      {log_path}")
        return

    # Emit manifest folder
    mapping: List[Tuple[Path, Path]] = []
    if args.emit_folder:
        mapping = copy_manifest(pick.picked, args.roots, manifest_dir)
        write_manifest_readme(manifest_dir, args, mapping, pick.est_total_mb, ts)

    # Emit ZIP
    if args.emit_zip:
        tmp_dir = manifest_dir if args.emit_folder else (exports_dir / f"_tmp_manifest_{ts}")
        if not args.emit_folder:
            copy_manifest(pick.picked, args.roots, tmp_dir)
            write_manifest_readme(tmp_dir, args, [], pick.est_total_mb, ts)
        zip_dir(tmp_dir, zip_path)
        if not args.emit_folder:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    # Final logs
    lines.append("")
    lines.append("--- Export Summary ---")
    lines.append(f"{ICON['ok']}エクスポート完了 ({round(pick.est_total_mb,2)} MB)")
    if args.emit_folder:
        lines.append(f"  - Manifest: {manifest_dir}")
    if args.emit_zip:
        lines.append(f"  - ZIP:      {zip_path}")
    lines.append(f"  - Log:      {log_path}")
    lines.append("--------------------")
    write_text_log(log_path, "\n".join(lines))
    mirror_log_to_exports(log_path, manifest_dir if args.emit_folder else None, exports_dir)

    cprint(f"{ICON['ok']}エクスポート完了 ({args.profile}, target={target_mb}MB)")
    if args.emit_folder:
        cprint(f"{ICON['box']}Manifest: {manifest_dir}")
    if args.emit_zip:
        cprint(f"{ICON['box']}ZIP:      {zip_path}")
    cprint(f"{ICON['memo']}Log:      {log_path}")

def build_argparser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        description="NexusCore Export Tool (Gemini/GPT-5/Custom).",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    ap.add_argument("--roots", nargs="*", default=[str(Path('.').resolve())], help="Root directories to include")
    ap.add_argument("--profile", choices=list(PROFILES.keys()), default="gemini-10")
    ap.add_argument("--target-mb", type=float, default=None, help="Override profile target size (MB)")
    ap.add_argument("--max-files", type=int, default=5000, help="Max number of files to scan")
    ap.add_argument("--emit-zip", action="store_true", help="Emit a consolidated ZIP")
    ap.add_argument("--emit-folder", action="store_true", help="Emit a manifest folder")
    ap.add_argument("--dry-run", action="store_true", help="Preview only (no outputs)")
    ap.add_argument("--exports-dir", default=str(Path("exports").resolve()))
    ap.add_argument("--logs-dir", default=str(Path("logs").resolve()))
    return ap

def main():
    ap = build_argparser()
    args = ap.parse_args()
    try:
        export_main(args)
    except Exception as e:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        logs_dir = Path(args.logs_dir).resolve()
        log_path = logs_dir / f"NexusCore_export_error_{ts}.txt"
        buf = io.StringIO()
        import traceback
        traceback.print_exc(file=buf)
        write_text_log(log_path, buf.getvalue())
        mirror_log_to_exports(log_path, None, Path(args.exports_dir).resolve())
        cprint(f"{ICON['fail']}エラー: {e}")
        cprint(f"{ICON['memo']}詳細ログ: {log_path}")

if __name__ == "__main__":
    main()
