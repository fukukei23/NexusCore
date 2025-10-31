# ==============================================================================
# 操作するソフト: VSCode（または任意のテキストエディタ）
# フォルダ      : tools/
# ファイル名    : context_bundle_prime.py
# バージョン    : 1.3 (2025-08-20)
#
# 変更点（重要）:
#  - exports/**, openenv/**, site-packages/** 等をデフォルト除外（自己再帰と巨大化の防止）
#  - ダイジェスト保存を「フラット保存（SHA1ファイル名）」に変更し MAX_PATH 問題を回避
#  - digests/_index.json に元パス→ハッシュ名の対応表を出力（逆引き用）
#  - すべてのファイル書込/作成で \\?\ プレフィックス対応と親ディレクトリ強制作成
#
# 目的:
#   LLM 前提の「軽量コンテキスト・バンドル」を生成（要約/依存/索引/差分/ZIP分割）
#   - repo_summary.md        : リポジトリ要約（規模、エントリ候補、注意点）
#   - tree.txt               : 除外規則反映のツリーテキスト
#   - imports_graph.json     : Python import 依存グラフ
#   - files_index.json       : 各ファイルのメタ（サイズ、行数、sha256、拡張子）
#   - top_files.md           : サイズTOP 50
#   - digests/_index.json    : ダイジェスト逆引きインデックス（元パス→ハッシュ名）
#   - digests/*.md           : 各ファイルのダイジェスト（フラット保存）
#   - diff/*                 : 旧バンドルとの差分（--prev-bundle 指定時）
#   - context_bundle_*.zip   : 一式のZIP（大きければ *.part*** に自動分割）
#
# 使い方（標準フロー）:
#   1) 初回生成:
#      python tools/context_bundle_prime.py .
#      -> exports/context_bundle_YYYYMMDD_hhmmss/ に一式、ZIPも出力
#
#   2) ChatGPTへの投入順:
#      (a) repo_summary.md
#      (b) tree.txt
#      (c) imports_graph.json
#      (d) files_index.json
#      以後、必要に応じて digests/_index.json を見て該当ダイジェスト（*.md）を追加投入。
#
#   3) 差分運用（更新時の再解析を最小化）:
#      python tools/context_bundle_prime.py . --prev-bundle exports/context_bundle_YYYYMMDD_hhmmss.zip
#      -> exports/.../diff/diff.json の added / changed を優先して再投入
#
# 任意設定（上書き可能）: tools/context_bundle_prime.config.json
#   {
#     "include_exts": [".py", ".md", ".toml", ".yaml", ".yml", ".json", ".ini", ".cfg", ".txt"],
#     "exclude_globs": ["**/.git/**", "**/exports/**", "**/.venv/**", "**/venv/**", ...],
#     "head_tail_lines": 120,
#     "zip_part_size_mb": 48,
#     "repo_name": "NexusCore"
#   }
# ==============================================================================

from __future__ import annotations

import os
import re
import ast
import json
import glob
import zipfile
import hashlib
import argparse
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple

# ---------------- Config（必要に応じて config で上書き） --------------------------
DEFAULT = {
    "include_exts": [".py", ".md", ".toml", ".yaml", ".yml", ".json", ".ini", ".cfg", ".txt"],
    "exclude_globs": [
        # 再帰取り込み・巨大化を防ぐ標準除外
        "**/.git/**", "**/exports/**",
        "**/__pycache__/**", "**/.mypy_cache/**", "**/.pytest_cache/**",
        "**/.venv/**", "**/venv/**", "**/openenv/**",
        "**/node_modules/**", "**/dist/**", "**/build/**",
        # site-packages 系（仮想環境内など）
        "**/Lib/site-packages/**", "**/lib/site-packages/**",
        # 大型・不要ファイル群
        "**/*.min.js", "**/*.min.css", "**/*.log", "**/*.zip", "**/*.7z", "**/*.tar*",
        "**/*.png", "**/*.jpg", "**/*.jpeg", "**/*.gif", "**/*.webp", "**/*.pdf"
    ],
    "follow_gitignore": True,
    "max_file_size_bytes": 2 * 1024 * 1024,  # 2MB を超える本文はダイジェスト生成をスキップ（メタのみ）
    "head_tail_lines": 120,
    "max_digest_chars": 80_000,
    "zip_part_size_mb": 48,
    "repo_name": None
}

# ---------------- Utils（長いパス & ディレクトリ作成） ---------------------------

def _win_longpath(s: str) -> str:
    if os.name == "nt" and not s.startswith("\\\\?\\") and len(s) >= 240:
        return "\\\\?\\" + s
    return s

def _ensure_parent_dir(p: Path) -> None:
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
    except Exception:
        os.makedirs(_win_longpath(str(p.parent)), exist_ok=True)

def save_text(p: Path, s: str) -> None:
    _ensure_parent_dir(p)
    with open(_win_longpath(str(p)), "w", encoding="utf-8", newline="\n", errors="replace") as f:
        f.write(s)

def save_json(p: Path, o: Any) -> None:
    _ensure_parent_dir(p)
    with open(_win_longpath(str(p)), "w", encoding="utf-8", newline="\n", errors="replace") as f:
        f.write(json.dumps(o, ensure_ascii=False, indent=2))

def human(n: int) -> str:
    u = ["B","KB","MB","GB","TB"]; i=0; x=float(n)
    while x >= 1024 and i < len(u)-1: x/=1024; i+=1
    return f"{x:.1f}{u[i]}" if i else f"{int(x)}B"

def sha256_file(p: Path) -> str:
    import hashlib
    h = hashlib.sha256()
    with open(_win_longpath(str(p)), "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()

def load_json(p: Path) -> Any:
    with open(_win_longpath(str(p)), "r", encoding="utf-8") as f:
        return json.load(f)

# ---------------- .gitignore & パターンマッチ ------------------------------------

def load_gitignore(root: Path) -> List[str]:
    gi = root / ".gitignore"
    if not gi.exists(): return []
    try:
        return [ln.strip() for ln in gi.read_text("utf-8", errors="ignore").splitlines()
                if ln.strip() and not ln.strip().startswith("#")]
    except Exception:
        return []

def match_any(rel: str, patterns: List[str]) -> bool:
    import fnmatch
    return any(fnmatch.fnmatch(rel, pat) or fnmatch.fnmatch(Path(rel).name, pat) for pat in patterns)

# ---------------- AST 抽出（.py のみ） -------------------------------------------

def ast_index(py_text: str) -> Dict[str, Any]:
    out = {"functions": [], "classes": [], "imports": []}
    try:
        tree = ast.parse(py_text)
    except Exception:
        return out
    for n in ast.walk(tree):
        if isinstance(n, ast.FunctionDef):
            out["functions"].append({"name": n.name, "lineno": n.lineno, "args": [a.arg for a in n.args.args]})
        elif isinstance(n, ast.AsyncFunctionDef):
            out["functions"].append({"name": f"async {n.name}", "lineno": n.lineno, "args": [a.arg for a in n.args.args]})
        elif isinstance(n, ast.ClassDef):
            out["classes"].append({"name": n.name, "lineno": n.lineno})
        elif isinstance(n, ast.Import):
            for a in n.names: out["imports"].append({"type":"import", "name": a.name})
        elif isinstance(n, ast.ImportFrom):
            mod = n.module or ""
            for a in n.names: out["imports"].append({"type":"from", "module": mod, "name": a.name})
    return out

def extract_docstrings(py_text: str) -> List[str]:
    try:
        tree = ast.parse(py_text)
    except Exception:
        return []
    docs = []
    md = ast.get_docstring(tree)
    if md: docs.append(md)
    for b in getattr(tree, "body", []):
        if isinstance(b, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            d = ast.get_docstring(b)
            if d: docs.append(d)
    return docs[:10]

# ---------------- 対象走査 ------------------------------------------------------

def iter_files(root: Path, cfg: Dict[str, Any]) -> List[Path]:
    ex = list(cfg["exclude_globs"])
    if cfg.get("follow_gitignore"): ex += load_gitignore(root)
    inc = set([e.lower() for e in cfg["include_exts"]])
    out: List[Path] = []
    for p in root.rglob("*"):
        if not p.is_file(): continue
        rel = p.relative_to(root).as_posix()
        if match_any(rel, ex): continue
        if inc and p.suffix.lower() not in inc: continue
        out.append(p)
    return out

# ---------------- ダイジェスト生成（フラット保存） -------------------------------

def make_digest(p: Path, root: Path, cfg: Dict[str, Any]) -> Tuple[Dict[str, Any], Optional[str]]:
    rel = p.relative_to(root).as_posix()
    b = p.read_bytes()
    sha = sha256_file(p)
    try:
        txt = b.decode("utf-8", errors="replace")
    except Exception:
        txt = None

    meta = {
        "path": rel, "sha256": sha, "size_bytes": len(b), "size_h": human(len(b)),
        "ext": p.suffix.lower(), "lines": (txt.count("\n")+1) if txt is not None else None
    }

    if txt is None or len(b) > cfg["max_file_size_bytes"]:
        return meta, None

    lines = txt.splitlines()
    n = int(cfg["head_tail_lines"])
    head = "\n".join(lines[:n])
    tail = "\n".join(lines[-n:]) if len(lines) > n else ""

    idx = ast_index(txt) if p.suffix.lower() == ".py" else {}
    docs = extract_docstrings(txt) if p.suffix.lower() == ".py" else []

    parts = [f"# File: {rel}\n- size: {meta['size_h']}  lines: {meta['lines']}  sha256: {sha}\n"]
    if idx.get("functions"):
        parts.append("## Functions\n" + "\n".join([f"- {f['name']}({', '.join(f['args'])}) @L{f['lineno']}" for f in idx["functions"][:200]]) + "\n")
    if idx.get("classes"):
        parts.append("## Classes\n" + "\n".join([f"- class {c['name']} @L{c['lineno']}" for c in idx["classes"][:200]]) + "\n")
    if docs:
        from textwrap import shorten
        parts.append("## Docstrings (truncated)\n" + "\n".join([shorten(d.replace("\n"," "), width=1000) for d in docs]) + "\n")
    parts.append("## Snippet: head\n```text\n" + head + "\n```\n")
    if tail:
        parts.append("## Snippet: tail\n```text\n" + tail + "\n```\n")

    digest = "".join(parts)
    if len(digest) > cfg["max_digest_chars"]:
        digest = digest[: cfg["max_digest_chars"]] + "\n\n<<TRUNCATED>>\n"
    return meta, digest

# ---------------- 依存グラフ（Pythonのみ） ----------------------------------------

def build_import_graph(py_files: List[Path], root: Path) -> Dict[str, Any]:
    graph: Dict[str, Any] = {"nodes": [], "edges": []}
    id_of: Dict[str, int] = {}

    def nid(name: str) -> int:
        if name not in id_of:
            id_of[name] = len(graph["nodes"])
            graph["nodes"].append({"id": id_of[name], "name": name})
        return id_of[name]

    module_to_file = {".".join(p.relative_to(root).with_suffix("").parts): p for p in py_files}

    for p in py_files:
        try:
            src = p.read_text("utf-8", errors="replace")
        except Exception:
            continue
        info = ast_index(src)
        s = nid(p.relative_to(root).as_posix())
        for imp in info.get("imports", []):
            tgt_mod = imp["name"] if imp["type"]=="import" else (imp.get("module") or "")
            tgt_file = module_to_file.get(tgt_mod.split(".")[0])
            tname = tgt_file.relative_to(root).as_posix() if tgt_file else tgt_mod
            t = nid(tname)
            graph["edges"].append({"source": s, "target": t})
    return graph

# ---------------- レポジトリ要約 / ツリー ----------------------------------------

def make_repo_summary(root: Path, cfg: Dict[str, Any], metas: List[Dict[str, Any]]) -> str:
    name = cfg.get("repo_name") or root.name
    tot_size = sum(m["size_bytes"] for m in metas)
    tot_lines = sum((m.get("lines") or 0) for m in metas)
    entries = []
    for cand in ("main.py","app.py","run.py","wsgi.py"):
        for m in metas:
            if m["path"].endswith("/"+cand) or m["path"] == cand:
                entries.append(m["path"])
    md = []
    md += [f"# Repository Summary: {name}\n",
           f"- Scanned at: {datetime.now():%Y-%m-%d %H:%M:%S}\n",
           f"- Files: {len(metas)}  |  Total lines: {tot_lines:,}  |  Total size: {human(tot_size)}\n\n"]
    if entries:
        md.append("## Entry Points (candidates)\n" + "\n".join(f"- {e}" for e in entries) + "\n\n")
    md.append("## Notes\n- LLM 用の軽量バンドル。必要箇所は個別ダイジェスト/原文を段階追加してください。\n")
    return "".join(md)

def make_tree_text(root: Path, files: List[Path]) -> str:
    dirs = {}
    for f in files:
        d = f.parent
        while d != root and root in d.parents:
            dirs[d] = True
            d = d.parent
    out = [f"{root.name}/"]
    for d in sorted(dirs.keys(), key=lambda p: p.as_posix()):
        rel = d.relative_to(root).as_posix()
        out.append(rel + "/")
        for f in sorted([x for x in files if x.parent == d], key=lambda p: p.name):
            out.append("  " + f.name)
    root_files = [x for x in files if x.parent == root]
    if root_files:
        out.append("\n# root files")
        out += [x.name for x in sorted(root_files, key=lambda p: p.name)]
    return "\n".join(out)

# ---------------- 差分（旧バンドルとの比較） -------------------------------------

def load_prev_index(prev_zip: Path) -> Dict[str, str]:
    idx: Dict[str, str] = {}
    with zipfile.ZipFile(_win_longpath(str(prev_zip)), "r") as z:
        for n in z.namelist():
            if n.endswith("files_index.json"):
                data = json.loads(z.read(n).decode("utf-8"))
                for m in data:
                    idx[m["path"]] = m["sha256"]
    return idx

def diff_metas(metas: List[Dict[str, Any]], prev: Dict[str, str]) -> Dict[str, List[str]]:
    cur = {m["path"]: m["sha256"] for m in metas}
    added = sorted([p for p in cur.keys() if p not in prev])
    removed = sorted([p for p in prev.keys() if p not in cur])
    changed = sorted([p for p in cur.keys() if p in prev and cur[p] != prev[p]])
    return {"added": added, "removed": removed, "changed": changed}

# ---------------- ZIP + 分割 -----------------------------------------------------

def zip_dir(src: Path, dst_zip: Path) -> None:
    with zipfile.ZipFile(_win_longpath(str(dst_zip)), "w", compression=zipfile.ZIP_DEFLATED) as z:
        for p in src.rglob("*"):
            if p.is_file():
                z.write(p, p.relative_to(src).as_posix())

def split_file(path: Path, part_mb: int) -> List[Path]:
    parts: List[Path] = []
    size = part_mb * 1024 * 1024
    with open(_win_longpath(str(path)), "rb") as f:
        i = 1
        while True:
            chunk = f.read(size)
            if not chunk: break
            part = path.with_suffix(path.suffix + f".part{i:03d}")
            _ensure_parent_dir(part)
            with open(_win_longpath(str(part)), "wb") as o:
                o.write(chunk)
            parts.append(part); i += 1
    return parts

# ---------------- Main -----------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description="Context Bundle Prime")
    ap.add_argument("target")
    ap.add_argument("--config", default=None)
    ap.add_argument("--prev-bundle", default=None)
    args = ap.parse_args()

    root = Path(args.target).resolve()
    if not root.exists(): raise SystemExit(f"not found: {root}")

    # 設定ロード
    cfg = dict(DEFAULT)
    if args.config:
        p = Path(args.config); p = p if p.is_absolute() else (root / p)
        if p.exists(): cfg.update(load_json(p))

    # 対象ファイル列挙
    files = iter_files(root, cfg)

    # 出力ルート
    out_dir = root / "exports" / f"context_bundle_{datetime.now():%Y%m%d_%H%M%S}"
    out_dir.mkdir(parents=True, exist_ok=True)

    # メタ & ダイジェスト（フラット保存 + 逆引きインデックス）
    metas: List[Dict[str, Any]] = []
    digest_index: Dict[str, str] = {}  # original_rel_path -> sha1.md

    for f in files:
        meta, digest = make_digest(f, root, cfg)
        metas.append(meta)
        if digest:
            rel = f.relative_to(root).as_posix()
            hexname = hashlib.sha1(rel.encode("utf-8")).hexdigest() + ".md"
            dst = out_dir / "digests" / hexname
            save_text(dst, "# Original: " + rel + "\n\n" + digest)
            digest_index[rel] = hexname

    # 依存グラフ（Python）
    py_files = [root / m["path"] for m in metas if m["path"].endswith(".py")]
    graph = build_import_graph(py_files, root)
    save_json(out_dir / "imports_graph.json", graph)

    # インデックス / ツリー / サマリー / Top / ダイジェスト逆引き
    save_json(out_dir / "files_index.json", metas)
    save_text(out_dir / "tree.txt", make_tree_text(root, [root / m["path"] for m in metas]))
    save_text(out_dir / "repo_summary.md", make_repo_summary(root, cfg, metas))
    save_json(out_dir / "digests" / "_index.json", digest_index)

    top = sorted(metas, key=lambda m: m["size_bytes"], reverse=True)[:50]
    save_text(out_dir / "top_files.md",
              "# Top 50 Largest Files\n\n" + "\n".join(
                  f"- {m['path']}  ({m['size_h']}, {m.get('lines') or '?'} lines)" for m in top))

    # 差分
    if args.prev_bundle:
        prev = Path(args.prev_bundle).resolve()
        if prev.exists():
            dd = diff_metas(metas, load_prev_index(prev))
            save_json(out_dir / "diff" / "diff.json", dd)
            save_text(out_dir / "diff" / "README.md",
                      "This diff compares against previous bundle.\n"
                      f"- added: {len(dd['added'])}\n- changed: {len(dd['changed'])}\n- removed: {len(dd['removed'])}\n")

    # ZIP + 分割
    z = out_dir.with_suffix(".zip")
    zip_dir(out_dir, z)

    parts = []
    if z.stat().st_size > cfg["zip_part_size_mb"] * 1024 * 1024:
        parts = split_file(z, cfg["zip_part_size_mb"])

    print(f"[OK] Bundle dir : {out_dir}")
    print(f"[OK] Bundle zip : {z} ({human(z.stat().st_size)})")
    if parts:
        print("[OK] Split parts:")
        for p in parts:
            print(f" - {p.name} ({human(p.stat().st_size)})")

if __name__ == "__main__":
    main()
