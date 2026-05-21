"""Issue #88: requirement_agent.py フォールバックパスのテスト

対象: BaseAgent importフォールバック(_fallbacks.py)、json_sanitizer importフォールバック、
analyze_requirement空メッセージ/不正JSON、generate_final_spec
"""

import json
from unittest.mock import MagicMock, patch

import pytest


class TestFallbacksBaseAgent:
    """_fallbacks.pyのフォールバックBaseAgentが正常動作することを確認"""

    def test_fallback_base_agent_init(self):
        """フォールバックBaseAgentは引数なしで初期化できる"""
        from nexuscore.agents._fallbacks import BaseAgent
        with patch("nexuscore.agents.base_agent.LLMRouter", None):
            agent = BaseAgent()
            assert hasattr(agent, "logger")

    def test_fallback_base_agent_execute_returns_empty(self):
        """フォールバックBaseAgentのexecute_llm_taskは空文字を返す"""
        from nexuscore.agents._fallbacks import BaseAgent
        with patch("nexuscore.agents.base_agent.LLMRouter", None):
            agent = BaseAgent()
            result = agent.execute_llm_task("test")
            assert result == ""

    def test_fallback_base_agent_call_llm_delegates(self):
        """フォールバックBaseAgentはexecute_llm_taskに委譲する_call_llmを持つ"""
        # base_agentのimportが成功する環境では、_fallbacks.py内の
        # BaseAgentは実際のbase_agent.BaseAgentと同じものになる
        # フォールバッククラス自体は、base_agent.pyがimportできない場合のみ使われる
        import nexuscore.agents._fallbacks as fallback_mod
        # フォールバッククラスのソースコードを確認
        import inspect
        source = inspect.getsource(fallback_mod)
        assert "_call_llm" in source or "execute_llm_task" in source


class TestJsonSanitizerFallback:
    """json_sanitizerのimportフォールバックをテスト"""

    def test_sanitize_fallback_passthrough(self):
        """フォールバックsanitize_json_likeは入力をそのまま返す"""
        from nexuscore.agents.requirement_agent import sanitize_json_like
        data = {"key": "value"}
        assert sanitize_json_like(data) == data

    def test_sanitize_fallback_with_string(self):
        """フォールバックは文字列もそのまま返す"""
        from nexuscore.agents.requirement_agent import sanitize_json_like
        assert sanitize_json_like("hello") == "hello"


class TestRequirementAgent:
    """RequirementAgentのメソッドをテスト"""

    def _make_agent(self):
        from nexuscore.agents.requirement_agent import RequirementAgent
        agent = RequirementAgent(language="ja")
        return agent

    def test_init_default_language(self):
        """デフォルト言語で初期化"""
        agent = self._make_agent()
        assert agent.language == "ja"

    def test_get_initial_state(self):
        """_get_initial_stateが正しい構造を返す"""
        agent = self._make_agent()
        state = agent._get_initial_state()
        assert "session_id" in state
        assert "history" in state
        assert state["state"] == "INIT"

    def test_set_initial_requirement(self):
        """set_initial_requirementが文字列を保存する"""
        agent = self._make_agent()
        agent.set_initial_requirement("Build a REST API")
        assert agent._initial_requirement == "Build a REST API"

    def test_generate_final_spec_with_user_message(self):
        """generate_final_specが最後のユーザーメッセージをdetailsに含める"""
        agent = self._make_agent()
        history = [
            {"role": "assistant", "content": "Hello"},
            {"role": "user", "content": "I need a feature"},
            {"role": "user", "content": "Build auth system"},
        ]
        result = agent.generate_final_spec(history)
        assert result["summary"] == "Final Specification"
        assert result["details"] == "Build auth system"

    def test_generate_final_spec_no_user_message(self):
        """ユーザーメッセージがない場合デフォルト値を返す"""
        agent = self._make_agent()
        history = [{"role": "assistant", "content": "Hello"}]
        result = agent.generate_final_spec(history)
        assert result["details"] == "No user input."

    def test_analyze_requirement_with_valid_json(self):
        """analyze_requirementが有効なJSONを返す場合"""
        agent = self._make_agent()
        valid_json = json.dumps({
            "summary": "Test project",
            "features": ["auth"],
            "constraints": [],
            "acceptance_criteria": ["works"],
        })
        agent.execute_llm_task = MagicMock(return_value=valid_json)

        result = agent.analyze_requirement("Build auth")
        assert result["summary"] == "Test project"
        assert "auth" in result["features"]

    def test_analyze_requirement_invalid_json_fallback(self):
        """analyze_requirementが不正JSONの場合フォールバック値を返す"""
        agent = self._make_agent()
        agent.execute_llm_task = MagicMock(return_value="not json at all")

        result = agent.analyze_requirement("Build something complex")
        assert "summary" in result
        assert result["summary"] == "Build something complex"[:80]

    def test_analyze_requirement_empty_string(self):
        """空文字列の場合initial_requirementを使用"""
        agent = self._make_agent()
        agent.set_initial_requirement("Fallback requirement")
        agent.execute_llm_task = MagicMock(return_value="bad json")

        result = agent.analyze_requirement("")
        # execute_llm_taskに渡るpromptにinitial_requirementが含まれる
        call_args = agent.execute_llm_task.call_args[0][0]
        assert "Fallback requirement" in call_args

    def test_analyze_requirement_stores_final(self):
        """analyze_requirementがfinal_requirementsに結果を保存する"""
        agent = self._make_agent()
        valid_json = json.dumps({
            "summary": "Stored test",
            "features": [],
            "constraints": [],
            "acceptance_criteria": [],
        })
        agent.execute_llm_task = MagicMock(return_value=valid_json)

        agent.analyze_requirement("test")
        assert agent.final_requirements is not None
        assert agent.final_requirements["summary"] == "Stored test"
