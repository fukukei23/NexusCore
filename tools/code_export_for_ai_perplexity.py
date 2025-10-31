# =================================================================================
# File:           tools/code_export_for_ai_perplexity.py
# Version:        v10.1 "Self-Tuning" (2025-08-30)
#
# Description:    統合版AIプロジェクトエクスポートツール - 自己学習版
#                 - v10.0の全機能を継承。
#                 - [NEW] 予測圧縮率の自己学習・最適化機能: 実行結果を記録し、
#                   次回の実行時に、より現実に即した圧縮率を自動的に使用する
#                   自己進化ロジックを追加。
#                 - [UX] UIのさらなる洗練: PerplexityのAPIトークン入力欄に
#                   説明を追加するなど、ユーザー体験を向上。
#
# 操作するソフト:
#   - VSCode, PowerShell, コマンドプロンプト, または任意のターミナル
#
# 使用方法 (CLI):
#   python tools/code_export_for_ai_perplexity.py --profile gemini-chronicle
#
# 使用方法 (UI):
#   python tools/code_export_for_ai_perplexity.py --ui
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
from math import log2
from pathlib import Path
from threading import Event
from typing import Any, Dict, List, Optional, Tuple

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
PERPLEXITY_SUPPORTED_EXTS = {".txt"}

# ★★★★★ [FIX] 自己学習機能のための動的圧縮率 ★★★★★
# これは初期値。実行後に実績値で更新される。
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
COMMON_EXCLUDE_DIRS = [
    "**/.git/**", "**/__pycache__/**", "**/node_modules/**",
    "**/.venv/**", "**/venv/**", "**/env/**", "**/openenv/**",
    "**/site-packages/**",
    "**/exports/**", "**/logs/**", "**/.mypy_cache/**", "**/.pytest_cache/**",
    "**/.idea/**", "**/.vscode/**", "**/build/**", "**/dist/**", "**/*.egg-info/**",
    "**/typings/**",
]

PROFILES: Dict[str, Dict[str, Any]] = {
    "gemini-chronicle": {
        "description": "Gemini向け。Git年代記と結合コードを含む4ファイル構成のZIP。",
        "target_mb": 9.5, "output_mode": "chronicle_zip", "max_single_mb": 4.0,
        "exclude_globs": {"dirs": COMMON_EXCLUDE_DIRS, "files": COMMON_EXCLUDE_FILES},
    },
    "gpt5-zip": {
        "description": "GPT-5向け。多数のファイルをそのまま格納したZIP/フォルダ。",
        "target_mb": 48.0, "output_mode": "standard_zip", "max_single_mb": 8.0,
        "exclude_globs": {"dirs": COMMON_EXCLUDE_DIRS, "files": COMMON_EXCLUDE_FILES},
    },
    "perplexity-upload": {
        "description": "Perplexity Proへ年代記とコードを自動テキスト化してアップロード。",
        "target_mb": PERPLEXITY_MAX_MB - 1.0, "output_mode": "perplexity_upload", "max_single_mb": PERPLEXITY_MAX_MB - 1.0,
        "exclude_globs": {"dirs": COMMON_EXCLUDE_DIRS, "files": COMMON_EXCLUDE_FILES},
    }
}

# ============================================================================
# 2. ユーティリティ & ヘルパー関数 (自己学習機能追加)
# ============================================================================
class LogSink: # ... (v10.0から変更なし)
    def __init__(self, logs_dir: Path, dry_run: bool):
        logs_dir.mkdir(parents=True, exist_ok=True)
        kind = "dryrun" if dry_run else "run"
        self.path = logs_dir / f"NexusCore_export_{kind}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        self._lines: List[str] = []
    def write(self, line: str, to_console: bool = True):
        if to_console: print(line)
        self._lines.append(line)
    def write_header(self, text: str): self.write(f"\n--- {text} ---")
    def write_heavy_topN(self, heavy_list: List[Tuple[float, Path]], n: int = 10):
        if not heavy_list: return
        self.write_header(f"サイズ超過等により除外されたファイル (上位{n}件)")
        for mb, p in sorted(heavy_list, key=lambda x: x[0], reverse=True)[:n]: self.write(f"- {mb:.2f} MB  {p}")
    def flush(self, summary_block: str):
        self.write(summary_block)
        try:
            with self.path.open("w", encoding="utf-8", errors="replace") as f: f.write("\n".join(self._lines))
            self.write(f"✅ ログファイルが正常に保存されました: {self.path}", to_console=False)
        except IOError as e: self.write(f"❌ ログファイルの書き込みに失敗しました: {self.path}\nエラー: {e}")

# ★★★★★ [NEW] 圧縮率の自己学習機能 ★★★★★
def load_compression_ratios(log: LogSink) -> defaultdict:
    ratios = BASE_COMPRESSION_RATIOS.copy()
    if COMPRESSION_STATS_FILE.exists():
        try:
            stats = json.loads(COMPRESSION_STATS_FILE.read_text("utf-8"))
            log.write_header("過去の圧縮実績から学習した圧縮率を適用")
            for ext, data in stats.items():
                if data["total_raw_bytes"] > 1024: # 統計的に意味のあるデータのみ
                    learned_ratio = data["total_zip_bytes"] / data["total_raw_bytes"]
                    # 安全のため、ベース値から極端に乖離しないように調整
                    base_ratio = BASE_COMPRESSION_RATIOS[ext]
                    ratios[ext] = max(0.05, min(0.95, (learned_ratio + base_ratio) / 2))
                    log.write(f"  - {ext}: {ratios[ext]:.2f} (実績: {learned_ratio:.2f})")
        except Exception as e:
            log.write(f"⚠️ 圧縮統計ファイルの読み込みに失敗: {e}")
    return ratios

def update_compression_stats(picked_items: List[FileItem], actual_zip_mb: float, log: LogSink):
    stats = {}
    if COMPRESSION_STATS_FILE.exists():
        try:
            stats = json.loads(COMPRESSION_STATS_FILE.read_text("utf-8"))
        except Exception:
            pass # ファイルが壊れていても無視して上書き

    # 今回の実行結果を拡張子ごとに集計
    by_ext = defaultdict(lambda: {"raw_bytes": 0})
    for item in picked_items:
        by_ext[item.path.suffix.lower()]["raw_bytes"] += item.size_bytes
    
    total_raw_bytes = sum(item.size_bytes for item in picked_items)
    if total_raw_bytes == 0: return

    # 全体の圧縮率を計算し、各拡張子に適用
    overall_ratio = (actual_zip_mb * 1024**2) / total_raw_bytes

    log.write_header("今回の圧縮実績を統計に記録")
    for ext, data in by_ext.items():
        if ext not in stats:
            stats[ext] = {"total_raw_bytes": 0, "total_zip_bytes": 0}
        
        stats[ext]["total_raw_bytes"] += data["raw_bytes"]
        # 全体の圧縮率を適用してzipサイズを按分
        stats[ext]["total_zip_bytes"] += int(data["raw_bytes"] * overall_ratio)
        log.write(f"  - {ext}: 生データ +{data['raw_bytes']/1024:.1f} KB")

    try:
        COMPRESSION_STATS_FILE.write_text(json.dumps(stats, indent=2), "utf-8")
        log.write(f"  - 統計ファイルを更新しました: {COMPRESSION_STATS_FILE}")
    except IOError as e:
        log.write(f"⚠️ 圧縮統計ファイルの書き込みに失敗: {e}")


def to_win_long(path: Path) -> str: # ... (v10.0から変更なし)
    p_str = str(path.resolve())
    if os.name == "nt" and not p_str.startswith(LONG_PATH_PREFIX): return LONG_PATH_PREFIX + p_str
    return p_str
def shorten_path(rel_path: Path, max_len: int = 180) -> Path: # ... (v10.0から変更なし)
    path_str = str(rel_path).replace("\\", "/")
    if len(path_str) <= max_len: return rel_path
    parts = path_str.split('/'); head, tail = "/".join(parts[:2]), "/".join(parts[-2:])
    mid_hash = hashlib.sha1("/".join(parts[2:-2]).encode()).hexdigest()[:8]
    return Path(head) / f"__shortened_{mid_hash}__" / tail
def glob_match(path: Path, patterns: List[str]) -> bool: # ... (v10.0から変更なし)
    return any(path.match(p) for p in patterns)
def get_loc(p: Path) -> int: # ... (v10.0から変更なし)
    try:
        with p.open("r", encoding="utf-8", errors="ignore") as f: return sum(1 for _ in f)
    except Exception: return 0

# ============================================================================
# 3. 年代記ジェネレータ (v10.0から変更なし)
# ============================================================================
class ChronicleGenerator: # ... (v10.0から変更なし)
    def __init__(self, root: Path):
        self.root = root; self.keyword_themes = {"Architecture & Refactoring":["refactor","architect","design","core","module"],"AI & Agents":["agent","llm","model","prompt","ai","orchestrator"],"Features & UI":["feature","add","ui","gradio","api","implement"],"Database & State":["db","database","sql","state","manager"],"Testing & Quality":["test","fix","bug","ci","quality","robust","error"]}
    def _run_git_log(self)->List[Dict[str,Any]]:
        if not (self.root/".git").exists():return[]
        try:
            cmd=["git","log","--date=short","--pretty=format:%H<DELIMITER>%ad<DELIMITER>%s","--no-merges","--since=1.year.ago"]; result=subprocess.run(cmd,cwd=self.root,capture_output=True,text=True,encoding='utf-8',errors='ignore')
            if result.returncode!=0:return[]
            return[{"hash":p[0],"date":p[1],"subject":p[2]}for line in result.stdout.strip().split("\n")if len(p:=line.split("<DELIMITER>",2))==3]
        except Exception:return[]
    def _summarize_by_week(self,commits:List[Dict[str,Any]])->Dict[str,List[str]]:
        weekly_commits:Dict[str,List[str]]=defaultdict(list)
        for commit in commits:
            try:
                commit_date=datetime.datetime.strptime(commit["date"],"%Y-%m-%d"); week_start=commit_date-datetime.timedelta(days=commit_date.weekday()); weekly_commits[week_start.strftime("%Y-%m-%d")].append(commit["subject"])
            except ValueError:continue
        return weekly_commits
    def _analyze_theme(self,subjects:List[str])->str:
        theme_counts=Counter(theme for s in subjects for theme,kws in self.keyword_themes.items()if any(kw in s.lower()for kw in kws))
        return theme_counts.most_common(1)[0][0]if theme_counts else"General Updates"
    def generate(self)->str:
        commits=self._run_git_log()
        if not commits:return"# 📖 プロジェクト年代記\n\nGit履歴が見つかりませんでした。\n"
        weekly_summary=self._summarize_by_week(commits)
        if not weekly_summary:return"# 📖 プロジェクト年代記\n\n分析可能なコミット履歴がありませんでした。\n"
        md=["# 📖 プロジェクト年代記 (AI-Generated)","\n**これは、Gitのコミット履歴を基にAIが自動生成したプロジェクトの進化の記録です。**\n"]
        for week_str in sorted(weekly_summary.keys(),reverse=True)[:12]:
            subjects=weekly_summary[week_str]; md.append(f"---\n### EPOCH: {datetime.datetime.strptime(week_str,'%Y-%m-%d').strftime('%Y年%m月%d日')} の週"); md.append(f"**テーマ: {self._analyze_theme(subjects)}**\n")
            for subj in subjects[:3]:md.append(f"- {subj}")
            if len(subjects)>3:md.append(f"- ...他 {len(subjects)-3} 件の改善")
            md.append("")
        return"\n".join(md)

# ============================================================================
# 4. ファイル収集・評価・選択 (select_files改修)
# ============================================================================
@dataclass
class FileItem:
    path: Path; root: Path; rel_path: Path; size_bytes: int; loc: int; score: float = 0.0

def build_import_map(root: Path, py_files: List[Path]) -> Dict[Path, Set[Path]]: # ... (v10.0から変更なし)
    module_map = {".".join(p.relative_to(root).with_suffix("").parts): p for p in py_files}
    import_map: Dict[Path, Set[Path]] = defaultdict(set)
    for pf in py_files:
        try:
            tree = ast.parse(pf.read_text("utf-8", errors="ignore"), filename=str(pf))
            for node in ast.walk(tree):
                module_name=None
                if isinstance(node,ast.Import):
                    if node.names:module_name=node.names[0].name
                elif isinstance(node,ast.ImportFrom)and node.module:module_name=node.module
                if module_name and(target_path:=module_map.get(module_name.split(".")[0])):import_map[pf].add(target_path)
        except Exception:continue
    return import_map

def score_files(items: List[FileItem], log: LogSink) -> None: # ... (v10.0から変更なし)
    py_files = [item.path for item in items if item.path.suffix == ".py"]
    centrality_scores = {}
    if nx and py_files:
        log.write_header("Importグラフ解析")
        import_map = build_import_map(items[0].root, py_files); g = nx.DiGraph(import_map); centrality_scores = nx.degree_centrality(g)
        log.write(f"  - 解析完了: {len(g.nodes)}ノード, {len(g.edges)}エッジ")
    path_weights={"src":2,"app":2,"nexuscore":3,"core":2};name_weights={"orchestrator":10,"main":8,"run":8,"api":5,"routes":5};ext_weights={".py":3,".toml":2,".yaml":2,".md":1,".txt":1}
    log.write_header("ファイルスコアリング")
    for item in items:
        score=0;s=str(item.rel_path).lower();score+=ext_weights.get(item.path.suffix,0);score+=next((w for p,w in path_weights.items()if p in s),0);score+=next((w for n,w in name_weights.items()if n in s),0);score+=centrality_scores.get(item.path,0)*20
        if item.loc>0:score+=min(log2(item.loc+1),5)
        item.score=score

def collect_and_score_files(root: Path, exclude_globs: Dict[str, List[str]], log: LogSink) -> List[FileItem]: # ... (v10.0から変更なし)
    log.write_header(f"ファイル収集開始: {root}")
    items: List[FileItem] = []
    for dirpath, dirnames, filenames in os.walk(root):
        current_dir = Path(dirpath)
        dirnames[:] = [d for d in dirnames if not glob_match(current_dir / d, exclude_globs["dirs"])]
        for filename in filenames:
            path = current_dir / filename
            if glob_match(path, exclude_globs["files"]): continue
            try:
                if (size := path.stat().st_size) > 0:
                    items.append(FileItem(path=path, root=root, rel_path=path.relative_to(root), size_bytes=size, loc=get_loc(path)))
            except Exception: continue
    log.write(f"  - 収集完了: {len(items)} ファイル")
    score_files(items, log)
    return sorted(items, key=lambda x: x.score, reverse=True)

# ★★★★★ [FIX] 予測圧縮サイズベースの選択ロジック (学習機能対応) ★★★★★
def select_files(items: List[FileItem], target_mb: float, max_single_mb: float, compression_ratios: defaultdict) -> Tuple[List[FileItem], List[Tuple[float, Path]]]:
    picked, heavy = [], []
    total_predicted_zip_size = 0.0
    target_bytes = target_mb * 1024 * 1024

    for item in items:
        if (item.size_bytes / 1024**2) > max_single_mb:
            heavy.append((item.size_bytes / 1024**2, item.rel_path))
            continue
        ratio = compression_ratios[item.path.suffix.lower()]
        predicted_zip_bytes = item.size_bytes * ratio
        if total_predicted_zip_size + predicted_zip_bytes > target_bytes:
            heavy.append((item.size_bytes / 1024**2, item.rel_path))
            continue
        picked.append(item)
        total_predicted_zip_size += predicted_zip_bytes
    return picked, heavy

# ============================================================================
# 5. 出力ファイル生成 & Perplexityアップロード (v10.0から変更なし)
# ============================================================================
def create_combined_code_and_info(items: List[FileItem], log: LogSink, profile_name: str) -> Tuple[str, str]: # ... (v10.0から変更なし)
    log.write_header("結合コードと情報ファイルを生成中")
    code_lines=[f"# === COMBINED SOURCE CODE ({len(items)} files) ==="]
    for item in items:
        try:
            content=item.path.read_text("utf-8",errors="ignore")
            code_lines.extend([f"\n# {'='*20} START OF: {item.rel_path} {'='*20}",content,f"# {'='*22} END OF: {item.rel_path} {'='*22}"])
        except Exception as e:code_lines.append(f"# ERROR reading {item.rel_path}: {e}")
    stats=defaultdict(lambda:{"files":0,"lines":0})
    for item in items:
        ext=item.path.suffix or"NoExt";stats[ext]["files"]+=1;stats[ext]["lines"]+=item.loc
    stats["total"]={"files":len(items),"lines":sum(s["lines"]for s in stats.values())}
    stats_table="|拡張子|ファイル数|コード行数|\n|---|---|---|\n"+"\n".join(f"|`{e}`|{d['files']:,}|{d['lines']:,}|"for e,d in sorted(stats.items(),key=lambda x:x[1]['files'],reverse=True))
    report_lines=["\n## 4. パッケージ品質レポート (自己診断)"]
    good_exts = {".py", ".md", ".txt", ".json", ".toml", ".yaml", ".yml", ".ini", ".cfg", ".sh", ".bat"}
    good_files = sum(1 for item in items if item.path.suffix.lower() in good_exts)
    total_files = len(items)
    purity_score = (good_files / total_files * 100) if total_files > 0 else 0
    report_lines.append(f"### コード純度スコア: {purity_score:.1f}%")
    if purity_score >= 95: report_lines.append("- ✅ **評価**: パッケージは高品質なソースコードとドキュメントで構成されており、AI分析に非常に適しています。")
    else: report_lines.append("- ⚠️ **警告**: パッケージに分析に不要なファイルが多数含まれています。除外ルールの見直しを強く推奨します。")
    bootstrap_prompt = f"""
---
## 5. 推奨ブートストラップ・プロンプト (AIへの最初の指示)
あなたはシニアソフトウェアアーキテクトです。添付されたプロジェクトパッケージを分析し、その概要を報告してください。
**分析対象パッケージの形式**: `{profile_name}`
**分析ステップ**:
1.  **パッケージ構成の確認**: まず、このパッケージに含まれる主要なファイル (`PROJECT_CHRONICLE.md`, `PROJECT_INFO.md`, `COMBINED_CODE.py`) を認識してください。
2.  **歴史の理解 (`PROJECT_CHRONICLE.md`)**: プロジェクトの進化の歴史と主要な開発テーマを把握してください。
3.  **定量的データの確認 (`PROJECT_INFO.md`)**: プロジェクトの規模（ファイル数、コード行数）と品質（コード純度スコア）を確認してください。
4.  **ソースコードの分析 (`COMBINED_CODE.py`)**: 結合されたソースコード全体をレビューし、以下の点を特定してください。
    - 主要なエントリーポイント（例: `main.py`, `orchestrator.py`）。
    - プロジェクトの中核となる設計思想やアーキテクチャパターン。
    - 主要な外部ライブラリへの依存関係。
5.  **総合報告**: 上記の分析結果を統合し、このプロジェクトが**何をするためのもので、どのような技術的特徴を持っているか**を簡潔に要約してください。
"""
    info_md=f"# 📦 プロジェクト情報\n## 1. 概要\n- 総ファイル数: {stats['total']['files']:,}\n- 総コード行数: {stats['total']['lines']:,}\n## 2. 統計\n{stats_table}\n{''.join(report_lines)}{bootstrap_prompt}"
    log.write("  - 生成完了")
    return"\n".join(code_lines),info_md

def perplexity_upload(items_to_upload: List[Path], api_token: str, log: LogSink): # ... (v10.0から変更なし)
    if not requests: return log.write("❌ `requests`ライブラリが必要です。`pip install requests`を実行してください。")
    log.write_header(f"Perplexity Proファイルアップロード開始 ({len(items_to_upload)}件)")
    headers={"Authorization":f"Bearer {api_token}"}
    uploaded_count=0
    for item_path in items_to_upload[:PERPLEXITY_MAX_FILES_PER_DAY]:
        try:
            with item_path.open("rb")as f:
                files_payload={"file":(item_path.name,f,"application/octet-stream")}
                response=requests.post(PERPLEXITY_API_ENDPOINT,headers=headers,files=files_payload,timeout=60)
                response.raise_for_status()
                log.write(f"  - ✅ 成功: {item_path.name}")
                uploaded_count+=1
        except requests.exceptions.RequestException as e:log.write(f"  - ❌ ネットワークエラー: {item_path.name} - {e}")
        except Exception as e:log.write(f"  - ❌ 例外: {item_path.name} - {e}")
    summary=f"Perplexity Proへのアップロード処理完了。{uploaded_count}個のファイルがアップロードされました。"
    log.flush(summary)

# ============================================================================
# 6. メイン実行ロジック & UI
# ============================================================================
def export_main(
    root_str: str, profile_name: str, emit_zip: bool, emit_folder: bool, dry_run: bool,
    exports_dir: Path, logs_dir: Path, stop_event: Event,
    api_token: Optional[str] = None, progress: Any = None
):
    log=LogSink(logs_dir,dry_run)
    if not(root:=Path(root_str)).is_dir():return log.write(f"❌ エラー: ルートはディレクトリではありません: {root_str}")
    profile=PROFILES[profile_name]
    
    # ★★★★★ [NEW] 自己学習機能 ★★★★★
    compression_ratios = load_compression_ratios(log)

    if progress:progress(0.05,desc="ファイル収集とスコアリング...")
    items=collect_and_score_files(root,profile["exclude_globs"],log)
    if stop_event.is_set():return log.write("⏹️ キャンセルされました")
    
    if profile["output_mode"]=="perplexity_upload":
        if not api_token:return log.flush("❌ Perplexity APIトークンが指定されていません。")
        if dry_run:
            log.write_header("Perplexityアップロード ドライラン")
            log.flush("  - Chronicle.txtとCombined_Code.txtが生成されアップロードされます。")
            return
        with tempfile.TemporaryDirectory()as temp_dir:
            temp_path=Path(temp_dir)
            log.write_header("Perplexity用コンテンツを一時生成中...")
            picked,_=select_files(items,profile["target_mb"],profile["max_single_mb"],compression_ratios)
            chronicle_content=ChronicleGenerator(root).generate()
            code_content,_=create_combined_code_and_info(picked,log,profile_name)
            (temp_path/"PROJECT_CHRONICLE.txt").write_text(chronicle_content,encoding="utf-8")
            (temp_path/"COMBINED_CODE.txt").write_text(code_content,encoding="utf-8")
            log.write("  - 一時ファイル生成完了")
            perplexity_upload([temp_path/"PROJECT_CHRONICLE.txt",temp_path/"COMBINED_CODE.txt"],api_token,log)
        return
        
    if progress:progress(0.3,desc="ファイル選択...")
    picked_items,heavy=select_files(items,profile["target_mb"],profile["max_single_mb"],compression_ratios)
    
    total_raw_bytes = sum(item.size_bytes for item in picked_items)
    total_predicted_zip_bytes = sum(item.size_bytes * compression_ratios[item.path.suffix.lower()] for item in picked_items)
    log.write_header(f"ファイル選択結果: {len(picked_items)}件 / 生データ合計 {total_raw_bytes/1024**2:.2f} MB / 予測ZIPサイズ {total_predicted_zip_bytes/1024**2:.2f} MB")
    
    for item in picked_items[:10]:log.write(f"  - (Top) {item.rel_path} (score: {item.score:.2f})")
    if len(picked_items)>10:log.write(f"  - ...他 {len(picked_items)-10}件")
    log.write_heavy_topN(heavy)
    if stop_event.is_set():return log.write("⏹️ キャンセルされました")
    if dry_run:return log.flush(f"👁‍🗨 ドライラン完了。{len(picked_items)}個のファイルが選択されました。")
    
    ts=datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    output_prefix=f"{root.name}_{profile_name.replace(' ','-')}_{ts}"
    summary=""; zip_path = None

    if profile["output_mode"]=="chronicle_zip":
        if progress:progress(0.6,desc="年代記・情報・結合コードを生成中...")
        chronicle_md=ChronicleGenerator(root).generate()
        combined_code_py,project_info_md=create_combined_code_and_info(picked_items,log,profile_name)
        readme_md=f"# {root.name} - AI Analysis Package"
        zip_path=exports_dir/f"{output_prefix}.zip"
        log.write_header(f"ZIPアーカイブ作成: {zip_path}")
        with zipfile.ZipFile(to_win_long(zip_path),"w",zipfile.ZIP_DEFLATED)as zf:
            zf.writestr("PROJECT_CHRONICLE.md",chronicle_md); zf.writestr("PROJECT_INFO.md",project_info_md); zf.writestr("COMBINED_CODE.py",combined_code_py); zf.writestr("README.md",readme_md)
        summary=f"✅ 年代記パッケージのエクスポート完了: {zip_path}"
    elif profile["output_mode"]=="standard_zip":
        manifest_dir=exports_dir/output_prefix
        if emit_folder:
            manifest_dir.mkdir(parents=True,exist_ok=True)
            if progress:progress(0.7,desc="マニフェストフォルダにコピー中...")
            for item in picked_items:
                dest=manifest_dir/shorten_path(item.rel_path);dest.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(to_win_long(item.path),to_win_long(dest))
        if emit_zip:
            zip_path=exports_dir/f"{output_prefix}.zip"
            target_dir = manifest_dir if emit_folder else exports_dir/f"_temp_{output_prefix}"
            if not emit_folder:
                target_dir.mkdir(parents=True,exist_ok=True)
                for item in picked_items:
                    dest=target_dir/shorten_path(item.rel_path);dest.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(to_win_long(item.path),to_win_long(dest))
            if progress:progress(0.9,desc="ZIPアーカイブ作成中...")
            with zipfile.ZipFile(to_win_long(zip_path),"w",zipfile.ZIP_DEFLATED)as zf:
                for p in target_dir.rglob("*"):zf.write(p,p.relative_to(target_dir))
            if not emit_folder:shutil.rmtree(target_dir)
        summary="✅ 標準ZIPパッケージのエクスポート完了。"

    if zip_path:
        actual_zip_mb = zip_path.stat().st_size / 1024**2
        prediction_accuracy = (1 - abs(actual_zip_mb - total_predicted_zip_bytes/1024**2) / (total_predicted_zip_bytes/1024**2)) * 100 if total_predicted_zip_bytes > 0 else 100
        summary += f"\n  - 予測ZIP: {total_predicted_zip_bytes/1024**2:.2f} MB / 実際ZIP: {actual_zip_mb:.2f} MB (予測精度: {prediction_accuracy:.1f}%)"
        # ★★★★★ [NEW] 自己学習機能 ★★★★★
        update_compression_stats(picked_items, actual_zip_mb, log)

    if progress:progress(1.0,desc="完了！")
    log.flush(summary)

def create_gradio_interface():
    if not gr:return print("Gradio未インストール。`pip install gradio`でUIが有効になります。")
    stop_event = Event()
    with gr.Blocks(title="NexusCore AI Exporter",theme=gr.themes.Soft())as demo:
        gr.Markdown("# 統合版AIプロジェクトエクスポート＆Perplexityアップロード v10.1")
        with gr.Row():
            root_tb = gr.Textbox(label="📁 プロジェクトルート", value=str(Path.cwd()))
            profile_dd = gr.Dropdown(choices=[(p["description"], p_name) for p_name, p in PROFILES.items()], value="gemini-chronicle", label="📜 プロファイル")
        profile_info = gr.Markdown(value=PROFILES["gemini-chronicle"]["description"])
        # ★★★★★ [UX] Accordionの可視性を動的に変更 ★★★★★
        with gr.Accordion("詳細設定", open=False, visible=False) as accordion:
            api_token_tb = gr.Textbox(label="🔑 Perplexity APIトークン", type="password", placeholder="pplx-...", info="Perplexity Proアップロード選択時に必須です。", visible=False)
            emit_zip_cb = gr.Checkbox(label="ZIPも出力 (gpt5-zip選択時)", value=True, visible=False)
            emit_folder_cb = gr.Checkbox(label="フォルダも出力 (gpt5-zip選択時)", value=False, visible=False)
        with gr.Row():
            run_btn = gr.Button("▶️ 実行", variant="primary"); dry_run_btn = gr.Button("👁️ ドライラン", variant="secondary"); cancel_btn = gr.Button("⏹️ キャンセル")
        status_out = gr.Textbox(label="📋 ログ", lines=15, max_lines=30, interactive=False)
        
        def start_export_wrapper(root, profile, api_token, emit_zip, emit_folder, dry_run, progress=gr.Progress(track_tqdm=True)):
            stop_event.clear(); log_sink=LogSink(DEFAULT_LOGS_DIR,dry_run)
            try:
                export_main(root,profile,emit_zip,emit_folder,dry_run,DEFAULT_EXPORTS_DIR,DEFAULT_LOGS_DIR,stop_event,api_token,progress)
                return log_sink.path.read_text(encoding='utf-8',errors='ignore')
            except Exception:
                log_sink.write(f"❌ 致命的なエラー:\n{traceback.format_exc()}"); return log_sink.path.read_text(encoding='utf-8',errors='ignore')
        
        def on_profile_change(profile_name: str):
            profile_data = PROFILES.get(profile_name, {}); mode = profile_data.get("output_mode")
            is_perplexity, is_standard_zip = (mode=="perplexity_upload"), (mode=="standard_zip")
            return {
                profile_info: gr.Markdown(visible=True, value=f"**選択中**: {profile_data.get('description', '')}"),
                accordion: gr.Accordion(visible=is_perplexity or is_standard_zip),
                api_token_tb: gr.Textbox(visible=is_perplexity, interactive=True),
                emit_zip_cb: gr.Checkbox(visible=is_standard_zip, interactive=is_standard_zip),
                emit_folder_cb: gr.Checkbox(visible=is_standard_zip, interactive=is_standard_zip),
            }

        run_btn.click(fn=start_export_wrapper,inputs=[root_tb, profile_dd, api_token_tb, emit_zip_cb, emit_folder_cb, gr.State(False)],outputs=[status_out])
        dry_run_btn.click(fn=start_export_wrapper,inputs=[root_tb, profile_dd, api_token_tb, emit_zip_cb, emit_folder_cb, gr.State(True)],outputs=[status_out])
        cancel_btn.click(fn=lambda: stop_event.set())
        profile_dd.change(fn=on_profile_change, inputs=[profile_dd], outputs=[profile_info, accordion, api_token_tb, emit_zip_cb, emit_folder_cb])
        demo.load(fn=lambda: on_profile_change("gemini-chronicle"), outputs=[profile_info, accordion, api_token_tb, emit_zip_cb, emit_folder_cb])
    demo.launch(inbrowser=True, server_name="127.0.0.1", server_port=7868)

def main():
    parser = argparse.ArgumentParser(description="NexusCore AI Exporter v10.1")
    parser.add_argument("root", nargs="?", default=str(Path.cwd()), help="プロジェクトルート")
    parser.add_argument("--profile", choices=list(PROFILES.keys()), default="gemini-chronicle", help="プロファイル")
    parser.add_argument("--emit-zip", action="store_true", help="[gpt5-zip] ZIP出力")
    parser.add_argument("--emit-folder", action="store_true", help="[gpt5-zip] フォルダ出力")
    parser.add_argument("--dry-run", action="store_true", help="ドライランモード")
    parser.add_argument("--ui", action="store_true", help="Gradio UIを起動")
    parser.add_argument("--api-token", type=str, help="Perplexity APIトークン")
    args = parser.parse_args()
    if args.ui: create_gradio_interface()
    else: export_main(args.root, args.profile, args.emit_zip, args.emit_folder, args.dry_run, DEFAULT_EXPORTS_DIR, DEFAULT_LOGS_DIR, Event(), args.api_token)

if __name__=="__main__":
    main()

