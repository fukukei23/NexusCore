# ==============================================================================
# File: src/nexuscore/npe/engine.py
# Purpose:
#   - LLM実行の直前直後に BudgetGuard を噛ませる
#   - 推定トークンで事前判定 → 実行後に実測で再記録
# ==============================================================================
from __future__ import annotations

import math
from typing import Any

from . import budget
from .logger import log_transaction

TOKEN_AVG_CHARS = 3.8  # 粗い見積り。必要ならモデル別に補正


def _estimate_tokens(text: str) -> int:
    # 依存を増やさず簡易見積
    if not text:
        return 0
    return max(1, int(math.ceil(len(text) / TOKEN_AVG_CHARS)))


def guarded_llm_call(
    *,
    model: str,
    task: str,
    system_prompt: str,
    user_prompt: str,
    llm_complete_fn,
) -> dict[str, Any]:
    """
    予算ガード付きで LLM を実行する。
      - llm_complete_fn は (model, system_prompt, user_prompt) -> dict を想定
      - 戻り値は {"ok": bool, "reason": str, "content": str, "usage": {...}} を基本とする
    """
    # ---- 事前見積り ----------------------------------------------------------
    est_prompt_tokens = _estimate_tokens(system_prompt) + _estimate_tokens(user_prompt)
    est_completion_tokens = 512  # ワースト見積り（必要なら呼び出し側から渡す仕様に拡張可）

    decision = budget.preflight_check(
        model=model,
        task=task,
        est_prompt_tokens=est_prompt_tokens,
        est_completion_tokens=est_completion_tokens,
    )
    budget.record_estimate(model, task, decision)

    if not decision.allow:
        log_transaction(
            {
                "event": "llm_blocked",
                "model": model,
                "task": task,
                "reason": decision.reason,
                "est_cost_jpy": decision.est_cost_jpy,
                "caps": decision.caps,
            }
        )
        return {
            "ok": False,
            "reason": f"Budget guard rejected: {decision.reason}",
            "content": "",
            "usage": {
                "prompt_tokens": est_prompt_tokens,
                "completion_tokens": 0,
                "cost_estimated_jpy": decision.est_cost_jpy,
            },
        }

    # ---- 実行 ----------------------------------------------------------------
    result = llm_complete_fn(model=model, system_prompt=system_prompt, user_prompt=user_prompt)

    # ---- 実測使用量の確定（なければ推定のまま）--------------------------------
    usage = result.get("usage", {}) if isinstance(result, dict) else {}
    pt = usage.get("prompt_tokens", est_prompt_tokens)
    ct = usage.get(
        "completion_tokens",
        _estimate_tokens(result.get("content", "")) if isinstance(result, dict) else 0,
    )
    cost = budget._estimate_cost_jpy(model, pt, ct)
    budget.record_usage(
        model=model, task=task, cost_jpy=cost, prompt_tokens=pt, completion_tokens=ct
    )

    # ---- 監査ログ ------------------------------------------------------------
    log_transaction(
        {
            "event": "llm_call",
            "model": model,
            "task": task,
            "ok": bool(result.get("ok", True)) if isinstance(result, dict) else True,
            "reason": result.get("reason", "") if isinstance(result, dict) else "",
            "usage": {"prompt_tokens": pt, "completion_tokens": ct, "cost_jpy": round(cost, 6)},
        }
    )

    # ---- 返却 ---------------------------------------------------------------
    if isinstance(result, dict):
        result.setdefault("usage", {})
        result["usage"].update({"prompt_tokens": pt, "completion_tokens": ct, "cost_jpy": cost})
        return result
    return {
        "ok": True,
        "reason": "",
        "content": str(result),
        "usage": {"prompt_tokens": pt, "completion_tokens": ct, "cost_jpy": cost},
    }
