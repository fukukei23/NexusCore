#!/usr/bin/env python3
"""学習レイヤー実API E2E検証 (Phase B / E案・案C-2)

目的: NexusCore学習ルート(postmortem→knowledge_curator検証→FKB永続化)が
      実API(GLM)で機能するかを、単体テスト(Mock版)の実LLM版で検証する。

構成(test_postmortem_learning_hook.pyを踏襲):
- 11 agents のうち postmortem/knowledge_curator だけ実LLM化
  (BaseAgent.__init__ が内部で LLMRouter() を自動生成し .env のGLM設定を読む)
- 残り9 agents は Mock(review_phase先頭のテスト失敗→早期returnで呼ばれない)
- review_phase を直接叩き、学習ルートのみ発火させる
- knowledge_base は Mock 化(案C-2・DB非汚染・永続化は呼び出し回数で観察)

バギーソース: is_prime が常にTrue(4で必ず失敗)→curator検証が通りやすい明確なバグ
"""
import logging
import sys
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

# CWD(NexusCore)とsrcをパスに追加(database パッケージ + nexuscore パッケージ)
_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT))
sys.path.insert(0, str(_ROOT / "src"))

from dotenv import load_dotenv  # noqa: E402

load_dotenv()  # .env を環境変数へ(GLM/FORCE_CHEAP/MAX_OUT_TOKENS・値非表示)

from nexuscore.agents.knowledge_curator_agent import KnowledgeCuratorAgent  # noqa: E402
from nexuscore.agents.postmortem_agent import PostmortemAgent  # noqa: E402
from nexuscore.core.orchestrator import Orchestrator, OrchestratorContext  # noqa: E402
from nexuscore.llm.llm_router import LLMRouter  # noqa: E402
from nexuscore.services.patch_applier import PatchApplier  # noqa: E402

# 検証用: PatchApplier.apply を allow_deletions=True で呼ぶようモンキーパッチ
# (curator検証が「行削除を含む修正パッチ」で止まらないようにする・本番運用なしのため安全)
def _apply_allow_deletions(self: PatchApplier, patch_str: str, project_path: str) -> bool:
    return self.apply_patch(
        patch_text=patch_str, project_path=project_path, allow_deletions=True
    )

PatchApplier.apply = _apply_allow_deletions  # type: ignore[method-assign]

# --- わざと失敗させるタスク(明確なバグ・curator検証が通りやすい) ---
BUGGY_SOURCE = "def is_prime(n: int) -> bool:\n    return True\n"
FAILING_TEST = (
    "from math_tools import is_prime\n"
    "def test_prime_2():\n    assert is_prime(2) is True\n"
    "def test_prime_4():\n    assert is_prime(4) is False\n"
)
ERROR_LOG = "FAILED test_prime_4 - AssertionError: assert True is False"


def make_context(project_path: Path) -> OrchestratorContext:
    """テスト失敗状態の context を組み立て(実ファイル配置含む)。"""
    src = project_path / "math_tools.py"
    src.write_text(BUGGY_SOURCE, encoding="utf-8")
    tests_dir = project_path / "tests"
    tests_dir.mkdir(exist_ok=True)
    test = tests_dir / "test_math_tools.py"
    test.write_text(FAILING_TEST, encoding="utf-8")

    ctx = OrchestratorContext(task_id="verify-e2e", user_requirement="is_prime検証")
    ctx.implementation = {"files": {"math_tools.py": BUGGY_SOURCE}}
    ctx.testing = {
        "tests": FAILING_TEST,
        "test_path": str(test),
        "passed": False,
        "stdout": "",
        "stderr": ERROR_LOG,
    }
    return ctx


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    with tempfile.TemporaryDirectory(prefix="nx_verify_") as project_path:
        proj = Path(project_path)
        # 11 agents: 学習ルート2体だけ実LLM、残り9はMock(呼ばれない想定)
        agents: dict = {
            "requirement_agent": Mock(),
            "architect_agent": Mock(),
            "planner_agent": Mock(),
            "coder_agent": Mock(),
            "tester_agent": Mock(),
            "debugger_agent": Mock(),
            "guardian_agent": Mock(),
            "policy_agent": Mock(),
            "patch_applier_agent": Mock(),
        }
        agents["postmortem_agent"] = PostmortemAgent()
        agents["knowledge_curator_agent"] = KnowledgeCuratorAgent()

        orchestrator = Orchestrator(
            project_path=str(proj),
            constitution={"rule": "verify"},
            llm_router=Mock(spec=LLMRouter),
            **agents,
        )
        context = make_context(proj)

        print("=" * 60)
        print("学習レイヤー実API E2E検証 開始 (実LLM=postmortem/curator)")
        print(f"project_path: {proj}")
        print("=" * 60)

        # 案C-2: knowledge_base をMock化(DB非汚染・呼び出しで永続化を観察)
        with patch("database.knowledge_base.knowledge_base") as mock_kb:
            mock_kb.add_knowledge.return_value = "created(verify-e2e)"
            result = orchestrator.run_review_phase(context)

        # --- 観察 ---
        print("\n" + "=" * 60)
        print("観察結果")
        print("=" * 60)
        print(f"terminal_state: {result.terminal_state}")
        pm = result.postmortem_report or {}
        print(f"postmortem_report 生成: {'あり' if pm else 'なし(空)'}")
        if pm:
            print(f"  error_signature: {pm.get('error_signature', '(無)')}")
            print(f"  cause: {str(pm.get('cause', '(無)'))[:80]}")
            sp = pm.get("solution_pattern", {})
            instr = str(sp.get("instruction", "(無)"))
            print(f"  instruction先頭: {instr[:100]}")
        persist_calls = mock_kb.add_knowledge.call_count
        print(f"FKB永続化(add_knowledge)呼出回数: {persist_calls}")
        if persist_calls:
            sig = mock_kb.add_knowledge.call_args[0][0].get("error_signature")
            print(f"  永続化suggestionのerror_signature: {sig}")

        # --- 判定 ---
        print("-" * 60)
        if persist_calls:
            verdict = "✅ 完全成功: 発火→curator検証通過→FKB永続化まで到達"
        elif pm:
            verdict = "🟡 部分成功: postmortem提案は生成されたがcurator検証を通らなかった"
        else:
            verdict = "❌ 発火せず: postmortem提案生成の時点で失敗(空応答/スキーマ違反)"
        print(f"判定: {verdict}")
        print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
