# ==============================================================================
# フォルダ: tests/agents
# ファイル名: test_policy_agent.py (最終修正版)
# ==============================================================================
import pytest
import json
from pathlib import Path
# インストールされたパッケージ名 'nexuscore' からインポート
from nexuscore.agents.policy_agent import PolicyAgent

@pytest.fixture
def policy_agent(tmp_path: Path) -> PolicyAgent:
    rules = [{"policy_id": "TEST_POLICY_001", "detection_pattern": "print\\(", "severity": "HIGH", "description": "Use of 'print' is forbidden."}]
    policy_file = tmp_path / "test_rules.json"
    policy_file.write_text(json.dumps(rules), encoding='utf-8')
    return PolicyAgent(api_key="dummy", model="dummy", policy_rules_path=str(policy_file))

def test_policy_agent_approve(policy_agent: PolicyAgent):
    files_for_audit = [{"path": "app/main.py", "content": "def main():\\n    pass"}]
    result = policy_agent.audit(files_for_audit)
    assert result["result"] == "APPROVED"

def test_policy_agent_reject(policy_agent: PolicyAgent):
    files_for_audit = [{"path": "app/main.py", "content": "def main():\\n    print('debug')"}]
    result = policy_agent.audit(files_for_audit)
    assert result["result"] == "REJECTED"
