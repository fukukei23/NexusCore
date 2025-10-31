# =================================================================================
# File:           tools/code_export_for_ai.py
# Version:        v13.0 "Phoenix" (2025-09-01)
#
# Description:    自律型AIプロジェクトエクスポートツール - 最終安定版
#                 - [FIX] 除外ディレクトリのパターンを修正し、.venvやlogsが
#                   含まれてしまう重大なバグを修正。
#                 - [PIVOT] Perplexity APIのボット対策強化に対応するため、
#                   自動アップロード機能を、手動アップロード用のファイルを
#                   準備する`perplexity-prepare`プロファイルに変更。
#
# 操作するソフト:
#   - VSCode, PowerShell, コマンドプロンプト, または任意のターミナル
#
# 依存ライブラリのインストール (初回のみ):
#   pip install "gradio>=4.0" python-dotenv networkx requests
#
# 使用方法 (UI):
#   python tools/code_export_for_ai.py --ui
#
# 使用方法 (CLI):
#   python tools/code_export_for_ai.py --profile gemini-single-file
#   python tools/code_export_for_ai.py --profile perplexity-prepare
# =================================================================================

from __future__ import annotations

import argparse
import ast
import datetime
import fnmatch
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import traceback
import zipfile
from collections import Counter, defaultdict
from dataclasses import dataclass
from math import log2, isnan
from pathlib import Path
from threading import Event, Thread
from typing import Any, Dict, List, Optional, Set, Tuple, Iterator

# --- オプションライブラリの安全なインポート ---
try:
    import gradio as gr
except ImportError:
    gr = None
try:
    import networkx as nx
except ImportError:
    nx = None
try:
    import requests
except ImportError:
    requests = None
try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

# ============================================================================
# 1. 設定とプロファイル
# ============================================================================

DEFAULT_EXPORTS_DIR = Path("./exports").resolve()
DEFAULT_LOGS_DIR = Path("./logs").resolve()
LONG_PATH_PREFIX = "\\\\?\\"
COMPRESSION_STATS_FILE = DEFAULT_EXPORTS_DIR / "compression_stats.json"

PERPLEXITY_API_ENDPOINT = "https://api.perplexity.ai/files"
PERPLEXITY_MAX_MB = 25.0
PERPLEXITY_MAX_FILES_PER_DAY = 100

BASE_COMPRESSION_RATIOS = defaultdict(lambda: 0.5, {
    ".py": 0.30, ".md": 0.35, ".txt": 0.40, ".json": 0.25,
    ".toml": 0.35, ".yaml": 0.40, ".yml": 0.40, ".html": 0.20,
    ".css": 0.25, ".js": 0.28, ".ts": 0.28, ".sh": 0.45,
})

COMMON_EXCLUDE_FILES = [
    "*.exe", "*.dll", "*.so", "*.a", "*.lib", "*.o", "*.obj", "*.pyc", "*.pyd", "*.pdb",
    "*.png", "*.jpg", "*.jpeg", "*.gif", "*.bmp", "*.svg", "*.webp", "*.ico",
    "*.mp4", "*.mov", "*.avi", "*.mp3", "*.wav", "*.ogg", "*.flac",
    "*.pdf", "*.docx", "*.pptx", "*.xlsx", "*.epub", "*.chm",
    "*.ttf", "*.otf", "*.woff", "*.woff2", "*.eot",
    "*.zip", "*.rar", "*.7z", "*.tar", "*.gz", "*.iso", "*.dmg",
    "*.db", "*.sqlite3", "*.log", "*.jsonl", "*.DS_Store", "*.swp", "*.swo",
]
# ★★★★★ [FIX] 除外ディレクトリのパターンから末尾の/**を削除 ★★★★★
COMMON_EXCLUDE_DIRS = [
    "**/.git", "**/__pycache__", "**/node_modules",
    "**/.venv", "**/venv", "**/env", "**/openenv",
    "**/site-packages",
    "**/exports", "**/logs", "**/.mypy_cache", "**/.pytest_cache",
    "**/.idea", "**/.vscode", "**/build", "**/dist", "**/*.egg-info",
    "**/typings",
]

PROFILES: Dict[str, Dict[str, Any]] = {
    "gemini-chronicle": {
        "description": "Gemini向け。Git年代記と結合コードを含む4ファイル構成のZIP。",
        "target_mb": 9.5, "output_mode": "chronicle_zip", "max_single_mb": 4.0,
        "exclude_globs": {"dirs": COMMON_EXCLUDE_DIRS, "files": COMMON_EXCLUDE_FILES},
        "priority_files": ["**/readme.md", "**/main.py", "**/app.py", "**/orchestrator.py"],
    },
    "gemini-single-file": {
        "description": "Gemini(ZIP非対応時)向け。全情報を単一のマークダウンファイルに結合。",
        "target_mb": 9.5, "output_mode": "single_file", "max_single_mb": 4.0,
        "exclude_globs": {"dirs": COMMON_EXCLUDE_DIRS, "files": COMMON_EXCLUDE_FILES},
        "priority_files": ["**/readme.md", "**/main.py", "**/app.py", "**/orchestrator.py"],
    },
    "gpt5-zip": {
        "description": "GPT-5向け。多数のファイルをそのまま格納したZIP/フォルダ。",
        "target_mb": 48.0, "output_mode": "standard_zip", "max_single_mb": 8.0,
        "exclude_globs": {"dirs": COMMON_EXCLUDE_DIRS, "files": COMMON_EXCLUDE_FILES},
        "priority_files": [],
    },
    "perplexity-prepare": {
        "description": "Perplexity Pro(手動)向け。最適化されたチャンクファイル群を準備。",
        "target_mb": 8.0,
        "chunk_target_mb": 2.0,
        "output_mode": "perplexity_prepare", 
        "max_single_mb": 1.8,
        "selection_mode": "raw",
        "exclude_globs": {"dirs": COMMON_EXCLUDE_DIRS, "files": COMMON_EXCLUDE_FILES},
        "priority_files": ["**/readme.md", "**/main.py", "**/app.py", "**/orchestrator.py"],
    }
}

# ============================================================================
# 2. ユーティリティ & ヘルパー関数
# ============================================================================
class LogSink:
    def __init__(self, logs_dir: Path, dry_run: bool, prefix: str = "NexusCore_export"):
        logs_dir.mkdir(parents=True, exist_ok=True)
        kind = "dryrun" if dry_run else "run"
        self.path = logs_dir / f"{prefix}_{kind}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        self._lines: List[str] = []

    def write(self, line: str, to_console: bool = True):
        safe_line = re.sub(r"pplx-([a-zA-Z0-9_=\-]+)", "pplx-********************", str(line))
        if to_console: print(safe_line)
        self._lines.append(safe_line)

    def get_full_log(self) -> str:
        return "\n".join(self._lines)

    def write_header(self, text: str): self.write(f"\n--- {text} ---")
    def write_heavy_topN(self, heavy_list: List[Tuple[float, Path]], n: int = 10):
        if not heavy_list: return
        self.write_header(f"サイズ超過等により除外されたファイル (上位{n}件)")
        for mb, p in sorted(heavy_list, key=lambda x: x[0], reverse=True)[:n]: self.write(f"- {mb:.2f} MB  {p}")

    def flush(self, summary_block: str):
        self.write(summary_block)
        try:
            with self.path.open("w", encoding="utf-8", errors="replace") as f:
                f.write(self.get_full_log())
            self.write(f"✅ ログファイルが正常に保存されました: {self.path}", to_console=False)
        except IOError as e: self.write(f"❌ ログファイルの書き込みに失敗しました: {self.path}\nエラー: {e}")

def load_compression_ratios(log: LogSink) -> defaultdict:
    ratios = BASE_COMPRESSION_RATIOS.copy()
    if COMPRESSION_STATS_FILE.exists():
        try:
            stats = json.loads(COMPRESSION_STATS_FILE.read_text("utf-8"))
            log.write_header("過去の圧縮実績から学習した圧縮率を適用")
            for ext, data in stats.items():
                total_raw_bytes = data.get("total_raw_bytes", 0)
                if total_raw_bytes > 1024:
                    learned_ratio = data["total_zip_bytes"] / total_raw_bytes
                    base_ratio = BASE_COMPRESSION_RATIOS[ext]
                    weight = min(0.95, total_raw_bytes / (10 * 1024**2))
                    final_ratio = (learned_ratio * weight) + (base_ratio * (1 - weight))
                    ratios[ext] = max(0.05, min(0.95, final_ratio))
                    log.write(f"  - {ext}: {ratios[ext]:.2f} (実績: {learned_ratio:.2f}, 重み: {weight:.2f})", to_console=False)
            log.write("...学習結果の適用完了。")
        except Exception as e: log.write(f"⚠️ 圧縮統計ファイルの読み込みに失敗: {e}")
    return ratios

def update_compression_stats(picked_items: List[FileItem], actual_zip_mb: float, log: LogSink):
    stats = {}
    if COMPRESSION_STATS_FILE.exists():
        try: stats = json.loads(COMPRESSION_STATS_FILE.read_text("utf-8"))
        except Exception: pass
    by_ext = defaultdict(lambda: {"raw_bytes": 0})
    for item in picked_items: by_ext[item.path.suffix.lower()]["raw_bytes"] += item.size_bytes
    total_raw_bytes = sum(item.size_bytes for item in picked_items)
    if total_raw_bytes == 0: return
    overall_ratio = (actual_zip_mb * 1024**2) / total_raw_bytes
    log.write_header("今回の圧縮実績を統計に記録")
    for ext, data in by_ext.items():
        if ext not in stats: stats[ext] = {"total_raw_bytes": 0, "total_zip_bytes": 0}
        stats[ext]["total_raw_bytes"] += data["raw_bytes"]
        stats[ext]["total_zip_bytes"] += int(data["raw_bytes"] * overall_ratio)
        log.write(f"  - {ext}: 生データ +{data['raw_bytes']/1024:.1f} KB", to_console=False)
    try:
        COMPRESSION_STATS_FILE.write_text(json.dumps(stats, indent=2), "utf-8")
        log.write(f"  - 統計ファイルを更新しました: {COMPRESSION_STATS_FILE}")
    except IOError as e: log.write(f"⚠️ 圧縮統計ファイルの書き込みに失敗: {e}")

def to_win_long(path: Path) -> str:
    p_str = str(path.resolve())
    if os.name == "nt" and not p_str.startswith(LONG_PATH_PREFIX): return LONG_PATH_PREFIX + p_str
    return p_str
def shorten_path(rel_path: Path, max_len: int = 180) -> Path:
    path_str = str(rel_path).replace("\\", "/")
    if len(path_str) <= max_len: return rel_path
    parts = path_str.split('/'); head, tail = "/".join(parts[:2]), "/".join(parts[-2:])
    mid_hash = hashlib.sha1("/".join(parts[2:-2]).encode()).hexdigest()[:8]
    return Path(head) / f"__shortened_{mid_hash}__" / tail
def glob_match(path: Path, patterns: List[str]) -> bool:
    # パスの各部分がパターンのいずれかに一致するかどうかをチェック
    path_str = str(path)
    return any(fnmatch.fnmatch(path_str, p) or any(part in path_str for part in p.split('/')) for p in patterns)


def get_file_stats(p: Path) -> Tuple[int, float]:
    try:
        content_bytes = p.read_bytes()
        loc = len(content_bytes.decode("utf-8", errors="ignore").splitlines())
        byte_counts = Counter(content_bytes)
        total_bytes = len(content_bytes)
        entropy = 0.0
        if total_bytes > 0:
            entropy = -sum((count / total_bytes) * log2(count / total_bytes) for count in byte_counts.values())
        return loc, entropy
    except Exception: return 0, 0.0

def get_file_hash(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(8192)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()

# ============================================================================
# 3. 年代記ジェネレータ
# ============================================================================
class ChronicleGenerator:
    def __init__(self, root: Path):
        self.root = root
        self.keyword_themes = {
            "Architecture & Refactoring": ["refactor", "architect", "design", "core", "module"],
            "AI & Agents": ["agent", "llm", "model", "prompt", "ai", "orchestrator"],
            "Features & UI": ["feature", "add", "ui", "gradio", "api", "implement"],
            "Database & State": ["db", "database", "sql", "state", "manager"],
            "Testing & Quality": ["test", "fix", "bug", "ci", "quality", "robust", "error"]
        }
    def _run_git_log(self)->List[Dict[str,Any]]:
        if not (self.root / ".git").exists(): return []
        try:
            cmd=["git", "log", "--date=short", "--pretty=format:%H<DELIMITER>%ad<DELIMITER>%s", "--no-merges", "--since=1.year.ago"]
            result=subprocess.run(cmd, cwd=self.root, capture_output=True, text=True, encoding='utf-8', errors='ignore')
            if result.returncode != 0: return []
            return [{"hash": p[0], "date": p[1], "subject": p[2]} for line in result.stdout.strip().split("\n") if len(p := line.split("<DELIMITER>", 2)) == 3]
        except Exception: return []

    def _summarize_by_week(self, commits:List[Dict[str,Any]]) -> Dict[str,List[str]]:
        weekly_commits:Dict[str, List[str]] = defaultdict(list)
        for commit in commits:
            try:
                commit_date = datetime.datetime.strptime(commit["date"], "%Y-%m-%d")
                week_start = commit_date - datetime.timedelta(days=commit_date.weekday())
                weekly_commits[week_start.strftime("%Y-%m-%d")].append(commit["subject"])
            except ValueError: continue
        return weekly_commits

    def _analyze_theme(self, subjects:List[str]) -> str:
        theme_counts = Counter(theme for s in subjects for theme, kws in self.keyword_themes.items() if any(kw in s.lower() for kw in kws))
        return theme_counts.most_common(1)[0][0] if theme_counts else "General Updates"

    def generate(self) -> str:
        commits = self._run_git_log()
        if not commits: return "# 📖 プロジェクト年代記\n\nGit履歴が見つかりませんでした。\n"
        weekly_summary = self._summarize_by_week(commits)
        if not weekly_summary: return "# 📖 プロジェクト年代記\n\n分析可能なコミット履歴がありませんでした。\n"
        md = ["# 📖 プロジェクト年代記 (AI-Generated)", "\n**これは、Gitのコミット履歴を基にAIが自動生成したプロジェクトの進化の記録です。**\n"]
        for week_str in sorted(weekly_summary.keys(), reverse=True)[:12]:
            subjects = weekly_summary[week_str]
            md.append(f"---\n### EPOCH: {datetime.datetime.strptime(week_str, '%Y-%m-%d').strftime('%Y年%m月%d日')} の週")
            md.append(f"**テーマ: {self._analyze_theme(subjects)}**\n")
            for subj in subjects[:3]: md.append(f"- {subj}")
            if len(subjects) > 3: md.append(f"- ...他 {len(subjects) - 3} 件の改善")
            md.append("")
        return "\n".join(md)

# ============================================================================
# 4. ファイル収集・評価・選択
# ============================================================================
@dataclass
class FileItem:
    path: Path; root: Path; rel_path: Path; size_bytes: int; loc: int; entropy: float; score: float = 0.0

def build_import_map(root: Path, py_files: List[Path]) -> Dict[Path, Set[Path]]:
    module_map: Dict[str, Path] = {}
    for p in py_files:
        try: module_map[".".join(p.relative_to(root).with_suffix("").parts)] = p
        except ValueError: continue
    import_map: Dict[Path, Set[Path]] = defaultdict(set)
    for pf in py_files:
        try:
            tree = ast.parse(pf.read_text("utf-8", errors="ignore"), filename=str(pf))
            for node in ast.walk(tree):
                module_name = None
                if isinstance(node, ast.Import) and node.names: module_name = node.names[0].name
                elif isinstance(node, ast.ImportFrom) and node.module: module_name = node.module
                if module_name and (target_path := module_map.get(module_name.split(".")[0])): import_map[pf].add(target_path)
        except Exception: continue
    return import_map

def score_files(items: List[FileItem], log: LogSink) -> None:
    py_files = [item.path for item in items if item.path.suffix == ".py"]
    centrality_scores: Dict[Path, float] = {}
    if nx and py_files:
        log.write_header("Importグラフ解析")
        import_map = build_import_map(items[0].root, py_files); g = nx.DiGraph(import_map); centrality_scores = nx.degree_centrality(g)
        log.write(f"  - 解析完了: {len(g.nodes)}ノード, {len(g.edges)}エッジ")
    path_weights = {"src": 2, "app": 2, "nexuscore": 3, "core": 2}
    name_weights = {"orchestrator": 10, "main": 8, "run": 8, "api": 5, "routes": 5}
    ext_weights = {".py": 3, ".toml": 2, ".yaml": 2, ".md": 1, ".txt": 1}
    log.write_header("ファイルスコアリング")
    for item in items:
        score = 0; s = str(item.rel_path).lower()
        score += ext_weights.get(item.path.suffix, 0)
        score += next((w for p, w in path_weights.items() if p in s), 0)
        score += next((w for n, w in name_weights.items() if n in s), 0)
        score += centrality_scores.get(item.path, 0) * 20
        if item.loc > 0: score += min(log2(item.loc + 1), 5)
        item.score = score

def collect_and_score_files(root: Path, exclude_globs: Dict[str, List[str]], log: LogSink) -> List[FileItem]:
    log.write_header(f"ファイル収集開始: {root}")
    items: List[FileItem] = []
    
    # 正規化された除外パターンを作成
    normalized_exclude_dirs = [str(Path(p)) for p in exclude_globs["dirs"]]

    for dirpath, dirnames, filenames in os.walk(root, topdown=True):
        current_dir = Path(dirpath)
        
        # os.walkから直接渡されるdirnamesをフィルタリング
        dirnames[:] = [d for d in dirnames if not any(fnmatch.fnmatch(str(current_dir / d), pattern) for pattern in normalized_exclude_dirs)]
        
        for filename in filenames:
            path = current_dir / filename
            if glob_match(path, exclude_globs["files"]):
                continue
            try:
                if (size := path.stat().st_size) > 0:
                    loc, entropy = get_file_stats(path)
                    items.append(FileItem(path=path, root=root, rel_path=path.relative_to(root), size_bytes=size, loc=loc, entropy=entropy))
            except Exception:
                continue
    log.write(f"  - 収集完了: {len(items)} ファイル")
    score_files(items, log)
    return sorted(items, key=lambda x: x.score, reverse=True)


def select_files(items: List[FileItem], profile: Dict[str, Any], compression_ratios: defaultdict) -> Tuple[List[FileItem], List[Tuple[float, Path]]]:
    target_bytes = profile["target_mb"] * 1024 * 1024
    max_single_bytes = profile["max_single_mb"] * 1024**2
    selection_mode = profile.get("selection_mode", "compressed")
    priority_globs = profile.get("priority_files", [])

    picked, heavy = [], []
    current_size = 0.0
    
    priority_items = [item for item in items if glob_match(item.rel_path, priority_globs)]
    remaining_items = [item for item in items if not glob_match(item.rel_path, priority_globs)]
    
    sorted_items = priority_items + remaining_items
    
    picked_paths = set()

    for item in sorted_items:
        if item.path in picked_paths:
            continue
            
        if item.size_bytes > max_single_bytes:
            heavy.append((item.size_bytes / 1024**2, item.rel_path))
            continue

        size_to_add = 0.0
        if selection_mode == 'raw':
            size_to_add = item.size_bytes
        else:
            base_ratio = compression_ratios[item.path.suffix.lower()]
            entropy_factor = 1.0 - (abs(item.entropy - 4.5) / 8.0) * 0.4
            final_ratio = max(0.05, min(0.95, base_ratio * entropy_factor))
            predicted_zip_bytes = item.size_bytes * final_ratio
            if isnan(predicted_zip_bytes): predicted_zip_bytes = item.size_bytes
            size_to_add = predicted_zip_bytes
        
        if current_size + size_to_add > target_bytes:
            heavy.append((item.size_bytes / 1024**2, item.rel_path))
            continue
            
        picked.append(item)
        picked_paths.add(item.path)
        current_size += size_to_add
        
    return picked, heavy

# ============================================================================
# 5. 出力ファイル生成 & Perplexityアップロード
# ============================================================================
def create_report_md(items: List[FileItem], profile_name: str, total_predicted_zip_bytes: float, actual_zip_mb: Optional[float]) -> str:
    stats = defaultdict(lambda: {"files": 0, "lines": 0})
    for item in items:
        ext = item.path.suffix or "NoExt"; stats[ext]["files"] += 1; stats[ext]["lines"] += item.loc
    stats["total"] = {"files": len(items), "lines": sum(s["lines"] for s in stats.values())}
    stats_table = "|拡張子|ファイル数|コード行数|\n|---|---|---|\n" + "\n".join(f"|`{e}`|{d['files']:,}|{d['lines']:,}|" for e, d in sorted(stats.items(), key=lambda x: x[1]['files'], reverse=True))
    report_lines = ["\n## 4. パッケージ品質レポート (自己診断)"]
    good_exts = {".py", ".md", ".txt", ".json", ".toml", ".yaml", ".yml", ".ini", ".cfg", ".sh", ".bat"}
    good_files = sum(1 for item in items if item.path.suffix.lower() in good_exts)
    total_files = len(items) if items else 1
    purity_score = (good_files / total_files) * 100
    report_lines.append(f"### コード純度: {purity_score:.1f}%")
    if purity_score < 80: report_lines.append("- ⚠️ **警告**: 分析に不要なファイルが多数含まれています。除外ルールを見直してください。")
    else: report_lines.append("- ✅ **評価**: パッケージは高品質なソースコードとドキュメントで構成されています。")
    if actual_zip_mb is not None:
        info_density = (sum(i.size_bytes for i in items) / 1024**2) / actual_zip_mb if actual_zip_mb > 0 else 0
        report_lines.append(f"### 情報密度: {info_density:.2f} (Raw/Zip Ratio)")
        if info_density < 3.0: report_lines.append("- 🟡 **情報**: 圧縮率の低いファイルが含まれている可能性があります。")
        else: report_lines.append("- ✅ **評価**: 効率的に圧縮されており、多くの情報が含まれています。")
        pred_accuracy = (1 - abs(actual_zip_mb - total_predicted_zip_bytes / 1024**2) / (total_predicted_zip_bytes / 1024**2)) * 100 if total_predicted_zip_bytes > 0 else 100
        report_lines.append(f"### 予測精度: {pred_accuracy:.1f}%")
        if pred_accuracy < 80: report_lines.append("- 🟡 **情報**: 予測と実際のZIPサイズに乖離があります。自己学習機能により次回以降精度が向上します。")
        else: report_lines.append("- ✅ **評価**: 圧縮サイズの予測は非常に正確です。")
    bootstrap_prompt = f"""
---
## 5. 推奨ブートストラップ・プロンプト (AIへの最初の指示)
あなたはシニアソフトウェアアーキテクトです。添付されたプロジェクトパッケージを分析し、その概要を報告してください。
**分析対象パッケージの形式**: `{profile_name}`
**分析ステップ**:
1.  **歴史の理解 (`PROJECT_CHRONICLE.md`)**: プロジェクトの進化の歴史と主要な開発テーマを把握してください。
2.  **定量的データの確認 (`PROJECT_INFO.md` or `MANIFEST_REPORT.md`)**: プロジェクトの規模（ファイル数、コード行数）と品質（コード純度、情報密度など）を確認してください。
3.  **ソースコードの分析 (`COMBINED_CODE.py` or `*.zip`)**: ソースコード全体をレビューし、主要なエントリーポイント、設計思想、外部依存関係を特定してください。
4.  **総合報告**: 上記を統合し、このプロジェクトが**何をするためのもので、どのような技術的特徴を持っているか**を簡潔に要約してください。
"""
    report_title = "プロジェクト情報" if "gemini" in profile_name else "マニフェストレポート"
    return f"# 📦 {report_title}\n## 1. 概要\n- 総ファイル数: {stats['total']['files']:,}\n- 総コード行数: {stats['total']['lines']:,}\n## 2. 統計\n{stats_table}\n{''.join(report_lines)}{bootstrap_prompt}"

def create_combined_code(items: List[FileItem], log: LogSink) -> str:
    log.write_header("結合コードを生成中")
    code_lines = [f"# === COMBINED SOURCE CODE ({len(items)} files) ==="]
    for item in items:
        try:
            content = item.path.read_text("utf-8", errors="ignore")
            code_lines.extend([f"\n# {'='*20} START OF: {item.rel_path} {'='*20}", content, f"# {'='*22} END OF: {item.rel_path} {'='*22}"])
        except Exception as e: code_lines.append(f"# ERROR reading {item.rel_path}: {e}")
    log.write("  - 生成完了")
    return "\n".join(code_lines)

def create_chunked_code_files(items: List[FileItem], output_dir: Path, chunk_target_mb: float, log: LogSink) -> List[Path]:
    log.write_header("結合コードをチャンク分割中...")
    chunk_target_bytes = chunk_target_mb * 1024 * 1024
    chunk_num = 1
    current_chunk_content = []
    current_chunk_bytes = 0
    chunk_paths = []

    header = f"# === COMBINED SOURCE CODE ({len(items)} files) - PART {chunk_num} ===\n"
    current_chunk_content.append(header)
    current_chunk_bytes += len(header.encode('utf-8'))

    for item in items:
        try:
            content = item.path.read_text("utf-8", errors="ignore")
            file_header = f"\n# {'='*20} START OF: {item.rel_path} {'='*20}\n"
            file_footer = f"\n# {'='*22} END OF: {item.rel_path} {'='*22}\n"
            
            content_bytes = (file_header + content + file_footer).encode('utf-8')
            
            if current_chunk_bytes + len(content_bytes) > chunk_target_bytes and current_chunk_bytes > len(header.encode('utf-8')):
                chunk_path = output_dir / f"COMBINED_CODE_{chunk_num}.txt"
                chunk_path.write_text("".join(current_chunk_content), encoding="utf-8")
                log.write(f"  - チャンク {chunk_num} を保存しました: {chunk_path.name} ({current_chunk_bytes / 1024**2:.2f} MB)")
                chunk_paths.append(chunk_path)
                
                chunk_num += 1
                header = f"# === COMBINED SOURCE CODE ({len(items)} files) - PART {chunk_num} ===\n"
                current_chunk_content = [header]
                current_chunk_bytes = len(header.encode('utf-8'))

            current_chunk_content.append(file_header + content + file_footer)
            current_chunk_bytes += len(content_bytes)
        
        except Exception as e:
            error_line = f"# ERROR reading {item.rel_path}: {e}"
            current_chunk_content.append(error_line)
            current_chunk_bytes += len(error_line.encode('utf-8'))

    if current_chunk_bytes > len(header.encode('utf-8')):
        chunk_path = output_dir / f"COMBINED_CODE_{chunk_num}.txt"
        chunk_path.write_text("".join(current_chunk_content), encoding="utf-8")
        log.write(f"  - チャンク {chunk_num} を保存しました: {chunk_path.name} ({current_chunk_bytes / 1024**2:.2f} MB)")
        chunk_paths.append(chunk_path)

    log.write("  - チャンク分割完了。")
    return chunk_paths

# ============================================================================
# 6. ガーディアンモード & メインロジック
# ============================================================================
class GuardianWatcher(Thread):
    def __init__(self, root: str, watch_interval: int, commit_trigger: int, stop_event: Event):
        super().__init__(daemon=True); self.root = Path(root); self.watch_interval = watch_interval; self.commit_trigger = commit_trigger; self.stop_event = stop_event; self.log = LogSink(DEFAULT_LOGS_DIR, dry_run=False, prefix="Guardian_run")
    def _get_last_commit(self) -> Optional[str]:
        if not (self.root / ".git").exists(): return None
        try:
            cmd = ["git", "rev-parse", "HEAD"]; result = subprocess.run(cmd, cwd=self.root, capture_output=True, text=True, check=True); return result.stdout.strip()
        except Exception: return None
    def run(self):
        self.log.write(f"🛡️ プロジェクト・ガーディアンモード起動 (監視間隔: {self.watch_interval}秒)")
        last_known_commit = self._get_last_commit(); commit_count_since_last_run = 0
        while not self.stop_event.is_set():
            time.sleep(self.watch_interval)
            current_commit = self._get_last_commit()
            if not current_commit: self.log.write("...Gitリポジトリが見つかりません。監視を一時停止します。", to_console=False); continue
            if current_commit != last_known_commit:
                self.log.write(f"新しいコミットを検知: {current_commit[:7]}"); last_known_commit = current_commit; commit_count_since_last_run += 1
                if commit_count_since_last_run >= self.commit_trigger:
                    self.log.write_header(f"{self.commit_trigger}回のコミットを検知。自動エクスポートを開始します...")
                    try:
                        for _ in export_main_generator(str(self.root), "gemini-chronicle", False, False, False, DEFAULT_EXPORTS_DIR, DEFAULT_LOGS_DIR, self.stop_event):
                            pass
                        self.log.write_header("自動エクスポート完了"); commit_count_since_last_run = 0
                    except Exception as e: self.log.write(f"❌ 自動エクスポート中にエラーが発生: {e}")
                else: self.log.write(f"...次の自動実行まであと {self.commit_trigger - commit_count_since_last_run} コミット")
        self.log.write("🛡️ ガーディアンモードが停止しました。")

def export_main_generator(
    root_str: str, profile_name: str, emit_zip: bool, emit_folder: bool, dry_run: bool,
    exports_dir: Path, logs_dir: Path, stop_event: Event,
    api_token: Optional[str] = None,
    progress: Optional[gr.Progress] = None
) -> Iterator[str]:
    log = LogSink(logs_dir, dry_run)
    try:
        if not (root := Path(root_str)).is_dir():
            log.write(f"❌ エラー: ルートはディレクトリではありません: {root_str}")
            yield log.get_full_log(); return
        
        if progress: progress(0, desc="設定読み込み...")
        profile = PROFILES[profile_name]
        
        compression_ratios = load_compression_ratios(log); yield log.get_full_log()
        
        if progress: progress(0.1, desc="ファイル収集とスコアリング...")
        items = collect_and_score_files(root, profile["exclude_globs"], log); yield log.get_full_log()
        
        if stop_event.is_set(): log.write("⏹️ キャンセルされました"); yield log.get_full_log(); return
        
        if progress: progress(0.3, desc="ファイル選択...")
        picked_items, heavy = select_files(items, profile, compression_ratios)
        
        total_raw_bytes = sum(item.size_bytes for item in picked_items)
        
        log.write_header(f"ファイル選択結果: {len(picked_items)}件 / 生データ合計 {total_raw_bytes/1024**2:.2f} MB")
        for item in picked_items[:10]: log.write(f"  - (Top) {item.rel_path} (score: {item.score:.2f})")
        if len(picked_items) > 10: log.write(f"  - ...他 {len(picked_items) - 10}件")
        log.write_heavy_topN(heavy)
        yield log.get_full_log()

        if stop_event.is_set(): log.write("⏹️ キャンセルされました"); yield log.get_full_log(); return
        
        if dry_run:
            log.flush(f"👁‍🗨 ドライラン完了。{len(picked_items)}個のファイルが選択されました。")
            if progress: progress(1.0, desc="完了！")
            yield log.get_full_log(); return

        ts = datetime.datetime.now().strftime('%Y%m%d_%H%M%S'); output_prefix = f"{root.name}_{profile_name.replace(' ', '-')}_{ts}"; summary = ""; zip_path = None
        
        if profile["output_mode"] == "perplexity_prepare":
            output_dir = exports_dir / output_prefix
            output_dir.mkdir(parents=True, exist_ok=True)
            log.write(f"ローカル保存先: {output_dir}")

            if progress: progress(0.5, desc="コンテンツ生成...")
            log.write_header("Perplexity用コンテンツを生成・保存中..."); yield log.get_full_log()
            
            chronicle_content = ChronicleGenerator(root).generate()
            chronicle_path = output_dir / "PROJECT_CHRONICLE.txt"
            chronicle_path.write_text(chronicle_content, encoding="utf-8")
            
            chunk_target_mb = profile.get("chunk_target_mb")
            if chunk_target_mb:
                code_files_to_upload = create_chunked_code_files(picked_items, output_dir, chunk_target_mb, log)
            else:
                combined_code_content = create_combined_code(picked_items, log)
                code_path = output_dir / "COMBINED_CODE.txt"
                code_path.write_text(combined_code_content, encoding="utf-8")
                code_files_to_upload = [code_path]
            
            yield log.get_full_log()
            
            files_to_upload = [chronicle_path] + code_files_to_upload
            
            summary = (
                f"✅ Perplexity用ファイルの準備が完了しました。\n"
                f"  以下のファイルをPerplexityのWebサイトから手動でアップロードしてください:\n"
                f"  フォルダ: {output_dir}\n"
                f"  ファイル: {[p.name for p in files_to_upload]}"
            )

        elif profile["output_mode"] == "single_file":
            if progress: progress(0.6, desc="コンポーネント生成...")
            chronicle_md = ChronicleGenerator(root).generate()
            combined_code_py = create_combined_code(picked_items, log); yield log.get_full_log()
            report_md = create_report_md(picked_items, profile_name, 0, None) 
            
            if progress: progress(0.8, desc="単一ファイルに結合中...")
            final_md_content = "\n\n---\n\n".join([
                f"# プロジェクト分析レポート: {root.name}",
                "## 1. プロジェクト年代記",
                chronicle_md.replace("# 📖 プロジェクト年代記 (AI-Generated)", ""),
                "## 2. プロジェクト情報",
                report_md.replace(f"# 📦 プロジェクト情報", ""),
                "## 3. 結合ソースコード",
                f"```python\n{combined_code_py}\n```"
            ])
            
            output_path = exports_dir / f"{output_prefix}.md"
            output_path.write_text(final_md_content, encoding="utf-8")
            summary = f"✅ シングルファイルレポートのエクスポート完了: {output_path}"
        
        elif profile["output_mode"] == "chronicle_zip":
            if progress: progress(0.6, desc="年代記・結合コード生成...")
            chronicle_md = ChronicleGenerator(root).generate()
            combined_code_py = create_combined_code(picked_items, log); yield log.get_full_log()
            readme_md = f"# {root.name} - AI Analysis Package"
            zip_path = exports_dir / f"{output_prefix}.zip"
            
            if progress: progress(0.8, desc="ZIPアーカイブ作成...")
            log.write_header(f"ZIPアーカイブ作成: {zip_path}"); yield log.get_full_log()
            with zipfile.ZipFile(to_win_long(zip_path), "w", zipfile.ZIP_DEFLATED) as zf:
                zf.writestr("PROJECT_CHRONICLE.md", chronicle_md)
                zf.writestr("COMBINED_CODE.py", combined_code_py)
                zf.writestr("README.md", readme_md)
                zf.writestr("PROJECT_INFO.md", "dummy content")
            actual_zip_mb_pre = zip_path.stat().st_size / 1024**2
            report_md = create_report_md(picked_items, profile_name, total_raw_bytes, actual_zip_mb_pre)
            with zipfile.ZipFile(to_win_long(zip_path), "a", zipfile.ZIP_DEFLATED) as zf:
                zf.writestr("PROJECT_INFO.md", report_md)
            summary = f"✅ 年代記パッケージのエクスポート完了: {zip_path}"
        elif profile["output_mode"] == "standard_zip":
            manifest_dir = exports_dir / output_prefix
            if emit_folder:
                if progress: progress(0.5, desc="マニフェストフォルダにコピー中...")
                manifest_dir.mkdir(parents=True, exist_ok=True)
                log.write_header("マニフェストフォルダにコピー中..."); yield log.get_full_log()
                for i, item in enumerate(picked_items):
                    dest = manifest_dir / shorten_path(item.rel_path); dest.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(to_win_long(item.path), to_win_long(dest))
                    if progress and i % 50 == 0: progress(0.5 + 0.3 * (i / len(picked_items)))

            if emit_zip:
                if progress: progress(0.8, desc="ZIPアーカイブ準備...")
                zip_path = exports_dir / f"{output_prefix}.zip"
                target_dir = manifest_dir if emit_folder else exports_dir / f"_temp_{output_prefix}"
                if not emit_folder:
                    target_dir.mkdir(parents=True, exist_ok=True)
                    for item in picked_items:
                        dest = target_dir / shorten_path(item.rel_path); dest.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(to_win_long(item.path), to_win_long(dest))
                report_md = create_report_md(picked_items, profile_name, 0, None)
                (target_dir / "MANIFEST_REPORT.md").write_text(report_md, encoding="utf-8")
                
                if progress: progress(0.9, desc="ZIPアーカイブ作成中...")
                log.write_header("ZIPアーカイブ作成中..."); yield log.get_full_log()
                shutil.make_archive(str(zip_path.with_suffix('')), 'zip', str(target_dir))
                if not emit_folder: shutil.rmtree(target_dir)
            summary = "✅ 標準ZIPパッケージのエクスポート完了。"

        if zip_path and zip_path.exists():
            actual_zip_mb = zip_path.stat().st_size / 1024**2
            total_predicted_zip_bytes_final = 0
            for item in picked_items:
                base_ratio = compression_ratios[item.path.suffix.lower()]
                entropy_factor = 1.0 - (abs(item.entropy - 4.5) / 8.0) * 0.4
                final_ratio = max(0.05, min(0.95, base_ratio * entropy_factor))
                predicted_zip_bytes = item.size_bytes * final_ratio
                if isnan(predicted_zip_bytes): predicted_zip_bytes = item.size_bytes
                total_predicted_zip_bytes_final += predicted_zip_bytes
            pred_acc = (1 - abs(actual_zip_mb - total_predicted_zip_bytes_final / 1024**2) / (total_predicted_zip_bytes_final / 1024**2)) * 100 if total_predicted_zip_bytes_final > 0 else 100
            summary += f"\n  - 予測ZIP: {total_predicted_zip_bytes_final/1024**2:.2f} MB / 実際ZIP: {actual_zip_mb:.2f} MB (予測精度: {pred_acc:.1f}%)"
            update_compression_stats(picked_items, actual_zip_mb, log)
        
        if progress: progress(1.0, desc="完了！")
        log.flush(summary)
        yield log.get_full_log()
    except Exception:
        tb_str = traceback.format_exc()
        log.write(f"❌ 致命的なエラー:\n{tb_str}")
        log.flush("エラーにより処理が中断されました。")
        if progress: progress(1.0, desc="エラー発生")
        yield log.get_full_log()

# ============================================================================
# 7. UI & CLI
# ============================================================================
def create_gradio_interface(initial_api_token: Optional[str] = None):
    if not gr: return print("Gradio未インストール。`pip install gradio`でUIが有効になります。")
    stop_event = Event()
    with gr.Blocks(title="NexusCore AI Exporter", theme=gr.themes.Soft()) as demo:
        gr.Markdown("# 自律型AIプロジェクトエクスポートツール v13.0")
        with gr.Row():
            root_tb = gr.Textbox(label="📁 プロジェクトルート", value=str(Path.cwd()))
            profile_dd = gr.Dropdown(choices=[(p["description"], p_name) for p_name, p in PROFILES.items()], value="gemini-chronicle", label="📜 プロファイル")
        profile_info = gr.Markdown(value=PROFILES["gemini-chronicle"]["description"])
        with gr.Accordion("詳細設定", open=False, visible=False) as accordion:
            loaded_from_env = bool(initial_api_token)
            placeholder = "✅ .envまたは環境変数から読込済" if loaded_from_env else "pplx-..."
            api_token_tb = gr.Textbox(label="🔑 Perplexity APIトークン (任意)", type="password", placeholder=placeholder, value="", visible=False)
            emit_zip_cb = gr.Checkbox(label="ZIPも出力 (gpt5-zip選択時)", value=True, visible=False)
            emit_folder_cb = gr.Checkbox(label="フォルダも出力 (gpt5-zip選択時)", value=False, visible=False)
        with gr.Row():
            run_btn = gr.Button("▶️ 実行", variant="primary")
            dry_run_btn = gr.Button("👁️ ドライラン", variant="secondary")
            cancel_btn = gr.Button("⏹️ キャンセル")
        status_out = gr.Textbox(label="📋 ログ", lines=15, max_lines=30, interactive=False, autoscroll=True)
        
        # NOTE: perplexity-prepare does not need a confirmation modal anymore
        # as it does not perform an irreversible online action.

        def on_profile_change(profile_name: str):
            profile_data = PROFILES.get(profile_name, {})
            mode = profile_data.get("output_mode")
            is_perplexity, is_standard_zip = (mode == "perplexity_prepare"), (mode == "standard_zip")
            return {
                profile_info: gr.Markdown(visible=True, value=f"**選択中**: {profile_data.get('description', '')}"),
                accordion: gr.Accordion(visible=is_perplexity or is_standard_zip),
                api_token_tb: gr.Textbox(visible=False), # No longer need API token in UI
                emit_zip_cb: gr.Checkbox(visible=is_standard_zip),
                emit_folder_cb: gr.Checkbox(visible=is_standard_zip),
            }

        def run_handler(root, profile, api_token, emit_zip, emit_folder, dry_run=False, progress=gr.Progress(track_tqdm=True)):
            stop_event.clear()

            yield {
                run_btn: gr.update(interactive=False),
                dry_run_btn: gr.update(interactive=False),
                status_out: "エクスポート処理を開始します..."
            }
            
            final_api_token = api_token or initial_api_token
            final_log = ""
            for log_update in export_main_generator(root, profile, emit_zip, emit_folder, dry_run, DEFAULT_EXPORTS_DIR, DEFAULT_LOGS_DIR, stop_event, final_api_token, progress):
                final_log = log_update
                yield { status_out: final_log }
            
            yield {
                run_btn: gr.update(interactive=True),
                dry_run_btn: gr.update(interactive=True),
                status_out: final_log
            }

        all_inputs = [root_tb, profile_dd, api_token_tb, emit_zip_cb, emit_folder_cb]
        
        run_btn.click(
            fn=run_handler,
            inputs=all_inputs + [gr.State(False)],
            outputs=[run_btn, dry_run_btn, status_out]
        )

        dry_run_btn.click(
            fn=run_handler,
            inputs=all_inputs + [gr.State(True)],
            outputs=[run_btn, dry_run_btn, status_out]
        )

        cancel_btn.click(fn=lambda: stop_event.set())
        profile_dd.change(fn=on_profile_change, inputs=[profile_dd], outputs=[profile_info, accordion, api_token_tb, emit_zip_cb, emit_folder_cb])
        demo.load(fn=lambda: on_profile_change("gemini-chronicle"), outputs=[profile_info, accordion, api_token_tb, emit_zip_cb, emit_folder_cb])

    demo.launch(inbrowser=True, server_name="127.0.0.1", server_port=7868)

def main():
    if load_dotenv:
        if load_dotenv():
            print("INFO: .env file found and loaded.")
    else:
        print("WARNING: python-dotenv not installed. .env file will not be loaded. Run 'pip install python-dotenv'.")

    parser = argparse.ArgumentParser(description="NexusCore AI Exporter v13.0")
    parser.add_argument("root", nargs="?", default=str(Path.cwd()), help="プロジェクトルート")
    parser.add_argument("--profile", choices=list(PROFILES.keys()), default="gemini-chronicle", help="プロファイル")
    parser.add_argument("--emit-zip", action="store_true", help="[gpt5-zip] ZIP出力")
    parser.add_argument("--emit-folder", action="store_true", help="[gpt5-zip] フォルダ出力")
    parser.add_argument("--dry-run", action="store_true", help="ドライランモード")
    parser.add_argument("--ui", action="store_true", help="Gradio UIを起動")
    parser.add_argument("--watch", action="store_true", help="ガーディアンモードで起動")
    parser.add_argument("--watch-interval", type=int, default=60, help="[Watch] 監視間隔 (秒)")
    parser.add_argument("--commit-trigger", type=int, default=5, help="[Watch] 自動実行トリガーのコミット回数")
    parser.add_argument("--api-token", type=str, help="Perplexity APIトークン (現在未使用)")
    args = parser.parse_args()
    
    api_token = os.getenv("PERPLEXITY_API_TOKEN") or os.getenv("PERPLEXITY_API_KEY") or args.api_token
    
    if api_token and not args.api_token:
        print("INFO: Perplexity API token loaded from environment variable or .env file.")

    if args.ui:
        create_gradio_interface(initial_api_token=api_token)
    elif args.watch:
        stop_event = Event()
        watcher = GuardianWatcher(args.root, args.watch_interval, args.commit_trigger, stop_event)
        watcher.start()
        try:
            while watcher.is_alive(): time.sleep(1)
        except KeyboardInterrupt:
            print("\nStopping Guardian mode...")
            stop_event.set()
            watcher.join()
    else:
        for _ in export_main_generator(args.root, args.profile, args.emit_zip, args.emit_folder, args.dry_run, DEFAULT_EXPORTS_DIR, DEFAULT_LOGS_DIR, Event(), api_token):
            pass

if __name__ == "__main__":
    main()

