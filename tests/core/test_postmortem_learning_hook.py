"""run_review_phase() のpostmortem学習フックのテスト（Stage 3・spec §5）。"""

from typing import Any
from unittest.mock import Mock, patch

from nexuscore.core.orchestrator import Orchestrator, OrchestratorContext
from nexuscore.llm.llm_router import LLMRouter


def _create_mock_agents() -> dict[str, Any]:
    architect_agent = Mock()
    architect_agent.design_architecture.return_value = {"design_directive": "d"}
    guardian_agent = Mock()
    guardian_agent.review = Mock(return_value={"decision": "APPROVE", "reason": "ok"})
    policy_agent = Mock()
    policy_agent.audit = Mock(return_value={"result": "APPROVED", "violations": []})
    guardian_agent.review_and_commit = Mock(
        return_value={"decision": "APPROVE", "reason": "ok", "commit": "abc123"}
    )
    return {
        "requirement_agent": Mock(),
        "architect_agent": architect_agent,
        "planner_agent": Mock(),
        "coder_agent": Mock(),
        "tester_agent": Mock(),
        "debugger_agent": Mock(),
        "guardian_agent": guardian_agent,
        "policy_agent": policy_agent,
        "postmortem_agent": Mock(),
        "knowledge_curator_agent": Mock(),
        "patch_applier_agent": Mock(),
    }


def _make_orchestrator(tmp_path, agents):
    return Orchestrator(
        project_path=str(tmp_path),
        constitution={"rule": "x"},
        llm_router=Mock(spec=LLMRouter),
        **agents,
    )


def _failing_test_context(tmp_path):
    test_path = tmp_path / "tests" / "test_main.py"
    test_path.parent.mkdir(parents=True, exist_ok=True)
    test_path.write_text("def test_x():\n    assert False\n", encoding="utf-8")

    context = OrchestratorContext(task_id="t1", user_requirement="req")
    context.implementation = {"files": {"main.py": "def broken(): return 1/0"}}
    context.testing = {
        "tests": "def test_x():\n    assert False\n",
        "test_path": str(test_path),
        "passed": False,
        "stdout": "",
        "stderr": "ZeroDivisionError: division by zero",
    }
    return context


class TestPostmortemLearningHook:
    def test_validated_suggestion_is_persisted_to_fkb(self, tmp_path):
        agents = _create_mock_agents()
        suggestion = {
            "id": "FKB-SUGGESTION-0001",
            "error_signature": "ZeroDivisionError",
            "cause": "ゼロ除算",
            "target": "source_file",
            "solution_pattern": {"type": "llm_diagnose_and_fix", "instruction": "fix it"},
            "description": "desc",
        }
        agents["postmortem_agent"].analyze_failure_and_suggest_fkb_entry = Mock(
            return_value=suggestion
        )
        agents["knowledge_curator_agent"].validate_fkb_suggestion = Mock(return_value=True)

        orchestrator = _make_orchestrator(tmp_path, agents)
        context = _failing_test_context(tmp_path)

        with patch("database.knowledge_base.knowledge_base") as mock_kb:
            mock_kb.add_knowledge.return_value = "created"
            result = orchestrator.run_review_phase(context)

        assert result.terminal_state == "NEEDS_HUMAN_REVIEW"
        assert result.postmortem_report == suggestion
        agents["knowledge_curator_agent"].validate_fkb_suggestion.assert_called_once()
        mock_kb.add_knowledge.assert_called_once_with(suggestion)

    def test_unvalidated_suggestion_is_not_persisted(self, tmp_path):
        agents = _create_mock_agents()
        suggestion = {
            "id": "FKB-SUGGESTION-0002",
            "error_signature": "ZeroDivisionError",
            "cause": "c",
            "target": "source_file",
            "solution_pattern": {"type": "llm_diagnose_and_fix", "instruction": "i"},
            "description": "d",
        }
        agents["postmortem_agent"].analyze_failure_and_suggest_fkb_entry = Mock(
            return_value=suggestion
        )
        agents["knowledge_curator_agent"].validate_fkb_suggestion = Mock(return_value=False)

        orchestrator = _make_orchestrator(tmp_path, agents)
        context = _failing_test_context(tmp_path)

        with patch("database.knowledge_base.knowledge_base") as mock_kb:
            result = orchestrator.run_review_phase(context)

        assert result.postmortem_report == suggestion
        mock_kb.add_knowledge.assert_not_called()

    def test_no_suggestion_leaves_postmortem_report_empty(self, tmp_path):
        agents = _create_mock_agents()
        agents["postmortem_agent"].analyze_failure_and_suggest_fkb_entry = Mock(
            return_value=None
        )

        orchestrator = _make_orchestrator(tmp_path, agents)
        context = _failing_test_context(tmp_path)

        result = orchestrator.run_review_phase(context)

        assert result.postmortem_report == {}
        agents["knowledge_curator_agent"].validate_fkb_suggestion.assert_not_called()
