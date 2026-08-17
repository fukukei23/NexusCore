#!/usr/bin/env python3
"""FKBフルループ実API E2E検証（nexuscore-bench Phase 0・ゲート(b)）

フルループ = 失敗 → postmortem → curator検証 → FKB永続化 → 次タスクでFKB参照 → 修正成功

構成:
- Part1(学習): 7/25資産 verify_learning_e2e_real.py の構成を踏襲。knowledge_base を
  Mockでなく実KnowledgeBase(隔離sqlite)にしてFKB永続化を本当に行う
- Part2(参照・解決): DebuggerAgent(knowledge_base_path=FKBスナップショットJSON) に
  同種バグの新しいプロジェクトを渡し、solution_used(FKB参照)と修正成功を観察
- 1試行 = Part1+Part2。4試行(1件必須+リトライ3回)で成功率>=60%をゲート判定

使い方:
  set -a; source ~/.secrets.env; set +a
  export DATABASE_URL="sqlite:///<隔離DBパス>"
  python scripts/verify_fkb_fullloop_real.py [--debug-gemini]
    --debug-gemini: Part2のDebuggerを NEXUS_TASK_MODEL_DEBUG=gemini_secondary で実行（壁3検証）
"""
import argparse
import json
import logging
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from unittest.mock import Mock, patch

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT))
sys.path.insert(0, str(_ROOT / "src"))

from dotenv import load_dotenv  # noqa: E402

load_dotenv()

from database.knowledge_base import KnowledgeBase  # noqa: E402
from nexuscore.agents.debugger_agent import DebuggerAgent  # noqa: E402
from nexuscore.agents.knowledge_curator_agent import KnowledgeCuratorAgent  # noqa: E402
from nexuscore.agents.postmortem_agent import PostmortemAgent  # noqa: E402
from nexuscore.core.orchestrator import Orchestrator, OrchestratorContext  # noqa: E402
from nexuscore.llm.llm_router import LLMRouter  # noqa: E402
from nexuscore.services.patch_applier import PatchApplier  # noqa: E402

BUGGY_SOURCE = "def is_prime(n: int) -> bool:\n    return True\n"
FAILING_TEST = (
    "from math_tools import is_prime\n"
    "def test_prime_2():\n    assert is_prime(2) is True\n"
    "def test_prime_4():\n    assert is_prime(4) is False\n"
)
ERROR_LOG = "FAILED test_prime_4 - AssertionError: assert True is False"

RESULTS_PATH = _ROOT / "phase0_fullloop_results.jsonl"


def _apply_allow_deletions(self: PatchApplier, patch_str: str, project_path: str) -> bool:
    """検証用: 学習経路のパッチ適用を許可(壁2-A上限+壁2-B AST検証は有効のまま)."""
    return self.apply_patch(
        patch_text=patch_str, project_path=project_path, allow_deletions=True
    )


def _setup_project(proj: Path) -> None:
    (proj / "math_tools.py").write_text(BUGGY_SOURCE, encoding="utf-8")
    tests = proj / "tests"
    tests.mkdir(exist_ok=True)
    (tests / "test_math_tools.py").write_text(FAILING_TEST, encoding="utf-8")


def _make_context(proj: Path) -> OrchestratorContext:
    ctx = OrchestratorContext(task_id="fullloop", user_requirement="is_prime検証")
    ctx.implementation = {"files": {"math_tools.py": BUGGY_SOURCE}}
    ctx.testing = {
        "tests": FAILING_TEST,
        "test_path": str(proj / "tests" / "test_math_tools.py"),
        "passed": False,
        "stdout": "",
        "stderr": ERROR_LOG,
    }
    return ctx


def _run_tests(proj: Path) -> bool:
    """隔離プロジェクトでpytestを走らせ全通過か返す."""
    r = subprocess.run(
        [sys.executable, "-m", "pytest", str(proj / "tests"), "-q"],
        capture_output=True, text=True, cwd=str(proj), timeout=120,
    )
    return r.returncode == 0


def run_trial(trial: int, kb: KnowledgeBase, debug_gemini: bool) -> dict:
    """1試行 = 学習(Part1) + 参照解決(Part2). 結果dictを返す."""
    t0 = time.time()
    outcome: dict = {
        "trial": trial,
        "debug_backend": "gemini" if debug_gemini else "glm",
        "fkb_saved": False,
        "fkb_referenced": False,
        "fixed": False,
        "note": "",
    }

    # ---- Part 1: 学習（review_phase → postmortem → curator → FKB永続化） ----
    PatchApplier.apply = _apply_allow_deletions  # type: ignore[method-assign]
    with tempfile.TemporaryDirectory(prefix="nx_full_p1_") as d:
        proj = Path(d)
        _setup_project(proj)
        agents: dict = {name: Mock() for name in [
            "requirement_agent", "architect_agent", "planner_agent", "coder_agent",
            "tester_agent", "debugger_agent", "guardian_agent", "policy_agent",
            "patch_applier_agent",
        ]}
        agents["postmortem_agent"] = PostmortemAgent()
        agents["knowledge_curator_agent"] = KnowledgeCuratorAgent()
        orchestrator = Orchestrator(
            project_path=str(proj),
            constitution={"rule": "verify"},
            llm_router=Mock(spec=LLMRouter),
            **agents,
        )
        # 実KBで学習させる（隔離sqlite・本番非汚染）
        with patch("database.knowledge_base.knowledge_base", kb):
            result = orchestrator.run_review_phase(_make_context(proj))
        pm = result.postmortem_report or {}
        active = {e["error_signature"] for e in kb.list_active()}
        outcome["fkb_saved"] = bool(pm) and any(
            pm.get("error_signature") == sig for sig in active
        )
        if not outcome["fkb_saved"]:
            outcome["note"] = f"part1: postmortem={bool(pm)} saved_sig_not_active"
            outcome["elapsed_sec"] = round(time.time() - t0, 1)
            return outcome

    # ---- Part 2: 参照・解決（新しいプロジェクトでDebuggerがFKBを引いて修正） ----
    snap_path = tempfile.mktemp(suffix=".json")
    kb.snapshot(snap_path)
    with tempfile.TemporaryDirectory(prefix="nx_full_p2_") as d:
        proj = Path(d)
        _setup_project(proj)
        assert not _run_tests(proj), "前提確認: バグ状態でテストは失敗するはず"
        debugger = DebuggerAgent(knowledge_base_path=snap_path)
        r = debugger.debug_and_patch(
            files_content={"math_tools.py": BUGGY_SOURCE},
            error_log=ERROR_LOG,
            project_path=str(proj),
        )
        solution = (r or {}).get("solution_used")
        outcome["fkb_referenced"] = solution is not None
        if outcome["fkb_referenced"]:
            # 参照ログに記録（bench主指標・計測フック）
            kid = kb.get_id_by_signature(solution.get("error_signature", ""))
            if kid is not None:
                kb.log_reference(kid, f"fullloop-trial{trial}", "debugger",
                                 "pending")
        fixed_code = (r or {}).get("fixed_code")
        if fixed_code:
            (proj / "math_tools.py").write_text(fixed_code, encoding="utf-8")
            passed = _run_tests(proj)
            outcome["fixed"] = passed
            if outcome["fkb_referenced"] and passed and kid is not None:
                # 参照が実功したら outcome を success に更新
                kb.log_reference(kid, f"fullloop-trial{trial}", "debugger", "success")
            elif kid is not None:
                kb.log_reference(kid, f"fullloop-trial{trial}", "debugger",
                                 "hit_but_failed")
        else:
            outcome["note"] = "part2: fixed_code生成なし"
    outcome["elapsed_sec"] = round(time.time() - t0, 1)
    return outcome


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--debug-gemini", action="store_true",
                        help="Part2のDebuggerをGeminiへ(NEXUS_TASK_MODEL_DEBUG)")
    args = parser.parse_args()
    logging.basicConfig(level=logging.WARNING)

    import os

    if args.debug_gemini:
        # 壁3: タスク単位env上書きでdebug系をGeminiへ（後方互換・未設定なら不変）
        os.environ["NEXUS_TASK_MODEL_DEBUGGING"] = "gemini_secondary"
        os.environ["NEXUS_TASK_MODEL_DEBUG"] = "gemini_secondary"

    db = os.environ.get("DATABASE_URL", "")
    if not db.startswith("sqlite:") or "fkb_fullloop" not in db:
        print("安全弁: DATABASE_URL が隔離用 sqlite(ファイル名に fkb_fullloop)ではありません。")
        print(f"  DATABASE_URL={db[:40]}...")
        print("  例: export DATABASE_URL=sqlite:////tmp/fkb_fullloop_phase0.db")
        return 2
    kb = KnowledgeBase()

    results = []
    for i in range(1, 5):
        print(f"--- trial {i}/4 開始 (debug={'gemini' if args.debug_gemini else 'glm'}) ---",
              flush=True)
        r = run_trial(i, kb, args.debug_gemini)
        print(json.dumps(r, ensure_ascii=False), flush=True)
        results.append(r)

    with open(RESULTS_PATH, "w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    ok = sum(1 for r in results
             if r["fkb_saved"] and r["fkb_referenced"] and r["fixed"])
    rate = ok / len(results)
    print(f"\nフルループ成功率: {ok}/{len(results)} ({rate:.0%})  # ゲート: >=60%")
    print(f"結果JSONL: {RESULTS_PATH}")
    return 0 if rate >= 0.6 else 1


if __name__ == "__main__":
    sys.exit(main())
