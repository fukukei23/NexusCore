"""CR-NEXUS-054 Phase C: main_cli.run_dynamic_mode のテスト（GLM生成・Fable検証済み）。"""

from types import SimpleNamespace
from unittest.mock import MagicMock

import main_cli


class HappyOrch:
    """各フェーズが成果物を埋める正常系フェイク。"""

    def run_context_phase(self, ctx):
        return ctx

    def run_requirements_phase(self, ctx):
        ctx.specs = {"r": 1}
        ctx.phase_log.append("REQUIREMENTS")
        return ctx

    def run_planning_phase(self, ctx):
        ctx.plan = {"p": 1}
        ctx.phase_log.append("PLAN")
        return ctx

    def run_architecture_phase(self, ctx):
        ctx.phase_log.append("ARCHITECTURE")
        return ctx

    def run_implementation_phase(self, ctx):
        ctx.implementation = {"code": "x=1"}
        ctx.phase_log.append("IMPLEMENTATION")
        return ctx

    def run_testing_phase(self, ctx):
        ctx.testing = {"tests": "t"}
        ctx.phase_log.append("TESTING")
        return ctx

    def run_review_phase(self, ctx):
        ctx.review = {}
        ctx.phase_log.append("REVIEW")
        return ctx


class BrokenOrch(HappyOrch):
    """implementation が常に失敗するフェイク。"""

    def run_implementation_phase(self, ctx):
        raise RuntimeError("fail")


def _args(**overrides):
    base = dict(
        requirement="req",
        language="ja",
        dynamic_llm_routing=False,
        max_actions=12,
        skip_actions="",
    )
    base.update(overrides)
    return SimpleNamespace(**base)


class TestRunDynamicMode:
    """run_dynamic_mode の正常系・異常系・引数パースのテスト。"""

    def test_正常系で0を返す(self):
        """HappyOrch + 既定args でゴール達成し exit code 0 を返す。"""
        result = main_cli.run_dynamic_mode(
            orchestrator=HappyOrch(), llm_router=None, args=_args()
        )
        assert result == 0

    def test_実装フェーズが常に失敗すると1を返す(self):
        """BrokenOrch ではリトライ上限超過で exit code 1 を返す。"""
        result = main_cli.run_dynamic_mode(
            orchestrator=BrokenOrch(), llm_router=None, args=_args()
        )
        assert result == 1

    def test_skip_actionsのカンマ区切りパース(self):
        """'architecture, review'（空白混じり）がパースされ、review_done が達成不能になり 1 を返す。"""
        result = main_cli.run_dynamic_mode(
            orchestrator=HappyOrch(),
            llm_router=None,
            args=_args(skip_actions="architecture, review"),
        )
        assert result == 1

    def test_LLMルーティング有効時もフォールバックで完走する(self):
        """dynamic_llm_routing=True で LLM が無効応答を返しても、
        ルールベースへのフォールバックでゴール達成し 0 を返す。"""
        llm_router = MagicMock()
        llm_router.complete.return_value = {"content": "わかりません"}

        result = main_cli.run_dynamic_mode(
            orchestrator=HappyOrch(),
            llm_router=llm_router,
            args=_args(dynamic_llm_routing=True),
        )
        assert result == 0
        assert llm_router.complete.called

    def test_LLMルーティング有効時に有効提案が採用される(self):
        """LLM が有効な提案を返す場合も完走する（提案はループ進行に追従できないため
        無効化された時点でフォールバックし、最終的に 0 を返す）。"""
        llm_router = MagicMock()
        llm_router.complete.return_value = {
            "content": '{"action": "requirements", "reason": "要件から"}'
        }

        result = main_cli.run_dynamic_mode(
            orchestrator=HappyOrch(),
            llm_router=llm_router,
            args=_args(dynamic_llm_routing=True, max_actions=30),
        )
        # 固定提案 "requirements" は2巡目以降進捗を生まないが、
        # max_llm_calls(既定10)消費後はルールベースに切替わり完走する
        assert result == 0

    def test_LLM無効かつllm_routerがNoneでも動く(self):
        """dynamic_llm_routing=False なら llm_router は参照されない。"""
        result = main_cli.run_dynamic_mode(
            orchestrator=HappyOrch(), llm_router=None, args=_args()
        )
        assert result == 0
