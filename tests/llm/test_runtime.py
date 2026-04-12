import logging

from nexuscore.llm import runtime
from nexuscore.llm.config import LLMRouterConfig


def test_current_diagnostics_reflects_http_flag(monkeypatch):
    monkeypatch.setattr(runtime, "HTTP_AVAILABLE", False, raising=True)
    diag = runtime.current_diagnostics()
    assert diag.http_available is False
    assert diag.request_timeout == runtime.REQUEST_TIMEOUT


def test_log_runtime_status_emits_summary(monkeypatch, caplog):
    dummy_config = LLMRouterConfig(
        glm_api_key=None,
        minimax_api_key=None,
        request_timeout=42.0,
        dry_run=True,
        real_calls_enabled=False,
    )
    monkeypatch.setattr(runtime, "CONFIG", dummy_config, raising=True)
    monkeypatch.setattr(runtime, "REQUEST_TIMEOUT", dummy_config.request_timeout, raising=True)
    monkeypatch.setenv("NEXUSCORE_ENV_LOADED", "/tmp/.env")
    monkeypatch.setattr(runtime, "HTTP_AVAILABLE", False, raising=True)

    caplog.set_level(logging.INFO, logger="LLMRuntime")
    diag = runtime.log_runtime_status()

    assert diag.env_file == "/tmp/.env"
    assert diag.dry_run is True
    assert diag.real_calls_enabled is False
    assert any("[Runtime]" in record.message for record in caplog.records)
    assert any("HTTP client unavailable" in record.message for record in caplog.records)
