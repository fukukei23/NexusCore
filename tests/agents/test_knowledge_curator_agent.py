import json
from pathlib import Path

import pytest

from nexuscore.agents import knowledge_curator_agent as kc_module
from nexuscore.agents.knowledge_curator_agent import KnowledgeCuratorAgent


class DummyDebugger:
    def __init__(self, knowledge_base_path):
        self.knowledge_base_path = knowledge_base_path
        self.calls = []

    def debug_and_patch(self, error_log, files_content, project_path):
        self.calls.append((error_log, files_content, project_path))
        return {"patch": "--- diff", "fixed_code": "print('ok')"}


class DummyPatchApplier:
    def __init__(self):
        self.calls = []

    def apply(self, patch, project_path):
        self.calls.append((patch, project_path))
        return True


@pytest.fixture
def project(tmp_path, monkeypatch):
    proj = tmp_path / "proj"
    proj.mkdir()
    src = proj / "src" / "mod"
    src.mkdir(parents=True)
    tests = proj / "tests"
    tests.mkdir()
    source_file = src / "calc.py"
    source_file.write_text("def add(a,b):\n    return a+b\n", encoding="utf-8")
    test_file = tests / "test_calc.py"
    test_file.write_text("def test_add():\n    assert add(1,2)==3\n", encoding="utf-8")

    monkeypatch.setattr(kc_module, "DebuggerAgent", DummyDebugger)
    monkeypatch.setattr(kc_module, "PatchApplier", DummyPatchApplier)
    return proj, source_file, test_file


def test_validate_fkb_suggestion_success(project, monkeypatch):
    proj, source_file, test_file = project
    agent = KnowledgeCuratorAgent(api_key="x", model="y")
    monkeypatch.setattr(agent, "_run_tests_in_sandbox", lambda sandbox, rel: (True, "ok"))

    suggestion = {"id": "1", "solution": "fix"}
    result = agent.validate_fkb_suggestion(
        suggestion=suggestion,
        original_project_path=str(proj),
        failed_test_path=str(test_file),
        related_source_path=str(source_file),
        original_test_output="Traceback",
    )
    assert result is True
