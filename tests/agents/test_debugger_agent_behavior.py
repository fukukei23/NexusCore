import json
from pathlib import Path

import pytest

from nexuscore.agents.debugger_agent import DebuggerAgent


@pytest.fixture(autouse=True)
def patch_base_init(monkeypatch):
    monkeypatch.setattr(
        "nexuscore.agents.debugger_agent.BaseAgent.__init__", lambda self: None
    )


def test_debug_and_patch_success(monkeypatch, tmp_path):
    agent = DebuggerAgent()
    agent.logger = lambda: None

    monkeypatch.setattr(
        DebuggerAgent,
        "execute_llm_task",
        lambda self, prompt, as_json=False: "print('fixed')",
    )
    monkeypatch.setattr(
        DebuggerAgent,
        "_create_diff",
        lambda self, original, fixed, source_path, project_path: "@@ diff @@",
    )

    files = {"src/app.py": "print('bug')"}
    result = agent.debug_and_patch("error", files, str(tmp_path))

    assert result["fixed_code"] == "print('fixed')"
    assert result["patch"] == "@@ diff @@"


def test_debug_and_patch_no_files(monkeypatch):
    agent = DebuggerAgent()
    assert agent.debug_and_patch("error", {}, "/tmp") == {"error": "No files provided for debugging."}
