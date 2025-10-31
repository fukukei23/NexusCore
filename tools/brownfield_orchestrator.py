# ==============================================================================
# 操作するソフト: VSCode (または任意のテキストエディタ)
# ファイル名 : brownfield_orchestrator.py
# レジストリ : tools/
# バージョン : v2.13 (Robust Subprocess Execution)
# 日付/時刻 : 2025-09-20 08:35 (JST)
#
# 目的:
#   既存システム（Brownfield）の「構造 & 履歴の見える化」と、
#   後続の「自動化サイクル」実行を単一のUI/CLIから操作できる統合ツール。
#
# 改修内容 (v2.13):
#   - `subprocess.Popen` を `shell=False` と引数リスト形式に変更し、
#     Windowsでの特殊文字を含む引数渡し問題を根本的に解消。
#   - 実行引数リスト(`repr`)を診断ログに出力し、デバッグ能力を向上。
#   - 文字エンコーディングを `utf-8` に固定し、Windowsでの日本語エラーメッセージの
#     文字化けを確実に防止。
#
# 搭載機能（継続）:
#   - ✅ モジュールベース実行 (v2.12)
#   - ✅ 単方向フォールバックロジック (v2.11)
#   - ✅ スナップショット収集粒度制御 (v2.9)
#   - ✅ UIログのターミナルミラーリング (v2.8)
#   - ✅ 他、全機能
#
# 使用方法:
#   ターミナルでプロジェクトルートに移動し、以下を実行してUIを起動。
#   python tools/brownfield_orchestrator.py --ui
# ==============================================================================

from __future__ import annotations

import os
import sys
import json
import shlex
import shutil
import argparse
import subprocess
import zipfile
import threading, queue, time, traceback, importlib
import importlib.util
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Tuple, Callable, Generator, Optional, Union

# ---------- 共通 ---------------------------------------------------------------
JST = timezone(timedelta(hours=9))
def now_tag() -> str:
    return datetime.now(JST).strftime("%Y-%m-%d_%H-%M-%S_JST")

HERE = Path(__file__).resolve()
PROJECT_TOP = HERE.parents[1]
SRC_DIR = PROJECT_TOP / "src"
TOOLS_DIR = PROJECT_TOP / "tools"
ORCHESTRATOR_MODULE_NAME = "nexuscore.core.orchestrator"

PICKER_ROOT = Path(os.getenv("NEXUS_BROWNFIELD_PICKER_ROOT", str(PROJECT_TOP.parent))).resolve()

PHASE_KEYS = ["structure", "snapshot", "unified", "graphs", "history", "quality", "ai_export"]
DEFAULT_PROFILES = ["gemini-single-file", "gpt5-zip"]
DEFAULT_OUT = PROJECT_TOP / "brownfield_snapshots"

def candidate_paths(name: str) -> List[Path]:
    cands = [TOOLS_DIR / name, PROJECT_TOP / "src" / "nexuscore" / "tools" / name]
    return [p for p in cands if p.exists()]

def phase_cmd(script: Path, args: List[str]) -> List[str]:
    return [sys.executable, str(script)] + args

# ---------- policy_profile メタ ------------------------------------------------
def _read_json_safe(p: Path) -> Dict[str, str]:
    try:
        if p.exists(): return json.loads(p.read_text(encoding="utf-8"))
    except Exception: pass
    return {}

def load_policy_meta() -> Dict[str, str]:
    for p in [PROJECT_TOP / "src" / "nexuscore" / "gradio_app" / ".nexus_context.json", PROJECT_TOP / ".nexus_context.json"]:
        d = _read_json_safe(p)
        if any(k in d for k in ("policy_profile", "policy_version", "policy_icon")):
            return {"policy_profile": str(d.get("policy_profile", "general")), "policy_version": str(d.get("policy_version", "v1")), "policy_icon": str(d.get("policy_icon", "🏷️"))}
    env_prof, env_ver, env_icon = os.getenv("NEXUS_POLICY_PROFILE"), os.getenv("NEXUS_POLICY_VERSION"), os.getenv("NEXUS_POLICY_ICON")
    if any([env_prof, env_ver, env_icon]):
        return {"policy_profile": env_prof or "general", "policy_version": env_ver or "v1", "policy_icon": env_icon or "🏷️"}
    return {"policy_profile": "general", "policy_version": "v1", "policy_icon": "🏷️"}

def inject_policy_meta_to_manifest(snap_dir: Path, meta: Dict[str, str]) -> None:
    m = snap_dir / "manifest.json"
    if not m.exists(): return
    try:
        data = json.loads(m.read_text(encoding="utf-8"))
        data.setdefault("policy_profile", meta.get("policy_profile", "general"))
        data.setdefault("policy_version", meta.get("policy_version", "v1"))
        data.setdefault("policy_icon",    meta.get("policy_icon", "🏷️"))
        m.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception: pass

# ---------- ストリーム実行ユーティリティ --------------------------------------
def stream_run(cmd: Union[List[str], str], cwd: Path) -> Generator[str, None, Tuple[bool, str]]:
    """サブプロセスの出力をリアルタイムで返し、ターミナルにも同時に出力する"""
    env = os.environ.copy()
    # PYTHONPATH を設定して、src ディレクトリ内のモジュールを見つけられるようにする
    python_path_entries = [str(SRC_DIR), str(PROJECT_TOP)]
    existing_python_path = env.get("PYTHONPATH")
    if existing_python_path:
        python_path_entries.extend(existing_python_path.split(os.pathsep))
    env["PYTHONPATH"] = os.pathsep.join(python_path_entries)

    use_shell = isinstance(cmd, str)
    proc = subprocess.Popen(cmd, cwd=str(cwd), shell=use_shell, text=True, encoding='utf-8', errors='replace',
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, bufsize=1, env=env)
    collected: List[str] = []
    try:
        if proc.stdout:
            for line in iter(proc.stdout.readline, ""):
                sys.stdout.write(line)
                sys.stdout.flush()
                collected.append(line)
                yield line
        proc.wait()
    finally:
        try:
            if proc.stdout: proc.stdout.close()
        except Exception: pass
    out = "".join(collected)
    ok = (proc.returncode == 0)
    return (ok, out)

# ---------- オーケストレーション（共通コア） ----------------------------------
def run_brownfield_stream(
    project_root: str, out_root: str, profiles: List[str], selected_phases: List[str],
    policy_profile_ui: str, policy_version_ui: str, policy_icon_ui: str,
    richness_mode: str, include_full_archive: bool,
) -> Generator[Tuple[str, str, Optional[str]], None, None]:
    log_buf: List[str] = []; snap_dir: Optional[Path] = None; emitted = False
    def emit(line: str, summary: str = "", zip_path: Optional[str] = None):
        print(line, end='', flush=True)
        nonlocal emitted; log_buf.append(line); emitted = True
        yield ("".join(log_buf), summary, zip_path)
    try:
        project_root_path = Path(project_root).resolve()
        if project_root_path.is_file(): project_root_path = project_root_path.parent
        out_root_path = Path(out_root).resolve(); out_root_path.mkdir(parents=True, exist_ok=True)
        base_meta = load_policy_meta()
        if policy_profile_ui.strip(): base_meta["policy_profile"] = policy_profile_ui.strip()
        if policy_version_ui.strip(): base_meta["policy_version"] = policy_version_ui.strip()
        if policy_icon_ui.strip():    base_meta["policy_icon"] = policy_icon_ui.strip()
        tag = now_tag(); snap_dir = out_root_path / tag
        for sub in PHASE_KEYS: (snap_dir / sub).mkdir(parents=True, exist_ok=True)
        manifest = {"snapshot_tag": tag, "project_root": str(project_root_path), "generated_at": datetime.now(JST).isoformat(), "phases": {}, "tool_root": str(PROJECT_TOP), "orchestrator": f"brownfield_orchestrator.py@v2.13", "richness_mode": richness_mode, "full_source_archive_included": include_full_archive}
        (snap_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        run_set = set(selected_phases or PHASE_KEYS)
        richness_arg = ["--richness-level", richness_mode] if richness_mode != "Light (fast)" else []
        def _do_phase(key: str, script_name: str, args_builder: Callable[[Path], List[str]]):
            if key not in run_set:
                manifest["phases"][key] = {"status": "skipped", "reason": "user-specified"}
            else:
                paths = candidate_paths(script_name)
                if not paths:
                    manifest["phases"][key] = {"status":"skipped","reason":f"{script_name} not found"}
                else:
                    save_dir = snap_dir / key
                    log_path = save_dir / f"{script_name.replace('.py','')}.log"
                    final_args = args_builder(save_dir) + richness_arg
                    cmd_list = phase_cmd(paths[0], final_args)
                    yield from emit(f"\n--- [{key}] {' '.join(shlex.quote(x) for x in cmd_list)}\n")
                    gen = stream_run(cmd_list, cwd=PROJECT_TOP); ok, out_text = False, ""
                    try:
                        while True: yield from emit(next(gen))
                    except StopIteration as si: ok, out_text = si.value
                    except Exception as e:
                        tb_str = f"[phase-exception] {e}\n{traceback.format_exc()}"
                        ok, out_text = False, tb_str; yield from emit(out_text)
                    log_path.write_text(out_text, encoding="utf-8")
                    manifest["phases"][key] = {"status": "ok" if ok else "error", "script": str(paths[0]), "output_dir": str(save_dir), "log": str(log_path)}
            (snap_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        yield from emit("スナップショット作成を開始します...\n")
        _do_phase("structure", "export_structure.py", lambda s: [str(project_root_path)])
        _do_phase("snapshot", "project_structure_and_code_export.py", lambda s: ["--root", str(project_root_path), "--out", str(s)])
        _do_phase("unified", "unified_analyzer.py", lambda s: ["--root", str(project_root_path), "--out", str(s)])
        _do_phase("graphs", "graph_builder.py", lambda s: ["--root", str(project_root_path), "--out", str(s)])
        _do_phase("history", "genesis_analyzer.py", lambda s: ["--root", str(project_root_path), "--out", str(s)])
        _do_phase("quality", "code_analyzer.py", lambda s: ["--root", str(project_root_path), "--out", str(s)])
        _do_phase("ai_export", "code_export_for_ai.py", lambda s: sum([["--root", str(project_root_path), "--out", str(s / p), "--profile", p] for p in (profiles or DEFAULT_PROFILES)], []))
    except Exception as e:
        yield from emit(f"\n[CRITICAL ERROR] 解析プロセスで重大な例外が発生しました:\n{e}\n{traceback.format_exc()}")
    finally:
        if snap_dir and snap_dir.exists():
            if include_full_archive:
                yield from emit("\nソースコード全体のアーカイブを作成しています...（時間がかかる場合があります）\n")
                archive_path = snap_dir / "_source_archive.zip"
                exclude_dirs = {'.git', '.idea', '.vscode', '__pycache__', 'venv', 'node_modules', 'dist', 'build'}
                try:
                    with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                        for root, dirs, files in os.walk(project_root_path):
                            dirs[:] = [d for d in dirs if d not in exclude_dirs]
                            for file in files:
                                file_path = Path(root) / file
                                zf.write(file_path, file_path.relative_to(project_root_path))
                    manifest_path = snap_dir / "manifest.json"
                    if manifest_path.exists():
                        data = json.loads(manifest_path.read_text(encoding="utf-8"))
                        data["full_source_archive"] = {"path": str(archive_path.relative_to(snap_dir)), "size_bytes": archive_path.stat().st_size}
                        manifest_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
                    yield from emit(f"ソースコードのアーカイブが完了しました: {archive_path}\n")
                except Exception as e:
                    yield from emit(f"[ERROR] ソースコードのアーカイブ作成に失敗しました: {e}\n")
            def summarize_snapshot(p: Path) -> str:
                m = p / "manifest.json"; r = p / "README.md"; lines: List[str] = [f"### 📁 Snapshot: `{p.name}`"]
                if m.exists():
                    try:
                        d = json.loads(m.read_text(encoding="utf-8"))
                        lines.extend([f"- richness_mode: `{d.get('richness_mode','N/A')}`"])
                        if d.get("full_source_archive_included"): lines.append(f"- full_source_archive: ✅ Included (`_source_archive.zip`)")
                        lines.extend([f"- generated_at: `{d.get('generated_at','')}`", f"- project_root: `{d.get('project_root','')}`"])
                        if d.get("policy_profile"): lines.append(f"- policy: {d['policy_profile']} ({d.get('policy_version','v?')}) {d.get('policy_icon','')}")
                        lines.append("- phases:"); [lines.append(f"  - {k}: {v.get('status','')}") for k, v in (d.get("phases") or {}).items()]
                    except Exception: lines.append("- manifest.json: 解析失敗")
                lines.append("\n#### 主要フォルダ"); [lines.append(f"- `{d}`") for s in PHASE_KEYS if (d := p / s).exists()]
                return "\n".join(lines)
            inject_policy_meta_to_manifest(snap_dir, load_policy_meta())
            (snap_dir / "README.md").write_text(f"# Brownfield Snapshot ({snap_dir.name})\n- generated_at: {datetime.now(JST).isoformat()}\n- project_root: {project_root}\nこのスナップショットは、既存システムの構造/履歴/品質/AIエクスポートをまとめたものです。", encoding="utf-8")
            summary_md = summarize_snapshot(snap_dir); zip_path: Optional[str] = None
            try:
                yield from emit("\nスナップショットをZIPファイルに圧縮しています...\n")
                zip_path = str(shutil.make_archive(str(snap_dir), "zip", root_dir=str(snap_dir)))
                yield from emit("圧縮が完了しました。\n", summary_md, zip_path)
            except Exception as e: yield from emit(f"\n[ERROR] ZIPファイルの作成に失敗しました:\n{e}\n", summary_md)
            yield from emit("\n[OK] 全ての処理が完了しました。\n", summary_md, zip_path)
        elif not emitted:
            yield from emit("\n[ERROR] 初期化に失敗し、処理を開始できませんでした。\n")

# ---------- UI ---------------------------------------------------------------
def try_build_dir_picker():
    try: from gradio import FileExplorer; return FileExplorer
    except Exception: return None

def detect_latest_snapshot(out_root: str) -> str:
    root = Path(out_root)
    if not root.exists(): return ""
    dirs = [p for p in root.iterdir() if p.is_dir()]
    return str(sorted(dirs, key=lambda p: p.name, reverse=True)[0]) if dirs else ""

def is_orchestrator_importable() -> bool:
    if str(SRC_DIR) not in sys.path: sys.path.insert(0, str(SRC_DIR))
    if str(PROJECT_TOP) not in sys.path: sys.path.insert(0, str(PROJECT_TOP))
    try:
        spec = importlib.util.find_spec(ORCHESTRATOR_MODULE_NAME)
        return spec is not None
    except Exception:
        return False

# ---------- Orchestrator Runners ---------------------------------------
def run_orchestrator_cli(latest: str, autonomy: str, budget: str, branch: str, qgates: str, policy: str):
    importable = is_orchestrator_importable()
    yield f"診断: Python実行パス: {sys.executable}\n"
    yield f"診断: CWDターゲット: {PROJECT_TOP}\n"
    yield f"診断: Orchestratorモジュール: {ORCHESTRATOR_MODULE_NAME} (Importable: {importable})\n"
    if not importable:
        yield f"[orchestrator][CLI] [FATAL] 実行モジュール '{ORCHESTRATOR_MODULE_NAME}' が見つかりません。\n"; return
    
    cmd_list = [sys.executable, "-m", ORCHESTRATOR_MODULE_NAME, "--baseline", latest]
    if policy.strip():   cmd_list.extend(["--policy-profile", policy.strip()])
    if autonomy.strip(): cmd_list.extend(["--autonomy-level", autonomy.strip()])
    if budget.strip():   cmd_list.extend(["--budget-usd", budget.strip()])
    if branch.strip():   cmd_list.extend(["--branch", branch.strip()])
    if qgates.strip():   cmd_list.extend(["--quality-gates", qgates.strip()])
    
    yield f"診断: 実行引数リスト (repr): {repr(cmd_list)}\n"
    yield f"[orchestrator][CLI] 実行コマンド (表示用):\n> {' '.join(shlex.quote(x) for x in cmd_list)}\n\n"
    
    gen = stream_run(cmd_list, cwd=PROJECT_TOP)
    try:
        while True: yield next(gen)
    except StopIteration as si:
        ok, full = si.value
        yield f"\n[orchestrator][CLI] 完了 (Exit Code: {'0' if ok else 'Non-zero'})\n";
        if full and not ok: yield full

def run_orchestrator_func(latest: str, autonomy: str, budget: str, branch: str, qgates: str, policy: str):
    try:
        if not is_orchestrator_importable():
            yield f"[orchestrator][FUNC] [FATAL] 実行モジュール '{ORCHESTRATOR_MODULE_NAME}' が見つかりません。\n"; return

        mod = importlib.import_module(ORCHESTRATOR_MODULE_NAME); importlib.reload(mod)
        target = next((getattr(mod, name) for name in ["run_cycle", "run_full_project", "main_entry"] if hasattr(mod, name)), None)
        if target is None:
            yield "[orchestrator][FUNC] [FATAL] 実行可能なエントリポイント (run_cycle等) が見つかりません。\n"; return

        q: queue.Queue[str] = queue.Queue()
        def _runner():
            try:
                kwargs = {"baseline": latest}; import inspect
                if autonomy: kwargs["autonomy_level"] = autonomy
                if budget:   kwargs["budget_usd"] = budget
                if branch:   kwargs["branch"] = branch
                if qgates:   kwargs["quality_gates"] = qgates
                if policy:   kwargs["policy_profile"] = policy
                valid_kwargs = {k: v for k, v in kwargs.items() if k in inspect.signature(target).parameters}
                ret = target(**valid_kwargs)
                if hasattr(ret, "__iter__") and not isinstance(ret, (dict, str)):
                    for msg in ret: q.put(str(msg))
                else: q.put(f"[orchestrator][FUNC] done: {ret}")
            except Exception: q.put("[orchestrator][FUNC] 例外発生:\n" + traceback.format_exc())
            finally: q.put("__END__")
        th = threading.Thread(target=_runner, daemon=True); th.start()
        yield f"[orchestrator][FUNC] モジュール '{ORCHESTRATOR_MODULE_NAME}' の import & call を開始\n"
        while True:
            try:
                msg = q.get(timeout=0.2)
                if msg == "__END__": yield "\n[orchestrator][FUNC] 完了\n"; break
                yield msg if msg.endswith("\n") else (msg + "\n")
            except queue.Empty: time.sleep(0.1)
    except Exception:
        yield "[orchestrator][FUNC] 重大な例外:\n" + traceback.format_exc()

def build_ui():
    import gradio as gr
    FileExplorer = try_build_dir_picker()
    with gr.Blocks(title="Brownfield Orchestrator — One-click UI", theme=gr.themes.Soft()) as demo:
        gr.Markdown("# 🧰 Brownfield Orchestrator — One-click UI (All-in)")
        with gr.Tabs():
            with gr.TabItem("1. スナップショット作成"):
                gr.Markdown("既存システムの **構造 & 履歴の見える化** をワンクリックで実行し、成果物を保存・ZIPダウンロードできます。")
                with gr.Row():
                    with gr.Column(scale=1):
                        if FileExplorer:
                            picker = FileExplorer(label="解析対象プロジェクト（フォルダ/ファイル複数選択可）", root_dir=str(PICKER_ROOT), file_count="multiple")
                            project_root_tb = gr.Textbox(label="最終的に解析されるルート（自動計算/手動修正可）", value=str(PICKER_ROOT), lines=1)
                            def _sync_picker(selection):
                                from pathlib import Path; import os as _os
                                if not selection: return str(PICKER_ROOT)
                                _ps = [Path(p).resolve() for p in selection if p]
                                if not _ps: return str(PICKER_ROOT)
                                return str(Path(_os.path.commonpath([str(p if p.is_dir() else p.parent) for p in _ps])))
                            picker.change(_sync_picker, inputs=picker, outputs=project_root_tb)
                        else: project_root_tb = gr.Textbox(label="解析対象プロジェクトのルートパス（手入力）", value=str(PICKER_ROOT), lines=1)
                        out_root = gr.Textbox(label="スナップショット出力先（親フォルダ）", value=str(DEFAULT_OUT), lines=1)
                        with gr.Accordion("詳細設定", open=False):
                            richness_dd = gr.Dropdown(label="収集モード (Code Richness)", choices=["Light (fast)", "Code-Rich (more .py)"], value="Light (fast)", info="収集するソースコードの量を調整します。")
                            full_archive_cb = gr.Checkbox(label="ソースコード全体のアーカイブを含める (_source_archive.zip)", value=False, info="リポジトリ全体の完全なコピーをZIPで同梱します。")
                            profiles_text = gr.Textbox(label="AIエクスポート プロフィール(カンマ区切り)", value=",".join(DEFAULT_PROFILES), info="例: gemini-single-file,gpt5-zip")
                            phases = gr.CheckboxGroup(choices=PHASE_KEYS, value=PHASE_KEYS, label="実行するフェーズ（未選択はスキップ）")
                            gr.Markdown("### ポリシー・メタ（manifest に注入）")
                            policy_profile = gr.Textbox(label="policy_profile", placeholder="例: enterprise_finance（未入力なら自動検出 or general）")
                            policy_version = gr.Textbox(label="policy_version", placeholder="例: v1.3")
                            policy_icon = gr.Textbox(label="policy_icon", placeholder="例: 🏦")
                        run_btn = gr.Button("▶ 解析を実行", variant="primary")
                    with gr.Column(scale=1):
                        log_box = gr.Textbox(label="実行ログ（逐次）", lines=22)
                        summary_md = gr.Markdown(label="スナップショット概要", value="準備OK。パラメータを設定して実行してください。")
                        dl_btn = gr.DownloadButton(label="⬇ ZIPをダウンロード", value=None, visible=False)
            with gr.TabItem("2. 自動化サイクル実行"):
                gr.Markdown("### 🚀 自動化サイクル (Orchestrator 実行)")
                gr.Markdown("最新のスナップショットをベースラインとして、`nexuscore.core.orchestrator` モジュールを実行します。")
                with gr.Row():
                    with gr.Column(scale=1):
                        run_mode = gr.Radio(choices=["CLI (-m)", "Function (import)"], value="CLI (-m)", label="Run mode", info="モジュールとして実行します。まずはCLI推奨。")
                        fallback_cb = gr.Checkbox(label="CLI実行失敗時にFunctionモードへ自動フォールバック", value=True, info="モジュールが見つからない場合、Functionモードで再試行します。")
                        autonomy_dd = gr.Dropdown(label="Autonomy Level", choices=["0", "1", "2", "3", "4"], value="2", info="エージェントの自律度。2以上でブランチ作成や自動コミットが有効化されます。")
                        budget_tb = gr.Textbox(label="Budget (USD)", value="1.0")
                        branch_presets = ["feature/nx-{date}-{slug}", "chore/nx-{date}-{slug}", "hotfix/nx-{date}-{slug}", "ai-patch-{YYYYMMDD}", "カスタム..."]
                        branch_dd = gr.Dropdown(label="Branch name", choices=branch_presets, value=branch_presets[0], info="自動コミット時に使用するブランチ名の形式。")
                        branch_tb = gr.Textbox(visible=False, placeholder="カスタムブランチ名を入力")
                        def _toggle_branch_tb(selection): return gr.update(visible=(selection == "カスタム..."))
                        branch_dd.change(_toggle_branch_tb, inputs=branch_dd, outputs=branch_tb)
                        qg_presets = {"Balanced (推奨)": "test-coverage>=80,pylint>=8.0,mypy=clean", "Strict": "test-coverage>=90,pylint>=8.5,mypy=clean", "Fast Iteration": "test-coverage>=60,pylint>=7.0,mypy=warn", "カスタム...": "custom"}
                        qg_dd = gr.Dropdown(label="Quality Gates", choices=list(qg_presets.keys()), value="Balanced (推奨)", info="コード品質の自動チェック基準。")
                        qg_tb = gr.Textbox(visible=False, placeholder="例: test-coverage>=80,security-scan=ok")
                        def _toggle_qg_tb(selection): return gr.update(visible=(selection == "カスタム..."))
                        qg_dd.change(_toggle_qg_tb, inputs=qg_dd, outputs=qg_tb)
                        pol_override = gr.Textbox(label="Policy Profile (Override)", placeholder="例: security_focused_v2", info="manifest内の値を上書きする場合に指定。空欄は既存値に従います。")
                        run_cycle_btn = gr.Button("▶ 自動化サイクルを実行", variant="primary")
                    with gr.Column(scale=1):
                        log_box_cycle = gr.Textbox(label="実行ログ（逐次）", lines=20)
        def _run_snapshot(project_root: str, profiles_csv: str, selected_phases: List[str], out_root_dir: str, p_prof: str, p_ver: str, p_icon: str, richness: str, full_archive: bool):
            profiles = [s.strip() for s in (profiles_csv or "").split(",") if s.strip()]
            gen = run_brownfield_stream(project_root, out_root_dir, profiles, selected_phases, p_prof, p_ver, p_icon, richness, full_archive)
            if gen is None: yield "エラー: 解析プロセスの初期化に失敗しました。", "処理失敗", None, None; return
            for log_inc, summary, zip_path in gen: yield log_inc, (summary or gr.update()), (zip_path or None), (bool(zip_path) and zip_path or None)
        run_btn.click(fn=_run_snapshot, inputs=[project_root_tb, profiles_text, phases, out_root, policy_profile, policy_version, policy_icon, richness_dd, full_archive_cb], outputs=[log_box, summary_md, gr.State(), dl_btn])
        def _kick_orchestrator(out_root_dir: str, autonomy: str, budget: str, branch_dd_val: str, branch_tb_val: str, qg_dd_val: str, qg_tb_val: str, policy_override: str, mode: str, auto_fallback: bool):
            log_buf = []; emit = lambda line: log_buf.append(line) or "".join(log_buf)
            def tee_emit(line: str):
                print(line, end='', flush=True)
                return emit(line)
            def tee_emit_and_run(runner_gen):
                for line in runner_gen: yield tee_emit(line)

            latest = detect_latest_snapshot(out_root_dir)
            if not latest:
                yield tee_emit("[orchestrator] 最新スナップショットが見つかりません。先に解析を実行してください。\n"); return
            
            yield tee_emit(f"最新スナップショット: {latest}\n")
            manifest_path = Path(latest) / "manifest.json"; policy_from_manifest = ""
            try:
                if manifest_path.exists(): policy_from_manifest = str(json.loads(manifest_path.read_text(encoding="utf-8")).get("policy_profile", ""))
            except Exception: pass
            policy_final = (policy_override or policy_from_manifest or "").strip()
            yield tee_emit(f"使用するポリシープロファイル: {policy_final or '(default)'}\n")
            branch_final = branch_tb_val if branch_dd_val == "カスタム..." else branch_dd_val
            yield tee_emit(f"ブランチ名形式: {branch_final}\n")
            qg_final = qg_tb_val if qg_dd_val == "カスタム..." else qg_presets.get(qg_dd_val, "")
            yield tee_emit(f"品質ゲート: {qg_final}\n\n")

            runner = None
            importable = is_orchestrator_importable()

            if mode.startswith("CLI"):
                if importable:
                    runner = run_orchestrator_cli
                elif auto_fallback:
                    yield tee_emit(f"診断: CLIモード(-m)が選択されましたが、モジュール '{ORCHESTRATOR_MODULE_NAME}' が見つかりません。\n"
                                 f"-> 自動フォールバックが有効なため、Functionモードで実行します。\n\n")
                    runner = run_orchestrator_func
                else:
                    yield tee_emit(f"診断: CLIモード(-m)が選択されましたが、モジュール '{ORCHESTRATOR_MODULE_NAME}' が見つかりません。\n"
                                 f"-> 自動フォールバックが無効なため、処理を中止します。\n")
                    return
            else: # Function mode
                runner = run_orchestrator_func
            
            if runner:
                yield from tee_emit_and_run(runner(latest, autonomy, budget, branch_final, qg_final, policy_final))
            else: # Should not happen
                yield tee_emit("[FATAL] 実行モードを決定できませんでした。\n")

        run_cycle_btn.click(fn=_kick_orchestrator, inputs=[out_root, autonomy_dd, budget_tb, branch_dd, branch_tb, qg_dd, qg_tb, pol_override, run_mode, fallback_cb], outputs=log_box_cycle)
    return demo

def auto_launch_with_increment(demo, base_port: int, share: bool):
    max_tries = 20
    for i in range(max_tries + 1):
        port = base_port + i
        try:
            demo.queue().launch(server_name="0.0.0.0" if share else "127.0.0.1", server_port=port, share=share, prevent_thread_lock=False)
            print(f"[UI] Launched at http://127.0.0.1:{port} (share={share})"); return
        except OSError as e:
            if "Address already in use" in str(e): print(f"[UI] Port {port} in use. Trying next..."); continue
            raise
    raise RuntimeError(f"Failed to launch UI after {max_tries} increments from base port {base_port}.")

# ---------- エントリ -----------------------------------------------------------
def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Brownfield Orchestrator — 構造 & 履歴の見える化 (UI/CLI)")
    p.add_argument("--project-root", type=str, default=str(PICKER_ROOT), help="解析対象のプロジェクトルート（CLI時）")
    p.add_argument("--out", type=str, default=str(DEFAULT_OUT), help="スナップショット出力先（親）")
    p.add_argument("--profiles", type=str, default=",".join(DEFAULT_PROFILES), help="AIエクスポートプロフィール（CSV）")
    p.add_argument("--skip", type=str, default="", help="スキップするフェーズ（CSV）")
    p.add_argument("--policy-profile", type=str, default="", help="manifest へ注入する policy_profile（任意）")
    p.add_argument("--policy-version", type=str, default="", help="manifest へ注入する policy_version（任意）")
    p.add_argument("--policy-icon", type=str, default="", help="manifest へ注入する policy_icon（任意）")
    p.add_argument("--richness", type=str, default="Light (fast)", choices=["Light (fast)", "Code-Rich (more .py)"], help="収集するコードの量を調整")
    p.add_argument("--full-archive", action="store_true", help="ソースコード全体のアーカイブをZIPで同梱する")
    p.add_argument("--ui", action="store_true", help="Gradio UI を起動")
    return p.parse_args()

def main():
    args = parse_args()
    if args.ui:
        base_port = int(os.getenv("NEXUS_BROWNFIELD_UI_PORT", "7862"))
        share = os.getenv("NEXUS_BROWNFIELD_UI_SHARE", "0") == "1"
        demo = build_ui(); auto_launch_with_increment(demo, base_port, share)
    else:
        target = Path(args.project_root).resolve()
        if target.is_file(): target = target.parent
        out_root = Path(args.out).resolve(); out_root.mkdir(parents=True, exist_ok=True)
        profiles = [s.strip() for s in (args.profiles or "").split(",") if s.strip()] or DEFAULT_PROFILES
        skip = [s.strip() for s in (args.skip or "").split(",") if s.strip()]
        selected_phases = [p for p in PHASE_KEYS if p not in set(skip)]
        meta = load_policy_meta()
        if args.policy_profile: meta["policy_profile"] = args.policy_profile
        if args.policy_version: meta["policy_version"] = args.policy_version
        if args.policy_icon:    meta["policy_icon"] = args.policy_icon
        summary, zip_path = "", None
        gen = run_brownfield_stream(str(target), str(out_root), profiles, selected_phases, meta.get("policy_profile",""), meta.get("policy_version",""), meta.get("policy_icon",""), args.richness, args.full_archive)
        if gen:
            for _, summary, zip_path in gen: pass
        print(summary);
        if zip_path: print(f"[ZIP] {zip_path}")

if __name__ == "__main__":
    main()

