import json
import time
from pathlib import Path

import pytest

from nexuscore.agents.constitutional_council_agent import ConstitutionalCouncilAgent


def test_load_policies_missing_file(tmp_path):
    agent = ConstitutionalCouncilAgent(
        policy_path=tmp_path / "policy.json",
        amendments_dir=tmp_path / "amendments",
    )
    assert agent._load_policies() == []


def test_save_policies_creates_backup(tmp_path, monkeypatch):
    policy_path = tmp_path / "policy.json"
    policy_path.write_text("[]", encoding="utf-8")
    agent = ConstitutionalCouncilAgent(policy_path=policy_path, amendments_dir=tmp_path / "amendments")

    monkeypatch.setattr(time, "time", lambda: 1234567890)

    agent._save_policies([{"policy_id": "P-1"}])

    backup = policy_path.with_suffix(".1234567890.bak.json")
    assert backup.exists()
    assert json.loads(policy_path.read_text(encoding="utf-8")) == [{"policy_id": "P-1"}]


@pytest.mark.parametrize(
    "proposal, expected",
    [
        ({"unknown": "x"}, False),
        ({"delete_policy_id": "A", "policy_id": "B"}, False),
        ({"delete_policy_id": "A", "description": "x"}, False),
        ({"policy_id": "PID-1", "description": "ok"}, True),
        ({}, True),
    ],
)
def test_validate_amendment(proposal, expected):
    agent = ConstitutionalCouncilAgent()
    assert agent._validate_amendment(proposal) is expected


def test_review_and_amend_creates_pending_file(tmp_path, monkeypatch):
    policy_path = tmp_path / "policy.json"
    policy_path.write_text("[]", encoding="utf-8")
    amendments_dir = tmp_path / "amendments"
    agent = ConstitutionalCouncilAgent(policy_path=policy_path, amendments_dir=amendments_dir)

    monkeypatch.setattr(
        ConstitutionalCouncilAgent,
        "_invoke_llm_with_retry",
        lambda self, prompt, retries=2, delay=1.0: json.dumps(
            {"policy_id": "PID-1", "description": "Add rule", "rules": ["a"]}
        ),
    )
    monkeypatch.setattr(time, "time", lambda: 1111111111)

    report = {"failure_summary": "fail", "root_cause": "bug"}
    knowledge = {"pattern": "pattern", "suggestion": "suggest"}

    agent.review_and_amend(report, knowledge)

    pending_files = list(amendments_dir.glob("pending_*.json"))
    assert len(pending_files) == 1
    payload = json.loads(pending_files[0].read_text(encoding="utf-8"))
    assert payload["policy_id"] == "PID-1"
