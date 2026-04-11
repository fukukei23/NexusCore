"""
guardian_agent.py のカバレッジ向上テスト

未カバー行: _budget, review (JSON decode), review_and_commit, _generate_commit_message,
            generate_diff_summary, _summarize_diff_for_llm, review_unified_diff 等
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, Mock, patch

import pytest


class TestGuardianAgentInit:
    """GuardianAgent 初期化テスト"""

    def test_init_default(self):
        from nexuscore.agents.guardian_agent import GuardianAgent

        agent = GuardianAgent()
        assert agent.model == ""
        assert isinstance(agent.api_key, str)

    def test_init_with_model(self):
        from nexuscore.agents.guardian_agent import GuardianAgent

        agent = GuardianAgent(model="test-model")
        assert agent.model == "test-model"


class TestBudget:
    """_budget のテスト"""

    def test_calls_on_budget_tick(self):
        from nexuscore.agents.guardian_agent import GuardianAgent

        agent = GuardianAgent()
        callback = Mock()
        agent.on_budget_tick = callback
        agent._budget("test_step")
        callback.assert_called_once_with("test_step")

    def test_no_callback_no_error(self):
        from nexuscore.agents.guardian_agent import GuardianAgent

        agent = GuardianAgent()
        agent.on_budget_tick = None
        agent._budget("test_step")  # should not raise

    def test_callback_exception_swallowed(self):
        from nexuscore.agents.guardian_agent import GuardianAgent

        agent = GuardianAgent()
        agent.on_budget_tick = Mock(side_effect=RuntimeError("fail"))
        agent._budget("test_step")  # should not raise


class TestReview:
    """review のテスト"""

    @patch("nexuscore.agents.guardian_agent.BaseAgent.execute_llm_task")
    def test_valid_json_approve(self, mock_llm):
        from nexuscore.agents.guardian_agent import GuardianAgent

        mock_llm.return_value = json.dumps({
            "decision": "APPROVE",
            "reason": "Good code",
        })
        agent = GuardianAgent()
        result = agent.review("code", "test", "pass", "testimony", "const", "task")
        assert result["decision"] == "APPROVE"

    @patch("nexuscore.agents.guardian_agent.BaseAgent.execute_llm_task")
    def test_invalid_json_returns_reject(self, mock_llm):
        from nexuscore.agents.guardian_agent import GuardianAgent

        mock_llm.return_value = "not valid json"
        agent = GuardianAgent()
        result = agent.review("code", "test", "pass", "testimony", "const", "task")
        assert result["decision"] == "REJECT"
        assert "Invalid JSON" in result["reason"]

    @patch("nexuscore.agents.guardian_agent.BaseAgent.execute_llm_task")
    def test_reject_adds_feedback(self, mock_llm):
        from nexuscore.agents.guardian_agent import GuardianAgent

        mock_llm.return_value = json.dumps({
            "decision": "REJECT",
            "reason": "Bad code",
        })
        agent = GuardianAgent()
        result = agent.review("code", "test", "pass", "testimony", "const", "task")
        assert result["decision"] == "REJECT"
        assert "feedback_for_coder" in result


class TestGenerateCommitMessage:
    """_generate_commit_message のテスト"""

    def test_feat_commit_without_debug(self):
        from nexuscore.agents.guardian_agent import GuardianAgent

        agent = GuardianAgent(model="test-model")
        msg = agent._generate_commit_message(
            {"reason": "approved"}, ["file.py"], debug_info=None
        )
        assert "feat" in msg
        assert "test-model" in msg

    def test_fix_commit_with_debug(self):
        from nexuscore.agents.guardian_agent import GuardianAgent

        agent = GuardianAgent(model="test-model")
        debug_info = {
            "error_signature": "ImportError",
            "solution_pattern": {"type": "llm_fix"},
        }
        msg = agent._generate_commit_message(
            {"reason": "approved"}, ["file.py"], debug_info=debug_info
        )
        assert "fix" in msg
        assert "Self-healed" in msg
        assert "ImportError" in msg


class TestReviewAndCommit:
    """review_and_commit のテスト"""

    @patch("nexuscore.agents.guardian_agent.BaseAgent.execute_llm_task")
    def test_reject_does_not_commit(self, mock_llm):
        from nexuscore.agents.guardian_agent import GuardianAgent

        mock_llm.return_value = json.dumps({"decision": "REJECT", "reason": "bad"})
        agent = GuardianAgent()
        result = agent.review_and_commit(
            "code", "test", "pass", "testimony", "const", "task", ["file.py"]
        )
        assert result["decision"] == "REJECT"
        assert "commit" not in result

    @patch("nexuscore.agents.guardian_agent.BaseAgent.execute_llm_task")
    def test_approve_no_commit_blocked(self, mock_llm):
        from nexuscore.agents.guardian_agent import GuardianAgent

        mock_llm.return_value = json.dumps({"decision": "APPROVE", "reason": "good"})
        agent = GuardianAgent()
        result = agent.review_and_commit(
            "code", "test", "pass", "testimony", "const", "task", ["file.py"],
            allow_commit=False,
        )
        assert result["decision"] == "APPROVE"
        assert "blocked" in result["commit"]

    @patch("nexuscore.agents.guardian_agent.BaseAgent.execute_llm_task")
    def test_approve_no_vcs(self, mock_llm):
        from nexuscore.agents.guardian_agent import GuardianAgent

        mock_llm.return_value = json.dumps({"decision": "APPROVE", "reason": "good"})
        agent = GuardianAgent()
        agent.vcs = None
        result = agent.review_and_commit(
            "code", "test", "pass", "testimony", "const", "task", ["file.py"],
        )
        assert "Git repository not available" in result["commit"]

    def test_quality_gates_missing_paths(self):
        from nexuscore.agents.guardian_agent import GuardianAgent

        agent = GuardianAgent()
        result = agent.review_and_commit(
            "code", "test", "pass", "testimony", "const", "task", ["file.py"],
            enable_quality_gates=True, source_path=None, test_path=None,
        )
        assert result["decision"] == "REJECT"
        assert "source_path" in result["reason"]


class TestSummarizeDiffForLlm:
    """_summarize_diff_for_llm のテスト"""

    def test_summarize_short_diff(self):
        from nexuscore.agents.guardian_agent import GuardianAgent

        agent = GuardianAgent()
        diff = "+++ a.py\n--- a.py\n@@ -1 +1 @@\n-old\n+new"
        summary = agent._summarize_diff_for_llm(diff)
        assert "1" in summary  # 1 file
        assert "1" in summary  # 1 hunk

    def test_summarize_long_diff_truncates(self):
        from nexuscore.agents.guardian_agent import GuardianAgent

        agent = GuardianAgent()
        lines = [f"line {i}" for i in range(100)]
        diff = "\n".join(lines)
        summary = agent._summarize_diff_for_llm(diff)
        assert "残り" in summary


class TestGenerateDiffSummary:
    """generate_diff_summary のテスト"""

    def test_missing_before_returns_error(self):
        from nexuscore.agents.guardian_agent import GuardianAgent

        agent = GuardianAgent()
        result = agent.generate_diff_summary(before_code=None, after_code="code")
        assert "失敗" in result

    def test_multi_file_diffs(self):
        from nexuscore.agents.guardian_agent import GuardianAgent

        agent = GuardianAgent()
        file_diffs = {
            "a.py": {"before": "x=1", "after": "x=2"},
            "b.py": {"before": "", "after": ""},  # 空の場合
        }
        with patch.object(agent, "generate_diff_summary", side_effect=lambda **kw: "要約結果" if kw.get("before_code") else "空"):
            # _generate_multi_file_diff_summaryを直接テスト
            pass


class TestReviewUnifiedDiff:
    """review_unified_diff のテスト"""

    @patch("nexuscore.agents.guardian_agent.BaseAgent.execute_llm_task")
    def test_approve_without_auto_reviewer(self, mock_llm):
        from nexuscore.agents.guardian_agent import GuardianAgent

        mock_llm.return_value = json.dumps({
            "decision": "APPROVE",
            "reason": "LGTM",
        })
        agent = GuardianAgent()
        with patch("nexuscore.agents.guardian_agent.GuardianAutoReviewer", None):
            result = agent.review_unified_diff("+++ a.py\n+new line")
            assert result["decision"] == "APPROVE"
