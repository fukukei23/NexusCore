"""
Tests for LLM fallback mechanism (Phase 1: LLM Router Hardening).

Covers:
- 429 triggers fallback to next candidate
- Cooldown skips provider after 429
- All candidates exhausted raises RuntimeError
- Success on first try (no fallback needed)
"""

from __future__ import annotations

import os
import time
from unittest.mock import MagicMock, patch

import pytest

from nexuscore.llm.fallback import FallbackTracker, RateLimitEntry


# ---------------------------------------------------------------------------
# FallbackTracker unit tests
# ---------------------------------------------------------------------------


class TestRateLimitEntry:
    def test_not_in_cooldown_initially(self):
        entry = RateLimitEntry()
        assert not entry.in_cooldown

    def test_in_cooldown_after_record(self):
        entry = RateLimitEntry(last_429_at=time.time(), cooldown_sec=60.0)
        assert entry.in_cooldown

    def test_cooldown_expires(self):
        entry = RateLimitEntry(last_429_at=time.time() - 61, cooldown_sec=60.0)
        assert not entry.in_cooldown


class TestFallbackTracker:
    def test_record_429_creates_entry(self):
        tracker = FallbackTracker()
        tracker.record_429("openai")
        assert "openai" in tracker.providers
        assert tracker.should_skip("openai")

    def test_should_skip_returns_false_for_unknown(self):
        tracker = FallbackTracker()
        assert not tracker.should_skip("unknown")

    def test_next_candidate_returns_first_available(self):
        tracker = FallbackTracker()
        family_fn = lambda m: m.split(":")[0]
        result = tracker.next_candidate(["openai:gpt-4o", "anthropic:claude"], family_fn)
        assert result == "openai:gpt-4o"

    def test_next_candidate_skips_cooldown_provider(self):
        tracker = FallbackTracker()
        tracker.record_429("openai")
        family_fn = lambda m: m.split(":")[0]
        result = tracker.next_candidate(["openai:gpt-4o", "anthropic:claude"], family_fn)
        assert result == "anthropic:claude"

    def test_next_candidate_returns_none_if_all_cooldown(self):
        tracker = FallbackTracker()
        tracker.record_429("openai")
        tracker.record_429("anthropic")
        family_fn = lambda m: m.split(":")[0]
        result = tracker.next_candidate(["openai:gpt-4o", "anthropic:claude"], family_fn)
        assert result is None

    def test_cooldown_from_env(self, monkeypatch):
        monkeypatch.setenv("NEXUS_429_COOLDOWN_SEC", "1")
        tracker = FallbackTracker()
        tracker.record_429("openai")
        assert tracker.should_skip("openai")
        time.sleep(1.1)
        assert not tracker.should_skip("openai")


# ---------------------------------------------------------------------------
# RoutedLLM fallback integration tests
# ---------------------------------------------------------------------------


def _make_mock_inner(response_text: str = "ok", raise_on_execute=None):
    """Create a mock inner LLM client."""
    inner = MagicMock()
    inner.model_name = "openai:gpt-4o"
    inner._last_usage = None
    inner.last_call_mode = "real"
    if raise_on_execute:
        inner.execute.side_effect = raise_on_execute
    else:
        inner.execute.return_value = response_text
    return inner


def _make_router(task_model_map=None):
    """Create a minimal LLMRouter with mock dependencies."""
    from nexuscore.llm.llm_router import LLMRouter

    if task_model_map is None:
        task_model_map = {
            "general": {
                "primary": "openai:gpt-4o",
                "fallbacks": ["anthropic:claude-sonnet-4-6", "glm:glm-5.1"],
            }
        }

    with patch.dict(os.environ, {"OPENAI_API_KEY": "test"}, clear=False):
        router = LLMRouter(task_model_map=task_model_map, daily_limit_usd=100.0)
    return router


class TestRoutedLLMFallback:
    def test_success_on_first_try(self):
        """正常時はフォールバックなし"""
        from nexuscore.llm.llm_router import RoutedLLM

        router = _make_router()
        inner = _make_mock_inner("result text")
        routed = RoutedLLM(inner, router, "general")

        result = routed.execute("prompt", "system")
        assert result == "result text"
        assert inner.execute.call_count == 1

    def test_429_triggers_fallback(self):
        """429 → 次の候補モデルにフォールバック"""
        from nexuscore.llm.llm_router import RoutedLLM
        from nexuscore.llm.http_client import RequestsHTTPError

        router = _make_router()
        error_response = MagicMock()
        error_response.status_code = 429
        http_error = RequestsHTTPError(response=error_response)

        inner_fail = _make_mock_inner(raise_on_execute=http_error)
        inner_ok = _make_mock_inner("fallback result")

        with patch.object(router, "_make_client", return_value=inner_ok):
            routed = RoutedLLM(inner_fail, router, "general")
            routed.model_name = "openai:gpt-4o"

            result = routed.execute("prompt", "system")
            assert result == "fallback result"

    def test_all_exhausted_raises(self):
        """全候補失敗時はRuntimeError"""
        from nexuscore.llm.llm_router import RoutedLLM
        from nexuscore.llm.http_client import RequestsHTTPError

        router = _make_router()
        error_response = MagicMock()
        error_response.status_code = 429
        http_error = RequestsHTTPError(response=error_response)

        inner_fail = _make_mock_inner(raise_on_execute=http_error)

        with patch.object(router, "_make_client", return_value=inner_fail):
            routed = RoutedLLM(inner_fail, router, "general")
            routed.model_name = "openai:gpt-4o"

            with pytest.raises(RuntimeError, match="All LLM candidates exhausted"):
                routed.execute("prompt", "system")

    def test_cooldown_skips_provider(self):
        """429直後の同一プロバイダーはスキップ"""
        from nexuscore.llm.llm_router import RoutedLLM
        from nexuscore.llm.http_client import RequestsHTTPError

        router = _make_router()
        error_response = MagicMock()
        error_response.status_code = 429
        http_error = RequestsHTTPError(response=error_response)

        inner_fail = _make_mock_inner(raise_on_execute=http_error)
        inner_ok = _make_mock_inner("success from glm")

        call_count = {"count": 0}

        def mock_make_client(model_name):
            call_count["count"] += 1
            if "openai" in model_name:
                return inner_fail
            if "anthropic" in model_name:
                return inner_fail
            return inner_ok

        with patch.object(router, "_make_client", side_effect=mock_make_client):
            routed = RoutedLLM(inner_fail, router, "general")
            routed.model_name = "openai:gpt-4o"

            result = routed.execute("prompt", "system")
            assert result == "success from glm"
