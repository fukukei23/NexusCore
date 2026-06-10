"""CR-NEXUS-054: dynamic_router モジュールのユニットテスト（MiniMax生成・Fable検証済み）。"""

import pytest

from nexuscore.core.dynamic_router import ActionRegistry, RuleBasedRouter
from nexuscore.core.goal_spec import CriterionResult
from nexuscore.core.orchestrator_models import OrchestratorContext


class TestActionRegistry:
    """ActionRegistry の基本操作を検証する。"""

    def test_register_and_has(self):
        """register した名前を has が True 判定し、未登録は False。"""
        registry = ActionRegistry()
        registry.register("planning", lambda ctx: ctx)
        assert registry.has("planning") is True
        assert registry.has("missing") is False

    def test_execute_returns_context(self):
        """execute は登録関数の戻り値（context）をそのまま返す。"""
        registry = ActionRegistry()
        ctx = OrchestratorContext(task_id="t", user_requirement="r")
        registry.register("requirements", lambda c: c)
        result = registry.execute("requirements", ctx)
        assert result is ctx

    def test_execute_unregistered_raises_keyerror(self):
        """未登録名を execute すると KeyError が発生する。"""
        registry = ActionRegistry()
        ctx = OrchestratorContext(task_id="t", user_requirement="r")
        with pytest.raises(KeyError):
            registry.execute("not_registered", ctx)


class TestFromOrchestrator:
    """ActionRegistry.from_orchestrator の登録挙動を検証する。"""

    def test_all_seven_methods_registered(self):
        """7 フェーズ全部持つオーケストレータからは 7 アクションが登録される。"""
        class FakeOrchestrator:
            def run_context_phase(self, ctx): return ctx
            def run_requirements_phase(self, ctx): return ctx
            def run_planning_phase(self, ctx): return ctx
            def run_architecture_phase(self, ctx): return ctx
            def run_implementation_phase(self, ctx): return ctx
            def run_testing_phase(self, ctx): return ctx
            def run_review_phase(self, ctx): return ctx

        registry = ActionRegistry.from_orchestrator(FakeOrchestrator())
        for name in (
            "context",
            "requirements",
            "planning",
            "architecture",
            "implementation",
            "testing",
            "review",
        ):
            assert registry.has(name), f"{name} が未登録です"

    def test_missing_method_skips_registration(self):
        """run_testing_phase を持たないフェイクなら testing だけ未登録。"""
        class FakeOrchestrator:
            def run_context_phase(self, ctx): return ctx
            def run_requirements_phase(self, ctx): return ctx
            def run_planning_phase(self, ctx): return ctx
            def run_architecture_phase(self, ctx): return ctx
            def run_implementation_phase(self, ctx): return ctx
            # run_testing_phase は意図的に未定義
            def run_review_phase(self, ctx): return ctx

        registry = ActionRegistry.from_orchestrator(FakeOrchestrator())
        assert registry.has("implementation") is True
        assert registry.has("review") is True
        assert registry.has("testing") is False


class TestRuleBasedRouter:
    """RuleBasedRouter の選択ロジックを検証する。"""

    def _build_registry(self):
        """全アクションを identity（context をそのまま返す）で登録する。"""
        registry = ActionRegistry()
        for name in (
            "context",
            "requirements",
            "planning",
            "architecture",
            "implementation",
            "testing",
            "review",
        ):
            registry.register(name, lambda ctx: ctx)
        return registry

    def test_rule1_retry_same_action(self):
        """ルール1: 直前失敗アクションが残リトライありなら同アクションを再実行する。"""
        router = RuleBasedRouter(self._build_registry())
        decision = router.next_action(
            unsatisfied=[CriterionResult(name="has_plan", satisfied=False)],
            last_failed_action="planning",
            retries_left_for_failed=2,
        )
        assert decision.action == "planning"
        assert "リトライ" in decision.reason

    def test_rule2_dependency_order(self):
        """ルール2: 依存順に従い has_plan が has_implementation より先に処理される。"""
        router = RuleBasedRouter(self._build_registry())
        decision = router.next_action(
            unsatisfied=[
                CriterionResult(name="has_implementation", satisfied=False),
                CriterionResult(name="has_plan", satisfied=False),
            ],
        )
        assert decision.action == "planning"

    def test_skip_actions_skipped(self):
        """skip_actions に登録されたアクションは飛ばして次を選ぶ。"""
        router = RuleBasedRouter(
            self._build_registry(),
            skip_actions=frozenset({"requirements"}),
        )
        decision = router.next_action(
            unsatisfied=[
                CriterionResult(name="has_specs", satisfied=False),
                CriterionResult(name="has_plan", satisfied=False),
            ],
        )
        assert decision.action == "planning"

    def test_unregistered_action_returns_none(self):
        """未登録アクションしか候補が無いとき action=None を返す。"""
        registry = ActionRegistry()
        for name in (
            "context",
            "requirements",
            "planning",
            "architecture",
            "testing",
            "review",
        ):
            registry.register(name, lambda ctx: ctx)
        # implementation は未登録のまま
        router = RuleBasedRouter(registry)
        decision = router.next_action(
            unsatisfied=[CriterionResult(name="has_implementation", satisfied=False)],
        )
        assert decision.action is None
        assert "has_implementation" in decision.reason

    def test_no_unsatisfied_returns_none(self):
        """未達が空なら action=None かつ reason に達成済みが入る。"""
        router = RuleBasedRouter(self._build_registry())
        decision = router.next_action(unsatisfied=[])
        assert decision.action is None
        assert "達成済み" in decision.reason

    def test_unknown_criterion_returns_none(self):
        """criterion_to_action に存在しない条件名のみ未達なら action=None。"""
        router = RuleBasedRouter(self._build_registry())
        decision = router.next_action(
            unsatisfied=[CriterionResult(name="totally_unknown", satisfied=False)],
        )
        assert decision.action is None
        assert "totally_unknown" in decision.reason

    def test_custom_criterion_to_action(self):
        """criterion_to_action を上書きするとカスタム条件にもアクションが選ばれる。"""
        custom_map = {"custom_ok": "implementation"}
        router = RuleBasedRouter(
            self._build_registry(),
            criterion_to_action=custom_map,
        )
        decision = router.next_action(
            unsatisfied=[CriterionResult(name="custom_ok", satisfied=False)],
        )
        assert decision.action == "implementation"
