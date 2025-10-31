# -*- coding: utf-8 -*-
"""
NexusCore Exporter - all-py-first v7.2 (2025-08-27, JST)
========================================================
- 目的: Gemini/GPT-5 へのアップロード最適化用のコード/マニフェストパッカー
- 本版の要点:
  * Geminiでも一旦 *.py を“できる限り全部”詰める挙動に切替（all_py_first）
  * フォルダ展開 + ZIP の両生成
  * プロファイル別ポリシー (gemini-10 / gpt5-50 / custom)
  * ドライラン & 逐次サイズ推移ログ
  * CustomサイズUIの条件表示（プリセット選択時は target-mb を無視）
  * ログは logs/ に分離保存（exports/ と別）
  * Windows 長パス対策（パス短縮/ハッシュ化＋ \\?\ プレフィックス利用）
  * MAX_FILES=5000
  * 重量超過時の重い順 TopN 出力
  * 進捗表示と、最終サマリの明示

使用ソフト/前提:
- Python 3.10+ 推奨（Windows 長パス有効化済が望ましい）
- zipfile, pathlib, shutil, hashlib, argparse, json, glob, time 等 標準ライブラリ

操作メモ:
- まず `--dry-run` で拾い方・見積りを確認
- 問題なければ `--emit-folder --emit-zip` で本番出力
- 10MBオーバー時はログ末尾の TopN 重ファイルを見て除外ルールを調整

(c) NexusCore Tools, けんゆきな様向けカスタム
"""

from __future__ import annotations
import argparse
import os
import sys
import re
import json
import time
import shutil
import hashlib
import zipfile
from dataclasses import dataclass
from typing import List, Tuple, Dict, Iterable, Optional
from pathlib import Path

# ---------------------------------------------------------------------------
# 0) 定数とプロファイルレジストリ（運用しやすいよう冒頭に集約）
# ---------------------------------------------------------------------------

# 既定ディレクトリ
DEFAULT_EXPORTS_DIR = r"C:\Users\USER\tools\NexusCore\exports"
DEFAULT_LOGS_DIR    = r"C:\Users\USER\tools\NexusCore\logs"

# 既定プロファイルとサイズ
DEFAULT_PROFILE   = "gemini-10"  # 既定をGemini(≤10MB)に固定
DEFAULT_TARGET_MB = 9.5          # 圧縮揺れ対策の余裕
MAX_PICK_FILES    = 5000         # 件数上限

# 単一ファイル上限（MB）と文書系上限（KB）
SINGLE_FILE_MAX_MB = 2.0         # あまりに重い単体はスキップ
DOC_MAX_KB         = 200         # .txt/.md/.html 等の文書を必要最小限に

# バイナリアタッチ fallback 阈値（プロファイル毎に上書き可）
FALLBACK_BINARY_MAX_BYTES_DEFAULT = 256_000
FALLBACK_BINARY_MAX_BYTES_GPT5    = 1_000_000  # GPT-5プロファイルでは引き上げ

# 強制除外（ディレクトリ・ファイル）
EXCLUDE_DIR_GLOBS_BASE = [
    "exports/**", "exported_projects/**", "output/**",
    "project_structure_export/**", "history/**",
    "htmlcov*/**", "coverage*/**",
    ".venv/**", "venv/**", "__pycache__/**", "node_modules/**",
    "logs/**",  # ログは別扱い
]

EXCLUDE_FILE_GLOBS_BASE = [
    "*.gif", "*.png", "*.jpg", "*.jpeg", "*.webp",
    "*.zip", "*.7z", "*.tar", "*.tar.gz", "*.tgz", "*.whl",
    "*.mp4", "*.mov", "*.avi",
    "*.log", "*.jsonl",
    "**/tree_sitter_languages/**/parser.c",
    "vscode-extension/**",
]

# プロファイル定義
SIZE_PROFILES: Dict[str, Dict] = {
    "gemini-10": {
        "target_mb": 9.5,
        "all_py_first": True,
        "exclude_files_more": [
            "*.ipynb",              # Gemini 用は ipynb は基本除外
            "*_combined_*.txt",     # 巨大結合テキスト
        ],
        "exclude_dirs_more": [],
        "doc_max_kb": 200,
        "single_file_max_mb": 2.0,
        "fallback_binary_max_bytes": FALLBACK_BINARY_MAX_BYTES_DEFAULT,
    },
    "gpt5-50": {
        "target_mb": 48.0,          # 余裕幅
        "all_py_first": True,
        "exclude_files_more": [
            # GPT5 は ipynb も積極採用するので追加除外は無し
        ],
        "exclude_dirs_more": [],
        "doc_max_kb": 400,          # 文書許容量を緩め
        "single_file_max_mb": 5.0,  # 単体許容量も拡大
        "fallback_binary_max_bytes": FALLBACK_BINARY_MAX_BYTES_GPT5,
    },
    "custom": {
        "target_mb": None,          # CLI --target-mb を使用
        "all_py_first": True,
        "exclude_files_more": [],
        "exclude_dirs_more": [],
        "doc_max_kb": DOC_MAX_KB,
        "single_file_max_mb": SINGLE_FILE_MAX_MB,
        "fallback_binary_max_bytes": FALLBACK_BINARY_MAX_BYTES_DEFAULT,
    }
}

# 推定圧縮率（概算）
COMPRESS_RATIO_BY_EXT = {
    ".py":   0.35,
    ".txt":  0.25,
    ".md":   0.25,
    ".html": 0.30,
    ".json": 0.30,
    ".yaml": 0.35, ".yml": 0.35,
    ".toml": 0.35,
    ".cfg":  0.35, ".ini": 0.35,
    # 既定
    "*":     0.60,
}

# Windows 長パス対策
LONG_PATH_PREFIX = "\\\\?\\"
MAX_PATH_SAFE = 240  # 目安: 260 未満でもフォルダ+ファイル名で溢れることあり


# ---------------------------------------------------------------------------
# 1) ユーティリティ
# ---------------------------------------------------------------------------

def now_stamp() -> str:
    return time.strftime("%Y%m%d_%H%M%S")

def to_win_long(path: Path) -> str:
    """Windowsで長パスを扱うためのプレフィックス付与。非Windowsはそのまま。"""
    p = str(path.resolve())
    if os.name == "nt" and not p.startswith(LONG_PATH_PREFIX):
        return LONG_PATH_PREFIX + p
    return p

def human_mb(n_bytes: int) -> float:
    return round(n_bytes / (1024 * 1024), 2)

def ext_of(path: Path) -> str:
    return path.suffix.lower()

def guess_ratio(path: Path) -> float:
    return COMPRESS_RATIO_BY_EXT.get(ext_of(path), COMPRESS_RATIO_BY_EXT["*"])

def sha1(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8", errors="ignore")).hexdigest()[:12]

def ensure_dir(p: Path):
    p.mkdir(parents=True, exist_ok=True)

def glob_match(path: Path, patterns: List[str]) -> bool:
    sp = str(path).replace("\\", "/")
    for pat in patterns:
        if Path(sp).match(pat):
            return True
    return False

def flatten_and_shorten(rel_path: Path) -> Path:
    """
    パス長対策:
    - 深いディレクトリを短縮: 先頭セグメント群をハッシュに置換
    - 末尾側（ファイル名付近）は極力保持
    例: included_source/tools/exports/.../app_20250703_223016/file.py
       -> _hx/<sha>/.../file.py
    """
    parts = list(rel_path.parts)
    if len("/".join(parts)) <= 160:
        return rel_path
    # 末尾3セグメントは保持
    tail = parts[-3:]
    head = "/".join(parts[:-3])
    return Path("_hx") / sha1(head) / Path(*tail)

def rel_path_under(root: Path, file_path: Path) -> Path:
    try:
        return file_path.relative_to(root)
    except Exception:
        # 探索ルートが複数の場合など
        return Path(file_path.name)


# ---------------------------------------------------------------------------
# 2) ロギング
# ---------------------------------------------------------------------------

class LogSink:
    def __init__(self, logs_dir: Path, dry_run: bool):
        ensure_dir(logs_dir)
        self.logs_dir = logs_dir
        self.dry_run = dry_run
        kind = "dryrun" if dry_run else "run"
        self.path = logs_dir / f"NexusCore_export_{kind}_{now_stamp()}.txt"
        self._lines: List[str] = []

    def write(self, line: str):
        self._lines.append(line)

    def write_step(self, rel: Path, cum_mb: float):
        self.write(f"+ {str(rel)} -> {cum_mb:.2f} MB")

    def write_header(self, header: str):
        self.write(header)

    def write_summary_block(self, manifest_dir: Optional[Path], zip_path: Optional[Path],
                            total_est_mb: float, cnt: int):
        self.write("\n--- Export Summary ---")
        if self.dry_run:
            self.write(f"👁‍🗨 ドライラン完了 (推定 {total_est_mb:.2f} MB / {cnt} 件)")
        else:
            self.write(f"✅ エクスポート完了 ({total_est_mb:.2f} MB)")
        if manifest_dir:
            self.write(f"  - Manifest: {manifest_dir}")
        if zip_path:
            self.write(f"  - ZIP:      {zip_path}")
        self.write(f"  - Log:      {self.path}")
        self.write("--------------------")

    def write_heavy_topN(self, heavy_list: List[Tuple[float, Path]], n: int = 20):
        if not heavy_list:
            return
        self.write("\n[HEAVY TOPN] サイズの大きいファイル上位（概算MB）")
        for i, (mb, p) in enumerate(sorted(heavy_list, key=lambda x: x[0], reverse=True)[:n], 1):
            self.write(f"{i:2d}. {mb:.2f} MB  {p}")

    def flush(self):
        with open(self.path, "w", encoding="utf-8", errors="ignore") as f:
            f.write("\n".join(self._lines))


# ---------------------------------------------------------------------------
# 3) 探索・ピック
# ---------------------------------------------------------------------------

@dataclass
class FileItem:
    path: Path
    size_bytes: int
    est_zip_mb: float
    rel: Path
    priority: int = 100  # 小さいほど高優先

def scan_files(roots: List[Path],
               exclude_dirs: List[str],
               exclude_files: List[str]) -> List[Path]:
    results: List[Path] = []
    for root in roots:
        for p in root.rglob("*"):
            if p.is_dir():
                # ディレクトリグロブはファイルに対して判定するためここではスキップ
                continue
            if glob_match(p, exclude_files):
                continue
            # ディレクトリ除外判定
            rel_parts = str(p.relative_to(root)).replace("\\", "/")
            skip_dir = False
            for pat in exclude_dirs:
                if Path(rel_parts).match(pat):
                    skip_dir = True
                    break
            if skip_dir:
                continue
            results.append(p)
    return results

def build_items(cands: List[Path], roots: List[Path]) -> List[FileItem]:
    items: List[FileItem] = []
    for p in cands:
        try:
            size = p.stat().st_size
        except Exception:
            continue
        ratio = guess_ratio(p)
        est = (size * ratio) / (1024 * 1024)
        # 最も短いrelを採用
        rels = [rel_path_under(r, p) for r in roots]
        rel = min(rels, key=lambda rp: len(str(rp)))
        items.append(FileItem(path=p, size_bytes=size, est_zip_mb=est, rel=rel))
    return items

def prioritize(items: List[FileItem]) -> None:
    """
    入口→オーケストレーター→API→設定→core py→その他 の順に優先度を付ける
    """
    for it in items:
        s = str(it.rel).replace("\\", "/").lower()
        ext = ext_of(it.path)
        # 基本は py 最優先
        base = 10 if ext == ".py" else 50
        # エントリポイント
        if re.search(r"(main_|run_|wsgi|asgi).*\.py$", s):
            base = 0
        # orchestrator
        if "orchestrator.py" in s or "/core/orchestrator" in s:
            base = min(base, 1)
        # API
        if "/routes.py" in s or "/api/" in s:
            base = min(base, 2)
        # config (小)
        if ext in (".toml", ".yaml", ".yml", ".json"):
            base = min(base, 5)
        # 代表的文書
        if it.rel.name in ("README.md", "PROJECT_CHRONICLE.md", "CODE_REFERENCE_INDEX.md"):
            base = min(base, 15)
        it.priority = base

def sort_by_priority(items: List[FileItem]) -> List[FileItem]:
    return sorted(items, key=lambda x: (x.priority, x.est_zip_mb))

def trim_by_limits(items: List[FileItem],
                   target_mb: float,
                   max_files: int,
                   single_file_max_mb: float,
                   doc_max_kb: int,
                   log: Optional[LogSink] = None) -> Tuple[List[FileItem], List[Tuple[float, Path]]]:
    picked: List[FileItem] = []
    heavy: List[Tuple[float, Path]] = []
    total = 0.0

    def is_doc(it: FileItem) -> bool:
        return ext_of(it.path) in (".txt", ".md", ".html")

    # まず優先度順に積む（途中で閾値フィルタ）
    for it in items:
        if len(picked) >= max_files:
            break
        # 単一ファイル上限
        if (it.size_bytes / (1024 * 1024)) > single_file_max_mb:
            heavy.append((it.size_bytes / (1024 * 1024), it.rel))
            continue
        # 文書上限
        if is_doc(it) and (it.size_bytes / 1024) > doc_max_kb:
            heavy.append((it.size_bytes / (1024 * 1024), it.rel))
            continue
        if (total + it.est_zip_mb) > target_mb:
            # いったん heavy に積んで後段の TopN 用に回す
            heavy.append((it.size_bytes / (1024 * 1024), it.rel))
            continue
        picked.append(it)
        total += it.est_zip_mb
        if log and not log.dry_run:
            log.write_step(it.rel, total)
    return picked, heavy


# ---------------------------------------------------------------------------
# 4) マニフェスト展開 & ZIP 生成（パス長対策付き）
# ---------------------------------------------------------------------------

def copy_with_short_path(src_root: Path, src_file: Path, dst_root: Path):
    rel = rel_path_under(src_root, src_file)
    rel_short = flatten_and_shorten(rel)
    dst_path = dst_root / rel_short
    ensure_dir(dst_path.parent)
    # Windows 長パスサポート
    sp = to_win_long(src_file)
    dp = to_win_long(dst_path)
    shutil.copy2(sp, dp)

def write_readme(manifest_dir: Path, profile_name: str, target_mb: float, picked: List[FileItem]):
    readme = manifest_dir / "README.md"
    lines = [
        f"# NexusCore Manifest Pack ({profile_name})",
        "",
        f"- Target ZIP Size: {target_mb} MB",
        f"- Files: {len(picked)}",
        "",
        "## Notes",
        "- This pack prioritizes `.py` files for model understanding.",
        "- Large documents and binary artifacts are intentionally excluded.",
        "",
        "## Entrypoints / Orchestrator / API examples",
    ]
    for it in picked[:30]:
        s = str(it.rel).replace("\\", "/")
        if re.search(r"(main_|run_|wsgi|asgi).*\.py$", s) or \
           ("orchestrator.py" in s) or \
           ("/routes.py" in s) or ("/api/" in s):
            lines.append(f"- {s}")
    readme.write_text("\n".join(lines), encoding="utf-8", errors="ignore")

def build_zip(zip_path: Path, manifest_dir: Path):
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for p in manifest_dir.rglob("*"):
            if p.is_dir():
                continue
            arc = p.relative_to(manifest_dir)
            zf.write(p, arcname=str(arc))


# ---------------------------------------------------------------------------
# 5) エクスポート本体
# ---------------------------------------------------------------------------

def export_main(roots: List[Path],
                profile_name: str,
                target_mb_cli: Optional[float],
                emit_zip: bool,
                emit_folder: bool,
                dry_run: bool,
                exports_dir: Path,
                logs_dir: Path,
                max_files: int):

    profile = SIZE_PROFILES.get(profile_name)
    if not profile:
        raise SystemExit(f"Unknown profile: {profile_name}")

    # プロファイルと target_mb の整合
    if profile_name != "custom" and target_mb_cli is not None:
        # プリセット選択時の Custom サイズは無視（UI違和感の是正）
        target_mb = profile["target_mb"]
        custom_note = f"[WARN] profile={profile_name} 選択のため --target-mb={target_mb_cli} は無視します。"
    else:
        target_mb = target_mb_cli if profile_name == "custom" else profile["target_mb"]
        custom_note = None

    all_py_first = profile.get("all_py_first", True)
    doc_max_kb = profile.get("doc_max_kb", DOC_MAX_KB)
    single_file_max_mb = profile.get("single_file_max_mb", SINGLE_FILE_MAX_MB)

    exclude_dirs = EXCLUDE_DIR_GLOBS_BASE + profile.get("exclude_dirs_more", [])
    exclude_files = EXCLUDE_FILE_GLOBS_BASE + profile.get("exclude_files_more", [])

    # ログ
    log = LogSink(logs_dir, dry_run=dry_run)
    if custom_note:
        log.write(custom_note)
    log.write(f"[INIT] profile={profile_name}, target={target_mb} MB, max_files={max_files}, all_py_first={all_py_first}")
    log.write(f"[INIT] exports_dir={exports_dir}")
    log.write(f"[INIT] logs_dir={logs_dir}")

    # スキャン
    all_cands = scan_files(roots, exclude_dirs, exclude_files)

    # all-py-first: まず .py を優先的に並べる
    py = [p for p in all_cands if ext_of(p) == ".py"]
    non_py = [p for p in all_cands if ext_of(p) != ".py"]

    # 設定/軽量文書を非pyから抽出
    light_cfg_exts = (".toml", ".yaml", ".yml", ".json")
    light_docs_exts = (".txt", ".md", ".html")

    cfg_small, docs_small, rest = [], [], []
    for p in non_py:
        try:
            sz = p.stat().st_size
        except Exception:
            continue
        if ext_of(p) in light_cfg_exts and sz <= (doc_max_kb * 1024):
            cfg_small.append(p)
        elif ext_of(p) in light_docs_exts and sz <= (doc_max_kb * 1024):
            # README, CODE_REFERENCE_INDEX 等は通す
            if p.name.lower() in ("readme.md", "project_chronicle.md", "code_reference_index.md"):
                docs_small.append(p)
            else:
                docs_small.append(p)
        else:
            rest.append(p)

    order = py + cfg_small + docs_small + rest
    items = build_items(order, roots=roots)
    prioritize(items)
    items_sorted = sort_by_priority(items)

    picked, heavy = trim_by_limits(
        items_sorted,
        target_mb=target_mb,
        max_files=max_files,
        single_file_max_mb=single_file_max_mb,
        doc_max_kb=doc_max_kb,
        log=log if not dry_run else None
    )

    est_total = sum(it.est_zip_mb for it in picked)

    # 出力先
    manifest_dir = None
    zip_path = None

    if dry_run:
        log.write(f"\n👁‍🗨 ドライラン結果: 推定ZIP {est_total:.2f} MB / 追加ファイル {len(picked)} 件")
        # 重い順TopN（予算超で落ちた候補含め）
        log.write_heavy_topN(heavy, n=20)
        log.write_summary_block(None, None, est_total, len(picked))
        log.flush()
        print(f"👁‍🗨 プレビュー完了 (target={target_mb}MB)  -> {log.path}")
        return None, None, log.path

    # 実行: フォルダ展開
    stamp = now_stamp()
    if emit_folder:
        manifest_dir = Path(exports_dir) / f"NexusCore_manifest_{stamp}"
        ensure_dir(manifest_dir)
        # コピー
        for it in picked:
            # 起点 root を推定（最短のrelがとれた root を利用）
            src_root = min(roots, key=lambda r: len(str(rel_path_under(r, it.path))))
            copy_with_short_path(src_root, it.path, manifest_dir)
        write_readme(manifest_dir, profile_name, target_mb, picked)

    # 実行: ZIP
    if emit_zip:
        if manifest_dir is None:
            # ZIPだけの時でも一時ディレクトリに出す → ここでは簡便のため manifest_dir を使い回し
            manifest_dir = Path(exports_dir) / f"NexusCore_manifest_{stamp}"
            ensure_dir(manifest_dir)
            for it in picked:
                src_root = min(roots, key=lambda r: len(str(rel_path_under(r, it.path))))
                copy_with_short_path(src_root, it.path, manifest_dir)
            write_readme(manifest_dir, profile_name, target_mb, picked)
        zip_path = Path(exports_dir) / f"NexusCore_{profile_name.replace('-', '')}_{stamp}.zip"
        build_zip(zip_path, manifest_dir)

    # まとめ
    log.write_heavy_topN(heavy, n=20)
    log.write_summary_block(manifest_dir, zip_path, est_total, len(picked))
    log.flush()

    # 画面出力（既存UIの見え方に寄せる）
    print(f"✅ エクスポート完了 ({profile_name}, target={target_mb}MB)")
    if manifest_dir:
        print(f"- Manifest: {manifest_dir}")
    if zip_path:
        print(f"- ZIP:      {zip_path}")
    print(f"- Log:      {log.path}")

    return manifest_dir, zip_path, log.path


# ---------------------------------------------------------------------------
# 6) CLI
# ---------------------------------------------------------------------------

def parse_args():
    p = argparse.ArgumentParser(
        description="NexusCore Exporter (all-py-first v7.2)",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    p.add_argument("--roots", nargs="*", default=["."],
                   help="探索ルート（複数可）")
    p.add_argument("--profile", choices=list(SIZE_PROFILES.keys()), default=DEFAULT_PROFILE,
                   help="サイズ/除外ポリシープリセット")
    p.add_argument("--target-mb", type=float, default=None,
                   help="custom のときのみ有効。それ以外のprofileでは無視（警告のみ）")
    p.add_argument("--max-files", type=int, default=MAX_PICK_FILES,
                   help="最大ピック件数")
    p.add_argument("--emit-zip", action="store_true", help="ZIP を生成")
    p.add_argument("--emit-folder", action="store_true", help="フォルダ展開を生成")
    p.add_argument("--dry-run", action="store_true", help="ドライラン（出力は作らずログのみ）")
    p.add_argument("--exports-dir", default=DEFAULT_EXPORTS_DIR, help="ZIP/Manifest出力先")
    p.add_argument("--logs-dir", default=DEFAULT_LOGS_DIR, help="ログ出力先（exportsと分離）")
    return p.parse_args()


def main():
    args = parse_args()
    roots = [Path(r).resolve() for r in args.roots]
    exports_dir = Path(args.exports_dir)
    logs_dir = Path(args.logs_dir)
    ensure_dir(exports_dir)
    ensure_dir(logs_dir)

    try:
        export_main(
            roots=roots,
            profile_name=args.profile,
            target_mb_cli=args.target_mb,
            emit_zip=args.emit_zip,
            emit_folder=args.emit_folder,
            dry_run=args.dry_run,
            exports_dir=exports_dir,
            logs_dir=logs_dir,
            max_files=args.max_files
        )
    except Exception as e:
        # 例外も logs/ に落とす
        errlog = logs_dir / f"NexusCore_export_error_{now_stamp()}.txt"
        with open(errlog, "w", encoding="utf-8", errors="ignore") as f:
            f.write("❌ 例外が発生しました:\n")
            f.write(f"{repr(e)}\n\n")
            f.write("詳細:\n")
            import traceback
            traceback.print_exc(file=f)
        print(f"❌ エラー: {e}\n詳細ログ: {errlog}")
        sys.exit(1)


if __name__ == "__main__":
    main()
