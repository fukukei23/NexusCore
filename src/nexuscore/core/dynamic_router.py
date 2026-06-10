"""CR-NEXUS-054: アクション登録と次アクション選択（ルールベース）。

ActionRegistry は既存 Orchestrator の run_*_phase をアクションとして登録し、
RuleBasedRouter が「未達条件 → 次の一手」を決定的に選択する。LLM コストゼロ。
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from nexuscore.core.goal_spec import CriterionResult
from nexuscore.core.orchestrator_models import OrchestratorContext

PhaseFn = Callable[[OrchestratorContext], OrchestratorContext]


@dataclass(frozen=True)
class ActionDecision:
    """ルーターの判断結果。reason は DecisionTrace 経由で説明可能性に使う。"""

    action: str | None  # None = 打つ手なし（ルーター降参）
    reason: str


@dataclass
class ActionRegistry:
    """アクション名 → フェーズ実行関数のレジストリ。"""

    actions: dict[str, PhaseFn] = field(default_factory=dict)

    def register(self, name: str, fn: PhaseFn) -> None:
        self.actions[name] = fn

    def has(self, name: str) -> bool:
        return name in self.actions

    def execute(self, name: str, context: OrchestratorContext) -> OrchestratorContext:
        if name not in self.actions:
            raise KeyError(f"Unknown action: {name}")
        return self.actions[name](context)

    @classmethod
    def from_orchestrator(cls, orchestrator: Any) -> ActionRegistry:
        """既存 Orchestrator(PhaseRunnerMixin) からアクションを自動登録する。"""
        registry = cls()
        phase_methods = {
            "context": "run_context_phase",
            "requirements": "run_requirements_phase",
            "planning": "run_planning_phase",
            "architecture": "run_architecture_phase",
            "implementation": "run_implementation_phase",
            "testing": "run_testing_phase",
            "review": "run_review_phase",
        }
        for action, method_name in phase_methods.items():
            method = getattr(orchestrator, method_name, None)
            if callable(method):
                registry.register(action, method)
        return registry


class RuleBasedRouter:
    """未達条件と直前の失敗から次アクションを選ぶ決定的ルーター。

    ルール（優先順）:
    1. 直前に失敗したアクションは、リトライ残があれば同じものを再実行
    2. 未達条件のうち依存順（specs→plan→code→tests→review）で最初のものに対応するアクション
    3. 対応アクションが skip_actions または未登録なら次の未達条件へ
    4. どれにも対応できなければ None（降参）
    """

    # 条件名 → それを満たすためのアクション（依存順）
    CRITERION_TO_ACTION: dict[str, str] = {
        "has_specs": "requirements",
        "has_plan": "planning",
        "has_implementation": "implementation",
        "has_tests": "testing",
        "review_done": "review",
    }
    DEPENDENCY_ORDER: list[str] = [
        "has_specs",
        "has_plan",
        "has_implementation",
        "has_tests",
        "review_done",
    ]

    def __init__(
        self,
        registry: ActionRegistry,
        skip_actions: frozenset[str] = frozenset(),
        criterion_to_action: dict[str, str] | None = None,
    ) -> None:
        self.registry = registry
        self.skip_actions = skip_actions
        self.criterion_to_action = criterion_to_action or dict(self.CRITERION_TO_ACTION)

    def next_action(
        self,
        unsatisfied: list[CriterionResult],
        last_failed_action: str | None = None,
        retries_left_for_failed: int = 0,
    ) -> ActionDecision:
        # ルール1: 失敗アクションのリトライ
        if last_failed_action and retries_left_for_failed > 0:
            return ActionDecision(
                action=last_failed_action,
                reason=(
                    f"直前の '{last_failed_action}' が失敗。"
                    f"リトライ残 {retries_left_for_failed} 回のため再実行"
                ),
            )

        # ルール2-3: 依存順で最初の未達条件に対応するアクション
        unsatisfied_names = {r.name for r in unsatisfied}
        ordered = [n for n in self.DEPENDENCY_ORDER if n in unsatisfied_names]
        # 標準セット外のカスタム条件は依存順の後ろに回す
        ordered += [r.name for r in unsatisfied if r.name not in self.DEPENDENCY_ORDER]

        for name in ordered:
            action = self.criterion_to_action.get(name)
            if action is None:
                continue  # 対応アクション未定義のカスタム条件
            if action in self.skip_actions:
                continue
            if not self.registry.has(action):
                continue
            return ActionDecision(
                action=action,
                reason=f"未達条件 '{name}' を満たすため '{action}' を選択",
            )

        if not unsatisfied:
            return ActionDecision(action=None, reason="全条件達成済み。実行不要")
        return ActionDecision(
            action=None,
            reason=(
                "未達条件 "
                + ", ".join(sorted(unsatisfied_names))
                + " に対応できるアクションがない（skip指定または未登録）"
            ),
        )
