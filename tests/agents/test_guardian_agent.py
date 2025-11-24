import json
import types

import pytest

from nexuscore.agents import guardian_agent as guardian_module
from nexuscore.agents.guardian_agent import GuardianAgent


class DummyGitController:
    def __init__(self):
        self.calls = []

    def commit_changes(self, file_paths, message):
        self.calls.append((file_paths, message))
        return "abc123"


@pytest.fixture(autouse=True)
def disable_llm_router(monkeypatch):
    from nexuscore.agents import base_agent

    monkeypatch.setattr(base_agent, "LLMRouter", None)


@pytest.fixture
def guardian(monkeypatch):
    dummy_controller = DummyGitController()
    monkeypatch.setattr(guardian_module, "GitController", lambda: dummy_controller)
    agent = GuardianAgent()
    agent.execute_llm_task = lambda *args, **kwargs: json.dumps(
        {"decision": "APPROVE", "reason": "Looks good"}
    )
    agent.llm_router = types.SimpleNamespace(last_mode="real")
    return agent, dummy_controller


def test_review_returns_reject_on_invalid_json(monkeypatch):
    monkeypatch.setattr(guardian_module, "GitController", lambda: DummyGitController())
    agent = GuardianAgent()
    agent.execute_llm_task = lambda *args, **kwargs: "{invalid json"

    result = agent.review("code", "tests", "ok", "testimony", "constitution", "task")
    assert result["decision"] == "REJECT"


def test_review_and_commit_skips_commit_when_disallowed(guardian):
    agent, dummy = guardian
    result = agent.review_and_commit(
        code_draft="code",
        test_code="tests",
        test_result="ok",
        testimony="done",
        constitution="law",
        task_description="task",
        changed_files=["file.py"],
        allow_commit=False,
    )
    assert "Commit blocked" in result["commit"]
    assert dummy.calls == []


def test_review_and_commit_executes_commit_when_approved(guardian):
    agent, dummy = guardian
    result = agent.review_and_commit(
        code_draft="code",
        test_code="tests",
        test_result="ok",
        testimony="done",
        constitution="law",
        task_description="task",
        changed_files=["file.py"],
        allow_commit=True,
    )

    assert result["commit"] == "abc123"
    assert len(dummy.calls) == 1
    paths, message = dummy.calls[0]
    assert paths == ["file.py"]
    assert "GuardianAgent" in message
