import json
import types

import pytest

from nexuscore.agents.planner_agent import PlannerAgent


@pytest.fixture(autouse=True)
def disable_llm_router(monkeypatch):
    from nexuscore.agents import base_agent

    monkeypatch.setattr(base_agent, "LLMRouter", None)


def make_agent(monkeypatch, response: str, mode: str = "real") -> PlannerAgent:
    agent = PlannerAgent()
    agent.llm_router = types.SimpleNamespace(last_mode=mode)
    agent.execute_llm_task = lambda *args, **kwargs: response
    return agent


def test_generate_plan_merges_with_fallback(tmp_path, monkeypatch):
    sample_plan = json.dumps(
        {
            "functions_to_implement": [
                {"name": "task_one"},
                {"name": "task_two"},
            ]
        }
    )
    agent = make_agent(monkeypatch, sample_plan)
    (tmp_path / "foo.py").write_text("print('hi')")

    plan = agent.generate_plan("Add feature", context={"project_path": str(tmp_path)})
    assert len(plan["functions_to_implement"]) >= 3
    names = [entry["name"] for entry in plan["functions_to_implement"]]
    assert "add_feature_core_implementation" in names


def test_generate_plan_falls_back_when_router_not_real(monkeypatch):
    response = json.dumps(
        {"functions_to_implement": [{"name": "original_task"}], "mode": "fallback_stub"}
    )
    agent = make_agent(monkeypatch, response, mode="stub")

    plan = agent.generate_plan("Build API")
    assert plan["functions_to_implement"][0]["name"].startswith("build_api")


def test_get_file_context_limits_output(tmp_path):
    agent = PlannerAgent()
    for idx in range(5):
        sub = tmp_path / f"pkg_{idx}"
        sub.mkdir()
        (sub / f"module_{idx}.py").write_text("pass")

    context = agent._get_file_context(str(tmp_path), max_files=3)
    assert "関連ファイル (一部抜粋):" in context
    listed = [line for line in context.splitlines() if line.startswith("- ")]
    assert len(listed) == 3
