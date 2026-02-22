import json
import time
from unittest.mock import patch

import pytest

from nexuscore.agents.constitutional_council_agent import ConstitutionalCouncilAgent


def test_load_policies_missing_file(tmp_path):
    agent = ConstitutionalCouncilAgent(
        policy_path=tmp_path / "policy.json",
        amendments_dir=tmp_path / "amendments",
    )
    assert agent._load_policies() == []


def test_load_policies_existing_file(tmp_path):
    policy_path = tmp_path / "policy.json"
    policies = [{"policy_id": "P-1", "description": "Test policy"}]
    policy_path.write_text(json.dumps(policies), encoding="utf-8")

    agent = ConstitutionalCouncilAgent(
        policy_path=policy_path, amendments_dir=tmp_path / "amendments"
    )
    loaded = agent._load_policies()

    assert loaded == policies


def test_load_policies_invalid_json(tmp_path):
    policy_path = tmp_path / "policy.json"
    policy_path.write_text("invalid json", encoding="utf-8")

    agent = ConstitutionalCouncilAgent(
        policy_path=policy_path, amendments_dir=tmp_path / "amendments"
    )

    with pytest.raises(RuntimeError):
        agent._load_policies()


def test_save_policies_creates_backup(tmp_path, monkeypatch):
    policy_path = tmp_path / "policy.json"
    policy_path.write_text("[]", encoding="utf-8")
    agent = ConstitutionalCouncilAgent(
        policy_path=policy_path, amendments_dir=tmp_path / "amendments"
    )

    monkeypatch.setattr(time, "time", lambda: 1234567890)

    agent._save_policies([{"policy_id": "P-1"}])

    backup = policy_path.with_suffix(".1234567890.bak.json")
    assert backup.exists()
    assert json.loads(policy_path.read_text(encoding="utf-8")) == [{"policy_id": "P-1"}]


def test_save_policies_no_existing_file(tmp_path):
    policy_path = tmp_path / "policy.json"
    agent = ConstitutionalCouncilAgent(
        policy_path=policy_path, amendments_dir=tmp_path / "amendments"
    )

    agent._save_policies([{"policy_id": "P-1"}])

    assert policy_path.exists()
    assert json.loads(policy_path.read_text(encoding="utf-8")) == [{"policy_id": "P-1"}]


@pytest.mark.parametrize(
    "proposal, expected",
    [
        ({"unknown": "x"}, False),
        ({"delete_policy_id": "A", "policy_id": "B"}, False),
        ({"delete_policy_id": "A", "description": "x"}, False),
        ({"policy_id": "PID-1", "description": "ok"}, True),
        ({}, True),
        ({"delete_policy_id": "PID-1"}, True),
        ({"policy_id": "PID-1", "description": "Test", "rules": ["rule1"]}, True),
    ],
)
def test_validate_amendment(proposal, expected):
    agent = ConstitutionalCouncilAgent()
    assert agent._validate_amendment(proposal) is expected


def test_validate_amendment_not_dict():
    agent = ConstitutionalCouncilAgent()
    assert agent._validate_amendment("not a dict") is False
    assert agent._validate_amendment(123) is False
    assert agent._validate_amendment(None) is False


def test_invoke_llm_with_retry_success(tmp_path, monkeypatch):
    agent = ConstitutionalCouncilAgent(
        policy_path=tmp_path / "policy.json", amendments_dir=tmp_path / "amendments"
    )

    with patch.object(agent, "execute_llm_task", return_value="test response"):
        result = agent._invoke_llm_with_retry("test prompt", retries=2, delay=0.1)
        assert result == "test response"


def test_invoke_llm_with_retry_failure_retry(tmp_path, monkeypatch):
    agent = ConstitutionalCouncilAgent(
        policy_path=tmp_path / "policy.json", amendments_dir=tmp_path / "amendments"
    )

    call_count = 0

    def mock_execute(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count < 2:
            raise Exception("Temporary error")
        return "success response"

    with patch.object(agent, "execute_llm_task", side_effect=mock_execute):
        result = agent._invoke_llm_with_retry("test prompt", retries=2, delay=0.1)
        assert result == "success response"
        assert call_count == 2


def test_invoke_llm_with_retry_all_failures(tmp_path, monkeypatch):
    agent = ConstitutionalCouncilAgent(
        policy_path=tmp_path / "policy.json", amendments_dir=tmp_path / "amendments"
    )

    with patch.object(agent, "execute_llm_task", side_effect=Exception("Always fails")):
        result = agent._invoke_llm_with_retry("test prompt", retries=2, delay=0.1)
        assert result is None


def test_invoke_llm_with_retry_empty_response(tmp_path, monkeypatch):
    agent = ConstitutionalCouncilAgent(
        policy_path=tmp_path / "policy.json", amendments_dir=tmp_path / "amendments"
    )

    with patch.object(agent, "execute_llm_task", return_value=""):
        result = agent._invoke_llm_with_retry("test prompt", retries=2, delay=0.1)
        assert result is None


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


def test_review_and_amend_no_change_proposal(tmp_path, monkeypatch):
    policy_path = tmp_path / "policy.json"
    policy_path.write_text("[]", encoding="utf-8")
    amendments_dir = tmp_path / "amendments"
    agent = ConstitutionalCouncilAgent(policy_path=policy_path, amendments_dir=amendments_dir)

    monkeypatch.setattr(
        ConstitutionalCouncilAgent,
        "_invoke_llm_with_retry",
        lambda self, prompt, retries=2, delay=1.0: json.dumps({}),
    )

    report = {"failure_summary": "fail", "root_cause": "bug"}
    knowledge = {"pattern": "pattern", "suggestion": "suggest"}

    agent.review_and_amend(report, knowledge)

    pending_files = list(amendments_dir.glob("pending_*.json"))
    assert len(pending_files) == 0


def test_review_and_amend_invalid_json_response(tmp_path, monkeypatch):
    policy_path = tmp_path / "policy.json"
    policy_path.write_text("[]", encoding="utf-8")
    amendments_dir = tmp_path / "amendments"
    agent = ConstitutionalCouncilAgent(policy_path=policy_path, amendments_dir=amendments_dir)

    monkeypatch.setattr(
        ConstitutionalCouncilAgent,
        "_invoke_llm_with_retry",
        lambda self, prompt, retries=2, delay=1.0: "invalid json",
    )

    report = {"failure_summary": "fail", "root_cause": "bug"}
    knowledge = {"pattern": "pattern", "suggestion": "suggest"}

    agent.review_and_amend(report, knowledge)

    pending_files = list(amendments_dir.glob("pending_*.json"))
    assert len(pending_files) == 0


def test_review_and_amend_json_in_code_block(tmp_path, monkeypatch):
    policy_path = tmp_path / "policy.json"
    policy_path.write_text("[]", encoding="utf-8")
    amendments_dir = tmp_path / "amendments"
    agent = ConstitutionalCouncilAgent(policy_path=policy_path, amendments_dir=amendments_dir)

    json_response = json.dumps({"policy_id": "PID-1", "description": "Test"})
    response_with_code_block = f"```json\n{json_response}\n```"

    monkeypatch.setattr(
        ConstitutionalCouncilAgent,
        "_invoke_llm_with_retry",
        lambda self, prompt, retries=2, delay=1.0: response_with_code_block,
    )
    monkeypatch.setattr(time, "time", lambda: 1111111111)

    report = {"failure_summary": "fail", "root_cause": "bug"}
    knowledge = {"pattern": "pattern", "suggestion": "suggest"}

    agent.review_and_amend(report, knowledge)

    pending_files = list(amendments_dir.glob("pending_*.json"))
    assert len(pending_files) == 1
