import json
from pathlib import Path

import pytest

import nexuscore.core.orchestrator as orchestrator_module
from nexuscore.core.orchestrator import Orchestrator


class DummyRouter:
    def __init__(self):
        self.task_model_map = {"planning": "gpt-task"}
        self.default_model = "gpt-default"

    def complete(self, *args, **kwargs):
        return {"choices": []}


def build_orchestrator(tmp_path, tester):
    stub = object()
    return Orchestrator(
        project_path=str(tmp_path),
        constitution={},
        requirement_agent=stub,
        architect_agent=stub,
        planner_agent=stub,
        coder_agent=stub,
        tester_agent=tester,
        debugger_agent=stub,
        guardian_agent=stub,
        policy_agent=stub,
        postmortem_agent=stub,
        knowledge_curator_agent=stub,
        patch_applier_agent=stub,
        llm_router=DummyRouter(),
    )


def test_execute_task_via_npe_uses_guarded_call(monkeypatch, tmp_path):
    orchestrator = build_orchestrator(tmp_path, tester=object())

    def fake_guarded_llm_call(**kwargs):
        fake_guarded_llm_call.kwargs = kwargs
        return {"content": " result "}

    monkeypatch.setattr(
        orchestrator_module, "guarded_llm_call", fake_guarded_llm_call
    )

    output = orchestrator._execute_task_via_npe(
        "Prompt", metadata={"task_type": "planning"}
    )

    assert output.strip() == "result"
    assert fake_guarded_llm_call.kwargs["task"] == "planning"
    assert callable(fake_guarded_llm_call.kwargs["llm_complete_fn"])


def test_ensure_fastlane_tests_prefers_plan_json(monkeypatch, tmp_path):
    class DummyTester:
        def __init__(self):
            self.calls = []

        def generate_tests_from_plan(self, plan, module):
            self.calls.append(("plan", plan))
            return "tests-by-plan"

        def generate_tests_and_testimony(self, code):
            self.calls.append(("code", code))
            return "tests-by-code"

    tester = DummyTester()
    orchestrator = build_orchestrator(tmp_path, tester=tester)
    plan_text = json.dumps({"functions_to_implement": []})

    output = orchestrator._ensure_fastlane_tests(
        initial_result="",
        plan_text=plan_text,
        code_result="print('hi')",
        requirement="build api",
    )

    assert output == "tests-by-plan"
    assert tester.calls[0][0] == "plan"


def test_ensure_fastlane_tests_falls_back_to_requirement(tmp_path):
    class DummyTester:
        def __init__(self):
            self.calls = []

        def generate_tests(self, req):
            self.calls.append(req)
            return "requirement-tests"

    tester = DummyTester()
    orchestrator = build_orchestrator(tmp_path, tester=tester)

    output = orchestrator._ensure_fastlane_tests(
        initial_result="",
        plan_text="",
        code_result="",
        requirement="fallback requirement",
    )

    assert output == "requirement-tests"
    assert tester.calls == ["fallback requirement"]
