"""openai_compat への Run全体タイムアウト予算配線（方向1v3.1 gem#1・2026-09-26）のテスト。

検証:
- 予算消費>=80%で新規呼出が fail-fast（RunBudgetExhausted・stub fallbackに濡れない）
- 呼出後に実経過時間が budget.consume される
- ReadTimeout時に構造化ログ（event=llm_timeout・timeout_type・budget残量）が出る
"""

import logging

import pytest
import requests

from nexuscore.llm import run_budget as rb
from nexuscore.llm.providers.glm_provider import GLMLLM


@pytest.fixture(autouse=True)
def _fresh_budget(monkeypatch):
    monkeypatch.delenv("NEXUS_RUN_IO_BUDGET_SEC", raising=False)
    rb.reset_run_budget()
    yield
    rb.reset_run_budget()


class FakeTimeoutResp:
    pass


class FakeTimeoutSession:
    """ReadTimeoutを必ず投げるFake session。"""

    def post(self, *args, **kwargs):
        raise requests.exceptions.ReadTimeout("read timed out. (read timeout=120.0)")


class FakeOKResp:
    def __init__(self) -> None:
        self.text = ""

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return {
            "choices": [{"message": {"content": "ok"}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1},
        }


class FakeOKSession:
    def post(self, *args, **kwargs):
        import time

        time.sleep(0.01)
        return FakeOKResp()


def _make_real_provider(monkeypatch, session):
    monkeypatch.setenv("GLM_API_KEY", "dummy")
    provider = GLMLLM("glm-5.3")
    monkeypatch.setattr(provider, "real_calls", True)
    monkeypatch.setattr(provider, "session", session)
    monkeypatch.setattr(provider, "base_url", "https://api.example.com")
    monkeypatch.setattr(provider, "api_key", "dummy")
    return provider


def test_budget_exhausted_rejects_new_call(monkeypatch):
    """予算消費>=80%で新規呼出がfail-fast（stub fallbackに濡れない）"""
    monkeypatch.delenv("NEXUSCORE_ALLOW_STUB_FALLBACK", raising=False)
    provider = _make_real_provider(monkeypatch, FakeOKSession())
    budget = rb.get_run_budget()
    budget.consume(400.0)  # 450 * 0.8 = 360 を超える
    with pytest.raises(rb.RunBudgetExhausted):
        provider.execute("p", "s")


def test_budget_exhausted_ignores_stub_fallback_flag(monkeypatch):
    """RunBudgetExhaustedはNEXUSCORE_ALLOW_STUB_FALLBACK=1でもstubに置き換わらない"""
    monkeypatch.setenv("NEXUSCORE_ALLOW_STUB_FALLBACK", "1")
    provider = _make_real_provider(monkeypatch, FakeOKSession())
    budget = rb.get_run_budget()
    budget.consume(400.0)
    with pytest.raises(rb.RunBudgetExhausted):
        provider.execute("p", "s")


def test_success_call_consumes_elapsed(monkeypatch):
    """成功呼出後に実経過時間がbudgetへ累積される"""
    provider = _make_real_provider(monkeypatch, FakeOKSession())
    provider.execute("p", "s")
    budget = rb.get_run_budget()
    assert budget.consumed > 0.0
    assert budget.consumed < 5.0  # Fakeは0.01s sleep のみ


def test_read_timeout_consumes_and_logs_structured(monkeypatch, caplog):
    """ReadTimeout時にbudget消費+構造化ログ（event=llm_timeout）が出る"""
    # conftestでSTUB_FALLBACK=1が設定されるため、本番契約（例外送出）へ明示上書き
    monkeypatch.delenv("NEXUSCORE_ALLOW_STUB_FALLBACK", raising=False)
    provider = _make_real_provider(monkeypatch, FakeTimeoutSession())
    caplog.set_level(logging.ERROR, logger="GLMLLM")
    with pytest.raises(requests.exceptions.ReadTimeout):
        provider.execute("p", "s")
    budget = rb.get_run_budget()
    assert budget.consumed > 0.0
    joined = "\n".join(r.getMessage() for r in caplog.records)
    assert "llm_timeout" in joined
    assert "timeout_type=read" in joined
    assert "budget_remaining_sec=" in joined
