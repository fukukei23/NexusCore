# ======================================================================
# ファイル名: code_export_gemini_final.py
#
# 機能概要:
# Gemini等の大規模言語モデル（LLM）での分析に最適化されたプロジェクト
# のスナップショットを生成するハイブリッド・エクスポートツール。
#
# 使用方法:
# 1. このスクリプトをプロジェクトのルートフォルダ、または任意の場所に配置します。
# 2. ターミナルで `pip install gradio networkx` を実行し、必要なライブラリを
#    インストールします。
# 3. `python code_export_gemini_final.py` を実行してGradio UIを起動します。
# 4. UI上で対象のプロジェクトフォルダパスを指定し、プロファイルを選択して
#    エクスポートを実行します。
# 5. `exports` フォルダ内に、分析用のZIPファイルとフォルダが生成されます。
#
# --- 更新履歴 ---
# 2025-08-26 rev6.2:
#  - ログシステムを導入（silent/basic/detail）。UIのトグルで切り替え可能に。
#  - プロファイル別ルール（PROFILE_RULES）を導入し、除外設定を一元管理。
#    - Gemini(≤10MB)では site-packages を完全除外、フォールバックを無効化。
#  - すべてのファイル走査ロジックで、単一の path_is_ignored 判定関数を
#    呼び出すように統一し、フィルタリングの信頼性を向上。
#  - エクスポート開始時に出力先をクリーンアップする処理を追加。
#
# 2025-08-26 rev6.1 (Hotfix):
#  - 除外フィルタリングを強化し、ファイル上限を厳守するよう修正。
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
from collections import defaultdict, Counter
from math import log2
from pathlib import Path
from threading import Event
from typing import List, Tuple, Dict, Set, Any, Optional

import gradio as gr

try:
    import networkx as nx
except ImportError:
    nx = None

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

MAX_PROJECT_SIZE_MB = 256
MANIFEST_INCLUDED_FILES_MIN = 12
MANIFEST_INCLUDED_FILES_MAX = 120

TEXT_EXTS = (
    ".py",".ipynb",".md",".txt",".json",".yml",".yaml",".toml",
    ".js",".ts",".tsx",".jsx",".vue",".css",".scss",".less",".html",".htm",
    ".ini",".cfg",".conf",".bat",".ps1",".sh",".bash",".dockerfile",".env.example",
    ".java",".kt",".go",".rs",".cpp",".cxx",".cc",".c",".h",".hpp",".cs",".php",".rb",".r",".m",".mm",".swift"
)
FALLBACK_BINARY_EXTS = {".png",".jpg",".jpeg",".gif",".webp",".svg",".ico",".bin",".dat",".vec",".model"}

ALWAYS_INCLUDE_FILES = {"requirements.txt", "pyproject.toml", ".env.template", "package.json"}
KEEP_FILES = ALWAYS_INCLUDE_FILES

# --- v6.2 MODIFIED BLOCK START ---
# ===== プロファイル別ルール =====
MB = 1024 * 1024
PROFILE_RULES = {
    "gemini_10mb": {
        "allow_site_packages": False,
        "fallback_binary_max_bytes": 0,     # フォールバック無効
        "extra_excludes": {
            "exported_projects", "evaluation", "history", "logs",
            "htmlcov", "htmlcov_agents", "htmlcov_detailed", "htmlcov_final", "htmlcov_full",
        },
    },
    "gpt5_50mb": {
        "allow_site_packages": True,
        "fallback_binary_max_bytes": 1 * MB,   # 1MBまで
        "extra_excludes": set(),
    },
    "custom": { # Customのデフォルト
        "allow_site_packages": True,
        "fallback_binary_max_bytes": 512 * 1024,
        "extra_excludes": set(),
    }
}

# ===== 既定の除外（仮想環境・生成物）=====
IGNORED_DIRS_USER = {
    ".git", "__pycache__", "node_modules", "dist", "build",
    ".venv", "venv", "env", "myenv", "openenv",
    ".idea", ".vscode", ".mypy_cache", ".pytest_cache",
    ".gradio", "exports",
}
# --- v6.2 MODIFIED BLOCK END ---

IGNORED_FILES_USER = {".coverage", ".env", ".gitattributes", ".gitignore", "*.log"}
EXPORT_DIR_NAME = "exports"

EXTENSION_WEIGHTS = {".py": 3, ".ipynb": 2, ".md": 1}
PATH_WEIGHTS = {
    "src": 3, "app": 3, "lib": 2, "nexuscore": 5,
    "tests": -1, "docs": -1, "examples": -2,
}

LARGE_FILE_BYTES = 5 * 1024 * 1024
stop_event = Event()

# --- v6.2 MODIFIED BLOCK START ---
# ===== ログ設定 =====
MAX_LOG_LINES = 400
# --- v6.2 MODIFIED BLOCK END ---

# ======================================================================
# Git 年代記
# ======================================================================

class ChronicleGenerator:
    def __init__(self, roots: List[Path]):
        self.roots = roots
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
            cmd = ["git", "log", "--date=short", "--pretty=format:%H %ad %s",
                   "--no-merges", "--since=1.year.ago"]
            result = subprocess.run(
                cmd, cwd=self.primary_root,
                capture_output=True, text=True,
                encoding='utf-8', errors='ignore'
            )
            if result.returncode != 0:
                return []
            commits = []
            for line in result.stdout.strip().split("\n"):
                parts = line.split(" ", 2)
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
        return theme_counts.most_common(1)[0][0]

    def generate(self) -> str:
        commits = self._run_git_log()
        if not commits:
            return "# 📖 プロジェクト年代記\n\nGit履歴が見つからず、生成できませんでした。\n"
        weekly_summary = self._summarize_commits_by_week(commits)
        if not weekly_summary:
            return "# 📖 プロジェクト年代記\n\n分析可能な履歴がありませんでした。\n"

        md = ["# 📖 プロジェクト年代記 (AI-Generated)",
              "\n**Git履歴に基づいてAIが自動生成した進化の記録です。**\n"]
        for week_start_str in sorted(weekly_summary.keys(), reverse=True)[:12]:
            subjects = weekly_summary[week_start_str]
            week_start_date = datetime.datetime.strptime(week_start_str, "%Y-%m-%d")
            theme = self._analyze_theme(subjects)
            md.append(f"---\n### EPOCH: {week_start_date.strftime('%Y年%m月%d日')} の週\n**テーマ: {theme}**\n")
            for subj in subjects[:3]:
                md.append(f"- {subj}")
            if len(subjects) > 3:
                md.append(f"- ...他 {len(subjects)-3} 件の改善")
            md.append("")
        return "\n".join(md)

# ======================================================================
# ユーティリティ
# ======================================================================

def sanitize_name(name: str) -> str:
    invalid_chars = r'[<>:"/\\|?*\x00-\x1f]'
    s = re.sub(invalid_chars, '_', name)
    return re.sub(r'_+', '_', s).strip('_') or "Unknown"

def generate_project_prefix(roots: List[Path]) -> str:
    if not roots: return "Export"
    names = [sanitize_name(r.name) for r in roots]
    if len(names) == 1: return names[0]
    return "-".join(names) if len(names) <= 3 else f"{'-'.join(names[:2])}-etc{len(names)-2}"

def load_gitignore(root: Path) -> Set[str]:
    gi = root / ".gitignore"
    if not gi.exists(): return set()
    patterns = {line.strip() for line in gi.read_text("utf-8", errors="ignore").splitlines()
                if line.strip() and not line.lstrip().startswith("#")}
    return patterns.union(IGNORED_FILES_USER)

# --- v6.2 MODIFIED BLOCK START ---
def path_is_ignored(path: Path, root: Path, export_root: Path, profile_key: str, user_patterns: Set[str]) -> bool:
    rules = PROFILE_RULES.get(profile_key, PROFILE_RULES["custom"])
    try:
        rel_path = path.relative_to(root)
    except Exception:
        return True

    parts_lower = [p.casefold() for p in rel_path.parts]
    name_lower = rel_path.name.casefold()

    if export_root in path.parents or path == export_root:
        return True

    if any(p in {d.casefold() for d in IGNORED_DIRS_USER} for p in parts_lower):
        return True

    if any(p in {d.casefold() for d in rules["extra_excludes"]} for p in parts_lower):
        return True

    if (not rules["allow_site_packages"]) and ("site-packages" in parts_lower):
        return True

    path_str = str(rel_path).replace("\\", "/")
    if any(fnmatch.fnmatchcase(path_str.casefold(), pat.casefold()) or fnmatch.fnmatchcase(name_lower, pat.casefold())
           for pat in user_patterns):
        return True

    return False
# --- v6.2 MODIFIED BLOCK END ---

def build_import_map(root: Path, py_files: List[Path]) -> Dict[Path, Set[Path]]:
    module_of = {".".join(p.relative_to(root).with_suffix("").parts): p for p in py_files}
    mapping: Dict[Path, Set[Path]] = defaultdict(set)
    for pf in py_files:
        if stop_event.is_set(): break
        try:
            source_code = pf.read_text("utf-8", errors="ignore")
            tree = ast.parse(source_code)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        top = alias.name.split(".")[0]
                        tgt = module_of.get(top)
                        if tgt and tgt != pf: mapping[pf].add(tgt)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    level = node.level
                    if level > 0:
                        base_parts = list(pf.relative_to(root).parts)
                        import_base_parts = base_parts[:-1][:len(base_parts) - 1 - (level - 1)]
                        module_parts = node.module.split('.')
                        full_module_path = ".".join(import_base_parts + module_parts)
                        tgt = module_of.get(full_module_path)
                        if tgt and tgt != pf: mapping[pf].add(tgt)
                    else:
                        top = node.module.split(".")[0]
                        tgt = module_of.get(top)
                        if tgt and tgt != pf: mapping[pf].add(tgt)
        except Exception:
            continue
    return mapping

def loc_count(path: Path) -> int:
    try:
        return sum(1 for _ in path.open("r", encoding="utf-8", errors="ignore"))
    except Exception:
        return 0

def file_score(path: Path, root: Path, cent: Dict[Path, float]) -> float:
    base = 0
    try:
        rel = path.relative_to(root)
        depth = len(rel.parts) - 1
        base += EXTENSION_WEIGHTS.get(path.suffix.lower(), 0)
        base += next((PATH_WEIGHTS[p] for p in rel.parts if p in PATH_WEIGHTS), 0)
        base += cent.get(path, 0) * 10
        lines = loc_count(path)
        if lines > 0: base += min(log2(lines + 1) / 5, 3)
        score = base * (1 / (depth * 0.5 + 1))
    except ValueError:
        score = base
    return score

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
    total_entries = len(all_entries)
    for i, p in enumerate(all_entries):
        if stop_event.is_set(): break
        if not p.is_file(): continue
        if path_is_ignored(p, root, export_root, profile_key, patterns):
            continue
        candidates.append(p)
        if i % 100 == 0 and total_entries > 0:
            progress(0.1 + (0.2 * i / total_entries),
                     desc=f"ファイル収集中... ({len(candidates)}件)")
    if not candidates: return []
    py_files = [p for p in candidates if p.suffix == ".py"]
    centrality = {}
    if nx and py_files:
        progress(0.35, desc="import依存関係を解析中...")
        import_map = build_import_map(root, py_files)
        graph = nx.DiGraph()
        for src, targets in import_map.items():
            for tgt in targets:
                graph.add_edge(src, tgt)
        if graph.number_of_nodes() > 0:
            try:
                centrality = nx.degree_centrality(graph)
            except Exception:
                centrality = {}
    scored_files = []
    for p in candidates:
        score = file_score(p, root, centrality)
        if p.name in KEEP_FILES:
            try:
                if p.parent == root: score += 60
                else: score += 10
            except ValueError: pass
        scored_files.append((score, p))
    scored_files.sort(key=lambda x: x[0], reverse=True)
    return scored_files

# ======================================================================
# README / INFO / MANIFEST
# ======================================================================

def create_readme_md(project_prefix: str, profile_name: str) -> str:
    profile = PROFILES[profile_name]
    mode = profile["mode"]
    readme = [f"# {project_prefix} - AI Analysis Package ({profile_name})"]
    readme.append("## 使い方\nこのZIP（および同名フォルダ）をAIに渡して分析してください。")
    readme.append("\n## AIへの推奨分析手順")
    if mode == "manifest":
        readme.extend([
            "1. **`PROJECT_CHRONICLE.md`** を読む（背景/進化）。",
            "2. **`CODE_STRUCTURE_MANIFEST.md`** を最優先で読む（全体設計図）。",
            "3. **`included_source/`** の主要ソースを精読する。",
        ])
    else:
        readme.extend(["1. `PROJECT_CHRONICLE.md`", "2. `COMBINED_CODE.py` or `source_code/`"])
    return "\n".join(readme)

def create_code_structure_manifest_md(
    all_files: List[Tuple[Path, Path]],
    included_files: List[Tuple[Path, Path]],
    roots: List[Path],
    import_map: Dict[Path, Set[Path]]
) -> str:
    manifest = ["# 🗺️ Code & Structure Manifest",
                "これはプロジェクト全体の構造と主要コンポーネントの概要を示す設計図です。"]
    manifest.append("\n## 🌳 プロジェクト全体ディレクトリ構造")
    manifest.append("`[INCLUDED]` は本パックに含まれる主要ファイル。")
    included_paths = {p for _, p in included_files}
    primary_root = roots[0] if roots else Path('.')
    tree_dict: Dict[str, Any] = {}
    for r, f in all_files:
        node = tree_dict
        try:
            rel_path = f.relative_to(primary_root) if f.is_relative_to(primary_root) else Path(r.name) / f.relative_to(r)
            parts = rel_path.parts
            for part in parts:
                node = node.setdefault(part, {})
        except ValueError: continue
    lines = [f"{primary_root.name}/"]
    def build_tree(d, prefix="", current_path=Path()):
        items = sorted(d.keys())
        for i, name in enumerate(items):
            is_last = (i == len(items) - 1)
            connector = "└── " if is_last else "├── "
            new_path = current_path / name
            full_path_to_check = primary_root / new_path
            mark = " [INCLUDED]" if full_path_to_check in included_paths else ""
            lines.append(f"{prefix}{connector}{name}{mark}")
            if d[name]:
                new_prefix = prefix + ("    " if is_last else "│   ")
                build_tree(d[name], new_prefix, new_path)
    build_tree(tree_dict)
    manifest.append("```\n" + "\n".join(lines) + "\n```")
    manifest.append("\n## 🧩 主要コンポーネント要約")
    py_files = sorted([(r, p) for r, p in all_files if p.suffix == '.py'],
                      key=lambda x: loc_count(x[1]), reverse=True)
    for root, py_path in py_files[:20]:
        try:
            rel_path = py_path.relative_to(root)
            manifest.append(f"\n### 📄 `{rel_path}`")
            source = py_path.read_text("utf-8", "ignore")
            tree = ast.parse(source)
            docstring = ast.get_docstring(tree)
            if docstring: manifest.append(f"> {docstring.strip().splitlines()[0]}")
            summary = [f"- **class** `{n.name}`" for n in tree.body if isinstance(n, ast.ClassDef)] + \
                      [f"- **def** `{n.name}()`" for n in tree.body if isinstance(n, ast.FunctionDef)]
            if summary: manifest.extend(summary)
        except Exception: manifest.append("- *解析中にエラー*")
    return "\n".join(manifest)

# ======================================================================
# エクスポート本体
# ======================================================================

def _bytes_from_mb(mb: float) -> int:
    return int(mb * 1024 * 1024)

def _copy_to_manifest_folder(base_dir: Path, roots: List[Path],
                             included_files: List[Tuple[Path, Path]],
                             chronicle_md: str,
                             manifest_md: str,
                             readme_md: str) -> Path:
    base_dir.mkdir(parents=True, exist_ok=True)
    (base_dir / "README.md").write_text(readme_md, encoding="utf-8")
    (base_dir / "PROJECT_CHRONICLE.md").write_text(chronicle_md, encoding="utf-8")
    (base_dir / "CODE_STRUCTURE_MANIFEST.md").write_text(manifest_md, encoding="utf-8")
    (base_dir / "included_source").mkdir(parents=True, exist_ok=True)
    for root, file_path in included_files:
        try:
            try:
                rel = file_path.relative_to(root)
                dst = base_dir / "included_source" / rel
            except ValueError:
                dst = base_dir / "included_source" / root.name / file_path.relative_to(root)
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(file_path, dst)
        except Exception: continue
    return base_dir

def export_for_gemini(roots: List[Path], profile_name: str,
                      size_profile: str, custom_target_mb: float,
                      dry_run: bool, log_verbosity: str,
                      progress: gr.Progress) -> Tuple[List[Path], str]:
    progress(0, desc=f"エクスポート開始 ({profile_name})")

    # --- v6.2 Logger Setup ---
    log_buffer: List[str] = []
    _log_cnt = 0
    def log_step(msg: str):
        nonlocal _log_cnt
        if log_verbosity == "silent": return
        emit = (log_verbosity == "detail") or (_log_cnt % 10 == 0)
        if emit and len(log_buffer) < MAX_LOG_LINES:
            log_buffer.append(msg)
        elif len(log_buffer) == MAX_LOG_LINES:
            log_buffer.append("... (log truncated)")
        _log_cnt += 1

    # --- v6.2 Profile & Policy ---
    if size_profile == "Gemini (≤10MB)":
        profile_key = "gemini_10mb"
        manifest_target_mb = 10.0
        allow_ipynb = False
        json_delay_threshold = 256 * 1024
    elif size_profile == "GPT-5 (≤50MB)":
        profile_key = "gpt5_50mb"
        manifest_target_mb = 50.0
        allow_ipynb = True
        json_delay_threshold = 1024 * 1024
    else:
        profile_key = "custom"
        manifest_target_mb = max(1.0, float(custom_target_mb or 24.0))
        allow_ipynb = True
        json_delay_threshold = 512 * 1024

    profile = PROFILES[profile_name]
    export_mode = profile["mode"]
    manifest_target_bytes = _bytes_from_mb(manifest_target_mb)

    # --- v6.2 Cleaning ---
    project_prefix = generate_project_prefix(roots)
    base_root = roots[0]
    export_root_dir = base_root / EXPORT_DIR_NAME
    if not dry_run:
        shutil.rmtree(export_root_dir, ignore_errors=True)
        export_root_dir.mkdir(parents=True, exist_ok=True)

    # 1) スコアリング収集
    all_scored_files_with_root = []
    for i, root in enumerate(roots):
        class SubProgress:
            def __init__(self, base, total): self.base, self.total = base, total
            def __call__(self, val, desc=""): progress(self.base + val * self.total, desc=desc)
        sub_progress = SubProgress(i / len(roots) * 0.7, 0.7 / len(roots))
        scored = collect_and_score_files(root, profile_key, sub_progress)
        all_scored_files_with_root.extend([(s, root, p) for s, p in scored])
    all_scored_files_with_root.sort(key=lambda t: t[0], reverse=True)

    final_files = [(r, p) for _, r, p in all_scored_files_with_root]
    if not final_files: raise RuntimeError("対象ファイルが見つかりませんでした。")

    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    progress(0.75, desc="メタデータ生成中...")
    chronicle_md = ChronicleGenerator(roots).generate()
    created_zips: List[Path] = []

    if export_mode == "manifest":
        picked: List[Tuple[Path, Path]] = []
        seen: Set[Path] = set()

        def priority_key(item):
            score, root, path = item
            sz = path.stat().st_size if path.exists() else 0
            late = (not allow_ipynb and path.suffix.lower() == ".ipynb") or \
                   (path.suffix.lower() == ".json" and sz > json_delay_threshold)
            return (1 if (path.name in KEEP_FILES and path.parent == root) else 2,
                    1 if path.suffix.lower() == ".py" else (3 if not late else 4), -score, sz)
        primary = sorted(all_scored_files_with_root, key=priority_key)

        def iter_fallback_files():
            rules = PROFILE_RULES[profile_key]
            fallback_max_bytes = rules["fallback_binary_max_bytes"]
            if fallback_max_bytes <= 0: return
            yielded: Set[Path] = set()
            for r in roots:
                patterns = load_gitignore(r)
                for p in r.rglob("*"):
                    if not p.is_file() or p in yielded: continue
                    if path_is_ignored(p, r, export_root_dir, profile_key, patterns): continue
                    ext = p.suffix.lower()
                    try: sz = p.stat().st_size
                    except Exception: continue
                    if ext in TEXT_EXTS: yielded.add(p); yield (0.0, r, p)
                    elif ext in FALLBACK_BINARY_EXTS and sz <= fallback_max_bytes:
                        yielded.add(p); yield (0.0, r, p)

        target = int(manifest_target_bytes * 1.05)
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            readme_md = create_readme_md(project_prefix, profile_name)
            py_files_all = [p for _, p in final_files if p.suffix == ".py"]
            import_map = build_import_map(roots[0], py_files_all) if roots else {}
            manifest_md_tmp = create_code_structure_manifest_md(final_files, [], roots, import_map)
            zf.writestr("README.md", readme_md); zf.writestr("PROJECT_CHRONICLE.md", chronicle_md)
            zf.writestr("CODE_STRUCTURE_MANIFEST.md", manifest_md_tmp)
            log_step(f"[INIT] ZIP = {buf.tell()/MB:.2f} MB")

            def try_add(root: Path, path: Path) -> bool:
                if not path.exists() or path in seen: return False
                try:
                    arcname = Path("included_source") / (path.relative_to(root) if path.is_relative_to(root) else Path(root.name) / path.relative_to(root))
                    arc_str = str(arcname).replace("\\", "/")
                    zf.write(path, arc_str)
                    picked.append((root, path)); seen.add(path)
                    log_step(f"+ {arc_str}  →  {buf.tell()/MB:.2f} MB")
                    return True
                except Exception: return False

            for _, root, path in primary:
                if len(picked) >= MANIFEST_INCLUDED_FILES_MAX: break
                if try_add(root, path) and buf.tell() >= target: break

            if buf.tell() < int(manifest_target_bytes * 0.98):
                for _, root, path in iter_fallback_files():
                    if len(picked) >= MANIFEST_INCLUDED_FILES_MAX: break
                    if try_add(root, path) and buf.tell() >= target: break

            final_manifest = create_code_structure_manifest_md(final_files, picked, roots, import_map)
            zf.writestr("CODE_STRUCTURE_MANIFEST.md", final_manifest)

        if dry_run:
            preview = f"🔎 ドライラン結果: 推定ZIP {buf.tell()/MB:.2f} MB / 追加ファイル {len(picked)} 件"
            top_samples = "\n".join([f"- {p[1]}" for p in picked[:10]])
            log_buffer.insert(0, preview + "\n≪サンプル（先頭10件）≫\n" + top_samples)
            return [], "\n".join(log_buffer)

        out_dir = export_root_dir / f"{project_prefix}_manifest_{ts}"
        _copy_to_manifest_folder(out_dir, roots, picked, chronicle_md, final_manifest, readme_md)
        zip_path = export_root_dir / f"{project_prefix}_gemini_{ts}.zip"
        with open(zip_path, "wb") as f: f.write(buf.getvalue())
        created_zips.append(zip_path)

    else: # Structured / Legacy
        if dry_run: return [], "⚠️ ドライランは Structured/Legacy では未対応です。"
        # ... (Structured/Legacy logic remains the same)

    progress(1.0, desc="エクスポート完了!")
    return created_zips, "\n".join(log_buffer)

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
        zip_paths, logs = export_for_gemini(
            roots, profile_name, size_profile, custom_target_mb, dry_run, log_verbosity, progress
        )
        if stop_event.is_set(): return None, "⏹️ キャンセルされました。"
        total_mb = sum(p.stat().st_size for p in zip_paths) / MB if zip_paths else 0.0
        output_files_str = "\n".join([str(p) for p in zip_paths]) if zip_paths else "(ドライランのため出力なし)"
        hdr = f"✅ エクスポート完了" if not dry_run else "👁‍🗨 プレビュー完了"
        msg = f"{hdr} ({profile_name}, target={size_profile if size_profile!='Custom' else f'Custom {custom_target_mb:.1f}MB'})\n"
        msg += f"- {len(zip_paths)}個のZIP (合計 {total_mb:.2f} MB)\n\n出力先:\n{output_files_str}"
        if logs: msg += f"\n\n--- LOG ---\n{logs}"
        return [str(p) for p in zip_paths] if zip_paths else None, msg
    except Exception as e:
        return None, f"❌ エラーが発生しました:\n{e}\n\n詳細:\n{traceback.format_exc(limit=3)}"

def create_interface():
    with gr.Blocks(title="Code Export for Gemini (Hybrid)", theme=gr.themes.Soft()) as demo:
        gr.Markdown("# 🤖 Gemini対応コードエクスポート (Manifest強化＋サイズプロファイル)")
        gr.Markdown("`Manifest / Structured / Legacy` から選択。Manifestは**フォルダ＋ZIP**を同時生成し、**目標サイズ**まで主要ファイルを自動同梱します。")

        dirs_tb = gr.Textbox(label="📁 プロジェクトフォルダ", value=str(Path.cwd()), lines=1)
        profile_dd = gr.Dropdown(label="🎯 分析プロファイル", choices=list(PROFILES.keys()), value=DEFAULT_PROFILE)
        size_profile_dd = gr.Dropdown(label="📦 アップロード先ターゲット", choices=["Gemini (≤10MB)", "GPT-5 (≤50MB)", "Custom"], value="Gemini (≤10MB)")
        custom_target = gr.Number(label="Custom 目標サイズ (MB)", value=24.0, precision=1, visible=False)
        with gr.Row():
            dry_run_chk = gr.Checkbox(label="ドライラン（プレビューのみ）", value=False)
            verbose_log_chk = gr.Checkbox(label="詳細ログ（サイズ推移を表示）", value=False) # Default OFF
        profile_info = gr.Markdown(f"**説明:** {PROFILES[DEFAULT_PROFILE]['description']}")

        def update_info(name): return gr.update(value=f"**説明:** {PROFILES[name]['description']}")
        profile_dd.change(update_info, inputs=profile_dd, outputs=profile_info)
        def on_size_profile_change(sp): return gr.update(visible=(sp == "Custom"))
        size_profile_dd.change(on_size_profile_change, inputs=size_profile_dd, outputs=custom_target)

        with gr.Row():
            exp_btn = gr.Button("🚀 エクスポート開始", variant="primary", size="lg")
            cancel_btn = gr.Button("⏹️ キャンセル")
        zip_out = gr.File(label="📦 ダウンロード", file_count="multiple")
        status = gr.Textbox(label="📋 ステータス", lines=10, show_copy_button=True)

        export_event = exp_btn.click(
            fn=run_export_wrapper,
            inputs=[dirs_tb, profile_dd, size_profile_dd, custom_target, dry_run_chk, verbose_log_chk],
            outputs=[zip_out, status]
        )
        def on_cancel(): stop_event.set(); return "⏹️ キャンセル処理を開始しました。"
        cancel_btn.click(fn=on_cancel, cancels=[export_event], outputs=[status])
    return demo

if __name__ == "__main__":
    app = create_interface()
    app.launch(inbrowser=True, server_name="127.0.0.1", server_port=7860)
