"""CR-NEXUS-054: ゴール駆動の動的実行ループ。

DynamicRunLoop は既存 Orchestrator をコンポジションで駆動する。
ゴール達成判定 → 次アクション選択 → 実行 → 記録 を予算内で繰り返し、
失敗時は全体停止ではなく必要なアクションだけ再試行する。
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from typing import Any

from nexuscore.core.dynamic_router import ActionRegistry, RuleBasedRouter
from nexuscore.core.goal_spec import GoalEvaluator, GoalSpec
from nexuscore.core.orchestrator_models import OrchestratorContext

_logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TraceEntry:
    """1ステップ分のルーティング記録（説明可能性の単位）。"""

    step: int
    action: str
    reason: str
    succeeded: bool
    error: str = ""
    unsatisfied_before: tuple[str, ...] = ()


@dataclass
class DecisionTrace:
    """全ステップのルーティング判断履歴。"""

    entries: list[TraceEntry] = field(default_factory=list)

    def record(self, entry: TraceEntry) -> None:
        self.entries.append(entry)

    def summary(self) -> str:
        lines = []
        for e in self.entries:
            mark = "OK" if e.succeeded else "NG"
            line = f"[{e.step}] {e.action} ({mark}) — {e.reason}"
            if e.error:
                line += f" / error: {e.error}"
            lines.append(line)
        return "\n".join(lines)


@dataclass
class GoalResult:
    """動的実行ループの最終結果。例外で落とさず必ずこれを返す。"""

    success: bool
    message: str
    context: OrchestratorContext
    trace: DecisionTrace
    actions_executed: int = 0
    unsatisfied_criteria: tuple[str, ...] = ()


class DynamicRunLoop:
    """ゴール駆動ループ本体。既存 Orchestrator は無改変のまま外側から駆動する。"""

    def __init__(
        self,
        orchestrator: Any,
        goal: GoalSpec,
        registry: ActionRegistry | None = None,
        router: RuleBasedRouter | None = None,
    ) -> None:
        self.orchestrator = orchestrator
        self.goal = goal
        self.evaluator = GoalEvaluator(goal)
        self.registry = registry or ActionRegistry.from_orchestrator(orchestrator)
        self.router = router or RuleBasedRouter(
            registry=self.registry,
            skip_actions=goal.skip_actions,
        )
        self.logger = getattr(orchestrator, "logger", None) or _logger

    def run(
        self,
        user_requirement: str,
        language: str = "ja",
        run_db_id: int | None = None,
        context: OrchestratorContext | None = None,
    ) -> GoalResult:
        """ゴール達成までアクションを動的に選択・実行する。

        既存 context を渡すと途中状態から再開できる（達成済み条件はスキップされる）。
        """
        ctx = context or OrchestratorContext(
            task_id=uuid.uuid4().hex,
            user_requirement=user_requirement,
            language=language,
            run_db_id=run_db_id,
        )
        trace = DecisionTrace()
        actions_executed = 0
        last_failed_action: str | None = None
        retries_left = self.goal.max_retries_per_action

        self.logger.info(
            "[%s] DynamicRunLoop start — goal: %s", ctx.task_id, self.goal.description
        )

        while actions_executed < self.goal.max_actions:
            unsatisfied = self.evaluator.unsatisfied(ctx)
            if not unsatisfied:
                self.logger.info(
                    "[%s] Goal satisfied after %d actions", ctx.task_id, actions_executed
                )
                return GoalResult(
                    success=True,
                    message=f"ゴール達成（{actions_executed}アクション実行）",
                    context=ctx,
                    trace=trace,
                    actions_executed=actions_executed,
                )

            decision = self.router.next_action(
                unsatisfied=unsatisfied,
                last_failed_action=last_failed_action,
                retries_left_for_failed=retries_left if last_failed_action else 0,
            )
            if decision.action is None:
                return GoalResult(
                    success=False,
                    message=f"打つ手がありません: {decision.reason}",
                    context=ctx,
                    trace=trace,
                    actions_executed=actions_executed,
                    unsatisfied_criteria=tuple(r.name for r in unsatisfied),
                )

            unsatisfied_names = tuple(r.name for r in unsatisfied)
            step = actions_executed + 1
            self.logger.info(
                "[%s] Step %d: action=%s (%s)",
                ctx.task_id, step, decision.action, decision.reason,
            )

            try:
                ctx = self.registry.execute(decision.action, ctx)
            except Exception as e:  # noqa: BLE001 — 失敗はループが捕捉しリトライ判断する
                actions_executed += 1
                trace.record(TraceEntry(
                    step=step,
                    action=decision.action,
                    reason=decision.reason,
                    succeeded=False,
                    error=str(e)[:300],
                    unsatisfied_before=unsatisfied_names,
                ))
                if last_failed_action == decision.action:
                    retries_left -= 1
                else:
                    last_failed_action = decision.action
                    retries_left = self.goal.max_retries_per_action
                if retries_left <= 0:
                    self.logger.error(
                        "[%s] Action '%s' exhausted retries: %s",
                        ctx.task_id, decision.action, e,
                    )
                    return GoalResult(
                        success=False,
                        message=(
                            f"アクション '{decision.action}' がリトライ上限"
                            f"（{self.goal.max_retries_per_action}回）を超えて失敗: {str(e)[:200]}"
                        ),
                        context=ctx,
                        trace=trace,
                        actions_executed=actions_executed,
                        unsatisfied_criteria=unsatisfied_names,
                    )
                self.logger.warning(
                    "[%s] Action '%s' failed (retries left %d): %s",
                    ctx.task_id, decision.action, retries_left, e,
                )
                continue

            actions_executed += 1
            last_failed_action = None
            retries_left = self.goal.max_retries_per_action
            trace.record(TraceEntry(
                step=step,
                action=decision.action,
                reason=decision.reason,
                succeeded=True,
                unsatisfied_before=unsatisfied_names,
            ))

        unsatisfied = self.evaluator.unsatisfied(ctx)
        if not unsatisfied:
            return GoalResult(
                success=True,
                message=f"ゴール達成（{actions_executed}アクション実行）",
                context=ctx,
                trace=trace,
                actions_executed=actions_executed,
            )
        return GoalResult(
            success=False,
            message=f"アクション予算（{self.goal.max_actions}回）を使い切りました",
            context=ctx,
            trace=trace,
            actions_executed=actions_executed,
            unsatisfied_criteria=tuple(r.name for r in unsatisfied),
        )
