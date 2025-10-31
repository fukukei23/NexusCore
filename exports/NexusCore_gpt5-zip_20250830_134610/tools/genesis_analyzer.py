# ==============================================================================
# フォルダ: tools/
# ファイル名: genesis_analyzer.py
# 目的: プロジェクト全容の「スナップショット」と「差分イベント」を Chronicle(JSONL) に記録
# 対応: ①差分検出(Git or ハッシュ) ②Chronicleに event_type/files_changed/folders_changed/diff_digest 追記
#       ③解析対象の設定化(includes/excludes) ④既存Chronicleとの後方互換（従来の integrated_summary も維持）
# 依存: 標準ライブラリのみ（Git差分は git CLI が存在する場合のみ利用）
# 使い方:
#   python tools/genesis_analyzer.py <PROJECT_ROOT> [--mode snapshot|diff] [--config tools/genesis_analyzer.config.json]
# 例:
#   python tools/genesis_analyzer.py . --mode snapshot
#   python tools/genesis_analyzer.py . --mode diff
# 備考:
#  - 既存の LLMRouter 等には触れず、integrated_summary は optional 生成（失敗しても続行）
#  - 既存 project_chronicle.jsonl に後方互換で追記
# ==============================================================================

from __future__ import annotations
import os
import re
import ast
import sys
import json
import time
import hashlib
import logging
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any, Optional, Iterable, Tuple, Set

# ========= ログ設定 =========
def _setup_logger(project_root: Path) -> logging.Logger:
    log_dir = project_root / ".logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "genesis_analyzer.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(), logging.FileHandler(log_file, encoding="utf-8")]
    )
    return logging.getLogger("genesis_analyzer")

# ========= 設定 =========
DEFAULT_CONFIG = {
    # 解析対象の上位ディレクトリ（相対パス）
    "includes": ["src", "tests", "app", "tools", "evaluation", "exports", "dev_tools"],
    # 除外ディレクトリ/ファイルのグロブ（先勝ち）
    "excludes": [
        ".git", ".venv", "__pycache__", "node_modules", "build", "dist",
        ".logs", ".gradio", "exports/_imports", "exported_projects", "sandbox_output",
        "deploy_output", "output", "*.zip", "*.7z", "*.log", "*.png", "*.jpg", "*.gif"
    ],
    # ファイルサイズ上限（MB）: 大型バイナリ等は無視
    "max_file_size_mb": 2,
    # 差分モード時: git CLI を使うか（なければ自動でハッシュ差分にフォールバック）
    "use_git_if_available": True,
    # Chronicle 出力先
    "chronicle_path": "project_chronicle.jsonl",
    # ステート（前回ハッシュスナップショット）保存先
    "state_path": ".nexus_state.json",
    # LLM要約（integrated_summary）を試行するか
    "try_integrated_summary": True
}

@dataclass
class AnalyzerConfig:
    includes: List[str] = field(default_factory=lambda: DEFAULT_CONFIG["includes"])
    excludes: List[str] = field(default_factory=lambda: DEFAULT_CONFIG["excludes"])
    max_file_size_mb: int = DEFAULT_CONFIG["max_file_size_mb"]
    use_git_if_available: bool = DEFAULT_CONFIG["use_git_if_available"]
    chronicle_path: str = DEFAULT_CONFIG["chronicle_path"]
    state_path: str = DEFAULT_CONFIG["state_path"]
    try_integrated_summary: bool = DEFAULT_CONFIG["try_integrated_summary"]

    @staticmethod
    def load(project_root: Path, config_path: Optional[str]) -> "AnalyzerConfig":
        cfg = dict(DEFAULT_CONFIG)
        if config_path:
            p = Path(config_path)
            if not p.is_absolute():
                p = project_root / p
            if p.is_file():
                with open(p, "r", encoding="utf-8") as f:
                    user = json.load(f)
                cfg.update(user or {})
        return AnalyzerConfig(
            includes=cfg["includes"],
            excludes=cfg["excludes"],
            max_file_size_mb=cfg["max_file_size_mb"],
            use_git_if_available=cfg["use_git_if_available"],
            chronicle_path=cfg["chronicle_path"],
            state_path=cfg["state_path"],
            try_integrated_summary=cfg["try_integrated_summary"]
        )

# ========= 共通ユーティリティ =========
def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def is_binary(path: Path) -> bool:
    # シンプル判定: 拡張子 + 部分ヘッダチェック
    BIN_EXT = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".pdf", ".onnx", ".pb", ".pbtxt", ".tar", ".gz"}
    if path.suffix.lower() in BIN_EXT:
        return True
    try:
        with open(path, "rb") as f:
            chunk = f.read(8000)
        return b"\0" in chunk
    except Exception:
        return True

def file_sha1(path: Path) -> str:
    h = hashlib.sha1()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()

def to_posix(project_root: Path, path: Path) -> str:
    return str(path.relative_to(project_root)).replace("\\", "/")

def match_excluded(rel: str, excludes: List[str]) -> bool:
    import fnmatch
    # 先勝ち: パス全体と末尾名の双方に対して照合
    name = Path(rel).name
    for pat in excludes:
        if fnmatch.fnmatch(rel, pat) or fnmatch.fnmatch(name, pat):
            return True
    return False

# ========= 対象ファイルの列挙 =========
def iter_target_files(project_root: Path, cfg: AnalyzerConfig) -> List[Path]:
    targets: List[Path] = []
    max_bytes = cfg.max_file_size_mb * 1024 * 1024
    for top in cfg.includes:
        base = (project_root / top)
        if not base.exists():
            continue
        for p in base.rglob("*"):
            if not p.is_file():
                continue
            rel = to_posix(project_root, p)
            if match_excluded(rel, cfg.excludes):
                continue
            try:
                if p.stat().st_size > max_bytes:
                    continue
            except Exception:
                continue
            if is_binary(p):
                continue
            targets.append(p)
    return targets

# ========= Git差分 or ハッシュ差分 =========
def is_git_repo(project_root: Path) -> bool:
    return (project_root / ".git").exists()

def git_changed_files(project_root: Path, since_ref: str) -> List[Tuple[str, str]]:
    """
    return: list of (status, posix_path)
      status: 'A'|'M'|'D' etc.
    """
    cmd = ["git", "-C", str(project_root), "diff", "--name-status", since_ref, "HEAD"]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        return []
    changed: List[Tuple[str, str]] = []
    for line in proc.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) >= 2:
            status = parts[0].strip()
            path = parts[1].strip().replace("\\", "/")
            changed.append((status, path))
    return changed

def load_state(project_root: Path, cfg: AnalyzerConfig) -> Dict[str, Any]:
    p = project_root / cfg.state_path
    if p.is_file():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}

def save_state(project_root: Path, cfg: AnalyzerConfig, data: Dict[str, Any]) -> None:
    (project_root / cfg.state_path).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

def hash_diff(project_root: Path, cfg: AnalyzerConfig) -> Tuple[Set[str], Set[str], Set[str]]:
    """
    return: (created, modified, deleted) in posix path strings
    """
    prev = load_state(project_root, cfg).get("file_hashes", {})
    current: Dict[str, str] = {}
    for p in iter_target_files(project_root, cfg):
        rel = to_posix(project_root, p)
        current[rel] = file_sha1(p)
    prev_keys = set(prev.keys())
    curr_keys = set(current.keys())
    created = curr_keys - prev_keys
    deleted = prev_keys - curr_keys
    modified = {k for k in (prev_keys & curr_keys) if prev[k] != current[k]}
    # 次回用保存
    save_state(project_root, cfg, {"file_hashes": current, "saved_at": utc_now_iso()})
    return created, modified, deleted

# ========= AST 概略解析（integrated_summary 用の素材） =========
def ast_outline_for_py(path: Path) -> Dict[str, Any]:
    try:
        src = path.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(src)
    except Exception as e:
        return {"file": str(path), "error": str(e)}
    classes, functions, imports = [], [], []
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            classes.append(node.name)
        elif isinstance(node, ast.FunctionDef):
            functions.append(node.name)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            try:
                imp = ast.get_source_segment(src, node) or ""
            except Exception:
                imp = ""
            imports.append(imp.strip())
    return {
        "file": str(path),
        "classes": classes[:50],
        "functions": functions[:100],
        "imports": imports[:50],
        "loc": len(src.splitlines())
    }

def build_integrated_summary(project_root: Path, cfg: AnalyzerConfig, logger: logging.Logger) -> Optional[Dict[str, Any]]:
    """
    既存との後方互換のため、integrated_summary を best effort で生成。
    LLM連携が無くても AST 概略の集計サマリーを返す。
    """
    try:
        py_files = [p for p in iter_target_files(project_root, cfg) if p.suffix == ".py"]
        outlines = [ast_outline_for_py(p) for p in py_files[:1000]]  # 安全のため上限
        total_loc = sum(o.get("loc", 0) for o in outlines if isinstance(o, dict))
        return {
            "mission_and_purpose": "NexusCoreプロジェクトのコード資産を走査し、構造と変更を記録する。",
            "architecture_and_agents": "ディレクトリ単位の構成/エージェント群は AST 概略から推測可。詳細は各モジュールのクラス/関数一覧参照。",
            "dependencies_and_stack": "imports 集計から主要依存を推測。",
            "testing_philosophy": "tests ディレクトリの存在/規模から基礎的なテスト方針を推測。",
            "ui_ux_philosophy": "app/tools 等のUI関連コード有無を俯瞰。",
            "policies_and_rules": "config/policy等の存在で運用ルールの痕跡を確認。",
            "knowledge_and_experience": "evaluation/exports など運用上の知見資産を確認可能。",
            "meta_capabilities": "差分検出・イベント記録・スナップショット可視化に対応。",
            "aggregates": {
                "files_analyzed": len(py_files),
                "total_loc_estimate": total_loc
            },
            "samples": outlines[:50]
        }
    except Exception as e:
        logger.warning(f"integrated_summary 生成に失敗: {e}")
        return None

# ========= Chronicle 追記 =========
def append_chronicle(project_root: Path, cfg: AnalyzerConfig, payload: Dict[str, Any]) -> None:
    path = project_root / cfg.chronicle_path
    line = json.dumps(payload, ensure_ascii=False)
    with open(path, "a", encoding="utf-8") as f:
        f.write(line + "\n")

# ========= 主要ロジック =========
def run_snapshot(project_root: Path, cfg: AnalyzerConfig, logger: logging.Logger) -> None:
    logger.info("Running SNAPSHOT mode")
    summary = build_integrated_summary(project_root, cfg, logger) if cfg.try_integrated_summary else None
    block = {
        "timestamp": utc_now_iso(),
        "event": "ANALYSIS_SNAPSHOT",    # 旧互換（event フィールド）
        "event_type": "snapshot",        # 新形式（可視化側が event_type を期待しても落ちない）
        "files_changed": [],             # スナップショットは差分無し
        "folders_changed": [],
        "diff_digest": {"created": 0, "modified": 0, "deleted": 0},
        "integrated_summary": summary
    }
    append_chronicle(project_root, cfg, block)
    logger.info("Snapshot appended to Chronicle")

def run_diff(project_root: Path, cfg: AnalyzerConfig, logger: logging.Logger) -> None:
    logger.info("Running DIFF mode")
    created: Set[str] = set()
    modified: Set[str] = set()
    deleted: Set[str] = set()

    used_git = False
    if cfg.use_git_if_available and is_git_repo(project_root):
        # 直近の state 保存時刻以降の変更をとる。無ければ 1つ前のコミット。
        state = load_state(project_root, cfg)
        since_ref = state.get("since_ref")
        if since_ref is None:
            # 1つ前のコミットを基準に
            proc = subprocess.run(["git", "-C", str(project_root), "rev-parse", "HEAD~1"],
                                  capture_output=True, text=True, check=False)
            if proc.returncode == 0:
                since_ref = proc.stdout.strip()
        if since_ref:
            changes = git_changed_files(project_root, since_ref)
            for st, path in changes:
                if st.upper().startswith("A"):
                    created.add(path)
                elif st.upper().startswith("M"):
                    modified.add(path)
                elif st.upper().startswith("D"):
                    deleted.add(path)
            used_git = True

        # 次回の since_ref を更新
        proc2 = subprocess.run(["git", "-C", str(project_root), "rev-parse", "HEAD"],
                               capture_output=True, text=True, check=False)
        if proc2.returncode == 0:
            new_ref = proc2.stdout.strip()
            st = load_state(project_root, cfg)
            st["since_ref"] = new_ref
            save_state(project_root, cfg, st)

    if not used_git:
        c, m, d = hash_diff(project_root, cfg)
        created |= c
        modified |= m
        deleted |= d

    # 可視化で使いやすいようフォルダ階層（最上位）を抽出
    def top_folder(posix_path: str) -> str:
        return posix_path.split("/", 1)[0] if "/" in posix_path else posix_path

    files_changed = sorted(created | modified | deleted)
    folders_changed = sorted({top_folder(p) for p in files_changed})

    # 変更イベント（created/modified/deleted）を個別行としても記録
    ts = utc_now_iso()
    if created:
        append_chronicle(project_root, cfg, {
            "timestamp": ts,
            "event": "FILE_CHANGE",      # 旧互換
            "event_type": "file_created",
            "files_changed": sorted(created),
            "folders_changed": sorted({top_folder(p) for p in created}),
            "diff_digest": {"created": len(created), "modified": 0, "deleted": 0}
        })
    if modified:
        append_chronicle(project_root, cfg, {
            "timestamp": ts,
            "event": "FILE_CHANGE",
            "event_type": "file_modified",
            "files_changed": sorted(modified),
            "folders_changed": sorted({top_folder(p) for p in modified}),
            "diff_digest": {"created": 0, "modified": len(modified), "deleted": 0}
        })
    if deleted:
        append_chronicle(project_root, cfg, {
            "timestamp": ts,
            "event": "FILE_CHANGE",
            "event_type": "file_deleted",
            "files_changed": sorted(deleted),
            "folders_changed": sorted({top_folder(p) for p in deleted}),
            "diff_digest": {"created": 0, "modified": 0, "deleted": len(deleted)}
        })

    # まとめ行（ダッシュボード用）
    summary_block = {
        "timestamp": ts,
        "event": "DIFF_SUMMARY",
        "event_type": "diff_summary",
        "files_changed": files_changed,
        "folders_changed": folders_changed,
        "diff_digest": {
            "created": len(created),
            "modified": len(modified),
            "deleted": len(deleted)
        }
    }
    append_chronicle(project_root, cfg, summary_block)
    logger.info("Diff summary appended to Chronicle")

# ========= CLI =========
def main():
    import argparse
    parser = argparse.ArgumentParser(description="Genesis Analyzer (snapshot + diff recorder)")
    parser.add_argument("project_root", help="プロジェクトルートへのパス")
    parser.add_argument("--mode", choices=["snapshot", "diff"], default="snapshot", help="実行モード")
    parser.add_argument("--config", default=None, help="設定ファイル(JSON)のパス（任意）")
    args = parser.parse_args()

    project_root = Path(args.project_root).absolute()
    if not project_root.is_dir():
        print(f"エラー: 指定パスが存在しません: {project_root}")
        sys.exit(1)

    cfg = AnalyzerConfig.load(project_root, args.config)
    logger = _setup_logger(project_root)

    logger.info(f"Project root: {project_root}")
    logger.info(f"Mode: {args.mode}")
    logger.info(f"Includes: {cfg.includes}")
    logger.info(f"Excludes: {cfg.excludes}")

    try:
        if args.mode == "snapshot":
            run_snapshot(project_root, cfg, logger)
        else:
            run_diff(project_root, cfg, logger)
        logger.info("✅ Completed")
    except Exception as e:
        logger.exception(f"❌ Failed: {e}")
        sys.exit(2)

if __name__ == "__main__":
    main()
