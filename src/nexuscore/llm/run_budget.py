"""Run全体タイムアウト予算（方向1v3.1 gem#1 critical・2026-09-26実装）。

- Run全体の「I/Oブロック+sleep合計」の絶対予算（既定450秒・env NEXUS_RUN_IO_BUDGET_SEC）
- 予算消費 >=80% で新規呼出を fail-fast（RunBudgetExhausted）
- bench実測（Step 0計測・2026-09-25/26）: timeoutはtest_generate/debugging呼出に集中
  （独立型・連鎖しない）ため、per-call retry短縮とrun予算の組合せが最適解

使い方（プロセス=1run前提のsingleton）:
    from nexuscore.llm.run_budget import get_run_budget, reset_run_budget
    budget = get_run_budget()
    budget.check_available()  # 消費>=80%なら RunBudgetExhausted
    ... HTTP呼出 ...
    budget.consume(elapsed_seconds)
    reset_run_budget()  # run開始時に呼ぶ
"""

from __future__ import annotations

import os
import threading

__all__ = ["RunBudgetExhausted", "RunIOBudget", "get_run_budget", "reset_run_budget"]

DEFAULT_RUN_IO_BUDGET_SEC = 450.0
_ENV_KEY = "NEXUS_RUN_IO_BUDGET_SEC"


class RunBudgetExhausted(RuntimeError):
    """Run全体タイムアウト予算の消費が80%超・新規呼出をfail-fastする。"""


class RunIOBudget:
    """Run単位の I/O 予算（I/Oブロック+sleep合計を累積消費する）。

    Args:
        total_seconds: 予算秒数。Noneなら env NEXUS_RUN_IO_BUDGET_SEC（既定450）。
    """

    def __init__(self, total_seconds: float | None = None) -> None:
        self._lock = threading.Lock()
        self.total_seconds = self._resolve_total(total_seconds)
        self._consumed = 0.0

    @staticmethod
    def _resolve_total(total_seconds: float | None) -> float:
        if total_seconds is not None:
            return float(total_seconds)
        raw = os.environ.get(_ENV_KEY, "")
        try:
            return float(raw)
        except (TypeError, ValueError):
            return DEFAULT_RUN_IO_BUDGET_SEC

    @property
    def consumed(self) -> float:
        """累積消費秒数。"""
        with self._lock:
            return self._consumed

    @property
    def remaining(self) -> float:
        """残予算秒数（total超過分はクランプ・負にならない）。"""
        with self._lock:
            return max(0.0, self.total_seconds - self._consumed)

    def reset(self) -> None:
        """消費を0に戻す（run開始時）。"""
        with self._lock:
            self._consumed = 0.0



    def consume(self, seconds: float) -> None:
        """I/O消費を累積する。負値は無視・total超過時はremaining=0へクランプ。"""
        if seconds is None or seconds <= 0:
            return
        with self._lock:
            self._consumed += float(seconds)

    def usage_ratio(self) -> float:
        """消費比率（0-1・total<=0のとき1.0=常にfail-fast）。"""
        with self._lock:
            if self.total_seconds <= 0:
                return 1.0
            return self._consumed / self.total_seconds

    def try_acquire_call(self) -> bool:
        """新規呼出の可否（消費>=80%ならFalse）。"""
        return self.usage_ratio() < 0.80

    def check_available(self) -> None:
        """消費>=80%なら RunBudgetExhausted を送出（新規呼出前のfail-fast）。"""
        ratio = self.usage_ratio()
        if ratio >= 0.80:
            with self._lock:
                consumed = self._consumed
                total = self.total_seconds
            raise RunBudgetExhausted(
                f"Run I/O budget exhausted: consumed={consumed:.1f}s / "
                f"total={total:.1f}s (usage>=80%). New LLM calls are rejected."
            )


_SINGLETON: RunIOBudget | None = None
_SINGLETON_LOCK = threading.Lock()


def get_run_budget() -> RunIOBudget:
    """プロセス単位のsingleton予算を返す（bench runnerは1プロセス=1run）。"""
    global _SINGLETON
    with _SINGLETON_LOCK:
        if _SINGLETON is None:
            _SINGLETON = RunIOBudget()
        return _SINGLETON


def reset_run_budget() -> None:
    """singleton予算をリセットする（run開始時）。インスタンスは再利用する。"""
    global _SINGLETON
    with _SINGLETON_LOCK:
        if _SINGLETON is None:
            _SINGLETON = RunIOBudget()
        else:
            _SINGLETON.reset()
