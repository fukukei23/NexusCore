import json
from pathlib import Path

import pytest

from nexuscore.agents.policy_agent import PolicyAgent


@pytest.fixture(autouse=True)
def disable_llm_router(monkeypatch):
    from nexuscore.agents import base_agent

    monkeypatch.setattr(base_agent, "LLMRouter", None)


@pytest.fixture
def policy_file(tmp_path: Path) -> Path:
    rules = [
        {
            "policy_id": "TEST_POLICY_001",
            "detection_pattern": "print\\(",
            "severity": "HIGH",
            "description": "Use of 'print' is forbidden.",
            "target_file_pattern": ".*\\.py",
        }
    ]
    file_path = tmp_path / "test_rules.json"
    file_path.write_text(json.dumps(rules), encoding="utf-8")
    return file_path


def test_policy_agent_approve(policy_file: Path):
    agent = PolicyAgent(policy_rules_path=str(policy_file))
    files_for_audit = [{"path": "app/main.py", "content": "def main():\n    pass"}]
    result = agent.audit(files_for_audit)
    assert result["result"] == "APPROVED"
    assert result["violations"] == []


def test_policy_agent_reject(policy_file: Path):
    agent = PolicyAgent(policy_rules_path=str(policy_file))
    files_for_audit = [{"path": "app/main.py", "content": "def main():\n    print('debug')"}]
    result = agent.audit(files_for_audit)
    assert result["result"] == "REJECTED"
    assert result["violations"][0]["policy_id"] == "TEST_POLICY_001"


def test_policy_agent_missing_rules(tmp_path: Path):
    agent = PolicyAgent(policy_rules_path=str(tmp_path / "missing.json"))
    result = agent.audit([{"path": "file.py", "content": "print('x')"}])
    assert result["result"] == "APPROVED"
