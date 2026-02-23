import json

import pytest

from nexuscore.agents.postmortem_agent import (
    PostmortemAgent,
    _redact,
    _truncate,
    _validate_and_normalize,
)


@pytest.fixture(autouse=True)
def disable_llm_router(monkeypatch):
    from nexuscore.agents import base_agent

    monkeypatch.setattr(base_agent, "LLMRouter", None)


def test_helpers_truncate_and_redact():
    secret = "API_KEY='AKIA1234567890ABCDE'"
    redacted = _redact(secret)
    assert "REDACTED" in redacted

    long = "x" * 200
    truncated = _truncate(long, limit=20)
    assert len(truncated) < len(long)


def test_validate_and_normalize_accepts_valid_payload():
    payload = {
        "id": "FKB-SUGGESTION-0001",
        "error_signature": "ValueError",
        "cause": "原因",
        "target": "source_file",
        "solution_pattern": {"type": "llm_diagnose_and_fix", "instruction": "fix"},
        "description": "desc",
    }
    assert _validate_and_normalize(payload.copy()) is not None


def test_analyze_failure_returns_valid_entry(monkeypatch):
    agent = PostmortemAgent()
    response = json.dumps(
        {
            "id": "FKB-SUGGESTION-1111",
            "error_signature": "ValueError",
            "cause": "原因",
            "target": "both",
            "solution_pattern": {"type": "llm_diagnose_and_fix", "instruction": "fix"},
            "description": "desc",
        }
    )
    agent.execute_llm_task = lambda *args, **kwargs: response

    entry = agent.analyze_failure_and_suggest_fkb_entry(
        error_log="Traceback",
        source_code="print('hi')",
        test_code="def test(): pass",
        source_file_path="src/main.py",
        test_file_path="tests/test_main.py",
    )
    assert entry["id"].startswith("FKB-SUGGESTION-")
