import json

from nexuscore.agents.requirement_agent import RequirementAgent


def test_analyze_requirement_fallback_on_bad_json(monkeypatch):
    ra = RequirementAgent()
    monkeypatch.setattr(ra, "execute_llm_task", lambda *a, **k: "{bad json")
    data = ra.analyze_requirement("Do something")
    assert data["summary"].startswith("Do something")
    assert "features" in data


def test_analyze_requirement_uses_initial(monkeypatch):
    ra = RequirementAgent()
    ra.set_initial_requirement("init req")
    monkeypatch.setattr(
        ra,
        "execute_llm_task",
        lambda *a, **k: json.dumps(
            {"summary": "ok", "features": [], "constraints": [], "acceptance_criteria": []}
        ),
    )
    data = ra.analyze_requirement("")
    assert data["summary"] == "ok"
