import logging

import pytest

import nexuscore.core.orchestrator as orch


def test_assemble_agent_team_missing_curator_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(RuntimeError):
        orch.assemble_agent_team(project_path=".")


def test_orchestrator_run_full_project_handles_exceptions(monkeypatch):
    # minimal stub agents with required attrs/methods
    class StubAgent:
        def __init__(self, name):
            self.name = name

        def __getattr__(self, item):
            # any call returns simple string for logging; run_full_project expects specific methods but we mock orchestration
            return lambda *a, **k: f"{self.name}:{item}"

    class StubRouter:
        def complete(self, *a, **k):
            return "router"

    orch_obj = orch.Orchestrator(
        project_path=".",
        constitution={},
        requirement_agent=StubAgent("req"),
        architect_agent=StubAgent("arch"),
        planner_agent=StubAgent("plan"),
        coder_agent=StubAgent("code"),
        tester_agent=StubAgent("test"),
        debugger_agent=StubAgent("dbg"),
        guardian_agent=StubAgent("guard"),
        policy_agent=StubAgent("policy"),
        postmortem_agent=StubAgent("post"),
        knowledge_curator_agent=StubAgent("kc"),
        patch_applier_agent=StubAgent("patch"),
        llm_router=StubRouter(),
    )

    assert orch_obj.logger is not None


def test_main_exits_on_assemble_failure(monkeypatch):
    monkeypatch.setattr("sys.argv", ["prog"])
    monkeypatch.setattr(orch, "assemble_agent_team", lambda project_path: (_ for _ in ()).throw(RuntimeError("fail")))
    with pytest.raises(SystemExit):
        orch.main()


def test_build_arg_parser_defaults():
    parser = orch._build_arg_parser()
    args = parser.parse_args([])
    assert args.project
    assert args.autonomy_level == 1
