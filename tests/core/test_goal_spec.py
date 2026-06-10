"""CR-NEXUS-054: goal_spec モジュールのユニットテスト（MiniMax生成・Fable検証済み）。"""

from nexuscore.core.goal_spec import CriterionResult, GoalEvaluator, GoalSpec, SuccessCriterion, standard_criteria
from nexuscore.core.orchestrator_models import OrchestratorContext
import pytest


class TestGoalSpecValidation:
    def test_正常な値でGoalSpecを生成できる(self):
        """criteria非空・max_actions>=1・max_retries_per_action>=0 で正常に生成されることを確認する。"""
        criterion = SuccessCriterion(
            name="c1",
            check=lambda ctx: True,
            description="desc",
        )
        goal = GoalSpec(
            description="goal",
            criteria=[criterion],
            max_actions=3,
            max_retries_per_action=1,
            skip_actions=frozenset({"skip_me"}),
        )
        assert goal.description == "goal"
        assert goal.criteria == [criterion]
        assert goal.max_actions == 3
        assert goal.max_retries_per_action == 1
        assert goal.skip_actions == frozenset({"skip_me"})

    def test_デフォルト値が期待どおりである(self):
        """max_actions=12, max_retries_per_action=2, skip_actions=frozenset() が既定値で適用されることを確認する。"""
        criterion = SuccessCriterion(name="c1", check=lambda ctx: True)
        goal = GoalSpec(description="goal", criteria=[criterion])
        assert goal.max_actions == 12
        assert goal.max_retries_per_action == 2
        assert goal.skip_actions == frozenset()

    def test_criteriaが空だとValueError(self):
        """criteria が空リストのとき ValueError が発生することを確認する。"""
        with pytest.raises(ValueError):
            GoalSpec(description="goal", criteria=[])

    def test_max_actionsが1未満だとValueError(self):
        """max_actions が 0 のとき ValueError が発生することを確認する。"""
        criterion = SuccessCriterion(name="c1", check=lambda ctx: True)
        with pytest.raises(ValueError):
            GoalSpec(description="goal", criteria=[criterion], max_actions=0)

    def test_max_retries_per_actionが負だとValueError(self):
        """max_retries_per_action が -1 のとき ValueError が発生することを確認する。"""
        criterion = SuccessCriterion(name="c1", check=lambda ctx: True)
        with pytest.raises(ValueError):
            GoalSpec(
                description="goal",
                criteria=[criterion],
                max_retries_per_action=-1,
            )


class TestGoalEvaluator:
    def _make_goal(self, criteria):
        return GoalEvaluator(GoalSpec(description="goal", criteria=criteria))

    def _ctx(self, **kwargs):
        """テスト用の OrchestratorContext を生成するヘルパー。"""
        ctx = OrchestratorContext(task_id="t1", user_requirement="req")
        for key, value in kwargs.items():
            setattr(ctx, key, value)
        return ctx

    def test_全条件達成でsatisfiedはTrue(self):
        """全 SuccessCriterion.check が True を返すとき satisfied() が True になることを確認する。"""
        criteria = [
            SuccessCriterion(name="a", check=lambda ctx: True),
            SuccessCriterion(name="b", check=lambda ctx: True),
        ]
        evaluator = self._make_goal(criteria)
        ctx = self._ctx()
        assert evaluator.satisfied(ctx) is True
        assert evaluator.unsatisfied(ctx) == []
        results = evaluator.evaluate(ctx)
        assert all(r.satisfied for r in results)

    def test_一部未達ならunsatisfiedに対象条件名が含まれる(self):
        """1つだけ False を返す条件があるとき unsatisfied() にその name が含まれ、satisfied() は False になることを確認する。"""
        criteria = [
            SuccessCriterion(name="alpha", check=lambda ctx: True),
            SuccessCriterion(name="beta", check=lambda ctx: False),
            SuccessCriterion(name="gamma", check=lambda ctx: True),
        ]
        evaluator = self._make_goal(criteria)
        ctx = self._ctx()
        assert evaluator.satisfied(ctx) is False
        unsatisfied = evaluator.unsatisfied(ctx)
        assert [r.name for r in unsatisfied] == ["beta"]
        assert unsatisfied[0].satisfied is False

    def test_全未達ならsatisfiedはFalse(self):
        """全条件が False のとき satisfied() が False で unsatisfied() に全条件が含まれることを確認する。"""
        criteria = [
            SuccessCriterion(name="a", check=lambda ctx: False),
            SuccessCriterion(name="b", check=lambda ctx: False),
        ]
        evaluator = self._make_goal(criteria)
        ctx = self._ctx()
        assert evaluator.satisfied(ctx) is False
        assert {r.name for r in evaluator.unsatisfied(ctx)} == {"a", "b"}

    def test_checkが例外を投げても未達として扱われる(self):
        """check が例外を発生させた条件は satisfied=False として扱われ、他条件は独立に評価されることを確認する。"""
        def boom(_ctx):
            raise RuntimeError("boom")

        criteria = [
            SuccessCriterion(name="ok", check=lambda ctx: True),
            SuccessCriterion(name="bad", check=boom),
        ]
        evaluator = self._make_goal(criteria)
        ctx = self._ctx()
        results = {r.name: r for r in evaluator.evaluate(ctx)}
        assert results["ok"].satisfied is True
        assert results["bad"].satisfied is False
        assert [r.name for r in evaluator.unsatisfied(ctx)] == ["bad"]
        assert evaluator.satisfied(ctx) is False

    def test_evaluateの結果がCriterionResultのnameとdescriptionを保持する(self):
        """CriterionResult に SuccessCriterion の name と description が引き継がれることを確認する。"""
        criteria = [
            SuccessCriterion(
                name="with_desc",
                check=lambda ctx: True,
                description="hello",
            ),
        ]
        evaluator = self._make_goal(criteria)
        ctx = self._ctx()
        result = evaluator.evaluate(ctx)[0]
        assert isinstance(result, CriterionResult)
        assert result.name == "with_desc"
        assert result.description == "hello"
        assert result.satisfied is True

    def test_未達条件のdescriptionも保持される(self):
        """未達判定の CriterionResult も SuccessCriterion の description を保持していることを確認する。"""
        criteria = [
            SuccessCriterion(
                name="neg",
                check=lambda ctx: False,
                description="never passes",
            ),
        ]
        evaluator = self._make_goal(criteria)
        ctx = self._ctx()
        result = evaluator.evaluate(ctx)[0]
        assert result.description == "never passes"
        assert result.satisfied is False


class TestStandardCriteria:
    def _ctx(self, **kwargs):
        """テスト用の OrchestratorContext を生成するヘルパー。"""
        ctx = OrchestratorContext(task_id="t1", user_requirement="req")
        for key, value in kwargs.items():
            setattr(ctx, key, value)
        return ctx

    def test_空コンテキストでは全条件未達(self):
        """空のコンテキストでは standard_criteria の全条件が未達となり unsatisfied に全 name が含まれることを確認する。"""
        evaluator = GoalEvaluator(GoalSpec(description="g", criteria=standard_criteria()))
        ctx = self._ctx()
        assert evaluator.satisfied(ctx) is False
        names = {r.name for r in evaluator.unsatisfied(ctx)}
        assert names == {
            "has_specs",
            "has_plan",
            "has_implementation",
            "has_tests",
            "review_done",
        }

    def test_全項目を埋めると全達成(self):
        """specs/plan/implementation.code/testing.tests/phase_logにREVIEWを全て設定すると satisfied() が True になることを確認する。"""
        evaluator = GoalEvaluator(GoalSpec(description="g", criteria=standard_criteria()))
        ctx = self._ctx(
            specs={"spec.md": "# spec"},
            plan={"steps": ["a", "b"]},
            implementation={"code": "print('hi')"},
            testing={"tests": "def test_x(): assert True"},
            phase_log=["DESIGN", "REVIEW"],
        )
        assert evaluator.satisfied(ctx) is True
        assert evaluator.unsatisfied(ctx) == []

    def test_planにerrorキーが含まれるとhas_planは未達(self):
        """plan dict に 'error' キーが含まれると has_plan が未達になることを確認する。"""
        evaluator = GoalEvaluator(GoalSpec(description="g", criteria=standard_criteria()))
        ctx = self._ctx(
            specs={"s": "x"},
            plan={"steps": ["a"], "error": "something went wrong"},
            implementation={"code": "x"},
            testing={"tests": "t"},
            phase_log=["REVIEW"],
        )
        results = {r.name: r for r in evaluator.evaluate(ctx)}
        assert results["has_plan"].satisfied is False
        assert "has_plan" in {r.name for r in evaluator.unsatisfied(ctx)}

    def test_planにerrorキーがないならhas_planは達成(self):
        """plan dict に 'error' キーがなく非空であれば has_plan が達成されることを確認する。"""
        evaluator = GoalEvaluator(GoalSpec(description="g", criteria=standard_criteria()))
        ctx = self._ctx(plan={"steps": [1, 2, 3]})
        results = {r.name: r for r in evaluator.evaluate(ctx)}
        assert results["has_plan"].satisfied is True

    def test_specsが空だとhas_specsは未達(self):
        """specs が空 dict のとき has_specs が未達になることを確認する。"""
        evaluator = GoalEvaluator(GoalSpec(description="g", criteria=standard_criteria()))
        ctx = self._ctx(specs={})
        results = {r.name: r for r in evaluator.evaluate(ctx)}
        assert results["has_specs"].satisfied is False

    def test_implementation_codeが空だとhas_implementationは未達(self):
        """implementation['code'] が空文字のとき has_implementation が未達になることを確認する。"""
        evaluator = GoalEvaluator(GoalSpec(description="g", criteria=standard_criteria()))
        ctx = self._ctx(implementation={"code": ""})
        results = {r.name: r for r in evaluator.evaluate(ctx)}
        assert results["has_implementation"].satisfied is False

    def test_testing_testsが空だとhas_testsは未達(self):
        """testing['tests'] が空のとき has_tests が未達になることを確認する。"""
        evaluator = GoalEvaluator(GoalSpec(description="g", criteria=standard_criteria()))
        ctx = self._ctx(testing={"tests": ""})
        results = {r.name: r for r in evaluator.evaluate(ctx)}
        assert results["has_tests"].satisfied is False

    def test_phase_logにREVIEWが無いとreview_doneは未達(self):
        """phase_log に 'REVIEW' が含まれないとき review_done が未達になることを確認する。"""
        evaluator = GoalEvaluator(GoalSpec(description="g", criteria=standard_criteria()))
        ctx = self._ctx(phase_log=["DESIGN", "IMPLEMENT"])
        results = {r.name: r for r in evaluator.evaluate(ctx)}
        assert results["review_done"].satisfied is False

    def test_phase_logにREVIEWが含まれるとreview_doneは達成(self):
        """phase_log に 'REVIEW' が含まれるとき review_done が達成されることを確認する。"""
        evaluator = GoalEvaluator(GoalSpec(description="g", criteria=standard_criteria()))
        ctx = self._ctx(phase_log=["REVIEW"])
        results = {r.name: r for r in evaluator.evaluate(ctx)}
        assert results["review_done"].satisfied is True

    def test_require_testsがFalseならhas_testsは含まれない(self):
        """require_tests=False のとき生成される条件一覧に has_tests が含まれないことを確認する。"""
        criteria = standard_criteria(require_tests=False, require_review=True)
        names = {c.name for c in criteria}
        assert "has_tests" not in names
        assert "review_done" in names
        assert "has_specs" in names
        assert "has_plan" in names
        assert "has_implementation" in names

    def test_require_reviewがFalseならreview_doneは含まれない(self):
        """require_review=False のとき生成される条件一覧に review_done が含まれないことを確認する。"""
        criteria = standard_criteria(require_tests=True, require_review=False)
        names = {c.name for c in criteria}
        assert "review_done" not in names
        assert "has_tests" in names

    def test_両方Falseでも残り3条件は常に含まれる(self):
        """require_tests=False, require_review=False でも has_specs/has_plan/has_implementation は常に含まれることを確認する。"""
        criteria = standard_criteria(require_tests=False, require_review=False)
        names = {c.name for c in criteria}
        assert names == {"has_specs", "has_plan", "has_implementation"}

    def test_両方Trueなら5条件すべて含まれる(self):
        """require_tests=True, require_review=True で 5 条件すべてが含まれることを確認する。"""
        criteria = standard_criteria(require_tests=True, require_review=True)
        assert {c.name for c in criteria} == {
            "has_specs",
            "has_plan",
            "has_implementation",
            "has_tests",
            "review_done",
        }

    def test_require_testsをFalseにすればtesting未設定でも全達成(self):
        """require_tests=False のときは testing を埋めなくても has_tests 判定がなく satisfied() が True になり得ることを確認する。"""
        evaluator = GoalEvaluator(
            GoalSpec(description="g", criteria=standard_criteria(require_tests=False))
        )
        ctx = self._ctx(
            specs={"s": "x"},
            plan={"steps": [1]},
            implementation={"code": "x"},
            phase_log=["REVIEW"],
        )
        assert evaluator.satisfied(ctx) is True

    def test_require_reviewをFalseにすればphase_logにREVIEWが無くても全達成(self):
        """require_review=False のときは phase_log に REVIEW がなくても satisfied() が True になり得ることを確認する。"""
        evaluator = GoalEvaluator(
            GoalSpec(description="g", criteria=standard_criteria(require_review=False))
        )
        ctx = self._ctx(
            specs={"s": "x"},
            plan={"steps": [1]},
            implementation={"code": "x"},
            testing={"tests": "t"},
        )
        assert evaluator.satisfied(ctx) is True
