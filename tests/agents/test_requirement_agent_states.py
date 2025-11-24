from nexuscore.agents.requirement_agent import RequirementAgent


def test_get_initial_state_unique():
    ra = RequirementAgent()
    state = ra._get_initial_state()
    assert state["state"] == "INIT"
    assert "session_id" in state


def test_generate_final_spec_uses_last_user():
    ra = RequirementAgent()
    history = [
        {"role": "assistant", "content": "hi"},
        {"role": "user", "content": "final request"},
    ]
    spec = ra.generate_final_spec(history)
    assert spec["details"] == "final request"


def test_analyze_requirement_empty_response(monkeypatch):
    ra = RequirementAgent()
    monkeypatch.setattr(ra, "execute_llm_task", lambda *a, **k: "")
    data = ra.analyze_requirement("need feature")
    assert data["summary"].startswith("need")
