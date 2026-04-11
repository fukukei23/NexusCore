"""
postmortem_agent.py のカバレッジ向上テスト

未カバー行: 189-190, 198-212, 226-230
"""

from __future__ import annotations

import json
from unittest.mock import Mock, patch

import pytest


class TestTruncate:
    """_truncate のテスト"""

    def test_short_string_unchanged(self):
        from nexuscore.agents.postmortem_agent import _truncate

        assert _truncate("short") == "short"

    def test_none_returns_none(self):
        from nexuscore.agents.postmortem_agent import _truncate

        assert _truncate(None) is None

    def test_long_string_truncated(self):
        from nexuscore.agents.postmortem_agent import _truncate

        long_str = "x" * 100
        result = _truncate(long_str, limit=20)
        assert "..." in result
        assert len(result) < 100


class TestRedact:
    """_redact のテスト"""

    def test_empty_string(self):
        from nexuscore.agents.postmortem_agent import _redact

        assert _redact("") == ""

    def test_none_returns_none(self):
        from nexuscore.agents.postmortem_agent import _redact

        assert _redact(None) is None

    def test_aws_key_masked(self):
        from nexuscore.agents.postmortem_agent import _redact

        text = "key=AKIAIOSFODNN7EXAMPLE"
        result = _redact(text)
        assert "AKIAIOSFODNN7EXAMPLE" not in result
        assert "AWS_KEY_REDACTED" in result

    def test_api_key_masked(self):
        from nexuscore.agents.postmortem_agent import _redact

        text = 'api_key="abcdef1234567890abcdef"'
        result = _redact(text)
        assert "abcdef1234567890abcdef" not in result or "REDACTED" in result

    def test_no_secrets_unchanged(self):
        from nexuscore.agents.postmortem_agent import _redact

        text = "normal text without secrets"
        assert _redact(text) == text


class TestValidateAndNormalize:
    """_validate_and_normalize のテスト"""

    def _valid_payload(self):
        return {
            "id": "FKB-SUGGESTION-0001",
            "error_signature": "ImportError: cannot import",
            "cause": "テスト原因",
            "target": "test_file",
            "solution_pattern": {
                "type": "llm_diagnose_and_fix",
                "instruction": "Fix the import error",
            },
            "description": "テスト説明",
        }

    def test_valid_payload(self):
        from nexuscore.agents.postmortem_agent import _validate_and_normalize

        payload = self._valid_payload()
        result = _validate_and_normalize(payload)
        assert result is not None
        assert result["id"] == "FKB-SUGGESTION-0001"

    def test_missing_required_key(self):
        from nexuscore.agents.postmortem_agent import _validate_and_normalize

        payload = {"id": "1", "error_signature": ".*"}  # cause, target等が不足
        result = _validate_and_normalize(payload)
        assert result is None

    def test_invalid_target(self):
        from nexuscore.agents.postmortem_agent import _validate_and_normalize

        payload = self._valid_payload()
        payload["target"] = "invalid_target"
        result = _validate_and_normalize(payload)
        assert result is None

    def test_invalid_solution_pattern_type(self):
        from nexuscore.agents.postmortem_agent import _validate_and_normalize

        payload = self._valid_payload()
        payload["solution_pattern"] = {"type": "manual_fix", "instruction": "fix it"}
        result = _validate_and_normalize(payload)
        assert result is None

    def test_solution_pattern_missing_instruction(self):
        from nexuscore.agents.postmortem_agent import _validate_and_normalize

        payload = self._valid_payload()
        payload["solution_pattern"] = {"type": "llm_diagnose_and_fix"}
        result = _validate_and_normalize(payload)
        assert result is None

    def test_solution_pattern_not_dict(self):
        from nexuscore.agents.postmortem_agent import _validate_and_normalize

        payload = self._valid_payload()
        payload["solution_pattern"] = "not a dict"
        result = _validate_and_normalize(payload)
        assert result is None

    def test_invalid_regex_error_signature(self):
        from nexuscore.agents.postmortem_agent import _validate_and_normalize

        payload = self._valid_payload()
        payload["error_signature"] = "[invalid regex("
        result = _validate_and_normalize(payload)
        assert result is None

    def test_not_dict_returns_none(self):
        from nexuscore.agents.postmortem_agent import _validate_and_normalize

        result = _validate_and_normalize("not a dict")
        assert result is None


class TestAnalyzeFailure:
    """analyze_failure_and_suggest_fkb_entry のテスト"""

    @patch("nexuscore.agents.postmortem_agent.BaseAgent.execute_llm_task")
    def test_empty_llm_response_returns_none(self, mock_llm):
        """行189-190: LLM空レスポンス"""
        from nexuscore.agents.postmortem_agent import PostmortemAgent

        mock_llm.return_value = ""
        agent = PostmortemAgent()
        result = agent.analyze_failure_and_suggest_fkb_entry("err", "src", "test", "src.py", "test.py")
        assert result is None

    @patch("nexuscore.agents.postmortem_agent.BaseAgent.execute_llm_task")
    def test_valid_json_response(self, mock_llm):
        """正常なJSONレスポンス"""
        from nexuscore.agents.postmortem_agent import PostmortemAgent

        valid = json.dumps({
            "id": "FKB-001",
            "error_signature": "Error: test",
            "cause": "原因",
            "target": "source_file",
            "solution_pattern": {"type": "llm_diagnose_and_fix", "instruction": "fix it"},
            "description": "説明",
        })
        mock_llm.return_value = valid
        agent = PostmortemAgent()
        result = agent.analyze_failure_and_suggest_fkb_entry("err", "src", "test", "src.py", "test.py")
        assert result is not None
        assert result["id"] == "FKB-001"

    @patch("nexuscore.agents.postmortem_agent.BaseAgent.execute_llm_task")
    def test_json_embedded_in_text(self, mock_llm):
        """行198-212: JSONがテキストに埋め込まれている場合"""
        from nexuscore.agents.postmortem_agent import PostmortemAgent

        valid = json.dumps({
            "id": "FKB-002",
            "error_signature": "ValueError: .*",
            "cause": "原因",
            "target": "both",
            "solution_pattern": {"type": "llm_diagnose_and_fix", "instruction": "fix"},
            "description": "説明",
        })
        mock_llm.return_value = f"以下が結果です:\n{valid}\n以上です。"
        agent = PostmortemAgent()
        result = agent.analyze_failure_and_suggest_fkb_entry("err", "src", "test", "src.py", "test.py")
        assert result is not None
        assert result["id"] == "FKB-002"

    @patch("nexuscore.agents.postmortem_agent.BaseAgent.execute_llm_task")
    def test_no_json_in_response_returns_none(self, mock_llm):
        """行201-205: JSONが見つからない場合"""
        from nexuscore.agents.postmortem_agent import PostmortemAgent

        mock_llm.return_value = "plain text without any json"
        agent = PostmortemAgent()
        result = agent.analyze_failure_and_suggest_fkb_entry("err", "src", "test", "src.py", "test.py")
        assert result is None

    @patch("nexuscore.agents.postmortem_agent.BaseAgent.execute_llm_task")
    def test_invalid_extracted_json_returns_none(self, mock_llm):
        """行207-212: 抽出したJSONが不正"""
        from nexuscore.agents.postmortem_agent import PostmortemAgent

        mock_llm.return_value = "result: {invalid json content}"
        agent = PostmortemAgent()
        result = agent.analyze_failure_and_suggest_fkb_entry("err", "src", "test", "src.py", "test.py")
        assert result is None

    @patch("nexuscore.agents.postmortem_agent.BaseAgent.execute_llm_task")
    def test_schema_validation_fails_returns_none(self, mock_llm):
        """行216-220: スキーマ検証失敗"""
        from nexuscore.agents.postmortem_agent import PostmortemAgent

        mock_llm.return_value = json.dumps({"invalid": "payload"})
        agent = PostmortemAgent()
        result = agent.analyze_failure_and_suggest_fkb_entry("err", "src", "test", "src.py", "test.py")
        assert result is None

    @patch("nexuscore.agents.postmortem_agent.BaseAgent.execute_llm_task")
    def test_unexpected_exception_returns_none(self, mock_llm):
        """行226-230: 予期せぬ例外"""
        from nexuscore.agents.postmortem_agent import PostmortemAgent

        mock_llm.side_effect = RuntimeError("unexpected")
        agent = PostmortemAgent()
        result = agent.analyze_failure_and_suggest_fkb_entry("err", "src", "test", "src.py", "test.py")
        assert result is None
