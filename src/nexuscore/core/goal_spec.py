"""CR-NEXUS-054: ゴール定義と達成判定。

GoalSpec はゴール（達成条件・予算・スキップ指定）を宣言的に表現し、
GoalEvaluator が OrchestratorContext を採点する。LLM は使わない（決定的）。
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from nexuscore.core.orchestrator_models import OrchestratorContext


@dataclass(frozen=True)
class SuccessCriterion:
    """ゴール達成条件1件。check は Context を受け取り bool を返す純粋関数。"""

    name: str
    check: Callable[[OrchestratorContext], bool]
    description: str = ""


@dataclass(frozen=True)
class CriterionResult:
    """1条件の評価結果。"""

    name: str
    satisfied: bool
    description: str = ""


@dataclass
class GoalSpec:
    """ゴール宣言。run_full_project の固定フェーズ消化に代わる完了定義。"""

    description: str
    criteria: list[SuccessCriterion]
    max_actions: int = 12
    max_retries_per_action: int = 2
    skip_actions: frozenset[str] = field(default_factory=frozenset)

    def __post_init__(self) -> None:
        if not self.criteria:
            raise ValueError("GoalSpec requires at least one SuccessCriterion")
        if self.max_actions < 1:
            raise ValueError("max_actions must be >= 1")
        if self.max_retries_per_action < 0:
            raise ValueError("max_retries_per_action must be >= 0")


class GoalEvaluator:
    """GoalSpec の条件群を Context に対して評価する。"""

    def __init__(self, goal: GoalSpec) -> None:
        self.goal = goal

    def evaluate(self, context: OrchestratorContext) -> list[CriterionResult]:
        results: list[CriterionResult] = []
        for criterion in self.goal.criteria:
            try:
                ok = bool(criterion.check(context))
            except Exception:  # noqa: BLE001 — 条件評価の失敗は「未達」として扱う
                ok = False
            results.append(
                CriterionResult(
                    name=criterion.name,
                    satisfied=ok,
                    description=criterion.description,
                )
            )
        return results

    def unsatisfied(self, context: OrchestratorContext) -> list[CriterionResult]:
        return [r for r in self.evaluate(context) if not r.satisfied]

    def satisfied(self, context: OrchestratorContext) -> bool:
        return not self.unsatisfied(context)


# ----------------------------------------------------------------------
# 標準クライテリア（Context の成果物スロットに対応）
# ----------------------------------------------------------------------

def _non_empty(value: object) -> bool:
    return bool(value)


def standard_criteria(
    require_tests: bool = True,
    require_review: bool = True,
) -> list[SuccessCriterion]:
    """run_full_project 相当の成果物を要求する標準条件セット。"""
    criteria = [
        SuccessCriterion(
            name="has_specs",
            check=lambda ctx: _non_empty(ctx.specs),
            description="要件仕様が生成されている",
        ),
        SuccessCriterion(
            name="has_plan",
            check=lambda ctx: _non_empty(ctx.plan) and "error" not in ctx.plan,
            description="実装計画が生成されている",
        ),
        SuccessCriterion(
            name="has_implementation",
            check=lambda ctx: _non_empty(ctx.implementation.get("code")),
            description="実装コードが生成されている",
        ),
    ]
    if require_tests:
        criteria.append(
            SuccessCriterion(
                name="has_tests",
                check=lambda ctx: _non_empty(ctx.testing.get("tests")),
                description="テストが生成されている",
            )
        )
    if require_review:
        criteria.append(
            SuccessCriterion(
                name="review_done",
                check=lambda ctx: "REVIEW" in ctx.phase_log,
                description="レビューフェーズを通過している",
            )
        )
    return criteria
