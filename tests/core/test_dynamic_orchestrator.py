"""CR-NEXUS-054: dynamic_orchestrator（DynamicRunLoop）のユニットテスト。

シナリオ設計: MiniMax生成案をベースに実APIへFableが適合させた。
"""

from nexuscore.core.dynamic_orchestrator import DecisionTrace, DynamicRunLoop, TraceEntry
from nexuscore.core.goal_spec import GoalSpec, SuccessCriterion, standard_criteria
from nexuscore.core.orchestrator_models import OrchestratorContext


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
        ctx.testing = {"tests": "def test(): pass"}
        ctx.phase_log.append("TESTING")
        return ctx

    def run_review_phase(self, ctx):
        ctx.review = {}
        ctx.phase_log.append("REVIEW")
        return ctx


class NoOpRequirementsOrch(HappyOrch):
    """requirements を実行しても specs を埋めない（進捗しない）フェイク。"""

    def run_requirements_phase(self, ctx):
        ctx.phase_log.append("REQUIREMENTS_NOOP")
        return ctx


class FlakyImplementationOrch(HappyOrch):
    """implementation が1回目失敗、2回目成功するフェイク。"""

    def __init__(self):
        self.call_count = 0

    def run_implementation_phase(self, ctx):
        self.call_count += 1
        if self.call_count == 1:
            raise RuntimeError("boom")
        return super().run_implementation_phase(ctx)


class AlwaysFailingImplementationOrch(HappyOrch):
    """implementation が常に RuntimeError を投げるフェイク。"""

    def run_implementation_phase(self, ctx):
        raise RuntimeError("always fail")


def _standard_goal(**kwargs) -> GoalSpec:
    return GoalSpec(description="標準ゴール", criteria=standard_criteria(), **kwargs)


def _specs_only_goal(**kwargs) -> GoalSpec:
    return GoalSpec(
        description="specsのみ",
        criteria=[SuccessCriterion(name="has_specs", check=lambda ctx: bool(ctx.specs))],
        **kwargs,
    )


class TestDynamicRunLoopHappyPath:
    """正常系・スキップ・再開のシナリオ。"""

    def test_正常系_5アクションで収束しarchitectureを通らない(self):
        """HappyOrch + standard_criteria で success=True、フェーズが依存順に5回実行される。"""
        loop = DynamicRunLoop(HappyOrch(), _standard_goal())
        result = loop.run("テスト要件")

        assert result.success is True
        assert result.actions_executed == 5
        assert result.unsatisfied_criteria == ()
        assert result.context.phase_log == [
            "REQUIREMENTS", "PLAN", "IMPLEMENTATION", "TESTING", "REVIEW",
        ]
        assert "ARCHITECTURE" not in result.context.phase_log
        assert len(result.trace.entries) == 5
        assert all(e.succeeded for e in result.trace.entries)
        assert "ゴール達成" in result.message

    def test_再開_途中状態のcontextから残りフェーズのみ実行(self):
        """specs/plan 済みの context を渡すと requirements/planning は再実行されない。"""
        ctx = OrchestratorContext(task_id="resume", user_requirement="req")
        ctx.specs = {"r": 1}
        ctx.plan = {"p": 1}
        ctx.phase_log = ["REQUIREMENTS", "PLAN"]

        loop = DynamicRunLoop(HappyOrch(), _standard_goal())
        result = loop.run("テスト要件", context=ctx)

        assert result.success is True
        assert result.actions_executed == 3
        assert result.context.phase_log.count("REQUIREMENTS") == 1
        assert result.context.phase_log.count("PLAN") == 1
        assert len(result.trace.entries) == 3

    def test_skip指定で必要アクションが封じられると打つ手なしで失敗(self):
        """has_specs 要求 + requirements スキップ → 例外を投げず success=False。"""
        loop = DynamicRunLoop(
            HappyOrch(),
            _specs_only_goal(skip_actions=frozenset({"requirements"})),
        )
        result = loop.run("要件")

        assert result.success is False
        assert "打つ手" in result.message
        assert "has_specs" in result.unsatisfied_criteria

    def test_失敗からのリトライ成功でループが継続する(self):
        """implementation 1回目失敗・2回目成功 → 失敗1件がtraceに残り最終的に成功。"""
        orch = FlakyImplementationOrch()
        loop = DynamicRunLoop(orch, _standard_goal())
        result = loop.run("要件")

        assert result.success is True
        assert orch.call_count == 2
        # 失敗1回もアクション消費としてカウントされる
        assert result.actions_executed == 6
        failed = [e for e in result.trace.entries if not e.succeeded]
        succeeded = [e for e in result.trace.entries if e.succeeded]
        assert len(failed) == 1
        assert failed[0].action == "implementation"
        assert "boom" in failed[0].error
        assert len(succeeded) == 5
        assert "IMPLEMENTATION" in result.context.phase_log


class TestDynamicRunLoopFailures:
    """リトライ上限・予算超過の失敗シナリオ。例外ではなく GoalResult で返ること。"""

    def test_リトライ上限超過でsuccessFalseと理由を返す(self):
        """常に失敗する implementation + max_retries_per_action=1 → リトライ上限メッセージ。"""
        loop = DynamicRunLoop(
            AlwaysFailingImplementationOrch(),
            _standard_goal(max_retries_per_action=1),
        )
        result = loop.run("要件")

        assert result.success is False
        assert "リトライ上限" in result.message
        assert "has_implementation" in result.unsatisfied_criteria
        impl_entries = [e for e in result.trace.entries if e.action == "implementation"]
        assert len(impl_entries) == 2  # 初回 + リトライ1回
        assert all(not e.succeeded for e in impl_entries)

    def test_進捗しないアクションは予算超過でsuccessFalse(self):
        """成果物を埋めない requirements + max_actions=3 → 予算メッセージで停止。"""
        loop = DynamicRunLoop(
            NoOpRequirementsOrch(),
            _specs_only_goal(max_actions=3),
        )
        result = loop.run("要件")

        assert result.success is False
        assert "予算" in result.message
        assert result.actions_executed == 3
        assert "has_specs" in result.unsatisfied_criteria

    def test_達成済みゴールなら何も実行せず成功(self):
        """最初から全条件達成済みの context → アクション0回で success=True。"""
        ctx = OrchestratorContext(task_id="done", user_requirement="req")
        ctx.specs = {"r": 1}

        loop = DynamicRunLoop(HappyOrch(), _specs_only_goal())
        result = loop.run("要件", context=ctx)

        assert result.success is True
        assert result.actions_executed == 0
        assert result.trace.entries == []


class TestDecisionTrace:
    """DecisionTrace / TraceEntry の記録内容と summary 出力。"""

    def test_summaryにアクション名とOKが含まれる(self):
        """正常系実行後の summary() に全アクション名と OK 表記が含まれる。"""
        loop = DynamicRunLoop(HappyOrch(), _standard_goal())
        result = loop.run("要件")
        summary = result.trace.summary()

        assert "OK" in summary
        for action in ["requirements", "planning", "implementation", "testing", "review"]:
            assert action in summary

    def test_1ステップ目のunsatisfied_beforeに初期未達条件が入る(self):
        """最初の TraceEntry が実行前の未達条件スナップショットを保持する。"""
        loop = DynamicRunLoop(HappyOrch(), _standard_goal())
        result = loop.run("要件")

        first = result.trace.entries[0]
        assert first.step == 1
        assert first.action == "requirements"
        assert "has_specs" in first.unsatisfied_before
        assert first.succeeded is True

    def test_recordでエントリが追記される(self):
        """DecisionTrace.record() がエントリを順に追加し、errorも保持する。"""
        trace = DecisionTrace()
        e1 = TraceEntry(step=1, action="requirements", reason="start", succeeded=True)
        e2 = TraceEntry(step=2, action="planning", reason="next", succeeded=False, error="oops")
        trace.record(e1)
        trace.record(e2)

        assert len(trace.entries) == 2
        assert trace.entries[0] is e1
        assert trace.entries[1].error == "oops"
        assert "NG" in trace.summary()
