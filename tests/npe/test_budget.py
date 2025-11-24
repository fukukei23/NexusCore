import json
import threading

import pytest

import nexuscore.npe.budget as budget


@pytest.fixture(autouse=True)
def use_temp_ledger(tmp_path, monkeypatch):
    ledger = tmp_path / "usage.jsonl"
    monkeypatch.setattr(budget, "USAGE_LEDGER", ledger)
    monkeypatch.setattr(budget, "_lock", threading.Lock())
    return ledger


def test_record_usage_and_read_total(tmp_path):
    budget.record_usage("gpt-5", "test", cost_jpy=1.23, prompt_tokens=100, completion_tokens=20)
    total = budget._read_today_total()
    assert total >= 1.23


def test_preflight_check_blocks_per_call(monkeypatch):
    monkeypatch.setattr(budget, "PER_CALL_CAP_JPY", 0.1)
    decision = budget.preflight_check(
        model="gpt-5",
        task="heavy",
        est_prompt_tokens=1000,
        est_completion_tokens=1000,
    )
    assert decision.allow is False
    assert "per-call cap" in decision.reason


def test_preflight_check_block_daily_hard(monkeypatch):
    monkeypatch.setattr(budget, "_read_today_total", lambda: 2000.0)
    monkeypatch.setattr(budget, "DAILY_HARD_CAP_JPY", 1000.0)
    decision = budget.preflight_check(
        model="gpt-5",
        task="daily",
        est_prompt_tokens=100,
        est_completion_tokens=100,
    )
    assert decision.allow is False
    assert "daily hard cap" in decision.reason
