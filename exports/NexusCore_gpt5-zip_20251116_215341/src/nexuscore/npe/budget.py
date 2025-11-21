# ==============================================================================
# File: src/nexuscore/npe/budget.py
# Purpose:
#   - LLMコールの事前予算判定と事後利用記録
#   - モデル別コスト表（概算）に基づく上限制御（ソフト／ハード）
#   - 1リクエスト上限 / 日次上限 / 用途別ホワイトリスト
# Notes:
#   - 実測トークンが取れる場合は事後で再精算（engine側で補正）
#   - ここは「ルータの前に立つ保安員」。依存は最小限に保つ
# ==============================================================================
from __future__ import annotations
import dataclasses
import json
import os
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any

# -------- コスト表（概算, JPY/1k tokens）--------------------------------------
# 必要なら環境変数で上書き（例: NPE_COST_OPENAI_GPT5_PROMPT=1.5）
DEFAULT_COST_TABLE = {
    "gpt-5":                {"prompt": 1.6, "completion": 5.0},
    "gpt-5-mini":           {"prompt": 0.2, "completion": 0.6},
    "gemini-2.5-pro":       {"prompt": 1.2, "completion": 3.0},
    "gemini-2.5-flash":     {"prompt": 0.15, "completion": 0.30},
    "kimi-k2-turbo-preview": {"prompt": 0.20, "completion": 0.40},
    "deepseek-coder":       {"prompt": 0.14, "completion": 0.28},
}

def _cost(model: str, kind: str) -> float:
    # env override: NPE_COST_{MODEL_UPPER}_{PROMPT|COMPLETION}
    key = f"NPE_COST_{model.replace('-', '_').upper()}_{'PROMPT' if kind=='prompt' else 'COMPLETION'}"
    if key in os.environ:
        try:
            return float(os.environ[key])
        except Exception:
            pass
    return DEFAULT_COST_TABLE.get(model, DEFAULT_COST_TABLE["gpt-5"]).get(kind, 1.0)

# -------- 設定 ----------------------------------------------------------------
def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, default))
    except Exception:
        return default

def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, default))
    except Exception:
        return default

DAILY_HARD_CAP_JPY   = _env_float("NPE_DAILY_HARD_CAP_JPY",   1500.0)  # 例: 1,500円/日
DAILY_SOFT_CAP_JPY   = _env_float("NPE_DAILY_SOFT_CAP_JPY",   1000.0)  # ソフト警告ライン
PER_CALL_CAP_JPY     = _env_float("NPE_PER_CALL_CAP_JPY",       80.0)  # 1回上限
ALLOW_WHEN_OVER_SOFT = os.getenv("NPE_ALLOW_OVER_SOFT", "true").lower() == "true"

AUDIT_DIR = Path(os.getenv("NPE_AUDIT_DIR", "logs/npe"))
AUDIT_DIR.mkdir(parents=True, exist_ok=True)
USAGE_LEDGER = AUDIT_DIR / "usage_ledger.jsonl"
_lock = threading.Lock()

# -------- データクラス ---------------------------------------------------------
@dataclasses.dataclass
class BudgetDecision:
    allow: bool
    reason: str
    est_cost_jpy: float
    est_prompt_tokens: int
    est_completion_tokens: int
    caps: Dict[str, Any]

def _now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def _day_key(ts: Optional[float] = None) -> str:
    return time.strftime("%Y-%m-%d", time.gmtime(ts or time.time()))

def _estimate_cost_jpy(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    jp = _cost(model, "prompt")
    jc = _cost(model, "completion")
    return (prompt_tokens / 1000.0) * jp + (completion_tokens / 1000.0) * jc

def _read_today_total() -> float:
    total = 0.0
    day = _day_key()
    if not USAGE_LEDGER.exists():
        return 0.0
    with _lock:
        try:
            with USAGE_LEDGER.open("r", encoding="utf-8") as f:
                for line in f:
                    try:
                        row = json.loads(line)
                        if row.get("day") == day:
                            total += float(row.get("cost_jpy", 0.0))
                    except Exception:
                        continue
        except Exception:
            return total
    return total

def record_usage(model: str, task: str, cost_jpy: float, prompt_tokens: int, completion_tokens: int) -> None:
    entry = {
        "ts_utc": _now_utc_iso(),
        "day": _day_key(),
        "model": model,
        "task": task,
        "cost_jpy": round(cost_jpy, 6),
        "prompt_tokens": int(prompt_tokens),
        "completion_tokens": int(completion_tokens),
        "source": "post_call",  # 事後記録
    }
    with _lock:
        try:
            with USAGE_LEDGER.open("a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception:
            # 失敗時はコンソールに出すだけ（致命にしない）
            print("[NPE-Budget] WARN: failed to append usage_ledger")

def preflight_check(
    *,
    model: str,
    task: str,
    est_prompt_tokens: int,
    est_completion_tokens: int
) -> BudgetDecision:
    """実行前の見積りで上限制御を行う。"""
    est_cost = _estimate_cost_jpy(model, est_prompt_tokens, est_completion_tokens)

    # 1回上限
    if est_cost > PER_CALL_CAP_JPY:
        return BudgetDecision(
            allow=False,
            reason=f"per-call cap exceeded: est {est_cost:.2f} JPY > {PER_CALL_CAP_JPY:.2f}",
            est_cost_jpy=est_cost,
            est_prompt_tokens=est_prompt_tokens,
            est_completion_tokens=est_completion_tokens,
            caps={
                "per_call_cap_jpy": PER_CALL_CAP_JPY,
                "daily_soft_cap_jpy": DAILY_SOFT_CAP_JPY,
                "daily_hard_cap_jpy": DAILY_HARD_CAP_JPY,
                "today_total_jpy": _read_today_total(),
            },
        )

    # 日次上限
    today_total = _read_today_total()
    after_cost = today_total + est_cost
    if after_cost > DAILY_HARD_CAP_JPY:
        return BudgetDecision(
            allow=False,
            reason=f"daily hard cap exceeded: {after_cost:.2f} JPY > {DAILY_HARD_CAP_JPY:.2f}",
            est_cost_jpy=est_cost,
            est_prompt_tokens=est_prompt_tokens,
            est_completion_tokens=est_completion_tokens,
            caps={
                "per_call_cap_jpy": PER_CALL_CAP_JPY,
                "daily_soft_cap_jpy": DAILY_SOFT_CAP_JPY,
                "daily_hard_cap_jpy": DAILY_HARD_CAP_JPY,
                "today_total_jpy": today_total,
            },
        )

    # ソフト上限（許可だが理由を返す）
    if after_cost > DAILY_SOFT_CAP_JPY and not ALLOW_WHEN_OVER_SOFT:
        return BudgetDecision(
            allow=False,
            reason=f"over daily soft cap and ALLOW_WHEN_OVER_SOFT=false: {after_cost:.2f} JPY > {DAILY_SOFT_CAP_JPY:.2f}",
            est_cost_jpy=est_cost,
            est_prompt_tokens=est_prompt_tokens,
            est_completion_tokens=est_completion_tokens,
            caps={
                "per_call_cap_jpy": PER_CALL_CAP_JPY,
                "daily_soft_cap_jpy": DAILY_SOFT_CAP_JPY,
                "daily_hard_cap_jpy": DAILY_HARD_CAP_JPY,
                "today_total_jpy": today_total,
            },
        )

    return BudgetDecision(
        allow=True,
        reason="ok",
        est_cost_jpy=est_cost,
        est_prompt_tokens=est_prompt_tokens,
        est_completion_tokens=est_completion_tokens,
        caps={
            "per_call_cap_jpy": PER_CALL_CAP_JPY,
            "daily_soft_cap_jpy": DAILY_SOFT_CAP_JPY,
            "daily_hard_cap_jpy": DAILY_HARD_CAP_JPY,
            "today_total_jpy": today_total,
        },
    )

def record_estimate(model: str, task: str, decision: BudgetDecision) -> None:
    """事前見積りを台帳に“仮記録”。後で実測で補正する。"""
    entry = {
        "ts_utc": _now_utc_iso(),
        "day": _day_key(),
        "model": model,
        "task": task,
        "cost_jpy": round(decision.est_cost_jpy, 6),
        "prompt_tokens": decision.est_prompt_tokens,
        "completion_tokens": decision.est_completion_tokens,
        "source": "preflight",  # 事前記録
        "allow": decision.allow,
        "reason": decision.reason,
        "caps": decision.caps,
    }
    with _lock:
        try:
            with USAGE_LEDGER.open("a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception:
            print("[NPE-Budget] WARN: failed to append preflight ledger")
