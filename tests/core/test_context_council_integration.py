"""Integration tests for ContextAgent and ConstitutionalCouncilAgent pipeline wiring."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from nexuscore.core.orchestrator_models import OrchestratorContext


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_context(**overrides):
    defaults = {
        "task_id": "test-001",
        "user_requirement": "Create a hello world app",
    }
    defaults.update(overrides)
    return OrchestratorContext(**defaults)


def _make_mock_orchestrator(context_agent=None, constitutional_council_agent=None):
    """Create a minimal mock with PhaseRunnerMixin methods."""
    from nexuscore.core.phase_runner_mixin import PhaseRunnerMixin

    class MockOrchestrator(PhaseRunnerMixin):
        pass

    orch = MockOrchestrator()
    orch.logger = MagicMock()
    orch.project_path = "/tmp/test_nexus"
    orch.context_agent = context_agent
    orch.constitutional_council_agent = constitutional_council_agent
    return orch


# ---------------------------------------------------------------------------
# ContextAgent Phase 0 tests
# ---------------------------------------------------------------------------

class TestRunContextPhase:

    def test_noop_when_agent_is_none(self):
        orch = _make_mock_orchestrator(context_agent=None)
        ctx = _make_context()
        result = orch.run_context_phase(ctx)
        assert result.context_profile == {}
        assert result.error_prevention_rules == {}

    def test_populates_context_when_agent_present(self):
        mock_agent = MagicMock()
        mock_agent.get_context.return_value = {"tech_stack": {"python": True}}
        mock_agent.get_error_prevention_rules.return_value = {"rule1": "value1"}

        orch = _make_mock_orchestrator(context_agent=mock_agent)
        ctx = _make_context()
        result = orch.run_context_phase(ctx)

        assert result.context_profile == {"tech_stack": {"python": True}}
        assert result.error_prevention_rules == {"rule1": "value1"}
        mock_agent.get_context.assert_called_once()
        mock_agent.get_error_prevention_rules.assert_called_once()

    def test_graceful_skip_on_exception(self):
        mock_agent = MagicMock()
        mock_agent.get_context.side_effect = RuntimeError("boom")

        orch = _make_mock_orchestrator(context_agent=mock_agent)
        ctx = _make_context()
        result = orch.run_context_phase(ctx)

        assert result.context_profile == {}
        orch.logger.warning.assert_called()


# ---------------------------------------------------------------------------
# ConstitutionalCouncilAgent Phase 6 tests
# ---------------------------------------------------------------------------

class TestConstitutionalReview:

    def test_noop_when_council_is_none(self):
        orch = _make_mock_orchestrator(constitutional_council_agent=None)
        ctx = _make_context()
        ctx.postmortem_report = {"error_signature": "test"}
        orch._maybe_run_constitutional_review(ctx)

    def test_noop_when_no_postmortem_data(self):
        mock_council = MagicMock()
        orch = _make_mock_orchestrator(constitutional_council_agent=mock_council)
        ctx = _make_context()
        orch._maybe_run_constitutional_review(ctx)
        mock_council.review_and_amend.assert_not_called()

    def test_triggers_on_postmortem_data(self):
        mock_council = MagicMock()
        orch = _make_mock_orchestrator(constitutional_council_agent=mock_council)
        ctx = _make_context()
        ctx.postmortem_report = {
            "error_signature": "ImportError",
            "solution_pattern": {"instruction": "Add missing import"},
        }
        orch._maybe_run_constitutional_review(ctx)

        mock_council.review_and_amend.assert_called_once()
        call_args = mock_council.review_and_amend.call_args
        assert call_args[1]["postmortem_report"]["error_signature"] == "ImportError"
        assert call_args[1]["knowledge_brief"]["pattern"] == "ImportError"

    def test_graceful_skip_on_exception(self):
        mock_council = MagicMock()
        mock_council.review_and_amend.side_effect = RuntimeError("council error")

        orch = _make_mock_orchestrator(constitutional_council_agent=mock_council)
        ctx = _make_context()
        ctx.postmortem_report = {"error_signature": "test"}
        orch._maybe_run_constitutional_review(ctx)

        orch.logger.warning.assert_called()


# ---------------------------------------------------------------------------
# Review phase integration test
# ---------------------------------------------------------------------------

class TestReviewPhaseIntegration:

    def test_review_phase_calls_constitutional_on_postmortem(self):
        mock_council = MagicMock()
        orch = _make_mock_orchestrator(constitutional_council_agent=mock_council)
        ctx = _make_context()
        ctx.postmortem_report = {"error_signature": "SyntaxError"}

        result = orch.run_review_phase(ctx)
        assert result.phase_log[-1] == "REVIEW"
        mock_council.review_and_amend.assert_called_once()

    def test_review_phase_without_council(self):
        orch = _make_mock_orchestrator(constitutional_council_agent=None)
        ctx = _make_context()
        result = orch.run_review_phase(ctx)
        assert result.phase_log[-1] == "REVIEW"
        assert result.review == {}


# ---------------------------------------------------------------------------
# OrchestratorContext new fields test
# ---------------------------------------------------------------------------

class TestOrchestratorContextFields:

    def test_new_fields_default_to_empty_dict(self):
        ctx = _make_context()
        assert ctx.context_profile == {}
        assert ctx.error_prevention_rules == {}
        assert ctx.postmortem_report == {}

    def test_new_fields_accept_values(self):
        ctx = _make_context(
            context_profile={"tech": "python"},
            error_prevention_rules={"no_hardcoded_keys": True},
            postmortem_report={"error_signature": "test"},
        )
        assert ctx.context_profile == {"tech": "python"}
        assert ctx.error_prevention_rules == {"no_hardcoded_keys": True}
        assert ctx.postmortem_report == {"error_signature": "test"}
