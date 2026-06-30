"""brownfield orchestrator 共通ユーティリティ・定数・IO ヘルパー。

旧 brownfield_orchestrator.py (commit 8e39d984 時点) から
定数・共通ヘルパー・stream_run・detect_latest_snapshot・orchestrator adapter を
分割・転記したもの。関数本体のロジックは一切変更していない（振る舞い保存）。
変更点は (a) import 文の再編成 (b) 定数の REPO_ROOT 化（HERE 廃止）のみ。
"""
from __future__ import annotations
import os, sys, json, shlex, shutil, argparse, subprocess, zipfile
import threading, queue, time, traceback, importlib, importlib.util
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Tuple, Callable, Generator, Optional, Union

# ---------- 定数 --------------------------------------------------------------
JST = timezone(timedelta(hours=9))

# 本ファイル物理位置基準。symlink/zipapp では要再考。
PACKAGE_DIR = Path(__file__).resolve().parent              # brownfield/
REPO_ROOT   = PACKAGE_DIR.parents[1]                        # brownfield -> tools -> repo root
PROJECT_TOP = REPO_ROOT
SRC_DIR     = REPO_ROOT / "src"
TOOLS_DIR   = REPO_ROOT / "tools"
ORCHESTRATOR_MODULE_NAME = "nexuscore.core.orchestrator"

PICKER_ROOT = Path(os.getenv("NEXUS_BROWNFIELD_PICKER_ROOT", str(PROJECT_TOP.parent))).resolve()
PHASE_KEYS = ["structure", "snapshot", "unified", "graphs", "history", "quality", "ai_export"]
DEFAULT_PROFILES = ["gemini-single-file", "gpt5-zip"]
DEFAULT_OUT = REPO_ROOT / "brownfield_snapshots"

# ---------- 共通ヘルパー ------------------------------------------------------
def now_tag() -> str:
    return datetime.now(JST).strftime("%Y-%m-%d_%H-%M-%S_JST")

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

# ---------- スナップショット検出 ----------------------------------------------
def detect_latest_snapshot(out_root: str) -> str:
    root = Path(out_root)
    if not root.exists(): return ""
    dirs = [p for p in root.iterdir() if p.is_dir()]
    return str(sorted(dirs, key=lambda p: p.name, reverse=True)[0]) if dirs else ""

# ---------- orchestrator adapter ----------------------------------------------
def is_orchestrator_importable() -> bool:
    """adapter: 外部モジュル nexuscore.core.orchestrator の importability を検証。"""
    if str(SRC_DIR) not in sys.path: sys.path.insert(0, str(SRC_DIR))
    if str(PROJECT_TOP) not in sys.path: sys.path.insert(0, str(PROJECT_TOP))
    try:
        spec = importlib.util.find_spec(ORCHESTRATOR_MODULE_NAME)
        return spec is not None
    except Exception:
        return False

def run_orchestrator_cli(latest: str, autonomy: str, budget: str, branch: str, qgates: str, policy: str):
    """adapter: orchestrator を `python -m` CLI でストリーム実行。"""
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
    """adapter: orchestrator を in-process で import & call 実行（CLI フォールバック先）。"""
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
