"""
Tests for API key health checker (Phase 2: Security Baseline).
"""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from nexuscore.llm.key_health import (
    PLACEHOLDERS,
    KeyReport,
    check_all_keys,
    log_key_health,
)


def _clear_all_keys(monkeypatch):
    for env_var, _ in [
        ("OPENAI_API_KEY", "openai"),
        ("ANTHROPIC_API_KEY", "anthropic"),
        ("GEMINI_API_KEY", "google"),
        ("GLM_API_KEY", "glm"),
        ("MINIMAX_API_KEY", "minimax"),
        ("DEEPSEEK_API_KEY", "deepseek"),
        ("KIMI_API_KEY", "moonshot"),
        ("PERPLEXITY_API_KEY", "perplexity"),
    ]:
        monkeypatch.delenv(env_var, raising=False)


class TestCheckAllKeys:
    def test_all_keys_missing(self, monkeypatch):
        _clear_all_keys(monkeypatch)
        reports = check_all_keys()
        assert all(r.status == "missing" for r in reports)

    def test_placeholder_detected(self, monkeypatch):
        _clear_all_keys(monkeypatch)
        monkeypatch.setenv("OPENAI_API_KEY", "sk-xxx")
        reports = check_all_keys()
        openai_report = next(r for r in reports if r.provider == "openai")
        assert openai_report.status == "missing"

    def test_ok_status(self, monkeypatch):
        _clear_all_keys(monkeypatch)
        monkeypatch.setenv("OPENAI_API_KEY", "sk-proj-realkey1234567890ab")
        reports = check_all_keys()
        openai_report = next(r for r in reports if r.provider == "openai")
        assert openai_report.status == "ok"
        assert openai_report.key_length > 0

    def test_duplicate_detected(self, monkeypatch):
        _clear_all_keys(monkeypatch)
        same_key = "sk-proj-samevalue12345678"
        monkeypatch.setenv("OPENAI_API_KEY", same_key)
        monkeypatch.setenv("ANTHROPIC_API_KEY", same_key)
        reports = check_all_keys()
        dup_reports = [r for r in reports if r.status == "duplicate"]
        assert len(dup_reports) == 1
        assert dup_reports[0].provider == "anthropic"

    def test_various_placeholders(self, monkeypatch):
        _clear_all_keys(monkeypatch)
        for p in PLACEHOLDERS:
            if not p:
                continue
            monkeypatch.setenv("OPENAI_API_KEY", p)
            reports = check_all_keys()
            openai_report = next(r for r in reports if r.provider == "openai")
            assert openai_report.status == "missing", f"Placeholder '{p}' not detected"


class TestLogKeyHealth:
    def test_log_output(self, monkeypatch, caplog):
        _clear_all_keys(monkeypatch)
        monkeypatch.setenv("GLM_API_KEY", "real.glm.key.value")
        with caplog.at_level("INFO", logger="KeyHealth"):
            log_key_health()
        assert any("glm" in r.message and "OK" in r.message for r in caplog.records)
        assert any("openai" in r.message and "missing" in r.message.lower() for r in caplog.records)
