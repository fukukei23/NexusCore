from types import SimpleNamespace

import pytest

from nexuscore.npe import budget
import nexuscore.npe.engine as engine


class DummyDecision(budget.BudgetDecision):
    def __init__(self, allow=True):
        super().__init__(
            allow=allow,
            reason="ok" if allow else "blocked",
            est_cost_jpy=0.5,
            est_prompt_tokens=10,
            est_completion_tokens=5,
            caps={},
        )


def test_guarded_llm_call_blocks_when_budget_denies(monkeypatch):
    decision = DummyDecision(allow=False)
    monkeypatch.setattr(budget, "preflight_check", lambda **kwargs: decision)
    monkeypatch.setattr(budget, "record_estimate", lambda *args, **kwargs: None)

    response = engine.guarded_llm_call(
        model="gpt-5",
        task="test",
        system_prompt="system",
        user_prompt="user",
        llm_complete_fn=lambda **kwargs: {"ok": True},
    )

    assert response["ok"] is False
    assert "Budget guard rejected" in response["reason"]


def test_guarded_llm_call_tracks_usage(monkeypatch):
    decision = DummyDecision(allow=True)
    monkeypatch.setattr(budget, "preflight_check", lambda **kwargs: decision)
    monkeypatch.setattr(budget, "record_estimate", lambda *args, **kwargs: None)
    usage_calls = []
    monkeypatch.setattr(budget, "record_usage", lambda **kwargs: usage_calls.append(kwargs))
    monkeypatch.setattr(
        engine, "log_transaction", lambda *args, **kwargs: None
    )

    def fake_complete(**kwargs):
        return {"ok": True, "content": "done", "usage": {"prompt_tokens": 5, "completion_tokens": 3}}

    response = engine.guarded_llm_call(
        model="gpt-5",
        task="run",
        system_prompt="system",
        user_prompt="user",
        llm_complete_fn=fake_complete,
    )

    assert response["ok"] is True
    assert usage_calls, "record_usage should be called"
    assert usage_calls[0]["model"] == "gpt-5"
