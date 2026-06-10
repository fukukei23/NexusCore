"""CR-NEXUS-054 Phase B: LLM支援ルーティング。

軽量ティアLLMが「次の一手」を提案し、検証に通らない場合は
ルールベース（RuleBasedRouter）に必ずフォールバックする。
リトライ判断は決定的ルールのまま（LLMに委ねない）。
"""

from __future__ import annotations

import json
import logging
import re
from collections.abc import Callable
from typing import Any

from nexuscore.core.dynamic_router import ActionDecision, ActionRegistry, RuleBasedRouter
from nexuscore.core.goal_spec import CriterionResult

_logger = logging.getLogger(__name__)

# propose_fn: (system_prompt, user_prompt) -> 生テキスト（JSON想定）
ProposeFn = Callable[[str, str], str]

_SYSTEM_PROMPT = (
    "You are the routing brain of NexusCore's dynamic orchestrator. "
    "Given a goal, unsatisfied success criteria, and available actions, "
    'choose the single best next action. Respond with strict JSON only: '
    '{"action": "<action_name>", "reason": "<short reason in Japanese>"}'
)


class LLMAssistedRouter:
    """LLM提案 + ルールベース・フォールバックのハイブリッドルーター。

    RuleBasedRouter と同一の next_action インターフェースを持ち、
    DynamicRunLoop にそのまま差し替え可能。
    """

    def __init__(
        self,
        registry: ActionRegistry,
        propose_fn: ProposeFn,
        goal_description: str = "",
        skip_actions: frozenset[str] = frozenset(),
        max_llm_calls: int = 10,
        fallback: RuleBasedRouter | None = None,
    ) -> None:
        self.registry = registry
        self.propose_fn = propose_fn
        self.goal_description = goal_description
        self.skip_actions = skip_actions
        self.max_llm_calls = max_llm_calls
        self.fallback = fallback or RuleBasedRouter(
            registry=registry, skip_actions=skip_actions
        )
        self.llm_calls_used = 0

    # ------------------------------------------------------------------
    # 統合ヘルパー: 既存 LLMRouter から propose_fn を構築
    # ------------------------------------------------------------------
    @classmethod
    def from_llm_router(
        cls,
        llm_router: Any,
        registry: ActionRegistry,
        goal_description: str = "",
        skip_actions: frozenset[str] = frozenset(),
        task: str = "classification",
        **kwargs: Any,
    ) -> LLMAssistedRouter:
        """nexuscore.llm.LLMRouter.complete() を propose_fn に適合させる。

        task は軽量ティアにルーティングされるタスク種別を指定する。
        """

        def propose(system_prompt: str, user_prompt: str) -> str:
            result = llm_router.complete(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                task=task,
                as_json=True,
            )
            if isinstance(result, dict):
                return str(result.get("content", ""))
            return str(result)

        return cls(
            registry=registry,
            propose_fn=propose,
            goal_description=goal_description,
            skip_actions=skip_actions,
            **kwargs,
        )

    # ------------------------------------------------------------------
    # ルーティング本体
    # ------------------------------------------------------------------
    def next_action(
        self,
        unsatisfied: list[CriterionResult],
        last_failed_action: str | None = None,
        retries_left_for_failed: int = 0,
    ) -> ActionDecision:
        # リトライ判断と「未達なし」は決定的ルールに即委譲（LLMコスト節約 + 安全）
        if last_failed_action and retries_left_for_failed > 0:
            return self.fallback.next_action(
                unsatisfied, last_failed_action, retries_left_for_failed
            )
        if not unsatisfied:
            return self.fallback.next_action(unsatisfied)

        if self.llm_calls_used >= self.max_llm_calls:
            decision = self.fallback.next_action(unsatisfied)
            return ActionDecision(
                action=decision.action,
                reason=f"LLM呼び出し予算超過のためルールベースで選択: {decision.reason}",
            )

        available = self._available_actions()
        if not available:
            return self.fallback.next_action(unsatisfied)

        proposal = self._propose(unsatisfied, available)
        if proposal is not None:
            action, reason = proposal
            return ActionDecision(
                action=action,
                reason=f"[LLM提案] {reason}",
            )

        decision = self.fallback.next_action(unsatisfied)
        return ActionDecision(
            action=decision.action,
            reason=f"LLM提案が無効のためルールベースにフォールバック: {decision.reason}",
        )

    # ------------------------------------------------------------------
    # 内部処理
    # ------------------------------------------------------------------
    def _available_actions(self) -> list[str]:
        return sorted(a for a in self.registry.actions if a not in self.skip_actions)

    def _build_prompt(
        self, unsatisfied: list[CriterionResult], available: list[str]
    ) -> str:
        criteria_lines = "\n".join(
            f"- {r.name}: {r.description or '(説明なし)'}" for r in unsatisfied
        )
        return (
            f"## ゴール\n{self.goal_description or '(未指定)'}\n\n"
            f"## 未達の成功条件\n{criteria_lines}\n\n"
            f"## 利用可能なアクション\n{', '.join(available)}\n\n"
            "未達条件を最も効率よく進めるアクションを1つ選び、JSONで返してください。"
        )

    def _propose(
        self, unsatisfied: list[CriterionResult], available: list[str]
    ) -> tuple[str, str] | None:
        """LLMに提案させ、検証に通れば (action, reason) を返す。失敗は None。"""
        self.llm_calls_used += 1
        try:
            raw = self.propose_fn(_SYSTEM_PROMPT, self._build_prompt(unsatisfied, available))
        except Exception as e:  # noqa: BLE001 — LLM障害は必ずフォールバックに倒す
            _logger.warning("LLM routing proposal failed: %s", e)
            return None

        parsed = self._parse_json(raw)
        if not parsed:
            _logger.warning("LLM routing proposal is not valid JSON: %.200s", raw)
            return None

        action = str(parsed.get("action", "")).strip()
        reason = str(parsed.get("reason", "")).strip() or "(理由なし)"
        if action not in available:
            _logger.warning(
                "LLM proposed unavailable action '%s' (available: %s)", action, available
            )
            return None
        return action, reason

    @staticmethod
    def _parse_json(raw: str) -> dict[str, Any] | None:
        try:
            data = json.loads(raw)
            return data if isinstance(data, dict) else None
        except (json.JSONDecodeError, TypeError):
            pass
        # コードブロックや前置きが混ざった応答から {...} を救出
        match = re.search(r"\{.*\}", raw or "", re.DOTALL)
        if match:
            try:
                data = json.loads(match.group(0))
                return data if isinstance(data, dict) else None
            except json.JSONDecodeError:
                return None
        return None
