# ==============================================================================
# ファイル名 : auto_revision_runner.py
# レジストリ : src/nexuscore/gradio_app/
# バージョン : v2.7 (enterprise policy badge + full features)
# 日付/時刻 : 2025-09-12 03:55 (JST)
#
# 使い方:
#   (.venv) PS C:\Users\USER\tools\NexusCore>
#       python -m src.nexuscore.gradio_app.auto_revision_runner
#
# 概要:
#   - pytest 実行 → 自己修復ループ (最大5回) → 結果を patch_history に保存
#   - 保存JSONに policy_profile / policy_version / policy_icon を付与 (監査用バッジ)
#   - 旧テキスト履歴 (patch_history.txt / *.log) も後方互換で保存
#   - unified diff を含む完全構造体でパッチを出力
#   - sandbox_output は PROJECT_ROOT / SRC_ROOT の両方を探索
#   - 可能なら既存の revision_tab.py の関数を**自動検出**して使用（なければ安全フォールバック）
#
# Policy 情報の取得優先度 (3段階):
#   1) .nexus_context.json（gradio_app 配下を優先／次にPROJECT_ROOT直下）
#   2) 環境変数: NEXUS_POLICY_PROFILE / VERSION / ICON
#   3) デフォルト: profile="general", version="v1", icon="🏷️"
#
# 備考:
#   - JST タイムスタンプ固定
#   - 例外は patch JSON にも書き出し
# ==============================================================================

from __future__ import annotations

import os
import sys
import json
import time
import difflib
import traceback
import importlib
from pathlib import Path
from typing import Any, Dict, List, Tuple, Optional
from datetime import datetime, timezone, timedelta

# ---------- ルート推定 --------------------------------------------------------
HERE = Path(__file__).resolve()
# .../src/nexuscore/gradio_app/auto_revision_runner.py -> PROJECT_ROOT を 3階層上と定義
PROJECT_ROOT = HERE.parents[3]
SRC_ROOT = HERE.parents[2]   # .../src/nexuscore/

PATCH_DIR = PROJECT_ROOT / "patch_history"
PATCH_DIR.mkdir(parents=True, exist_ok=True)

# sandbox_output は 2系統見に行く（どちらかが有効になっていればOK）
SANDBOX_DIRS = [
    PROJECT_ROOT / "sandbox_output",
    SRC_ROOT.parent / "sandbox_output",  # .../src/sandbox_output
]
for d in SANDBOX_DIRS:
    d.mkdir(parents=True, exist_ok=True)

# ---------- JST タイムスタンプ ------------------------------------------------
JST = timezone(timedelta(hours=9))

def now_tag() -> str:
    return datetime.now(JST).strftime("%Y%m%d_%H%M%S")

def now_iso() -> str:
    return datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S%z")

# ---------- Policy 取得 (3段階フォールバック) ---------------------------------
def read_json_safe(p: Path) -> Dict[str, Any]:
    try:
        if p.exists():
            return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}

def load_policy_context() -> Dict[str, str]:
    # 1) .nexus_context.json を優先（gradio_app 配下 → PROJECT_ROOT 直下）
    ctx_paths = [
        SRC_ROOT / "gradio_app" / ".nexus_context.json",
        PROJECT_ROOT / ".nexus_context.json",
    ]
    for p in ctx_paths:
        data = read_json_safe(p)
        if any(k in data for k in ("policy_profile", "policy_version", "policy_icon")):
            return {
                "policy_profile": str(data.get("policy_profile", "general")),
                "policy_version": str(data.get("policy_version", "v1")),
                "policy_icon": str(data.get("policy_icon", "🏷️")),
            }

    # 2) 環境変数
    env_profile = os.getenv("NEXUS_POLICY_PROFILE")
    env_version = os.getenv("NEXUS_POLICY_VERSION")
    env_icon = os.getenv("NEXUS_POLICY_ICON")
    if env_profile or env_version or env_icon:
        return {
            "policy_profile": env_profile or "general",
            "policy_version": env_version or "v1",
            "policy_icon": env_icon or "🏷️",
        }

    # 3) デフォルト
    return {"policy_profile": "general", "policy_version": "v1", "policy_icon": "🏷️"}

# ---------- 既存 API の動的ディスパッチ (revision_tab) ------------------------
def _import_revision_tab():
    """
    既存の revision_tab.py / revision_loop.py / streamlit_migrated_tab.py 等から
    実在する関数を**可能な限り**拾って使う。
    """
    candidates = [
        "src.nexuscore.gradio_app.revision_tab",
        "src.nexuscore.gradio_app.revision_loop",
        "src.nexuscore.gradio_app.streamlit_migrated_tab",
        "nexuscore.gradio_app.revision_tab",
        "nexuscore.gradio_app.revision_loop",
    ]
    for name in candidates:
        try:
            return importlib.import_module(name)
        except Exception:
            continue
    return None

RT = _import_revision_tab()

def _coerce_bool_log(ret: Any) -> Tuple[bool, str]:
    """戻り値が (bool,str) でなくても無理なく解釈する小ヘルパ"""
    if isinstance(ret, tuple) and len(ret) >= 2 and isinstance(ret[0], bool):
        return bool(ret[0]), str(ret[1])
    if isinstance(ret, bool):
        return ret, ""
    return False, str(ret)

def run_pytest_once() -> Tuple[bool, str]:
    """
    既存の API を最大限利用。見つからなければ subprocess で pytest を実行。
    """
    # 1) revision_tab に run_pytest/ run_tests 的なものがあるか探す
    if RT is not None:
        for fn_name in ("run_pytest", "run_tests", "run_test"):
            if hasattr(RT, fn_name):
                try:
                    ret = getattr(RT, fn_name)()
                    return _coerce_bool_log(ret)
                except Exception as e:
                    return False, f"[rt.{fn_name}] exception: {e}\n{traceback.format_exc()}"

    # 2) サブプロセスで pytest 実行（-q）。sandbox_output 下のテストも広くカバー。
    import subprocess, shlex
    cmd = "pytest -q"
    try:
        proc = subprocess.run(
            shlex.split(cmd),
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=300,
        )
        ok = (proc.returncode == 0)
        log = (proc.stdout or "") + (proc.stderr or "")
        return ok, log
    except Exception as e:
        return False, f"[pytest subprocess] exception: {e}\n{traceback.format_exc()}"

def attempt_auto_fix(prev_log: str) -> Tuple[bool, str, Dict[str, str]]:
    """
    既存ロジックを**できるだけ**呼び出す。
    戻り値: (ok, test_log, changes_dict) 変更ファイル名 -> 新内容
    変更検出ができない場合は空 dict を返す（diff は保存時に graceful に処理）。
    """
    # 1) revision_tab に auto_fix/attempt_auto_fix/repair_once 等があるか探す
    if RT is not None:
        for fn_name in ("auto_fix_once", "attempt_auto_fix", "repair_once", "run_auto_fix"):
            if hasattr(RT, fn_name):
                try:
                    ret = getattr(RT, fn_name)(prev_log)
                    # 返却が (ok, log, changes) 想定。足りなければ整形する
                    if isinstance(ret, tuple):
                        if len(ret) == 3:
                            return bool(ret[0]), str(ret[1]), dict(ret[2] or {})
                        if len(ret) == 2:
                            return bool(ret[0]), str(ret[1]), {}
                    # それ以外は bool/str とみなす
                    ok, log = _coerce_bool_log(ret)
                    return ok, log, {}
                except Exception as e:
                    return False, f"[rt.{fn_name}] exception: {e}\n{traceback.format_exc()}", {}

    # 2) 何も無ければ no-op: 失敗ログを返す（安全フォールバック）
    return False, "[auto-fix] no available function; skipped.", {}

# ---------- 統一 diff 生成 -----------------------------------------------------
def read_file_text(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8")
    except Exception:
        return ""

def unified_diff_text(before: str, after: str, path: str) -> str:
    before_lines = before.splitlines(keepends=True)
    after_lines = after.splitlines(keepends=True)
    return "".join(
        difflib.unified_diff(before_lines, after_lines, fromfile=f"a/{path}", tofile=f"b/{path}")
    )

def snapshot_sandbox_files() -> Dict[str, str]:
    """
    sandbox_output 配下の *.py を**両方**のルートから収集して (相対パス -> 内容)
    """
    files: Dict[str, str] = {}
    for base in SANDBOX_DIRS:
        if not base.exists():
            continue
        for p in base.rglob("*.py"):
            rel = str(p.relative_to(base))
            # 先勝ちでOK（両方に同名があれば最初に見つけた方）
            files.setdefault(rel, read_file_text(p))
    return files

def build_unified_diff(old_snap: Dict[str, str], new_snap: Dict[str, str]) -> str:
    paths = sorted(set(old_snap.keys()) | set(new_snap.keys()))
    chunks: List[str] = []
    for rel in paths:
        before = old_snap.get(rel, "")
        after = new_snap.get(rel, "")
        if before != after:
            chunks.append(unified_diff_text(before, after, rel))
    return "\n".join(chunks).strip()

# ---------- 旧テキスト形式の後方互換保存 --------------------------------------
def append_legacy_history_line(status: str, reason: str) -> None:
    line = f"{now_iso()} [{status}] {reason}\n"
    (PROJECT_ROOT / "patch_history.txt").write_text(
        ((PROJECT_ROOT / "patch_history.txt").read_text(encoding="utf-8") if (PROJECT_ROOT / "patch_history.txt").exists() else "")
        + line,
        encoding="utf-8"
    )

def write_legacy_log(timestamp: str, test_log: str) -> None:
    log_file = PATCH_DIR / f"patch_{timestamp}.log"
    try:
        log_file.write_text(test_log, encoding="utf-8")
    except Exception:
        pass

# ---------- パッチ JSON 保存（完全構造体 + policy フィールド） -----------------
def write_patch_json(
    *,
    timestamp: str,
    status: str,
    reason: str,
    test_log: str,
    code_diff: str,
    policy: Dict[str, str],
    attempts: int,
) -> Path:
    record: Dict[str, Any] = {
        "timestamp": timestamp,
        "status": status,                 # "initial_pass" / "success" / "attempt_i/5" / "attempt_error"
        "reason": reason,
        "test_log": test_log,
        "code_diff": code_diff,
        "attempt_count": attempts,
        # --- 監査バッジ用 -----------------------------------------------------
        "policy_profile": policy.get("policy_profile", "general"),
        "policy_version": policy.get("policy_version", "v1"),
        "policy_icon": policy.get("policy_icon", "🏷️"),
        # --- 追加メタ ----------------------------------------------------------
        "saved_at_jst": now_iso(),
        "project_root": str(PROJECT_ROOT),
        "sandbox_roots": [str(p) for p in SANDBOX_DIRS],
        "runner_version": "auto_revision_runner.py@v2.7",
    }
    out = PATCH_DIR / f"patch_{timestamp}.json"
    out.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[AutoRevision] Structured patch history saved -> {out}")
    return out

# ---------- メインループ ------------------------------------------------------
def main():
    print(f"[AutoRevision] start (runner v2.7) JST={now_iso()}")
    policy = load_policy_context()
    print(f"[AutoRevision] policy -> profile={policy['policy_profile']} ver={policy['policy_version']} icon={policy['policy_icon']}")

    # 初期スナップショット
    snap_before = snapshot_sandbox_files()

    # 1) 初回 pytest
    ok, log = run_pytest_once()
    ts = now_tag()
    attempts = 0

    if ok:
        diff_text = build_unified_diff(snap_before, snapshot_sandbox_files())
        write_patch_json(
            timestamp=ts,
            status="initial_pass",
            reason="Initial tests passed",
            test_log=log,
            code_diff=diff_text,
            policy=policy,
            attempts=attempts,
        )
        write_legacy_log(ts, log)
        append_legacy_history_line("initial_pass", "Initial tests passed")
        print("[AutoRevision] ✅ Tests passed successfully. No repair needed.")
        return

    # 2) 自己修復ループ（最大5回）
    prev_log = log
    for i in range(1, 6):
        attempts = i
        print(f"[AutoRevision] --- Attempt {i}/5 ---")
        try:
            # 直前スナップショット
            snap_mid = snapshot_sandbox_files()

            ok2, log2, changes = attempt_auto_fix(prev_log)

            # 変更が dict で返ってきた場合はファイルへ反映（diff生成のため）
            if isinstance(changes, dict) and changes:
                for rel, content in changes.items():
                    # 最初に見つかった sandbox に書く（無ければ PROJECT_ROOT 側）
                    target_dir = SANDBOX_DIRS[0]
                    target_dir.mkdir(parents=True, exist_ok=True)
                    (target_dir / rel).parent.mkdir(parents=True, exist_ok=True)
                    (target_dir / rel).write_text(content, encoding="utf-8")

            # diff は attempt 時点の差分を採取
            snap_after = snapshot_sandbox_files()
            diff_text = build_unified_diff(snap_mid, snap_after)

            status = "success" if ok2 else f"attempt_{i}/5"
            reason = "Auto-fix success" if ok2 else "Auto-fix attempt"
            ts = now_tag()

            write_patch_json(
                timestamp=ts,
                status=status,
                reason=reason,
                test_log=log2,
                code_diff=diff_text,
                policy=policy,
                attempts=attempts,
            )
            write_legacy_log(ts, log2)
            append_legacy_history_line(status, reason)

            if ok2:
                print("[AutoRevision] ✅ Repair complete.")
                return

            prev_log = log2

        except Exception as e:
            ts = now_tag()
            tb = traceback.format_exc()
            write_patch_json(
                timestamp=ts,
                status="attempt_error",
                reason=f"Exception: {e}",
                test_log=tb,
                code_diff="",
                policy=policy,
                attempts=attempts,
            )
            write_legacy_log(ts, tb)
            append_legacy_history_line("attempt_error", f"Exception: {e}")
            print("[AutoRevision] ❌ Exception during attempt:", e)

    print("[AutoRevision] done (max attempts reached)")

if __name__ == "__main__":
    main()
