# ======================================================================
# code_export_gemini.py — Gemini 10ファイル制限最適化（4ファイル構成）
# 外部共有“安全寄り”デフォルト（KEEP優先 / .envは除外）
# 2025-08-24 rev: プロジェクト年代記の自動生成機能を追加
# ======================================================================

from __future__ import annotations

import ast
import datetime
import fnmatch
import os
import re
import subprocess
import traceback
import zipfile
from collections import defaultdict, Counter
from math import log2
from pathlib import Path
from threading import Event
from typing import List, Tuple, Dict, Set, Any

import gradio as gr

try:
    import networkx as nx
except ImportError:
    nx = None

# === CONFIG (変更なし) =======================================================
KEEP_FILES: Set[str] = {
    "requirements.txt", "pyproject.toml", "project_structure.json", ".env.template",
}
IGNORED_DIRS_USER: Set[str] = {
    ".git", "__pycache__", "node_modules", "dist", "build", ".venv", "venv",
    ".idea", ".vscode", ".mypy_cache", ".pytest_cache", "htmlcov", ".gradio", "exports",
    "openenv", "myenv", "old_tool", "quality_loop_test_sandbox", "result_images",
    "sandbox_repo", "scripts", "output", "patch_history", "policy_test_sandbox",
    "project_structure_export", "quality_gate_test_sandbox", "test_cache",
}
IGNORED_FILES_USER: Set[str] = {
    ".coverage", ".env", ".env.template", ".gitattributes", ".gitignore", ".nexus_context.json",
    ".python-version", "nexus_api_server.log", "nexus_core_run.log", "orchestrator_test.log",
    "quality_gate_test_run.log", "OpenCodeInterpreter.code-workspace", "launch.bat",
    "launch_all.ps1", "launch_dev.ps1", "LICENSE", "project_chronicle.jsonl",
    "project_structure.json", "fix_imports.py", "gradio_app.py", "main_cli.py",
    "project_structure_and_code_export.py", "pytest.ini", "vscode-extension.zip",
}
EXPORT_DIR_NAME = "exports"
MAX_COMBINED_CODE_SIZE_MB = 10
WIN_PATH_CAP = 250
FILE_TYPES: Tuple[str, ...] = (
    ".py", ".ipynb", ".md", ".txt", "package.json", ".json", ".yml", ".yaml", ".toml",
)
EXTENSION_WEIGHTS = {".py": 3, ".ipynb": 2, ".md": 1}
PATH_WEIGHTS = {"src": 2, "app": 2, "lib": 1, "nexuscore": 3, "tests": -1, "docs": -1}
stop_event = Event()

# === HELPERS (変更なし) =====================================================
# ... (sanitize_name, generate_project_prefix, etc. は変更ないため省略) ...
def sanitize_name(name: str) -> str:
    invalid_chars = r'[<>:"/\\|?*\x00-\x1f]'
    s = re.sub(invalid_chars, '_', name)
    s = re.sub(r'_+', '_', s).strip('_') or "Unknown"
    return s[:50]

def generate_project_prefix(roots: List[Path]) -> str:
    if not roots: return "Export"
    names = [sanitize_name(r.name) for r in roots]
    if len(names) == 1: return names[0]
    return "-".join(names) if len(names) <= 3 else f"{'-'.join(names[:2])}-etc{len(names)-2}"

def load_gitignore(root: Path) -> Set[str]:
    gi = root / ".gitignore"
    if not gi.exists(): return set()
    return {
        line.strip()
        for line in gi.read_text("utf-8", errors="ignore").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }

def path_is_ignored(path: Path, root: Path, patterns: Set[str], export_root: Path) -> bool:
    if export_root in path.parents or path == export_root: return True
    for d in IGNORED_DIRS_USER:
        try:
            if (root / d) in path.parents: return True
        except Exception: pass
    try:
        rel = path.relative_to(root)
    except ValueError: return True
    for pat in patterns:
        if pat.endswith("/") and fnmatch.fnmatch(f"{rel}/", pat): return True
        if fnmatch.fnmatch(str(rel), pat) or fnmatch.fnmatch(path.name, pat): return True
    if path.is_file() and path.name in IGNORED_FILES_USER: return True
    return False

def build_import_map(root: Path, py_files: List[Path], progress: gr.Progress) -> Dict[Path, Set[Path]]:
    progress(0.35, desc="import依存関係を解析中...")
    module_of = {".".join(p.relative_to(root).with_suffix("").parts): p for p in py_files}
    mapping: Dict[Path, Set[Path]] = defaultdict(set)
    for i, pf in enumerate(py_files):
        if stop_event.is_set(): break
        try:
            tree = ast.parse(pf.read_text("utf-8", errors="ignore"))
        except Exception: continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for a in node.names:
                    tgt = module_of.get(a.name.split(".")[0])
                    if tgt: mapping[pf].add(tgt)
            elif isinstance(node, ast.ImportFrom) and node.module:
                tgt = module_of.get(node.module.split(".")[0])
                if tgt: mapping[pf].add(tgt)
        if i % 10 == 0 and py_files:
            progress(0.35 + (0.1 * i / len(py_files)), desc=f"import解析中... ({i+1}/{len(py_files)})")
    return mapping

def degree_centrality(mapping: Dict[Path, Set[Path]]) -> Dict[Path, float]:
    if not nx: return {k: float(len(v)) for k, v in mapping.items()}
    g = nx.DiGraph()
    for s, tgts in mapping.items():
        for t in tgts: g.add_edge(s, t)
    return nx.degree_centrality(g)

def loc_count(p: Path) -> int:
    try: return sum(1 for _ in p.open("r", encoding="utf-8", errors="ignore"))
    except Exception: return 0

def file_score(path: Path, root: Path, cent: Dict[Path, float]) -> float:
    score = EXTENSION_WEIGHTS.get(path.suffix.lower(), 0)
    score += next((PATH_WEIGHTS[p] for p in path.parts if p in PATH_WEIGHTS), 0)
    score += cent.get(path, 0) * 5
    lines = loc_count(path)
    if lines: score += min(log2(lines + 1) / 5, 3)
    return score

def collect_files(root: Path, max_single_mb: int, progress: gr.Progress) -> List[Path]:
    progress(0.05, desc=f"フォルダをスキャン中... ({root.name})")
    export_root = root / EXPORT_DIR_NAME
    patterns = load_gitignore(root)
    cap_single = max_single_mb * 1024 * 1024
    cand: List[Path] = []
    try:
        entries = list(root.rglob("*"))
    except (PermissionError, FileNotFoundError): return []
    total_entries = len(entries)
    for i, p in enumerate(entries):
        if stop_event.is_set(): break
        include_by_keep = p.is_file() and (p.name in KEEP_FILES)
        if not include_by_keep:
            if not path_is_ignored(p, root, patterns, export_root):
                if p.is_file() and (p.suffix.lower() in FILE_TYPES) and (p.stat().st_size <= cap_single):
                    if os.name == "nt":
                        try:
                            if len(str(export_root / p.relative_to(root))) > WIN_PATH_CAP: p = None
                        except ValueError: p = None
                    if p is not None: cand.append(p)
        else:
            cand.append(p)
        if i % 100 == 0 and total_entries:
            progress(0.1 + (0.15 * i / total_entries), desc=f"ファイル収集中... ({len(cand)}件)")
    if not cand: return []
    progress(0.3, desc="重要度を計算中...")
    py = [p for p in cand if p.suffix == ".py"]
    cent = degree_centrality(build_import_map(root, py, progress)) if py and nx else {}
    progress(0.5, desc="ファイルを重要度順にソート中...")
    cand.sort(key=lambda p: file_score(p, root, cent), reverse=True)
    return cand

def make_tree_and_list(pairs: List[Tuple[Path, Path]]) -> Tuple[str, str]:
    by_root: Dict[Path, List[Path]] = defaultdict(list)
    for rt, p in pairs: by_root[rt].append(p)
    sections, flat_list = [], []
    for rt, files in by_root.items():
        tree_dict: Dict[str, Dict] = {}
        for f in files:
            try: rel = f.relative_to(rt)
            except ValueError: rel = Path(f.name)
            node = tree_dict
            for part in rel.parts: node = node.setdefault(part, {})
            flat_list.append(str(rel).replace("\\", "/"))
        lines = [f"./ ({rt.name})"]
        def dfs(d: Dict[str, Dict], pref=""):
            items = sorted(d.keys())
            for i, k in enumerate(items):
                conn = "└── " if i == len(items) - 1 else "├── "
                lines.append(f"{pref}{conn}{k}")
                if d[k]: dfs(d[k], pref + ("    " if i == len(items)-1 else "│   "))
        dfs(tree_dict)
        sections.append("\n".join(lines))
    return "\n\n".join(sections), "\n".join(sorted(flat_list))


# === NEW ChronicleGenerator CLASS ==========================================
class ChronicleGenerator:
    """Git履歴を分析し、プロジェクトの物語を生成するクラス"""
    def __init__(self, roots: List[Path]):
        self.roots = roots
        # 複数のリポジトリがある場合、最初のものをプライマリとして扱う
        self.primary_root = roots[0] if roots else Path(".")
        self.keyword_themes = {
            "Architecture & Refactoring": ["refactor", "architect", "design", "core", "module", "restructure"],
            "AI & Agents": ["agent", "llm", "model", "prompt", "ai", "orchestrator"],
            "Features & UI": ["feature", "add", "ui", "gradio", "api", "endpoint", "implement"],
            "Database & State": ["db", "database", "redis", "postgres", "sql", "state", "manager"],
            "Testing & Quality": ["test", "fix", "bug", "ci", "quality", "robust", "error", "debug"],
        }

    def _run_git_log(self) -> List[Dict[str, Any]]:
        if not (self.primary_root / ".git").exists():
            return []
        try:
            # --date=short: YYYY-MM-DD, --pretty=format: ... : カスタムフォーマット
            # %H: commit hash, %ad: author date, %s: subject
            # <DELIMITER>で各項目を区切る
            cmd = [
                "git", "log", "--date=short", "--pretty=format:%H<DELIMITER>%ad<DELIMITER>%s",
                "--no-merges", "--since=1.year.ago" # 直近1年間に限定
            ]
            result = subprocess.run(
                cmd, cwd=self.primary_root, capture_output=True, text=True,
                encoding='utf-8', errors='ignore'
            )
            if result.returncode != 0: return []
            
            commits = []
            for line in result.stdout.strip().split("\n"):
                parts = line.split("<DELIMITER>")
                if len(parts) == 3:
                    commits.append({"hash": parts[0], "date": parts[1], "subject": parts[2]})
            return commits
        except (FileNotFoundError, subprocess.SubprocessError):
            return []

    def _summarize_commits_by_week(self, commits: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        weekly_commits: Dict[str, List[str]] = defaultdict(list)
        for commit in commits:
            try:
                commit_date = datetime.datetime.strptime(commit["date"], "%Y-%m-%d")
                # 週の始まり（月曜日）を基準にグルーピング
                week_start = commit_date - datetime.timedelta(days=commit_date.weekday())
                week_key = week_start.strftime("%Y-%m-%d")
                weekly_commits[week_key].append(commit["subject"])
            except ValueError:
                continue
        return weekly_commits

    def _analyze_theme(self, subjects: List[str]) -> str:
        theme_counts = Counter()
        for subject in subjects:
            subj_lower = subject.lower()
            for theme, keywords in self.keyword_themes.items():
                if any(keyword in subj_lower for keyword in keywords):
                    theme_counts[theme] += 1
        if not theme_counts:
            return "General Updates & Maintenance"
        # 最も頻繁に出現したテーマを返す
        return theme_counts.most_common(1)[0][0]

    def generate(self) -> str:
        commits = self._run_git_log()
        if not commits:
            return "# 📖 プロジェクト年代記\n\nGitの履歴が見つからないため、年代記を生成できませんでした。\n"

        weekly_summary = self._summarize_commits_by_week(commits)
        if not weekly_summary:
            return "# 📖 プロジェクト年代記\n\n分析可能なコミット履歴がありませんでした。\n"

        md = ["# 📖 プロジェクト年代記 (AI-Generated)"]
        md.append("\n**これは、Gitのコミット履歴を基にAIが自動生成したプロジェクトの進化の記録です。**\n")

        # 週ごとにソートして表示
        for week_start_str in sorted(weekly_summary.keys(), reverse=True)[:12]: # 直近12週に限定
            subjects = weekly_summary[week_start_str]
            week_start_date = datetime.datetime.strptime(week_start_str, "%Y-%m-%d")
            theme = self._analyze_theme(subjects)
            
            md.append(f"---")
            md.append(f"###  EPOCH: {week_start_date.strftime('%Y年%m月%d日')} の週")
            md.append(f"**テーマ: {theme}**\n")
            
            # 各週のコミットから代表的なものをいくつか抜粋
            for subj in subjects[:3]: # 3つまで表示
                md.append(f"- {subj}")
            if len(subjects) > 3:
                md.append(f"- ...他 {len(subjects) - 3} 件の改善")
            md.append("")

        return "\n".join(md)


# === MODIFIED FUNCTIONS (自己説明機能) =========================================
def generate_project_info_content(
    total_files: int, total_lines: int, stats: Dict[str, Dict[str, int]],
    export_type: str, max_size_mb: int, project_name: str,
    tree_txt: str = "", path_list_txt: str = "", kept: List[str] | None = None
) -> str:
    # ... (この関数は前回の提案から変更なし) ...
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    warning_section = f"""
# ⚠️ 重要: このパッケージの構造について
このZIPファイルは、AIによる分析を効率化するために特別に作成された **分析用パッケージ** です。
**実際のプロジェクトのディレクトリ構造やファイル構成をそのまま反映したものではありません。**

- **`COMBINED_CODE.py`**: これは、分析対象として選ばれた複数のソースコードファイルを **1つに結合した合成ファイル** です。実際のプロジェクトには存在しません。
- **実際の構造**: 元のプロジェクトのファイル構造については、後述の「3. ディレクトリツリー」や「4. パス一覧」を参照してください。

---
"""
    project_summary = f"""# 📦 {project_name} プロジェクト解析パッケージ ({export_type})

## 1. 概要
- 総ファイル数: {total_files}
- 総コード行数: {total_lines:,} 行
- エクスポート日時: {timestamp}
"""
    stats_table = "| 拡張子 | ファイル数 | コード行数 |\n|---|---|---|\n"
    for ext, data in sorted(stats.items(), key=lambda x: x[1]['files'], reverse=True):
        stats_table += f"| `{ext}` | {data['files']:,} | {data['lines']:,} |\n"
    stats_table += f"| 合計 | {total_files:,} | {total_lines:,} |\n"
    keep_note = f"\n保持優先ファイル: {', '.join(sorted(kept))}\n" if kept else ""
    package_info = f"""
---
## 2. パッケージの作り方
このZIPは `code_export_gemini.py` により、~{max_size_mb}MB 制約内で重要度順に抽出・結合しています。

### 重要度判定
- 拡張子重み: `.py`(3), `.ipynb`(2), `.md`(1)
- パス重み: `src/`, `app/`, `nexuscore/`(+)、`tests/`, `docs/`(-)
- import結合度（中心性）・LOC
{keep_note}
"""
    structure_block = ""
    if tree_txt:
        structure_block += f"\n---\n## 3. ディレクトリツリー\n```\n{tree_txt}\n```\n"
    if path_list_txt:
        lines = path_list_txt.splitlines()
        limit = 5000
        shown = "\n".join(lines[:limit])
        more = f"\n…(省略: {len(lines)-limit} 行)\n" if len(lines) > limit else ""
        structure_block += f"\n## 4. パス一覧\n```\n{shown}{more}```\n"
    return f"{warning_section}{project_summary}\n## ファイル統計\n{stats_table}{package_info}{structure_block}"


def create_combined_code(all_files: List[Tuple[Path, Path]], progress: gr.Progress) -> str:
    # ... (この関数は前回の提案から変更なし) ...
    progress(0.85, desc="統合コード生成中...")
    warning_header = """
# ///////////////////////////////////////////////////////////////////////////
# ///                                                                     ///
# ///   !!!   W A R N I N G   !!!                                         ///
# ///                                                                     ///
# ///   THIS IS A COMBINED FILE FOR AI ANALYSIS.                          ///
# ///   DO NOT EDIT THIS FILE DIRECTLY.                                   ///
# ///                                                                     ///
# ///   The original project consists of multiple separate files.         ///
# ///   This file was automatically generated by concatenating them.      ///
# ///                                                                     ///
# ///////////////////////////////////////////////////////////////////////////
"""
    lines = [
        warning_header,
        f"# === COMBINED SOURCE CODE ===",
        f"# Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"# Total files combined: {len(all_files)}",
        ""
    ]
    for i, (root, file_path) in enumerate(all_files):
        if stop_event.is_set(): break
        try:
            rel = file_path.relative_to(root)
            lines.append(f"\n# === START OF: {root.name}/{rel} ===")
            lines.extend(file_path.read_text("utf-8", errors="ignore").splitlines())
            lines.append(f"# === END OF: {root.name}/{rel} ===")
        except Exception as e:
            lines.append(f"# ERROR reading {file_path}: {e}")
        if i % 10 == 0 and all_files:
            progress(0.85 + (0.1 * i / len(all_files)), desc=f"統合中... ({i+1}/{len(all_files)})")
    return "\n".join(lines)


def create_readme_md(project_prefix: str, roots: List[Path]) -> str:
    # 【変更】PROJECT_CHRONICLE.mdへの言及を追加
    return f"""# {project_prefix} - AI Analysis Package

## 概要
このZIPは、`{project_prefix}` プロジェクトの重要ファイルを抽出し、GeminiのようなAIによる分析に最適化したものです。

## 分析対象
{chr(10).join(f"- `{root}`" for root in roots)}

## 使い方
このZIPをそのままAIにアップロードして、プロジェクトに関する質問をしてください。

## 構成
- **`PROJECT_CHRONICLE.md`**: **【NEW】** Git履歴からAIが自動生成した **プロジェクトの進化の記録** です。まずはこちらを読むことをお勧めします。
- `PROJECT_INFO.md`: プロジェクトの統計情報、作成方法、および元のファイル構造（ツリー/パス一覧）が含まれています。
- `COMBINED_CODE.py`: **【注意】** これは分析のためにソースコードを一つにまとめた **合成ファイル** です。
- `README.md`: このファイルです。
"""

# === MAIN LOGIC (MODIFIED) ==================================================
def export_for_gemini(roots: List[Path], max_single_mb: int, progress: gr.Progress) -> Path:
    progress(0, desc="Gemini用エクスポートを開始...")
    project_prefix = generate_project_prefix(roots)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    export_dir = roots[0] / EXPORT_DIR_NAME
    export_dir.mkdir(exist_ok=True)
    
    # ... (ファイル収集とスコアリング部分は変更なし) ...
    all_files_scored: List[Tuple[float, Path, Path]] = []
    total_files, total_lines = 0, 0
    stats: Dict[str, Dict[str, int]] = defaultdict(lambda: {"files": 0, "lines": 0})
    for idx, rt in enumerate(roots, 1):
        if stop_event.is_set(): raise RuntimeError("キャンセルされました")
        progress(0.1 * idx / len(roots), desc=f"フォルダ解析中... ({rt.name})")
        class SubProgress:
            def __call__(self, value, desc=""):
                progress(0.1 * (idx - 1) / len(roots) + value * 0.6 / len(roots), desc=desc) # scale factor adjusted
        collected = collect_files(rt, max_single_mb, SubProgress())
        py_files = [p for p in collected if p.suffix == ".py"]
        cent = degree_centrality(build_import_map(rt, py_files, SubProgress())) if py_files and nx else {}
        for p in collected:
            all_files_scored.append((file_score(p, rt, cent), rt, p))
            ext = p.suffix or "No Ext"
            stats[ext]["files"] += 1
            lines = loc_count(p)
            stats[ext]["lines"] += lines
            total_lines += lines
    total_files = len(all_files_scored)
    all_files_scored.sort(key=lambda x: x[0], reverse=True)
    keep_scored = [t for t in all_files_scored if t[2].name in KEEP_FILES]
    py_scored = [t for t in all_files_scored if t[2].suffix == ".py" and t[2].name not in KEEP_FILES]
    rest_scored = [t for t in all_files_scored if t not in keep_scored and t not in py_scored]
    ordered = keep_scored + py_scored + rest_scored
    final_files: List[Tuple[Path, Path]] = []
    current_size = 0
    max_total_bytes = MAX_COMBINED_CODE_SIZE_MB * 1024 * 1024
    for _, root, path in ordered:
        size = path.stat().st_size
        if current_size + size > max_total_bytes: continue
        final_files.append((root, path))
        current_size += size
    if not final_files: raise RuntimeError("処理対象ファイルがありません")
    
    tree_txt, path_list_txt = make_tree_and_list(final_files)
    
    progress(0.7, desc="Gemini用ファイル生成中...")
    project_info = generate_project_info_content(
        len(final_files), sum(loc_count(p) for _, p in final_files), stats, "Gemini", MAX_COMBINED_CODE_SIZE_MB,
        project_prefix, tree_txt=tree_txt, path_list_txt=path_list_txt, kept=list(KEEP_FILES)
    )
    combined_code = create_combined_code(final_files, progress) # progress is passed inside
    readme = create_readme_md(project_prefix, roots)

    # 【NEW】年代記の生成
    progress(0.90, desc="プロジェクト年代記を生成中...")
    chronicle_generator = ChronicleGenerator(roots)
    project_chronicle = chronicle_generator.generate()

    progress(0.95, desc="ZIPアーカイブ作成中...")
    zip_path = export_dir / f"{project_prefix}_gemini_{ts}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("PROJECT_CHRONICLE.md", project_chronicle) # 新しいファイルを追加
        zf.writestr("PROJECT_INFO.md", project_info)
        zf.writestr("COMBINED_CODE.py", combined_code)
        zf.writestr("README.md", readme)
        
    progress(1.0, desc="Gemini用エクスポート完了!")
    return zip_path

# === GRADIO UI (MODIFIED) ===================================================
def create_interface():
    with gr.Blocks(title="Code Export for Gemini", css=".gr-button{min-width:6rem} .gr-textbox{font-family:monospace}", theme=gr.themes.Soft()) as demo:
        # 【変更】タイトルを更新
        gr.Markdown("## 🤖 Gemini対応コードエクスポート（年代記自動生成機能付き）")
        with gr.Row():
            dirs_tb = gr.Textbox(label="📁 プロジェクトフォルダ (1行=1フォルダ)", lines=3)
            with gr.Column(min_width=120):
                browse_btn = gr.Button("📂 参照して追加", size="sm")
                preview_btn = gr.Button("👁️ プレビュー", variant="secondary", size="sm")
        gemini_preview = gr.Textbox(label="プレビュー", lines=9, interactive=False, visible=False) # linesを増やした
        max_slider = gr.Slider(1, 50, value=MAX_COMBINED_CODE_SIZE_MB, step=1, label="🔧 統合コード最大サイズ (MB)")
        with gr.Row():
            exp_btn = gr.Button("▶️ エクスポート開始", variant="primary", size="lg")
            cancel_btn = gr.Button("⏹️ キャンセル", variant="secondary")
        zip_out = gr.File(label="📦 ZIP")
        status = gr.Textbox(label="📋 ステータス", lines=10, max_lines=20, show_copy_button=True)
        
        # ... (イベントハンドラは変更なし) ...
        browse_btn.click(browse_and_append, inputs=[dirs_tb], outputs=[dirs_tb])
        preview_btn.click(show_gemini_preview, inputs=[dirs_tb], outputs=[gemini_preview]).then(
            lambda: gr.update(visible=True), outputs=[gemini_preview]
        )
        export_event = exp_btn.click(run_export_wrapper, inputs=[dirs_tb, max_slider], outputs=[zip_out, status], show_progress="full")
        cancel_btn.click(fn=cancel_export, inputs=None, outputs=[status], cancels=[export_event])
        demo.queue(default_concurrency_limit=1, max_size=10)
    return demo

def show_gemini_preview(roots_str: str):
    # 【変更】プレビュー内容を更新
    roots_list = [p.strip() for p in roots_str.splitlines() if p.strip()]
    if not roots_list: return "⚠️ フォルダを選択してください"
    try:
        prefix = generate_project_prefix([Path(p) for p in roots_list])
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"""🎯 Gemini用エクスポートプレビュー:
📦 ZIP: `{prefix}_gemini_{ts}.zip`
📋 4ファイル構成:
1. **PROJECT_CHRONICLE.md (NEW)**: Git履歴からAIが生成するプロジェクトの進化史
2. PROJECT_INFO.md: 統計/ツリー/パス一覧
3. COMBINED_CODE.py: ソースコード結合ファイル
4. README.md: パッケージ全体の案内
🔐 KEEP: {", ".join(sorted(KEEP_FILES))}
"""
    except Exception as e: return f"⚠️ プレビュー生成エラー: {e}"

# ... (run_export_wrapper, cancel_export, browse_and_append, _get_allowed_paths, __main__ は変更なし) ...
def run_export_wrapper(roots_str: str, max_mb: int, progress=gr.Progress(track_tqdm=True)):
    stop_event.clear()
    roots_list = [p.strip() for p in roots_str.splitlines() if p.strip()]
    if not roots_list: return None, "⚠️ 少なくとも1つのフォルダを選択してください"
    roots = []
    for path_str in roots_list:
        try:
            path = Path(path_str).expanduser().resolve()
            if not path.is_dir(): return None, f"⚠️ フォルダではありません: {path_str}"
            roots.append(path)
        except Exception: return None, f"⚠️ 無効なパス: {path_str}"
    try:
        zp = export_for_gemini(roots, max_mb, progress)
        mb = zp.stat().st_size / (1024 * 1024)
        return str(zp), f"✅ Gemini対応エクスポート完了!\n- ファイルサイズ: {mb:.2f} MB\n- 出力場所: {zp}"
    except Exception as e:
        return None, f"❌ エラー:\n{e}\n\n詳細:\n{traceback.format_exc(limit=3)}"

def cancel_export():
    stop_event.set()
    return "⏹️ キャンセル信号を送信しました"

def browse_and_append(existing: str):
    try:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        path = filedialog.askdirectory(title="プロジェクトフォルダを選択")
        root.destroy()
        if path:
            paths = [p.strip() for p in existing.splitlines() if p.strip()]
            if path not in paths: paths.append(path)
            return "\n".join(paths)
    except Exception: pass
    return existing

def _get_allowed_paths() -> list[str]:
    env = os.environ.get("GRADIO_ALLOWED_PATHS", "").strip()
    if env:
        paths = [p.strip() for p in env.split(",") if p.strip()]
        abs_paths = []
        for p in paths:
            try: abs_paths.append(str(Path(p).resolve()))
            except Exception: pass
        return abs_paths
    defaults = [
        r"C:\Users\USER\tools\atelier-kyo-manager\exports",
        r"C:\Users\USER\tools\NexusCore\exports",
    ]
    resolved = []
    for p in defaults:
        try: resolved.append(str(Path(p).resolve()))
        except Exception: pass
    return resolved

if __name__ == "__main__":
    print("🤖 Code Export for Gemini (Chronicle Generator) 起動")
    allowed_paths = _get_allowed_paths()
    blocked_paths = None
    demo = create_interface()
    launch_kwargs = dict(
        inbrowser=True, server_name="127.0.0.1", server_port=7860, share=False,
    )
    if allowed_paths: launch_kwargs["allowed_paths"] = allowed_paths
    if blocked_paths: launch_kwargs["blocked_paths"] = blocked_paths
    demo.launch(**launch_kwargs)
