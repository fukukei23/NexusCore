"""
Comprehensive tests for RequirementAgent and DebuggerAgent.
Targets: requirement_agent.py (65%), debugger_agent.py (62%) → 80%+
"""

from __future__ import annotations

import json
import os
import tempfile
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from nexuscore.agents.debugger_agent import DebuggerAgent
from nexuscore.agents.requirement_agent import RequirementAgent

# StateMachine and TextLocalization were removed from requirement_agent.py


# ---------------------------------------------------------------------------
# TextLocalization
# ---------------------------------------------------------------------------

@pytest.mark.skip("TextLocalization removed from requirement_agent.py")
class TestTextLocalization:
    def test_ja_getitem(self):
        loc = TextLocalization("ja")
        assert loc["title"] == "NexusCore: 対話型 要件定義エージェント"

    def test_en_getitem(self):
        loc = TextLocalization("en")
        assert loc["title"] == "NexusCore: Interactive Requirement Agent"

    def test_unknown_language_falls_back_to_en(self):
        loc = TextLocalization("fr")
        assert loc["title"] == "NexusCore: Interactive Requirement Agent"

    def test_missing_key_returns_placeholder(self):
        loc = TextLocalization("ja")
        assert loc["nonexistent_key"] == "<nonexistent_key>"


# ---------------------------------------------------------------------------
# StateMachine
# ---------------------------------------------------------------------------

@pytest.mark.skip("StateMachine removed from requirement_agent.py")
class TestStateMachine:
    @patch.object(RequirementAgent, "execute_llm_task")
    def test_transition_returns_tuples(self, mock_execute):
        mock_execute.return_value = "テスト応答"
        agent = RequirementAgent()
        sm = StateMachine(agent)
        result = sm.transition("test")
        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], tuple)

    def test_transition_sets_collecting_from_init(self):
        agent = RequirementAgent()
        sm = StateMachine(agent)
        sm.transition()
        assert sm.state["state"] == "COLLECTING"


# ---------------------------------------------------------------------------
# RequirementAgent
# ---------------------------------------------------------------------------

@pytest.mark.skip("agent.use_ui removed from RequirementAgent")
class TestRequirementAgentInit:
    def test_default_init(self):
        agent = RequirementAgent()
        assert agent.language == "ja"
        assert agent.use_ui is False
        assert agent.final_requirements is None
        assert agent._initial_requirement == ""

    def test_custom_init(self):
        agent = RequirementAgent(language="en", use_ui=True)
        assert agent.language == "en"
        assert agent.use_ui is True


class TestRequirementAgentGetInitialState:
    def test_returns_valid_state(self):
        agent = RequirementAgent()
        state = agent._get_initial_state()
        assert "session_id" in state
        assert state["history"] == []
        assert state["state"] == "INIT"

    def test_unique_session_ids(self):
        agent = RequirementAgent()
        s1 = agent._get_initial_state()
        s2 = agent._get_initial_state()
        assert s1["session_id"] != s2["session_id"]


class TestGenerateFinalSpec:
    def test_extracts_last_user_content(self):
        agent = RequirementAgent()
        history = [
            {"role": "user", "content": "first"},
            {"role": "assistant", "content": "ok"},
            {"role": "user", "content": "last message"},
        ]
        result = agent.generate_final_spec(history)
        assert result["details"] == "last message"
        assert result["summary"] == "Final Specification"

    def test_no_user_messages(self):
        agent = RequirementAgent()
        result = agent.generate_final_spec([{"role": "assistant", "content": "hi"}])
        assert result["details"] == "No user input."

    def test_empty_history(self):
        agent = RequirementAgent()
        result = agent.generate_final_spec([])
        assert result["details"] == "No user input."


class TestSetInitialRequirement:
    def test_sets_requirement(self):
        agent = RequirementAgent()
        agent.set_initial_requirement("build auth system")
        assert agent._initial_requirement == "build auth system"


class TestAnalyzeRequirement:
    def test_successful_llm_response(self, monkeypatch):
        agent = RequirementAgent()
        expected = {
            "summary": "Auth system",
            "features": ["login"],
            "constraints": [],
            "acceptance_criteria": ["test"],
        }
        monkeypatch.setattr(
            agent, "execute_llm_task", lambda p, as_json=False: json.dumps(expected)
        )
        result = agent.analyze_requirement("build auth system")
        assert result["summary"] == "Auth system"
        assert agent.final_requirements == result

    def test_invalid_json_falls_back(self, monkeypatch):
        agent = RequirementAgent()
        monkeypatch.setattr(
            agent, "execute_llm_task", lambda p, as_json=False: "not json at all"
        )
        result = agent.analyze_requirement("test requirement")
        assert result["summary"] == "test requirement"
        assert "Auto-generated draft feature list" in result["features"]

    def test_empty_requirement_uses_initial(self, monkeypatch):
        agent = RequirementAgent()
        agent.set_initial_requirement("fallback req")
        monkeypatch.setattr(
            agent, "execute_llm_task", lambda p, as_json=False: json.dumps({"summary": "ok"})
        )
        result = agent.analyze_requirement("  ")
        assert result["summary"] == "ok"

    def test_empty_requirement_no_initial_uses_default(self, monkeypatch):
        agent = RequirementAgent()
        monkeypatch.setattr(
            agent, "execute_llm_task", lambda p, as_json=False: json.dumps({"summary": "ok"})
        )
        result = agent.analyze_requirement("")
        # Should use "No requirement provided." since both empty
        assert result["summary"] == "ok"

    def test_llm_exception_propagates(self, monkeypatch):
        """execute_llm_task raises → propagates (no try/except around the call at line 141)."""
        agent = RequirementAgent()
        monkeypatch.setattr(
            agent, "execute_llm_task", MagicMock(side_effect=RuntimeError("boom"))
        )
        with pytest.raises(RuntimeError, match="boom"):
            agent.analyze_requirement("test")


@pytest.mark.skip("launch_gradio_ui removed from RequirementAgent")
class TestLaunchGradioUI:
    def test_headless_mode_calls_analyze(self, monkeypatch):
        agent = RequirementAgent(use_ui=False)
        agent.set_initial_requirement("headless test")
        called = {}
        def mock_analyze(req):
            called["req"] = req
            return {"summary": "done"}
        monkeypatch.setattr(agent, "analyze_requirement", mock_analyze)
        result = agent.launch_gradio_ui(share=False)
        assert result == {"summary": "done"}
        assert called["req"] == "headless test"

    def test_ui_mode_gradio_not_installed(self, monkeypatch):
        agent = RequirementAgent(use_ui=True)
        agent.set_initial_requirement("no gradio")
        # Make gradio import fail
        import builtins
        real_import = builtins.__import__
        def fake_import(name, *args, **kwargs):
            if name == "gradio":
                raise ImportError("no gradio")
            return real_import(name, *args, **kwargs)
        monkeypatch.setattr(builtins, "__import__", fake_import)
        result = agent.launch_gradio_ui(share=False)
        # Should fallback to headless
        assert result is not None


# ---------------------------------------------------------------------------
# DebuggerAgent
# ---------------------------------------------------------------------------

class TestDebuggerAgentInit:
    def test_default_init(self):
        agent = DebuggerAgent()
        assert agent.local_knowledge_base is None

    def test_init_with_knowledge_base(self, tmp_path):
        kb_data = [{"error_signature": "ImportError", "cause": "missing", "solution_pattern": {}}]
        kb_file = tmp_path / "kb.json"
        kb_file.write_text(json.dumps(kb_data))
        agent = DebuggerAgent(knowledge_base_path=str(kb_file))
        assert agent.local_knowledge_base == kb_data

    def test_init_with_invalid_path(self):
        agent = DebuggerAgent(knowledge_base_path="/nonexistent/path/kb.json")
        assert agent.local_knowledge_base is None

    def test_init_with_invalid_json(self, tmp_path):
        bad_file = tmp_path / "bad.json"
        bad_file.write_text("not valid json{{{")
        agent = DebuggerAgent(knowledge_base_path=str(bad_file))
        assert agent.local_knowledge_base is None


class TestFindSolutionFromKB:
    def test_local_kb_match(self, tmp_path):
        kb_data = [{"error_signature": "ImportError.*missing", "cause": "missing module"}]
        kb_file = tmp_path / "kb.json"
        kb_file.write_text(json.dumps(kb_data))
        agent = DebuggerAgent(knowledge_base_path=str(kb_file))
        result = agent._find_solution_from_kb("ImportError: No module named missing")
        assert result is not None
        assert result["cause"] == "missing module"

    def test_local_kb_no_match(self, tmp_path):
        kb_data = [{"error_signature": "TypeError.*int", "cause": "type error"}]
        kb_file = tmp_path / "kb.json"
        kb_file.write_text(json.dumps(kb_data))
        agent = DebuggerAgent(knowledge_base_path=str(kb_file))
        result = agent._find_solution_from_kb("ImportError: something")
        assert result is None

    def test_no_kb_no_global(self, monkeypatch):
        import nexuscore.agents.debugger_agent as mod
        monkeypatch.setattr(mod, "knowledge_base", None)
        agent = DebuggerAgent()
        result = agent._find_solution_from_kb("some error")
        assert result is None

    def test_global_kb_with_find_solution(self, monkeypatch):
        mock_kb = MagicMock()
        mock_kb.find_solution.return_value = {"cause": "found"}
        import nexuscore.agents.debugger_agent as mod
        monkeypatch.setattr(mod, "knowledge_base", mock_kb)
        agent = DebuggerAgent()
        result = agent._find_solution_from_kb("some error")
        assert result == {"cause": "found"}

    def test_global_kb_find_solution_exception(self, monkeypatch):
        mock_kb = MagicMock()
        mock_kb.find_solution.side_effect = RuntimeError("kb error")
        import nexuscore.agents.debugger_agent as mod
        monkeypatch.setattr(mod, "knowledge_base", mock_kb)
        agent = DebuggerAgent()
        result = agent._find_solution_from_kb("some error")
        assert result is None

    def test_global_kb_no_find_solution_attr(self, monkeypatch):
        mock_kb = MagicMock(spec=[])
        import nexuscore.agents.debugger_agent as mod
        monkeypatch.setattr(mod, "knowledge_base", mock_kb)
        agent = DebuggerAgent()
        result = agent._find_solution_from_kb("error")
        assert result is None


class TestGenerateFixedCode:
    def test_successful_response(self, monkeypatch):
        agent = DebuggerAgent()
        monkeypatch.setattr(
            agent, "execute_llm_task",
            lambda p, as_json=False: "```python\ndef fixed(): pass\n```"
        )
        result = agent._generate_fixed_code("err", "path.py", "code", "fix it")
        assert result == "def fixed(): pass"

    def test_diff_prefix_stripped(self, monkeypatch):
        agent = DebuggerAgent()
        monkeypatch.setattr(
            agent, "execute_llm_task",
            lambda p, as_json=False: "```diff\n+ new line\n- old line\n```"
        )
        result = agent._generate_fixed_code("err", "p", "c", "fix")
        assert result == "+ new line\n- old line"

    def test_plain_response(self, monkeypatch):
        agent = DebuggerAgent()
        monkeypatch.setattr(
            agent, "execute_llm_task",
            lambda p, as_json=False: "plain code here"
        )
        result = agent._generate_fixed_code("err", "p", "c", "fix")
        assert result == "plain code here"

    def test_empty_response(self, monkeypatch):
        agent = DebuggerAgent()
        monkeypatch.setattr(agent, "execute_llm_task", lambda p, as_json=False: "")
        result = agent._generate_fixed_code("err", "p", "c", "fix")
        assert result is None

    def test_llm_exception(self, monkeypatch):
        agent = DebuggerAgent()
        monkeypatch.setattr(
            agent, "execute_llm_task",
            MagicMock(side_effect=RuntimeError("llm fail"))
        )
        result = agent._generate_fixed_code("err", "p", "c", "fix")
        assert result is None


class TestCreateDiff:
    def test_produces_unified_diff(self):
        agent = DebuggerAgent()
        original = "line1\nline2\n"
        fixed = "line1\nline2_fixed\n"
        result = agent._create_diff(original, fixed, "src/main.py", "/project")
        assert "--- a/" in result
        assert "+++ b/" in result
        assert "-line2" in result
        assert "+line2_fixed" in result

    def test_no_changes(self):
        agent = DebuggerAgent()
        code = "same\n"
        result = agent._create_diff(code, code, "p.py", "/project")
        assert result == ""

    def test_relpath_fallback(self, monkeypatch):
        agent = DebuggerAgent()
        monkeypatch.setattr(os.path, "relpath", MagicMock(side_effect=ValueError("err")))
        result = agent._create_diff("a\n", "b\n", "src/p.py", "/project")
        assert "--- a/src/p.py" in result


class TestDebugAndPatch:
    def test_empty_files_returns_error(self):
        agent = DebuggerAgent()
        result = agent.debug_and_patch("error log", {}, "/project")
        assert "error" in result

    def test_full_flow(self, monkeypatch):
        agent = DebuggerAgent()
        monkeypatch.setattr(agent, "_find_solution_from_kb", lambda e: None)
        monkeypatch.setattr(
            agent, "_generate_fixed_code",
            lambda e, sp, sc, i: "def fixed(): pass"
        )
        result = agent.debug_and_patch(
            "ImportError",
            {"src/main.py": "import old"},
            "/project"
        )
        assert "patch" in result
        assert result["fixed_code"] == "def fixed(): pass"
        assert result["solution_used"] is None

    def test_with_solution(self, monkeypatch, tmp_path):
        kb_data = [{"error_signature": "ImportError", "cause": "missing", "solution_pattern": {"fix": "install"}}]
        kb_file = tmp_path / "kb.json"
        kb_file.write_text(json.dumps(kb_data))
        agent = DebuggerAgent(knowledge_base_path=str(kb_file))
        monkeypatch.setattr(
            agent, "_generate_fixed_code",
            lambda e, sp, sc, i: "import fixed"
        )
        result = agent.debug_and_patch(
            "ImportError: missing module",
            {"src/main.py": "import old"},
            "/project"
        )
        assert result["solution_used"] is not None
        assert result["solution_used"]["cause"] == "missing"

    def test_generate_fails_returns_error(self, monkeypatch):
        agent = DebuggerAgent()
        monkeypatch.setattr(agent, "_find_solution_from_kb", lambda e: None)
        monkeypatch.setattr(agent, "_generate_fixed_code", lambda *a: None)
        result = agent.debug_and_patch("err", {"p.py": "code"}, "/proj")
        assert "error" in result
