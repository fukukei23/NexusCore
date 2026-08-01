from __future__ import annotations

import json
import logging
from pathlib import Path

# ---- BudgetManager adapter ------------------------------------------------

try:
    from nexuscore.npe import budget as _budget_mod

    BUDGET_API = "v2"

    class BudgetManager:
        """LLMコスト予算管理のアダプター（npe.budget への委譲）。"""

        def __init__(self, daily_limit_usd: float | None = None, log_dir=None):
            """BudgetManager を初期化する（引数は互換用・実際の設定は npe.budget が保持）。"""
            self._b = _budget_mod

        def check_budget(self, model_name: str, est_input_tokens: int) -> tuple[bool, float]:
            """実行前の予算チェック。(許可, 推定コスト) を返す。失敗時は実行を許可。"""
            try:
                return self._b.preflight_check(
                    model_name=model_name, est_input_tokens=est_input_tokens
                )
            except Exception:  # noqa: BLE001 — budget check failure allows execution
                return True, 0.0

        def track_cost(self, model_name: str, input_tokens: int, output_tokens: int) -> float:
            """実行後のコスト記録。記録失敗時は 0.0 を返す。"""
            try:
                return self._b.record_usage(
                    model_name=model_name,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                )
            except Exception:  # noqa: BLE001 — tracking failure returns 0
                return 0.0

except ImportError:
    BUDGET_API = "none"

    class BudgetManager:  # type: ignore[no-redef]
        """BudgetManager が利用不可時のフォールバック（予算ガードなしで実行を許可）。"""

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
except ImportError:
    try:
        from nexuscore.npe import logger as _logger_v2

        log_transaction = _logger_v2.log_transaction
    except ImportError:

        def log_transaction(payload: dict, log_file: str):
            """監査ログをJSONL追記するフォールバック（npe.logger 未可用時）。"""
            try:
                Path(log_file).parent.mkdir(parents=True, exist_ok=True)
                with open(log_file, "a", encoding="utf-8") as f:
                    f.write(json.dumps(payload, ensure_ascii=False) + "\n")
            except OSError as e:
                logging.getLogger("LLMRouter").warning(
                    "[LogTransaction] Failed to write log file %s: %s", log_file, e
                )
