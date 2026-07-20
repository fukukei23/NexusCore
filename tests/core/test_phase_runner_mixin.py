import importlib
import os


def test_default_retry_limits(monkeypatch):
    monkeypatch.delenv("NEXUS_DEBUG_MAX_RETRIES", raising=False)
    monkeypatch.delenv("NEXUS_REVIEW_MAX_RETRIES", raising=False)
    import nexuscore.core.phase_runner_mixin as mod
    importlib.reload(mod)
    assert mod.DEBUG_MAX_RETRIES == 3
    assert mod.REVIEW_MAX_RETRIES == 2


def test_env_override_retry_limits(monkeypatch):
    monkeypatch.setenv("NEXUS_DEBUG_MAX_RETRIES", "7")
    monkeypatch.setenv("NEXUS_REVIEW_MAX_RETRIES", "1")
    import nexuscore.core.phase_runner_mixin as mod
    importlib.reload(mod)
    assert mod.DEBUG_MAX_RETRIES == 7
    assert mod.REVIEW_MAX_RETRIES == 1
