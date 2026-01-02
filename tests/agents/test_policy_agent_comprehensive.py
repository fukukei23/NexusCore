"""
policy_agent.py の包括的テスト

カバレッジ:
- PolicyAgent: ポリシー監査エージェント
  - __init__: ポリシールール読み込み
  - audit: ファイル群の監査実行
"""

import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

try:
    from nexuscore.agents.policy_agent import PolicyAgent
    HAS_POLICY_AGENT = True
except ImportError:
    HAS_POLICY_AGENT = False
    PolicyAgent = None


@pytest.mark.skipif(not HAS_POLICY_AGENT, reason="policy_agent module not available")
class TestPolicyAgentInit:
    """PolicyAgent 初期化のテスト"""

    @patch('nexuscore.agents.policy_agent.BaseAgent.__init__', return_value=None)
    def test_init_with_valid_policy_file(self, mock_base_init, tmp_path):
        """有効なポリシーファイルで初期化"""
        policy_file = tmp_path / "policy_rules.json"
        policies = [
            {
                "policy_id": "SEC-001",
                "detection_pattern": r"api_key\s*=\s*['\"].*['\"]",
                "severity": "error",
                "description": "Hardcoded API key detected"
            }
        ]
        policy_file.write_text(json.dumps(policies))

        agent = PolicyAgent.__new__(PolicyAgent)
        agent.logger = Mock()
        PolicyAgent.__init__(agent, policy_rules_path=str(policy_file))

        assert len(agent.policies) == 1
        assert agent.policies[0]["policy_id"] == "SEC-001"

    @patch('nexuscore.agents.policy_agent.BaseAgent.__init__', return_value=None)
    def test_init_with_nonexistent_file(self, mock_base_init):
        """存在しないファイルパス"""
        agent = PolicyAgent.__new__(PolicyAgent)

        agent.logger = Mock()

        PolicyAgent.__init__(agent, policy_rules_path="/nonexistent/path.json")

        assert agent.policies == []

    @patch('nexuscore.agents.policy_agent.BaseAgent.__init__', return_value=None)
    def test_init_with_invalid_json(self, mock_base_init, tmp_path):
        """無効なJSONファイル"""
        policy_file = tmp_path / "invalid.json"
        policy_file.write_text("not valid json")

        agent = PolicyAgent.__new__(PolicyAgent)
        agent.logger = Mock()
        PolicyAgent.__init__(agent, policy_rules_path=str(policy_file))

        assert agent.policies == []


@pytest.mark.skipif(not HAS_POLICY_AGENT, reason="policy_agent module not available")
class TestAudit:
    """PolicyAgent.audit() のテスト"""

    @patch('nexuscore.agents.policy_agent.BaseAgent.__init__', return_value=None)
    def test_audit_no_violations(self, mock_base_init, tmp_path):
        """違反がない場合"""
        policy_file = tmp_path / "policy_rules.json"
        policies = [
            {
                "policy_id": "SEC-001",
                "detection_pattern": r"api_key\s*=\s*['\"].*['\"]",
                "severity": "error",
                "description": "Hardcoded API key"
            }
        ]
        policy_file.write_text(json.dumps(policies))

        agent = PolicyAgent.__new__(PolicyAgent)
        agent.logger = Mock()
        PolicyAgent.__init__(agent, policy_rules_path=str(policy_file))

        files_to_check = [
            {
                "path": "src/config.py",
                "content": "api_key = os.getenv('API_KEY')"
            }
        ]

        result = agent.audit(files_to_check)

        assert result["result"] == "APPROVED"
        assert len(result["violations"]) == 0

    @patch('nexuscore.agents.policy_agent.BaseAgent.__init__', return_value=None)
    def test_audit_with_violation(self, mock_base_init, tmp_path):
        """違反がある場合"""
        policy_file = tmp_path / "policy_rules.json"
        policies = [
            {
                "policy_id": "SEC-001",
                "detection_pattern": r"api_key\s*=\s*['\"].*['\"]",
                "severity": "error",
                "description": "Hardcoded API key detected",
                "suggestion": "Use environment variables"
            }
        ]
        policy_file.write_text(json.dumps(policies))

        agent = PolicyAgent.__new__(PolicyAgent)
        agent.logger = Mock()
        PolicyAgent.__init__(agent, policy_rules_path=str(policy_file))

        files_to_check = [
            {
                "path": "src/config.py",
                "content": 'api_key = "sk-1234567890abcdef"'
            }
        ]

        result = agent.audit(files_to_check)

        assert result["result"] == "REJECTED"
        assert len(result["violations"]) == 1
        assert result["violations"][0]["policy_id"] == "SEC-001"
        assert result["violations"][0]["file_path"] == "src/config.py"
        assert result["violations"][0]["severity"] == "error"

    @patch('nexuscore.agents.policy_agent.BaseAgent.__init__', return_value=None)
    def test_audit_multiple_violations(self, mock_base_init, tmp_path):
        """複数の違反がある場合"""
        policy_file = tmp_path / "policy_rules.json"
        policies = [
            {
                "policy_id": "SEC-001",
                "detection_pattern": r"api_key\s*=\s*['\"]",
                "severity": "error",
                "description": "Hardcoded API key"
            },
            {
                "policy_id": "SEC-002",
                "detection_pattern": r"password\s*=\s*['\"]",
                "severity": "error",
                "description": "Hardcoded password"
            }
        ]
        policy_file.write_text(json.dumps(policies))

        agent = PolicyAgent.__new__(PolicyAgent)
        agent.logger = Mock()
        PolicyAgent.__init__(agent, policy_rules_path=str(policy_file))

        files_to_check = [
            {
                "path": "src/config.py",
                "content": 'api_key = "secret"\npassword = "12345"'
            }
        ]

        result = agent.audit(files_to_check)

        assert result["result"] == "REJECTED"
        assert len(result["violations"]) == 2

    @patch('nexuscore.agents.policy_agent.BaseAgent.__init__', return_value=None)
    def test_audit_target_file_pattern(self, mock_base_init, tmp_path):
        """target_file_patternによるファイルフィルタリング"""
        policy_file = tmp_path / "policy_rules.json"
        policies = [
            {
                "policy_id": "TEST-001",
                "detection_pattern": r"print\(",
                "severity": "warning",
                "description": "Use logging instead of print",
                "target_file_pattern": r"src/.*\.py$"
            }
        ]
        policy_file.write_text(json.dumps(policies))

        agent = PolicyAgent.__new__(PolicyAgent)
        agent.logger = Mock()
        PolicyAgent.__init__(agent, policy_rules_path=str(policy_file))

        files_to_check = [
            {
                "path": "src/module.py",
                "content": "print('debug')"
            },
            {
                "path": "tests/test_module.py",
                "content": "print('debug')"
            }
        ]

        result = agent.audit(files_to_check)

        # src/module.pyのみが検出される
        assert len(result["violations"]) == 1
        assert result["violations"][0]["file_path"] == "src/module.py"

    @patch('nexuscore.agents.policy_agent.BaseAgent.__init__', return_value=None)
    def test_audit_line_number_tracking(self, mock_base_init, tmp_path):
        """行番号が正しく記録される"""
        policy_file = tmp_path / "policy_rules.json"
        policies = [
            {
                "policy_id": "SEC-001",
                "detection_pattern": r"eval\(",
                "severity": "error",
                "description": "Dangerous eval usage"
            }
        ]
        policy_file.write_text(json.dumps(policies))

        agent = PolicyAgent.__new__(PolicyAgent)
        agent.logger = Mock()
        PolicyAgent.__init__(agent, policy_rules_path=str(policy_file))

        files_to_check = [
            {
                "path": "src/code.py",
                "content": "def foo():\n    pass\n    eval(user_input)\n    pass"
            }
        ]

        result = agent.audit(files_to_check)

        assert len(result["violations"]) == 1
        assert result["violations"][0]["line_number"] == 3

    @patch('nexuscore.agents.policy_agent.BaseAgent.__init__', return_value=None)
    def test_audit_no_policies_loaded(self, mock_base_init):
        """ポリシーが読み込まれていない場合"""
        agent = PolicyAgent.__new__(PolicyAgent)

        agent.logger = Mock()

        PolicyAgent.__init__(agent, policy_rules_path="/nonexistent/path.json")

        files_to_check = [
            {
                "path": "src/code.py",
                "content": "any code"
            }
        ]

        result = agent.audit(files_to_check)

        # ポリシーがない場合は承認
        assert result["result"] == "APPROVED"
        assert len(result["violations"]) == 0

    @patch('nexuscore.agents.policy_agent.BaseAgent.__init__', return_value=None)
    def test_audit_malformed_policy(self, mock_base_init, tmp_path):
        """不正な形式のポリシー"""
        policy_file = tmp_path / "policy_rules.json"
        policies = [
            {
                "policy_id": "VALID-001",
                "detection_pattern": r"test",
                "severity": "error",
                "description": "Valid policy"
            },
            {
                # 必須フィールドが欠けている
                "policy_id": "INVALID-001",
                "detection_pattern": r"bad"
                # severity, description が欠けている
            }
        ]
        policy_file.write_text(json.dumps(policies))

        agent = PolicyAgent.__new__(PolicyAgent)
        agent.logger = Mock()
        PolicyAgent.__init__(agent, policy_rules_path=str(policy_file))

        files_to_check = [
            {
                "path": "src/code.py",
                "content": "test line\nbad line"
            }
        ]

        result = agent.audit(files_to_check)

        # 有効なポリシーのみが適用される
        assert len(result["violations"]) == 1
        assert result["violations"][0]["policy_id"] == "VALID-001"


@pytest.mark.skipif(not HAS_POLICY_AGENT, reason="policy_agent module not available")
class TestEdgeCases:
    """エッジケースのテスト"""

    @patch('nexuscore.agents.policy_agent.BaseAgent.__init__', return_value=None)
    def test_audit_empty_file_list(self, mock_base_init, tmp_path):
        """空のファイルリスト"""
        policy_file = tmp_path / "policy_rules.json"
        policy_file.write_text("[]")

        agent = PolicyAgent.__new__(PolicyAgent)
        agent.logger = Mock()
        PolicyAgent.__init__(agent, policy_rules_path=str(policy_file))

        result = agent.audit([])

        assert result["result"] == "APPROVED"
        assert len(result["violations"]) == 0

    @patch('nexuscore.agents.policy_agent.BaseAgent.__init__', return_value=None)
    def test_audit_file_without_path(self, mock_base_init, tmp_path):
        """pathフィールドがないファイル"""
        policy_file = tmp_path / "policy_rules.json"
        policies = [
            {
                "policy_id": "TEST-001",
                "detection_pattern": r"test",
                "severity": "error",
                "description": "Test"
            }
        ]
        policy_file.write_text(json.dumps(policies))

        agent = PolicyAgent.__new__(PolicyAgent)
        agent.logger = Mock()
        PolicyAgent.__init__(agent, policy_rules_path=str(policy_file))

        files_to_check = [
            {
                # pathがない
                "content": "test content"
            }
        ]

        result = agent.audit(files_to_check)

        # pathがないファイルはスキップされる
        assert result["result"] == "APPROVED"

    @patch('nexuscore.agents.policy_agent.BaseAgent.__init__', return_value=None)
    def test_audit_file_without_content(self, mock_base_init, tmp_path):
        """contentフィールドがないファイル"""
        policy_file = tmp_path / "policy_rules.json"
        policies = [
            {
                "policy_id": "TEST-001",
                "detection_pattern": r"test",
                "severity": "error",
                "description": "Test"
            }
        ]
        policy_file.write_text(json.dumps(policies))

        agent = PolicyAgent.__new__(PolicyAgent)
        agent.logger = Mock()
        PolicyAgent.__init__(agent, policy_rules_path=str(policy_file))

        files_to_check = [
            {
                "path": "src/code.py"
                # contentがない
            }
        ]

        result = agent.audit(files_to_check)

        # contentがないファイルはスキップされる
        assert result["result"] == "APPROVED"

    @patch('nexuscore.agents.policy_agent.BaseAgent.__init__', return_value=None)
    def test_audit_multiline_content(self, mock_base_init, tmp_path):
        """複数行のコンテンツ"""
        policy_file = tmp_path / "policy_rules.json"
        policies = [
            {
                "policy_id": "SEC-001",
                "detection_pattern": r"TODO",
                "severity": "warning",
                "description": "TODO found"
            }
        ]
        policy_file.write_text(json.dumps(policies))

        agent = PolicyAgent.__new__(PolicyAgent)
        agent.logger = Mock()
        PolicyAgent.__init__(agent, policy_rules_path=str(policy_file))

        files_to_check = [
            {
                "path": "src/code.py",
                "content": "line 1\n# TODO: fix this\nline 3\n# TODO: another one"
            }
        ]

        result = agent.audit(files_to_check)

        # 2つのTODOが検出される
        assert len(result["violations"]) == 2
        assert result["violations"][0]["line_number"] == 2
        assert result["violations"][1]["line_number"] == 4

    @patch('nexuscore.agents.policy_agent.BaseAgent.__init__', return_value=None)
    def test_audit_policy_with_no_suggestion(self, mock_base_init, tmp_path):
        """suggestionフィールドがないポリシー"""
        policy_file = tmp_path / "policy_rules.json"
        policies = [
            {
                "policy_id": "TEST-001",
                "detection_pattern": r"test",
                "severity": "error",
                "description": "Test violation"
                # suggestionなし
            }
        ]
        policy_file.write_text(json.dumps(policies))

        agent = PolicyAgent.__new__(PolicyAgent)
        agent.logger = Mock()
        PolicyAgent.__init__(agent, policy_rules_path=str(policy_file))

        files_to_check = [
            {
                "path": "src/code.py",
                "content": "test line"
            }
        ]

        result = agent.audit(files_to_check)

        # デフォルトのsuggestionが使用される
        assert result["violations"][0]["suggestion"] == "No specific suggestion."
