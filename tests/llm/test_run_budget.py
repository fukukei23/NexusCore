"""RunIOBudget（Run全体タイムアウト予算・方向1v3.1 gem#1 critical）のテスト。

v3.1設計:
- Run全体の I/O ブロック+sleep 合計の絶対予算（既定450秒・env NEXUS_RUN_IO_BUDGET_SEC）
- 予算消費 ≥80% で新規呼出を fail-fast（RunBudgetExhausted）
- 構造化ログ用に consumed / remaining を参照可能
"""

import pytest

from nexuscore.llm.run_budget import RunBudgetExhausted, RunIOBudget


class TestRunIOBudgetInit:
    """初期化とenv連動のテスト"""

    def test_default_budget_450_seconds(self, monkeypatch):
        monkeypatch.delenv("NEXUS_RUN_IO_BUDGET_SEC", raising=False)
        budget = RunIOBudget()
        assert budget.total_seconds == 450.0

    def test_env_override(self, monkeypatch):
        monkeypatch.setenv("NEXUS_RUN_IO_BUDGET_SEC", "600")
        budget = RunIOBudget()
        assert budget.total_seconds == 600.0

    def test_env_invalid_value_falls_back_to_default(self, monkeypatch):
        monkeypatch.setenv("NEXUS_RUN_IO_BUDGET_SEC", "not-a-number")
        budget = RunIOBudget()
        assert budget.total_seconds == 450.0

    def test_explicit_argument_overrides_env(self, monkeypatch):
        monkeypatch.setenv("NEXUS_RUN_IO_BUDGET_SEC", "600")
        budget = RunIOBudget(total_seconds=300.0)
        assert budget.total_seconds == 300.0


class TestRunIOBudgetConsume:
    """consume の算術テスト"""

    def test_consume_reduces_remaining(self):
        budget = RunIOBudget(total_seconds=450.0)
        budget.consume(120.0)
        assert budget.remaining == pytest.approx(330.0)
        assert budget.consumed == pytest.approx(120.0)

    def test_consume_multiple_times_accumulates(self):
        budget = RunIOBudget(total_seconds=450.0)
        budget.consume(120.0)
        budget.consume(120.0)
        assert budget.consumed == pytest.approx(240.0)

    def test_consume_clamps_at_total(self):
        """消費が予算を超えても remaining は負にならない"""
        budget = RunIOBudget(total_seconds=450.0)
        budget.consume(500.0)
        assert budget.remaining == 0.0
        assert budget.consumed == pytest.approx(500.0)

    def test_consume_negative_is_ignored(self):
        budget = RunIOBudget(total_seconds=450.0)
        budget.consume(-10.0)
        assert budget.consumed == 0.0


class TestRunIOBudgetGate:
    """予算消費 ≥80% で新規呼出 fail-fast（gem#1）のテスト"""

    def test_call_allowed_under_80_percent(self):
        budget = RunIOBudget(total_seconds=450.0)
        budget.consume(359.0)  # 79.8%
        assert budget.try_acquire_call() is True

    def test_call_rejected_at_or_over_80_percent(self):
        budget = RunIOBudget(total_seconds=450.0)
        budget.consume(360.0)  # 80.0%
        assert budget.try_acquire_call() is False

    def test_rejection_raises_via_check(self):
        budget = RunIOBudget(total_seconds=450.0)
        budget.consume(400.0)
        with pytest.raises(RunBudgetExhausted):
            budget.check_available()

    def test_check_available_passes_when_fresh(self):
        budget = RunIOBudget(total_seconds=450.0)
        budget.check_available()  # 例外が出ないこと

    def test_run_budget_exhausted_is_runtime_error(self):
        assert issubclass(RunBudgetExhausted, RuntimeError)

    def test_exhausted_error_contains_budget_info(self):
        budget = RunIOBudget(total_seconds=450.0)
        budget.consume(400.0)
        with pytest.raises(RunBudgetExhausted) as exc_info:
            budget.check_available()
        assert "450" in str(exc_info.value)
        assert "400" in str(exc_info.value)


class TestRunIOBudgetReset:
    """run単位リセット（プロセス=1run前提のsingleton運用）"""

    def test_reset_restores_full_budget(self):
        budget = RunIOBudget(total_seconds=450.0)
        budget.consume(200.0)
        budget.reset()
        assert budget.consumed == 0.0
        assert budget.remaining == 450.0

    def test_global_singleton_and_reset(self, monkeypatch):
        from nexuscore.llm import run_budget as rb

        monkeypatch.delenv("NEXUS_RUN_IO_BUDGET_SEC", raising=False)
        b1 = rb.get_run_budget()
        b2 = rb.get_run_budget()
        assert b1 is b2
        b1.consume(100.0)
        rb.reset_run_budget()
        b3 = rb.get_run_budget()
        assert b3.consumed == 0.0
