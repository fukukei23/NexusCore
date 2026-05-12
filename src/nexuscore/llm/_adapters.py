"""Budget and logging adapters for LLMRouter.

Auto-detects NPE v1/v2/none and provides a unified interface.
Extracted from llm_router.py for maintainability.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

# ---- BudgetManager adapter ------------------------------------------------

try:
    from nexuscore.npe import budget as _budget_mod

    BUDGET_API = "v2"

    class BudgetManager:
        def __init__(self, daily_limit_usd: float | None = None, log_dir=None):
            self._b = _budget_mod

        def check_budget(self, model_name: str, est_input_tokens: int) -> tuple[bool, float]:
            try:
                return self._b.preflight_check(
                    model_name=model_name, est_input_tokens=est_input_tokens
                )
            except Exception:
                return True, 0.0

        def track_cost(self, model_name: str, input_tokens: int, output_tokens: int) -> float:
            try:
                return self._b.record_usage(
                    model_name=model_name,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                )
            except Exception:
                return 0.0

except Exception:
    BUDGET_API = "none"

    class BudgetManager:  # type: ignore[no-redef]
        def __init__(self, daily_limit_usd: float | None = None, log_dir=None):
            logging.getLogger("LLMRouter").warning(
                "[Budget] No BudgetManager found. Running with NO budget guard!"
            )

        def check_budget(self, model_name: str, est_input_tokens: int) -> tuple[bool, float]:
            return True, 0.0

        def track_cost(self, model_name: str, input_tokens: int, output_tokens: int) -> float:
            return 0.0


# ---- Logger adapter -------------------------------------------------------

try:
    from nexuscore.npe.logger import log_transaction  # v1
except Exception:
    try:
        from nexuscore.npe import logger as _logger_v2

        log_transaction = _logger_v2.log_transaction
    except Exception:

        def log_transaction(payload: dict, log_file: str):
            try:
                Path(log_file).parent.mkdir(parents=True, exist_ok=True)
                with open(log_file, "a", encoding="utf-8") as f:
                    f.write(json.dumps(payload, ensure_ascii=False) + "\n")
            except Exception as e:
                logging.getLogger("LLMRouter").warning(
                    "[LogTransaction] Failed to write log file %s: %s", log_file, e
                )
