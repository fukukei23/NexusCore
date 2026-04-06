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


# ── CR-NEXUS-052: 新スキーマ対応テスト ──────────────────────────────


def _write_policy(tmp_path: Path, rules: list) -> Path:
    file_path = tmp_path / "new_schema_rules.json"
    file_path.write_text(json.dumps(rules), encoding="utf-8")
    return file_path


def test_new_schema_disabled_policy_skipped(tmp_path: Path):
    """enabled=falseのルールは監査でスキップされること"""
    rules = [
        {
            "policy_id": "POLICY_ENABLED_001",
            "category": "LINT",
            "tags": ["lint"],
            "priority": 1,
            "enabled": True,
            "description": "Detect print.",
            "target_file_pattern": "\\.py$",
            "detection_pattern": "\\bprint\\s*\\(",
            "severity": "MINOR",
            "suggestion": "Use logging.",
        },
        {
            "policy_id": "POLICY_DISABLED_001",
            "category": "MAINTAINABILITY",
            "tags": ["typing"],
            "priority": 3,
            "enabled": False,
            "description": "Type hint missing.",
            "target_file_pattern": "\\.py$",
            "detection_pattern": "def\\s+\\w+",
            "severity": "MINOR",
            "suggestion": "Add type hints.",
        },
    ]
    policy_file = _write_policy(tmp_path, rules)
    agent = PolicyAgent(policy_rules_path=str(policy_file))
    result = agent.audit([{"path": "app/main.py", "content": "def main():\n    print('x')"}])

    assert result["result"] == "REJECTED"
    violation_ids = [v["policy_id"] for v in result["violations"]]
    assert "POLICY_ENABLED_001" in violation_ids
    assert "POLICY_DISABLED_001" not in violation_ids
    assert result["summary"]["skipped_disabled"] == 1


def test_new_schema_violation_includes_new_fields(tmp_path: Path):
    """violation出力にcategory, tags, priorityが含まれること"""
    rules = [
        {
            "policy_id": "POLICY_SEC_001",
            "category": "SECURITY",
            "tags": ["security", "credentials"],
            "priority": 1,
            "enabled": True,
            "description": "Hardcoded secret.",
            "target_file_pattern": "\\.py$",
            "detection_pattern": "password\\s*=\\s*['\"][^'\"]{8,}",
            "severity": "CRITICAL",
            "suggestion": "Use env vars.",
        },
    ]
    policy_file = _write_policy(tmp_path, rules)
    agent = PolicyAgent(policy_rules_path=str(policy_file))
    result = agent.audit([{"path": "app/config.py", "content": "password = 'supersecret123'"}])

    assert result["result"] == "REJECTED"
    v = result["violations"][0]
    assert v["policy_id"] == "POLICY_SEC_001"
    assert v["category"] == "SECURITY"
    assert "credentials" in v["tags"]
    assert v["priority"] == 1


def test_new_schema_exception_allowed_patterns(tmp_path: Path):
    """exception_rules.allowed_patternsに行レベル除外があること"""
    rules = [
        {
            "policy_id": "POLICY_LINT_001",
            "category": "LINT",
            "tags": ["lint", "debugging"],
            "priority": 3,
            "enabled": True,
            "description": "print detected.",
            "target_file_pattern": "\\.py$",
            "detection_pattern": "\\bprint\\s*\\(",
            "severity": "MINOR",
            "suggestion": "Use logging.",
            "exception_rules": {
                "allowed_patterns": ["# DEBUG:"],
                "allowlisted_files": [],
                "project_exclusions": [],
            },
        },
    ]
    policy_file = _write_policy(tmp_path, rules)
    agent = PolicyAgent(policy_rules_path=str(policy_file))

    # 通常のprint → 違反検出
    r1 = agent.audit([{"path": "app/main.py", "content": "print('hello')"}])
    assert r1["result"] == "REJECTED"

    # allowed_patternを含む行 → 除外
    r2 = agent.audit([{"path": "app/main.py", "content": "# DEBUG: print('hello')"}])
    assert r2["result"] == "APPROVED"


def test_new_schema_exception_allowlisted_files(tmp_path: Path):
    """exception_rules.allowlisted_filesに一致するファイルはスキップ"""
    rules = [
        {
            "policy_id": "POLICY_LINT_001",
            "category": "LINT",
            "tags": ["lint"],
            "priority": 3,
            "enabled": True,
            "description": "print detected.",
            "target_file_pattern": "\\.py$",
            "detection_pattern": "\\bprint\\s*\\(",
            "severity": "MINOR",
            "suggestion": "Use logging.",
            "exception_rules": {
                "allowed_patterns": [],
                "allowlisted_files": ["tests/.*\\.py$", "debug_.*\\.py$"],
                "project_exclusions": [],
            },
        },
    ]
    policy_file = _write_policy(tmp_path, rules)
    agent = PolicyAgent(policy_rules_path=str(policy_file))

    r1 = agent.audit([{"path": "tests/test_main.py", "content": "print('test')"}])
    assert r1["result"] == "APPROVED"

    r2 = agent.audit([{"path": "app/main.py", "content": "print('hello')"}])
    assert r2["result"] == "REJECTED"


def test_new_schema_summary_fields(tmp_path: Path):
    """戻り値にsummaryが含まれ、統計値が正しいこと"""
    rules = [
        {
            "policy_id": "POLICY_SEC_001",
            "category": "SECURITY",
            "tags": ["security"],
            "priority": 1,
            "enabled": True,
            "description": "Hardcoded secret.",
            "target_file_pattern": "\\.py$",
            "detection_pattern": "secret\\s*=\\s*['\"]",
            "severity": "CRITICAL",
            "suggestion": "Use env vars.",
        },
        {
            "policy_id": "POLICY_LINT_001",
            "category": "LINT",
            "tags": ["lint"],
            "priority": 3,
            "enabled": True,
            "description": "print detected.",
            "target_file_pattern": "\\.py$",
            "detection_pattern": "\\bprint\\s*\\(",
            "severity": "MINOR",
            "suggestion": "Use logging.",
        },
        {
            "policy_id": "POLICY_MAINT_003",
            "category": "MAINTAINABILITY",
            "tags": ["typing"],
            "priority": 3,
            "enabled": False,
            "description": "Type hints.",
            "target_file_pattern": "\\.py$",
            "detection_pattern": "def\\s+\\w+",
            "severity": "MINOR",
            "suggestion": "Add type hints.",
        },
    ]
    policy_file = _write_policy(tmp_path, rules)
    agent = PolicyAgent(policy_rules_path=str(policy_file))
    result = agent.audit([{"path": "app/main.py", "content": "secret = 'x'\nprint('y')"}])

    assert "summary" in result
    s = result["summary"]
    assert s["total_policies"] == 3
    assert s["enabled_policies"] == 2
    assert s["skipped_disabled"] == 1
    assert s["violations_found"] >= 1
    assert "SECURITY" in s["categories_checked"]
    assert "LINT" in s["categories_checked"]


def test_new_schema_priority_order(tmp_path: Path):
    """priority順（1→3）にソートされてチェックされること"""
    rules = [
        {
            "policy_id": "POLICY_LOW",
            "category": "LINT",
            "tags": ["lint"],
            "priority": 3,
            "enabled": True,
            "description": "print detected.",
            "target_file_pattern": "\\.py$",
            "detection_pattern": "\\bprint\\s*\\(",
            "severity": "MINOR",
            "suggestion": "Use logging.",
        },
        {
            "policy_id": "POLICY_HIGH",
            "category": "SECURITY",
            "tags": ["security"],
            "priority": 1,
            "enabled": True,
            "description": "Secret detected.",
            "target_file_pattern": "\\.py$",
            "detection_pattern": "secret\\s*=",
            "severity": "CRITICAL",
            "suggestion": "Use env vars.",
        },
    ]
    policy_file = _write_policy(tmp_path, rules)
    agent = PolicyAgent(policy_rules_path=str(policy_file))
    result = agent.audit([{"path": "app/main.py", "content": "secret = 'x'\nprint('y')"}])

    assert result["result"] == "REJECTED"
    priorities = [v["priority"] for v in result["violations"]]
    assert priorities == sorted(priorities), f"Violations not in priority order: {priorities}"
