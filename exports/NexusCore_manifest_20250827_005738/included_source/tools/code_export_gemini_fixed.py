# -*- coding: utf-8 -*-
"""
File: tools/code_export_gemini_policy_driven.py
Version: v9.0 (policy-driven)
Date: 2025-08-27 JST
Author: NexusCore Export Pipeline (with Policy Enforcement)

目的:
  - v8.0の全機能(パス堅牢化/プロファイル/デュアル出力/ドライラン)を維持
  - [恒久対策] 成果物・レポート・計測系ディレクトリの除外ルールを強化
    - output/, evaluation/, project_structure_export/ 等をdenylistに追加
  - [gemini-10ポリシー] 10MB超過を防ぐための自動ブレーキを実装
    - .pyファイルを最優先とし、巨大テキストファイル(>2MB)を自動除外
    - バイナリファイルの上限を128KBに維持
  - [運用性向上] ログ出力先を分離する --logs-dir オプションを追加

このスクリプトが生成するもの:
  - C:/NXC/exp/NexusCore_manifest_YYYYMMDD_HHMMSS/         (フォルダ展開)
    - included_source/ ... 選定したファイルの実体（パスは短縮/フラット化される可能性あり）
    - _PATHMAP.txt       ... 元パスと短縮後パスの対応表
    - README.md / PROJECT_CHRONICLE.md / CODE_REFERENCE_INDEX.md / EXPORT_LOG.txt
  - C:/NXC/exp/NexusCore_gemini_YYYYMMDD_HHMMSS.zip        (ZIPアーカイブ)
  - C:/NXC/logs/NexusCore_export_run_YYYYMMDD_HHMMSS.txt   (実行ログ; --logs-dirで指定)

想定の操作ソフト/運用メモ:
  - CLI (推奨):
    - [ドライラン] python tools/code_export_gemini_policy_driven.py --roots . --profile gemini-10 --dry-run --exports-dir C:/NXC/exp --logs-dir C:/NXC/logs
    - [本番実行]   python tools/code_export_gemini_policy_driven.py --roots . --profile gemini-10 --exports-dir C:/NXC/exp --logs-dir C:/NXC/logs
  - GUI: 既存のGUIから本スクリプトを呼び出す。
    - [推奨設定] GUIのデフォルト出力先(ExportRoot)は `C:/NXC/exp`、ログ(LogRoot)は `C:/NXC/logs` のように短い固定パスをレジストリ等で保持。
"""

from __future__ import annotations
import argparse
import io
import os
import sys
import shutil
import zipfile
import hashlib
import fnmatch
from pathlib import Path
from datetime import datetime
from typing import List, Tuple, Dict, Optional, Set

# =========================
#  固定情報・ポリシー定数
# =========================

VERSION = "v9.0 (policy-driven)"
BUILD_DATE_JST = "2025-08-27"

MANIFEST_INCLUDED_FILES_MAX: Optional[int] = 5000
DEFAULT_EXPORTS_DIR = Path("./exports").resolve()
ZIP_COMPRESSION = zipfile.ZIP_DEFLATED

# [恒久対策] 除外ディレクトリ (denylist)
EXCLUDE_DIRS: Set[str] = {
    # 標準的な除外
    ".git", ".venv", "venv", "__pycache__", "node_modules", ".idea", ".vscode",
    # 自己再帰・成果物・レポート・計測系
    "exports", "exported_projects", "output", "project_structure_export",
    "dist", "build", "out",
    "htmlcov", "coverage", "logs", "history", "evaluation",
    ".pytest_cache", ".mypy_cache", ".ruff_cache",
    "site-packages", "Lib", "Scripts"
}

# [恒久対策] 除外グロブパターン (denylist)
EXCLUDE_GLOB_PATTERNS: List[str] = [
    # 成果物/レポート/自己再帰
    "**/exports/**", "**/exported_projects/**", "**/output/**",
    "**/project_structure_export/**", "**/htmlcov*/**", "**/coverage*/**",
    "**/logs/**", "**/history/**", "**/evaluation/**",
    # アーカイブ/画像
    "**/*.zip", "**/*.7z", "**/*.tar", "**/*.gz",
    "**/*.gif", "**/*.png", "**/*.jpg", "**/*.jpeg",
    # コンパイル済みファイル/バイナリ
    "*.pyc", "*.pyo", "*.pyd", "*.so", "*.dylib", "*.dll", "*.exe", "*.class",
]

# パス長/深さ制限
MAX_PATH_SAFE = 240
MAX_DEPTH = 12

# プロファイルレジストリ
PROFILE_REGISTRY: Dict[str, Dict] = {
    "gemini-10": {
        "label": "Gemini (≤10MB, policy-driven)", "target_mb": 10, "include_ipynb": False,
        "fallback_binary_max_bytes": 128 * 1024,
        "json_defer_threshold_bytes": 512 * 1024,
        "max_text_file_bytes": 2 * 1024 * 1024,  # [新規ポリシー] 巨大テキスト自動除外
    },
    "gpt5-50": {
        "label": "GPT-5 (≤50MB)", "target_mb": 50, "include_ipynb": True,
        "fallback_binary_max_bytes": 1024 * 1024,
        "json_defer_threshold_bytes": 2 * 1024 * 1024,
    },
    "custom": {
        "label": "Custom", "target_mb": None, "include_ipynb": True,
        "fallback_binary_max_bytes": 1024 * 1024,
        "json_defer_threshold_bytes": 1024 * 1024,
    }
}

PRIMARY_EXTS = {".py"}
SECONDARY_TEXT_EXTS = {
    ".md", ".txt", ".toml", ".ini", ".cfg", ".json", ".yml", ".yaml",
    ".csv", ".html", ".htm", ".css", ".js", "pyproject.toml", "requirements.txt"
}
SECONDARY_BIN_EXTS = {".svg", ".ico"} # .png, .jpg等はGLOBで除外

ENTRYPOINT_HINTS = {"main_", "run_", "wsgi", "asgi", "manage.py", "__init__.py"}
IMPORTANT_PATH_HINTS = {"orchestrator.py", "routes.py", "src/nexuscore/core"}

# =========================
#  ユーティリティ
# =========================

MB = 1024 * 1024

def now_stamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")

def to_mb(nbytes: int) -> float:
    return round(nbytes / MB, 2)

def safe_mkdir(p: Path):
    p.mkdir(parents=True, exist_ok=True)

def is_hidden(p: Path) -> bool:
    return p.name.startswith(".") and p.name not in {".env", ".env.template"}

def ext_of(p: Path) -> str:
    # "requirements.txt" のようなファイル名自体を拡張子として扱う
    if p.name in {"pyproject.toml", "requirements.txt"}:
        return p.name
    return p.suffix.lower()

def relpath_under_roots(path: Path, roots: List[Path]) -> Path:
    for r in roots:
        try:
            return path.relative_to(r)
        except ValueError:
            continue
    return Path(path.name)

# ===================================
#  パス操作ユーティリティ群 (v8.0から変更なし)
# ===================================

def _maybe_flatten_rel(rel_path: Path) -> Path:
    try:
        parts = rel_path.parts
        if len(parts) <= MAX_DEPTH: return rel_path
        keep = parts[:MAX_DEPTH - 1]
        deep_rest = "_".join(parts[MAX_DEPTH - 1:-1])
        return Path(*keep) / ("__deep__" + deep_rest) / parts[-1]
    except Exception: return rel_path

def _path_shorten(base_dir: Path, rel_path: Path) -> Path:
    rel_str = str(rel_path).replace("\\", "/")
    if len(str(base_dir / rel_str)) <= MAX_PATH_SAFE:
        return Path(rel_str.replace("/", "\\"))
    parts = rel_str.split("/")
    if len(parts) <= 2:
        head, tail = ("/".join(parts[:-1]), parts[-1])
        h = hashlib.sha1(rel_str.encode("utf-8")).hexdigest()[:12]
        short_tail = (tail[:40] + "__" + h) if len(tail) > 55 else tail
        return Path(((head + "/" + short_tail).strip("/")).replace("/", "\\"))
    head, mid, tail = parts[0], parts[1:-1], parts[-1]
    new_mid = [
        (seg if seg.lower() in {"src", "app", "tools", "nexuscore"}
         else seg[:8] + "_" + hashlib.sha1(seg.encode("utf-8")).hexdigest()[:8])
        for seg in mid
    ]
    candidate_str = "/".join([head] + new_mid + [tail])
    if len(str(base_dir / candidate_str)) <= MAX_PATH_SAFE:
        return Path(candidate_str.replace("/", "\\"))
    h2 = hashlib.sha1(candidate_str.encode("utf-8")).hexdigest()[:10]
    stem, ext = tail.rsplit(".", 1) if "." in tail else (tail, "")
    tail_short = f"{stem[:30]}__{h2}{'.' + ext if ext else ''}"
    return Path(("/".join([head] + new_mid + [tail_short])).replace("/", "\\"))

def _write_pathmap(pathmap: List[Tuple[str, str]], out_dir: Path):
    if not pathmap: return
    with (out_dir / "_PATHMAP.txt").open("w", encoding="utf-8") as f:
        f.write("# original_relpath -> shortened_relpath\n")
        for orig, short in sorted(pathmap):
            f.write(f"{orig} -> {short}\n")

# =========================
#  ログクラス
# =========================

class ExportLogger:
    def __init__(self): self.lines: List[str] = []
    def log(self, s: str): self.lines.append(s); print(s)
    def step(self, s: str): self.log(s)
    def dump_to(self, path: Path):
        safe_mkdir(path.parent)
        path.write_text("\n".join(self.lines), encoding="utf-8")

# =========================
#  スキャン & スコアリング
# =========================

def scan_candidates(roots: List[Path], profile: Dict, logger: ExportLogger) -> List[Tuple[Path, Path, int, int]]:
    cands, seen_paths = [], set()
    max_text_size = profile.get("max_text_file_bytes")

    logger.step(f"🔎 スキャン開始 (除外 Dirs: {len(EXCLUDE_DIRS)}, Globs: {len(EXCLUDE_GLOB_PATTERNS)})")
    for root in roots:
        if not root.is_dir(): continue
        for abs_path in root.rglob("*"):
            if abs_path in seen_paths or abs_path.is_dir(): continue
            seen_paths.add(abs_path)

            try: rel_parts = abs_path.relative_to(root).parts
            except ValueError: continue

            if any(p in EXCLUDE_DIRS for p in rel_parts): continue
            if any(fnmatch.fnmatch(abs_path.as_posix(), pat) for pat in EXCLUDE_GLOB_PATTERNS): continue
            if is_hidden(abs_path): continue

            try: size = abs_path.stat().st_size
            except OSError: continue

            ext = ext_of(abs_path)
            if ext == ".ipynb" and not profile["include_ipynb"]: continue
            
            # [gemini-10ポリシー] 巨大テキストファイルの自動除外
            if max_text_size and ext in SECONDARY_TEXT_EXTS and size > max_text_size:
                logger.log(f"  -SKIP(size): {abs_path.relative_to(root)} ({to_mb(size):.1f}MB > {to_mb(max_text_size):.1f}MB)")
                continue

            score = 0
            if ext in PRIMARY_EXTS: score += 1000
            elif ext in {"pyproject.toml", "requirements.txt"}: score += 500
            elif ext in SECONDARY_TEXT_EXTS: score += 100
            elif ext in SECONDARY_BIN_EXTS: score += 10
            else: score += 1
            
            low_name = abs_path.name.lower()
            if any(h in low_name for h in ENTRYPOINT_HINTS): score += 50
            if any(h in str(abs_path.relative_to(root)).lower() for h in IMPORTANT_PATH_HINTS): score += 80
            if ext == ".json" and size >= profile["json_defer_threshold_bytes"]: score -= 40
            
            cands.append((root, abs_path, size, score))

    cands.sort(key=lambda x: (-x[3], x[2]))
    logger.step(f"✅ スキャン完了: {len(cands)}件の候補ファイルを発見")
    return cands

# =========================
#  圧縮試算 & ピック
# =========================

def pick_files(roots: List[Path], profile: Dict, target_mb: int, logger: ExportLogger) -> Tuple[List[Tuple[Path, Path]], int, List[str]]:
    notes, picked = [], []
    cands = scan_candidates(roots, profile, logger)
    target_bytes = int(target_mb * MB)
    
    with io.BytesIO() as buf, zipfile.ZipFile(buf, "w", ZIP_COMPRESSION) as zf:
        logger.step(f"[INIT] ZIP = {to_mb(buf.tell())} MB")
        for root, abspath, size, score in cands:
            if MANIFEST_INCLUDED_FILES_MAX and len(picked) >= MANIFEST_INCLUDED_FILES_MAX:
                notes.append(f"hit file-cap {MANIFEST_INCLUDED_FILES_MAX}"); break
            if buf.tell() >= target_bytes * 1.02: break

            if ext_of(abspath) in SECONDARY_BIN_EXTS and size > profile["fallback_binary_max_bytes"]: continue
            
            rel = relpath_under_roots(abspath, roots)
            arcname = ("included_source" / rel).as_posix()
            
            zf.write(abspath, arcname)
            picked.append((root, abspath))
            logger.step(f"+ {rel.as_posix()} (score:{score}) -> {to_mb(buf.tell())} MB")
        
        final_bytes = buf.tell()
    return picked, final_bytes, notes

# =========================
#  マニフェスト生成
# =========================

def create_manifest_and_zip(
    manifest_dir: Path, zip_path: Path, roots: List[Path], picked: List[Tuple[Path, Path]],
    meta_docs: Dict[str, str], logger: ExportLogger
):
    safe_mkdir(manifest_dir)
    inc_dir = manifest_dir / "included_source"
    safe_mkdir(inc_dir)
    pathmap: List[Tuple[str, str]] = []

    for root, abspath in picked:
        orig_rel = relpath_under_roots(abspath, roots)
        flattened_rel = _maybe_flatten_rel(orig_rel)
        safe_rel = _path_shorten(inc_dir, flattened_rel)
        dest = inc_dir / safe_rel
        safe_mkdir(dest.parent)
        shutil.copy2(abspath, dest)
        if orig_rel.as_posix() != safe_rel.as_posix():
            pathmap.append((orig_rel.as_posix(), safe_rel.as_posix()))

    for name, content in meta_docs.items():
        (manifest_dir / name).write_text(content, encoding="utf-8")
    _write_pathmap(pathmap, manifest_dir)

    with zipfile.ZipFile(zip_path, "w", ZIP_COMPRESSION) as zf:
        for item in manifest_dir.rglob("*"):
            if item.is_file(): zf.write(item, item.relative_to(manifest_dir).as_posix())

# =========================
#  エクスポート本体
# =========================

def export_for_profile(
    roots: List[Path], profile_name: str, target_mb_custom: Optional[int],
    dry_run: bool, exports_dir: Path, logs_dir: Path, logger: ExportLogger,
) -> Tuple[Optional[Path], Optional[Path], Path]:
    profile = PROFILE_REGISTRY[profile_name]
    target_mb = target_mb_custom if profile_name == "custom" else profile["target_mb"]
    if profile_name == "custom" and not target_mb:
        raise ValueError("customプロファイルでは --target-mb を正の値で指定してください。")

    ts = now_stamp()
    manifest_dir = exports_dir / f"NexusCore_manifest_{ts}"
    zip_label = profile_name.split('-')[0]
    zip_path = exports_dir / f"NexusCore_{zip_label}_{ts}.zip"

    picked, est_bytes, notes = pick_files(roots, profile, target_mb, logger)
    est_mb = to_mb(est_bytes)

    readme_md = f"""# NexusCore Export Manifest
- Version: {VERSION} / Build: {BUILD_DATE_JST}
- Profile: {profile['label']} (Target: {target_mb} MB)
- Roots: {", ".join(str(r.resolve()) for r in roots)}
- Files Picked: {len(picked)} (~{est_mb} MB, zipped estimate)
- Path Safety: Enabled (MAX_PATH={MAX_PATH_SAFE}, MAX_DEPTH={MAX_DEPTH})
"""
    meta_docs = {
        "README.md": readme_md,
        "PROJECT_CHRONICLE.md": f"# PROJECT_CHRONICLE\n- Exported at: {ts}\n- Notes: {', '.join(notes) if notes else 'N/A'}\n",
        "CODE_REFERENCE_INDEX.md": "# CODE_REFERENCE_INDEX\n\n" + "\n".join(f"- {relpath_under_roots(p, roots).as_posix()}" for _, p in picked),
        "EXPORT_LOG.txt": "\n".join(logger.lines)
    }

    logger.step(f"🔎 {'ドライラン' if dry_run else 'ピック'}結果: 推定ZIP {est_mb} MB / {len(picked)} 件")
    
    log_name = f"NexusCore_export_{'dryrun_' if dry_run else 'run_'}{ts}.txt"
    saved_log_path = logs_dir / log_name
    logger.dump_to(saved_log_path)

    if not dry_run:
        create_manifest_and_zip(manifest_dir, zip_path, roots, picked, meta_docs, logger)
        logger.step(f"📦 出力先(Manifest): {manifest_dir}")
        logger.step(f"📦 出力先(ZIP):      {zip_path}")
    
    logger.step(f"📝 ログ保存:         {saved_log_path}")
    return (None, None, saved_log_path) if dry_run else (zip_path, manifest_dir, saved_log_path)

# =========================
#  CLI
# =========================

def main():
    p = argparse.ArgumentParser(description=f"NexusCore Exporter ({VERSION})")
    p.add_argument("--roots", nargs="+", default=["."], help="スキャン対象のルートディレクトリ")
    p.add_argument("--profile", choices=list(PROFILE_REGISTRY.keys()), default="gemini-10", help="ターゲットプロファイル")
    p.add_argument("--target-mb", type=int, help="profile=custom時の目標サイズ(MB)")
    p.add_argument("--dry-run", action="store_true", help="見積とログのみ保存")
    p.add_argument("--exports-dir", default=str(DEFAULT_EXPORTS_DIR), help="出力先ディレクトリ")
    p.add_argument("--logs-dir", help="ログファイルの出力先 (デフォルトは --exports-dir)")
    args = p.parse_args()

    logger = ExportLogger()
    logger.step(f"=== NexusCore Exporter {VERSION} / Build {BUILD_DATE_JST} ===")
    logger.step(f"Profile: {args.profile} ({PROFILE_REGISTRY[args.profile]['label']})")
    
    try:
        exports_dir = Path(args.exports_dir).resolve()
        logs_dir = Path(args.logs_dir).resolve() if args.logs_dir else exports_dir
        safe_mkdir(exports_dir); safe_mkdir(logs_dir)
        
        zip_path, manifest_dir, log_path = export_for_profile(
            roots=[Path(r) for r in args.roots],
            profile_name=args.profile, target_mb_custom=args.target_mb,
            dry_run=args.dry_run, exports_dir=exports_dir,
            logs_dir=logs_dir, logger=logger,
        )

        print("\n--- Export Summary ---")
        if args.dry_run:
            print("👁‍🗨 プレビュー完了 (ドライラン)")
        else:
            total_mb = to_mb(zip_path.stat().st_size) if zip_path and zip_path.exists() else 0.0
            print(f"✅ エクスポート完了 ({total_mb:.2f} MB)")
            print(f"  - Manifest: {manifest_dir}")
            print(f"  - ZIP:      {zip_path}")
        print(f"  - Log:      {log_path}")
        print("--------------------")

    except Exception as e:
        logger.log(f"\n❌ エラーが発生しました: {type(e).__name__}: {e}")
        error_log_path = (Path(args.logs_dir) if args.logs_dir else Path(args.exports_dir)) / f"NexusCore_export_ERROR_{now_stamp()}.txt"
        logger.dump_to(error_log_path)
        print(f"🔥 詳細エラーログ: {error_log_path}")
        sys.exit(1)

if __name__ == "__main__":
    main()
