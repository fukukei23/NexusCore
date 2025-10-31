# -*- coding: utf-8 -*-
"""
File: tools/code_export_gemini_robust_final.py
Version: v8.0 (robust-path)
Date: 2025-08-26 JST
Author: NexusCore Export Pipeline (with Robustness Patch)

目的:
  - v7.2の全機能(プロファイル別/all-py-first戦略/デュアル出力/ドライラン)を維持
  - [堅牢化] Windowsの最大パス長制限(MAX_PATH)に対応
    1. 自己再帰/成果物を厳密に除外 (exports, dist, build等をスキャン対象外に)
    2. パス長が240文字を超える場合、中間セグメントをハッシュ化して短縮
    3. パスの階層が深すぎる場合、中間をフラット化して階層を抑制
    4. パス短縮の対応表 `_PATHMAP.txt` を自動生成し、追跡可能性を確保

このスクリプトが生成するもの:
  - C:/NXC/exp/NexusCore_manifest_YYYYMMDD_HHMMSS/         (フォルダ展開)
    - included_source/ ... 選定したファイルの実体（パスは短縮/フラット化される可能性あり）
    - _PATHMAP.txt       ... (新規) 元パスと短縮後パスの対応表
    - README.md / PROJECT_CHRONICLE.md / CODE_REFERENCE_INDEX.md / EXPORT_LOG.txt
  - C:/NXC/exp/NexusCore_gemini_YYYYMMDD_HHMMSS.zip        (ZIPアーカイブ)
  - C:/NXC/exp/NexusCore_export_run_YYYYMMDD_HHMMSS.txt    (実行ログ; ドライラン時は *_dryrun_*.txt)

想定の操作ソフト/運用メモ:
  - CLI (推奨):
    `python tools/code_export_gemini_robust_final.py --roots . --profile gemini-10 --exports-dir C:/NXC/exp`
  - GUI: 既存の `tools/code_export_gui.py` 等から本スクリプトを呼び出す。
    - [推奨設定] GUIのデフォルト出力先やレジストリキー(例: `ExportRoot`)で `C:/NXC/exp` のような短い固定パスを保持すると、パス長問題のリスクをさらに低減できます。
  - ログは指定された出力先 (例: `C:/NXC/exp/`) に常時保存されます。
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

VERSION = "v8.0 (robust-path)"
BUILD_DATE_JST = "2025-08-26"

# 上限は「十分大きく」。ただし OOM/極端膨張を防ぐため 5,000 で安全運用
MANIFEST_INCLUDED_FILES_MAX: Optional[int] = 5000

# ルート/出力
SCRIPT_DIR = Path(__file__).resolve().parent
# [運用メモ] C:\NXC\exp のような短い固定パスを推奨
DEFAULT_EXPORTS_DIR = (SCRIPT_DIR / ".." / "exports").resolve()

# 圧縮
ZIP_COMPRESSION = zipfile.ZIP_DEFLATED

# [堅牢化①] 除外ルールの強化
EXCLUDE_DIRS: Set[str] = {
    # 標準的な除外
    ".git", ".venv", "venv", "__pycache__", "node_modules", ".idea", ".vscode",
    # 自己再帰・成果物の再混入を防止
    "exports", "exported_projects",
    "dist", "build", "out",
    ".pytest_cache", ".mypy_cache", ".ruff_cache",
    "htmlcov", "coverage", "logs", "site-packages", "Lib", "Scripts"
}
EXCLUDE_GLOB_PATTERNS: List[str] = [
    # 成果物/アーカイブ
    "**/tools/exports/**", "**/export*/**", "**/htmlcov*/**", "**/coverage*/**",
    "**/*.zip", "**/*.7z", "**/*.tar", "**/*.gz",
    # コンパイル済みファイル/バイナリ
    "*.pyc", "*.pyo", "*.pyd", "*.so", "*.dylib", "*.dll", "*.exe", "*.class",
]

# [堅牢化②/③] パス長/深さ制限
MAX_PATH_SAFE = 240  # Windowsでの安全マージン
MAX_DEPTH = 12       # これを超える階層はフラット化

# プロファイルレジストリ
PROFILE_REGISTRY: Dict[str, Dict] = {
    "gemini-10": {
        "label": "Gemini (≤10MB)", "target_mb": 10, "include_ipynb": False,
        "fallback_binary_max_bytes": 128 * 1024, "json_defer_threshold_bytes": 512 * 1024,
    },
    "gpt5-50": {
        "label": "GPT-5 (≤50MB)", "target_mb": 50, "include_ipynb": True,
        "fallback_binary_max_bytes": 1024 * 1024, "json_defer_threshold_bytes": 2 * 1024 * 1024,
    },
    "custom": {
        "label": "Custom", "target_mb": None, "include_ipynb": True,
        "fallback_binary_max_bytes": 1024 * 1024, "json_defer_threshold_bytes": 1024 * 1024,
    }
}

PRIMARY_EXTS = {".py"}
SECONDARY_TEXT_EXTS = {
    ".md", ".txt", ".toml", ".ini", ".cfg", ".json", ".yml", ".yaml",
    ".csv", ".html", ".htm", ".css", ".js",
}
SECONDARY_BIN_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico"}

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
    return p.suffix.lower()

def relpath_under_roots(path: Path, roots: List[Path]) -> Path:
    for r in roots:
        try:
            return path.relative_to(r)
        except ValueError:
            continue
    return Path(path.name)

# ===================================
#  [堅牢化] パス操作ユーティリティ群
# ===================================

def _maybe_flatten_rel(rel_path: Path) -> Path:
    """深すぎる階層をフラット化する (最終安全弁)"""
    try:
        parts = rel_path.parts
        if len(parts) <= MAX_DEPTH:
            return rel_path
        # 超過分をまとめて '__deep__' に押し込む
        keep = parts[:MAX_DEPTH - 1]
        deep_rest = "_".join(parts[MAX_DEPTH - 1:-1])
        flattened = Path(*keep) / ("__deep__" + deep_rest) / parts[-1]
        return flattened
    except Exception:
        return rel_path

def _path_shorten(base_dir: Path, rel_path: Path) -> Path:
    """相対パスを240文字以下に短縮。中間セグメントをハッシュ置換。"""
    rel_str = str(rel_path).replace("\\", "/")
    full_path_str = str(base_dir / rel_str).replace("/", "\\")

    if len(full_path_str) <= MAX_PATH_SAFE:
        return Path(rel_str.replace("/", "\\"))

    parts = rel_str.split("/")
    # ファイル名はなるべく保持し、中間セグメントを短縮
    if len(parts) <= 2:
        # ディレクトリ/ファイル名 の形式
        head, tail = ("/".join(parts[:-1]), parts[-1])
        h = hashlib.sha1(rel_str.encode("utf-8")).hexdigest()[:12]
        short_tail = (tail[:40] + "__" + h) if len(tail) > 55 else tail
        s = (head + "/" + short_tail).strip("/")
        return Path(s.replace("/", "\\"))

    # 中間をハッシュ化しながら短縮
    head, mid, tail = parts[0], parts[1:-1], parts[-1]
    new_mid = []
    for seg in mid:
        if seg.lower() in {"src", "app", "tools", "nexuscore"}:
            new_mid.append(seg)
            continue
        h = hashlib.sha1(seg.encode("utf-8")).hexdigest()[:8]
        new_mid.append(seg[:8] + "_" + h)

    candidate_str = "/".join([head] + new_mid + [tail])
    if len(str(base_dir / candidate_str)) <= MAX_PATH_SAFE:
        return Path(candidate_str.replace("/", "\\"))

    # まだ長い場合はファイル名も短縮
    h2 = hashlib.sha1(candidate_str.encode("utf-8")).hexdigest()[:10]
    if "." in tail:
        stem, ext = tail.rsplit(".", 1)
        tail_short = f"{stem[:30]}__{h2}.{ext}"
    else:
        tail_short = f"{tail[:30]}__{h2}"
    
    candidate2_str = "/".join([head] + new_mid + [tail_short])
    return Path(candidate2_str.replace("/", "\\"))

def _write_pathmap(pathmap: List[Tuple[str, str]], out_dir: Path):
    """元の相対パス -> 短縮後パス の対応表を書き出す"""
    if not pathmap: return
    p = out_dir / "_PATHMAP.txt"
    with p.open("w", encoding="utf-8") as f:
        f.write("# original_relpath -> shortened_relpath\n")
        for orig, short in sorted(pathmap):
            f.write(f"{orig} -> {short}\n")

# =========================
#  ログクラス
# =========================

class ExportLogger:
    def __init__(self):
        self.lines: List[str] = []

    def log(self, s: str):
        self.lines.append(s)
        print(s)

    def step(self, s: str): self.log(s)

    def dump_to(self, path: Path):
        safe_mkdir(path.parent)
        path.write_text("\n".join(self.lines), encoding="utf-8")

# =========================
#  スキャン & スコアリング
# =========================

def scan_candidates(roots: List[Path], profile: Dict, logger: ExportLogger) -> List[Tuple[Path, Path, int, int]]:
    """return: list of (root, abs_path, size_bytes, score)"""
    cands: List[Tuple[Path, Path, int, int]] = []
    seen_paths: Set[Path] = set()
    
    for root in roots:
        if not root.is_dir(): continue
        # rglobはシンボリックリンクを追わない
        for abs_path in root.rglob("*"):
            if abs_path in seen_paths: continue
            seen_paths.add(abs_path)

            # [堅牢化①] 除外ルールの適用
            rel_parts = abs_path.relative_to(root).parts
            if any(part in EXCLUDE_DIRS for part in rel_parts):
                continue
            
            if abs_path.is_dir(): continue
            
            posix_path = abs_path.as_posix()
            if any(fnmatch.fnmatch(posix_path, pat) for pat in EXCLUDE_GLOB_PATTERNS):
                continue
            if is_hidden(abs_path): continue

            ext = ext_of(abs_path)
            if ext == ".ipynb" and not profile["include_ipynb"]: continue

            try:
                size = abs_path.stat().st_size
            except OSError:
                continue

            # スコアリング
            score = 0
            if ext in PRIMARY_EXTS: score += 1000
            elif ext in SECONDARY_TEXT_EXTS: score += 100
            elif ext in SECONDARY_BIN_EXTS: score += 10
            else: score += 1

            low_name = abs_path.name.lower()
            if any(h in low_name for h in ENTRYPOINT_HINTS): score += 50
            
            low_rel_path = str(abs_path.relative_to(root)).lower().replace("\\", "/")
            if any(h in low_rel_path for h in IMPORTANT_PATH_HINTS): score += 80

            if ext == ".json" and size >= profile["json_defer_threshold_bytes"]: score -= 40
            
            if size < 64 * 1024: score += 5
            elif size > 256 * 1024: score -= 2

            cands.append((root, abs_path, size, score))

    cands.sort(key=lambda x: (-x[3], x[2]))
    return cands

# =========================
#  圧縮試算 & ピック
# =========================

class ZipSizer:
    def __init__(self):
        self.buf = io.BytesIO()
        self.zip = zipfile.ZipFile(self.buf, "w", compression=ZIP_COMPRESSION)

    def add_file(self, arcname: str, abspath: Path):
        self.zip.write(abspath, arcname)

    def tell(self) -> int:
        self.zip.fp.flush()
        return self.buf.tell()

    def close(self): self.zip.close()

def pick_files(roots: List[Path], profile: Dict, target_mb: int, logger: ExportLogger) -> Tuple[List[Tuple[Path, Path]], int, List[str]]:
    """ファイルを選択し、推定ZIPサイズを返す"""
    notes: List[str] = []
    cands = scan_candidates(roots, profile, logger)
    target_bytes = int(target_mb * MB)
    sizer = ZipSizer()
    picked: List[Tuple[Path, Path]] = []
    
    logger.step(f"[INIT] ZIP = {to_mb(sizer.tell())} MB")

    for root, abspath, size, score in cands:
        if MANIFEST_INCLUDED_FILES_MAX and len(picked) >= MANIFEST_INCLUDED_FILES_MAX:
            notes.append(f"hit file-cap {MANIFEST_INCLUDED_FILES_MAX}")
            break
        if sizer.tell() >= target_bytes * 1.02: # 2%の超過を許容
            break

        # バイナリはサイズ上限をチェック
        if ext_of(abspath) in SECONDARY_BIN_EXTS and size > profile["fallback_binary_max_bytes"]:
            continue
        
        # arcnameは仮で。サイズ見積もりが主目的
        rel = relpath_under_roots(abspath, roots)
        arcname = ("included_source" / rel).as_posix()

        before = sizer.tell()
        sizer.add_file(arcname, abspath)
        after = sizer.tell()
        
        picked.append((root, abspath))
        logger.step(f"+ {arcname} ({ext_of(abspath)}, {score}) -> {to_mb(after)} MB")

    final_bytes = sizer.tell()
    sizer.close()
    return picked, final_bytes, notes

# =========================
#  マニフェスト生成
# =========================

def create_manifest_and_zip(
    manifest_dir: Path, zip_path: Path, roots: List[Path], picked: List[Tuple[Path, Path]],
    meta_docs: Dict[str, str], logger: ExportLogger
):
    """フォルダ展開とZIPアーカイブを同時に生成する"""
    safe_mkdir(manifest_dir)
    inc_dir = manifest_dir / "included_source"
    safe_mkdir(inc_dir)
    
    pathmap: List[Tuple[str, str]] = []

    # ファイルコピーとパス短縮
    for root, abspath in picked:
        orig_rel = relpath_under_roots(abspath, roots)
        
        # [堅牢化③ -> ②] 深さ制限をかけてからパス短縮
        flattened_rel = _maybe_flatten_rel(orig_rel)
        safe_rel = _path_shorten(inc_dir, flattened_rel)
        
        dest = inc_dir / safe_rel
        safe_mkdir(dest.parent)
        shutil.copy2(abspath, dest)

        orig_rel_posix = orig_rel.as_posix()
        safe_rel_posix = safe_rel.as_posix()
        if orig_rel_posix != safe_rel_posix:
            pathmap.append((orig_rel_posix, safe_rel_posix))

    # メタドキュメントとパス対応表
    for name, content in meta_docs.items():
        (manifest_dir / name).write_text(content, encoding="utf-8")
    
    _write_pathmap(pathmap, manifest_dir)

    # ZIP 生成（Manifest 丸ごと）
    with zipfile.ZipFile(zip_path, "w", compression=ZIP_COMPRESSION) as zf:
        for item in manifest_dir.rglob("*"):
            if item.is_file():
                zf.write(item, item.relative_to(manifest_dir).as_posix())

# =========================
#  エクスポート本体
# =========================

def export_for_profile(
    roots: List[Path], profile_name: str, target_mb_custom: Optional[int],
    dry_run: bool, exports_dir: Path, logger: ExportLogger,
) -> Tuple[Optional[Path], Optional[Path], Path]:
    """ returns: (zip_path or None, manifest_dir or None, saved_log_path) """
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

    # メタドキュメント準備
    readme_md = f"""# NexusCore Export Manifest
- Version: {VERSION} / Build: {BUILD_DATE_JST}
- Profile: {profile['label']} (Target: {target_mb} MB)
- Roots: {", ".join(str(r.resolve()) for r in roots)}
- Files Picked: {len(picked)} (~{est_mb} MB, zipped estimate)
- Path Safety: Enabled (MAX_PATH={MAX_PATH_SAFE}, MAX_DEPTH={MAX_DEPTH})
"""
    chronicle_md = f"# PROJECT_CHRONICLE\n- Exported at: {ts}\n- Notes: {', '.join(notes) if notes else 'N/A'}\n"
    refindex_md = "# CODE_REFERENCE_INDEX\n\n" + "\n".join(f"- {relpath_under_roots(p, roots).as_posix()}" for _, p in picked)
    
    meta_docs = {
        "README.md": readme_md,
        "PROJECT_CHRONICLE.md": chronicle_md,
        "CODE_REFERENCE_INDEX.md": refindex_md,
        "EXPORT_LOG.txt": "\n".join(logger.lines)
    }

    if dry_run:
        logger.step(f"🔎 ドライラン結果: 推定ZIP {est_mb} MB / 追加ファイル {len(picked)} 件")
    else:
        logger.step(f"✅ ピック完了: 推定ZIP {est_mb} MB / 追加ファイル {len(picked)} 件")

    log_name = f"NexusCore_export_{'dryrun_' if dry_run else 'run_'}{ts}.txt"
    saved_log_path = exports_dir / log_name
    logger.dump_to(saved_log_path)

    if dry_run:
        return None, None, saved_log_path

    create_manifest_and_zip(manifest_dir, zip_path, roots, picked, meta_docs, logger)
    
    logger.step(f"📦 出力先(Manifest): {manifest_dir}")
    logger.step(f"📦 出力先(ZIP):      {zip_path}")
    logger.step(f"📝 ログ保存:         {saved_log_path}")

    return zip_path, manifest_dir, saved_log_path

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
    args = p.parse_args()

    logger = ExportLogger()
    logger.step(f"=== NexusCore Exporter {VERSION} / Build {BUILD_DATE_JST} ===")
    logger.step(f"Profile: {args.profile} ({PROFILE_REGISTRY[args.profile]['label']})")
    
    try:
        exports_dir = Path(args.exports_dir).resolve()
        safe_mkdir(exports_dir)
        
        zip_path, manifest_dir, log_path = export_for_profile(
            roots=[Path(r) for r in args.roots],
            profile_name=args.profile,
            target_mb_custom=args.target_mb,
            dry_run=args.dry_run,
            exports_dir=exports_dir,
            logger=logger,
        )

        print("\n--- Export Summary ---")
        if args.dry_run:
            print("👁‍🗨 プレビュー完了 (ドライラン)")
            print(f"📝 ログ保存: {log_path}")
        else:
            total_mb = to_mb(zip_path.stat().st_size) if zip_path and zip_path.exists() else 0.0
            print(f"✅ エクスポート完了 ({total_mb:.2f} MB)")
            print(f"  - Manifest: {manifest_dir}")
            print(f"  - ZIP:      {zip_path}")
            print(f"  - Log:      {log_path}")
        print("--------------------")

    except Exception as e:
        logger.log(f"\n❌ エラーが発生しました: {type(e).__name__}: {e}")
        # ログファイルにもエラーを書き込む
        error_log_path = Path(args.exports_dir) / f"NexusCore_export_ERROR_{now_stamp()}.txt"
        logger.dump_to(error_log_path)
        print(f"🔥 詳細エラーログ: {error_log_path}")
        sys.exit(1)

if __name__ == "__main__":
    main()
