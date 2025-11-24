from nexuscore.agents.guardian_agent import GuardianAgent


def test_guardian_agent_invalid_json(monkeypatch):
    ga = GuardianAgent()
    monkeypatch.setattr(ga, "execute_llm_task", lambda *a, **k: "{bad}")
    review = ga.review("c", "t", "r", "w", "const", "task")
    assert review["decision"] == "REJECT"
    assert "Invalid" in review["reason"]
