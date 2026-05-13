from __future__ import annotations

import logging
import time

from nexuscore.llm._adapters import log_transaction
from nexuscore.llm._router_utils import estimate_tokens
from nexuscore.llm.providers.base import BaseLLM
from nexuscore.llm.routing_policy import model_family


class RoutedLLM(BaseLLM):
    """
    LLMRouter.get_llm_for_task() が返す実体。
    vendor LLM クライアント(self.inner)を包んで、
    execute() 時に BudgetManager と log_transaction を噛ませる。
    """

    def __init__(
        self,
        inner_llm: BaseLLM,
        router,  # LLMRouter — circular import回避のため型注釈なし
        task_type: str,
    ):
        super().__init__(inner_llm.model_name)
        self.inner = inner_llm
        self.router = router
        self.task_type = task_type
        self.logger = logging.getLogger("RoutedLLM")

    def _estimate_tokens(self, text: str) -> int:
        return estimate_tokens(text)

    def execute(self, prompt: str, system_prompt: str, **kwargs) -> str:
        """
        1. 予算チェック
        2. inner_llm.execute() 呼び出し
        3. 実トークン/推定トークン決定
        4. コスト記録
        5. 呼び出しログをJSONLに追記
        """
        started_at = time.time()

        # --- 1) 予算チェック ---
        in_tokens = estimate_tokens(prompt + "\n" + system_prompt)
        can_run, est_cost = self.router.budget_manager.check_budget(
            model_name=self.model_name,
            est_input_tokens=in_tokens,
        )
        if not can_run:
            raise RuntimeError(
                f"[LLMRouter] Budget limit exceeded for model={self.model_name}. "
                f"estimated_cost_usd={est_cost}"
            )

        # --- 2) 実際のLLM呼び出し ---
        self.inner._last_usage = None
        temp_override = self.router.task_temperature_overrides.get(self.task_type)
        if temp_override is not None and "temperature" not in kwargs:
            kwargs["temperature"] = temp_override
        output_text = self.inner.execute(prompt, system_prompt, **kwargs)
        self.router.last_mode = getattr(self.inner, "last_call_mode", "stub")

        # --- 3) 実コスト記録 ---
        out_tokens = 0
        if getattr(self.inner, "_last_usage", None):
            u = self.inner._last_usage
            in_tokens_real = u.get("prompt_tokens")
            if in_tokens_real:
                in_tokens = int(in_tokens_real)
            out_tokens_real = u.get("completion_tokens")
            if out_tokens_real:
                out_tokens = int(out_tokens_real)
            else:
                out_tokens = estimate_tokens(output_text)

        if out_tokens == 0:
            out_tokens = estimate_tokens(output_text)

        actual_cost = self.router.budget_manager.track_cost(
            model_name=self.model_name,
            input_tokens=in_tokens,
            output_tokens=out_tokens,
        )

        duration_s = time.time() - started_at

        # --- 4) 呼び出しログ(JSONL) ---
        log_transaction(
            {
                "ts": time.time(),
                "task_type": self.task_type,
                "model": self.model_name,
                "provider": model_family(self.model_name),
                "mode": getattr(self.inner, "last_call_mode", "stub"),
                "input_tokens": in_tokens,
                "output_tokens": out_tokens,
                "input_tokens_est": in_tokens,
                "output_tokens_est": out_tokens,
                "cost_est_usd": actual_cost,
                "duration_sec": duration_s,
                "prompt_preview": prompt[:200],
            },
            log_file=self.router.call_log_path,
        )

        return output_text
