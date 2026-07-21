"""
run_review_phase() のguardianループ+3値終端状態の独立テスト（spec §4-3/4-4）。

test_orchestrator_comprehensive.py の TestReviewPhaseGuardianLoop と同じ4シナリオを
カバーするが、あのファイルは `_build_arg_parser` の削除に伴う壊れたimport（別issueで
追跡中）で HAS_ORCHESTRATOR = False となり、ファイル内の全テストが機械的にskipされて
しまう。そのためこの重要な新規ロジック（guardianループ+APPROVED/NEEDS_HUMAN_REVIEW
終端状態）に対する実行される形のテストが存在しない状態だった。

本ファイルは Orchestrator / OrchestratorContext を実モジュールから直接importすることで
その壊れたimportチェーンを回避し、上記4シナリオを実際にPASSする形で担保する。
"""

from typing import Any
from unittest.mock import Mock

from nexuscore.core.orchestrator import Orchestrator, OrchestratorContext
from nexuscore.llm.llm_router import LLMRouter


def _create_mock_agents() -> dict[str, Any]:
    """モックエージェント群を作成（test_orchestrator_comprehensive.py と同等）"""
    requirement_agent = Mock()
    requirement_agent.use_ui = False  # Mockのtruthy属性でGradio UIパスに入らないようにする
    architect_agent = Mock()
    architect_agent.design_architecture.return_value = {
        "design_directive": "test design directive"
    }
    tester_agent = Mock()
    tester_agent.generate_tests = Mock(return_value="# generated tests")
    debugger_agent = Mock()
    debugger_agent.debug_and_patch = Mock(
        return_value={"fixed_code": "# fixed code", "patch": ""}
    )
    guardian_agent = Mock()
    guardian_agent.review = Mock(return_value={"decision": "APPROVE", "reason": "ok"})
    guardian_agent.review_and_commit = Mock(
        return_value={"decision": "APPROVE", "reason": "ok", "commit": "abc123"}
    )
    policy_agent = Mock()
    policy_agent.audit = Mock(return_value={"result": "APPROVED", "violations": []})
    return {
        "requirement_agent": requirement_agent,
        "architect_agent": architect_agent,
        "planner_agent": Mock(),
        "coder_agent": Mock(),
        "tester_agent": tester_agent,
        "debugger_agent": debugger_agent,
        "guardian_agent": guardian_agent,
        "policy_agent": policy_agent,
        "postmortem_agent": Mock(),
        "knowledge_curator_agent": Mock(),
        "patch_applier_agent": Mock(),
    }


class TestReviewPhaseGuardianLoop:
    """run_review_phase() のテスト（Stage 2・spec §4-3/4-4）"""

    def _make_orchestrator(self, tmp_path, agents):
        return Orchestrator(
            project_path=str(tmp_path),
            constitution={"rule": "x"},
            llm_router=Mock(spec=LLMRouter),
            **agents,
        )

    def _context_with_passing_tests(self, tmp_path):
        context = OrchestratorContext(task_id="t1", user_requirement="req")
        context.implementation = {"files": {"app.py": "code"}}
        context.testing = {"tests": "def test(): pass", "passed": True, "stdout": "1 passed", "stderr": ""}
        return context

    def test_review_phase_approves_on_first_pass(self, tmp_path):
        agents = _create_mock_agents()
        agents["guardian_agent"].review.return_value = {"decision": "APPROVE", "reason": "ok"}

        orchestrator = self._make_orchestrator(tmp_path, agents)
        context = self._context_with_passing_tests(tmp_path)

        result = orchestrator.run_review_phase(context)

        assert result.terminal_state == "APPROVED"
        assert result.review_retries == 0
        agents["coder_agent"].implement_code.assert_not_called()

    def test_review_phase_reimplements_on_reject_then_approves(self, tmp_path):
        agents = _create_mock_agents()
        agents["guardian_agent"].review.side_effect = [
            {"decision": "REJECT", "reason": "命名規則違反", "feedback_for_coder": "スネークケースにせよ"},
            {"decision": "APPROVE", "reason": "ok"},
        ]
        agents["coder_agent"].implement_code.return_value = "fixed code"

        orchestrator = self._make_orchestrator(tmp_path, agents)
        context = self._context_with_passing_tests(tmp_path)

        result = orchestrator.run_review_phase(context)

        assert result.terminal_state == "APPROVED"
        assert result.review_retries == 1
        reimpl_kwargs = agents["coder_agent"].implement_code.call_args.kwargs
        assert "スネークケースにせよ" in reimpl_kwargs["task_description"]

    def test_review_phase_exhausts_retries_needs_human_review(self, tmp_path):
        agents = _create_mock_agents()
        agents["guardian_agent"].review.return_value = {
            "decision": "REJECT", "reason": "重大な問題", "feedback_for_coder": "全面修正が必要"
        }
        agents["coder_agent"].implement_code.return_value = "still bad code"

        orchestrator = self._make_orchestrator(tmp_path, agents)
        context = self._context_with_passing_tests(tmp_path)

        result = orchestrator.run_review_phase(context)

        assert result.terminal_state == "NEEDS_HUMAN_REVIEW"
        assert result.review_retries == 2  # REVIEW_MAX_RETRIES
        report_path = tmp_path / "review_report.md"
        assert report_path.exists()
        assert "全面修正が必要" in report_path.read_text(encoding="utf-8")

    def test_review_phase_skips_guardian_when_tests_still_failing(self, tmp_path):
        agents = _create_mock_agents()

        orchestrator = self._make_orchestrator(tmp_path, agents)
        context = OrchestratorContext(task_id="t1", user_requirement="req")
        context.implementation = {"files": {"app.py": "code"}}
        context.testing = {"tests": "t", "passed": False, "stdout": "", "stderr": "still failing"}

        result = orchestrator.run_review_phase(context)

        assert result.terminal_state == "NEEDS_HUMAN_REVIEW"
        agents["guardian_agent"].review.assert_not_called()
        report_path = tmp_path / "review_report.md"
        assert report_path.exists()

    def test_review_phase_bypasses_guardian_in_fast_lane(self, tmp_path):
        """fast_lane時はStage2のguardianループ/NEEDS_HUMAN_REVIEW強制をバイパスする
        （Stage2導入前の挙動を復元・回帰テスト）。

        fast_laneのcontext.testingは{"tests": ...}のみで"passed"キーを持たない
        （run_planning_phaseがそのまま設定し、run_testing_phaseのfast_lane早期
        リターンでも補完されない）ため、"passed"キーの有無に関わらずAPPROVEDに
        なることを確認する。
        """
        agents = _create_mock_agents()

        orchestrator = self._make_orchestrator(tmp_path, agents)
        context = OrchestratorContext(task_id="t1", user_requirement="req", fast_lane=True)
        context.implementation = {"files": {"app.py": "code"}}
        context.testing = {"tests": "some test code"}  # fast_lane shape, no "passed" key

        result = orchestrator.run_review_phase(context)

        assert result.terminal_state == "APPROVED"
        agents["guardian_agent"].review.assert_not_called()

    def test_review_phase_calls_review_and_commit_with_policy_allow_commit(self, tmp_path):
        """guardian APPROVE後、policy_agent.auditの結果がallow_commitとしてreview_and_commitに渡ること"""
        agents = _create_mock_agents()
        agents["guardian_agent"].review.return_value = {"decision": "APPROVE", "reason": "ok"}
        agents["guardian_agent"].review_and_commit.return_value = {
            "decision": "APPROVE", "reason": "ok", "commit": "deadbeef",
        }

        orchestrator = self._make_orchestrator(tmp_path, agents)
        context = self._context_with_passing_tests(tmp_path)

        result = orchestrator.run_review_phase(context)

        assert result.terminal_state == "APPROVED"
        agents["policy_agent"].audit.assert_called_once()
        agents["guardian_agent"].review_and_commit.assert_called_once()
        call_kwargs = agents["guardian_agent"].review_and_commit.call_args.kwargs
        assert call_kwargs["allow_commit"] is True
        assert call_kwargs["changed_files"] == ["app.py"]
        assert result.review["commit"] == "deadbeef"

    def test_review_phase_blocks_commit_on_policy_violation(self, tmp_path):
        """policy_agent.auditがREJECTEDならallow_commit=Falseで渡し、review_and_commitがREJECTを返したらNEEDS_HUMAN_REVIEWになること"""
        agents = _create_mock_agents()
        agents["guardian_agent"].review.return_value = {"decision": "APPROVE", "reason": "ok"}
        agents["policy_agent"].audit.return_value = {
            "result": "REJECTED", "violations": ["banned pattern"],
        }
        agents["guardian_agent"].review_and_commit.return_value = {
            "decision": "REJECT", "reason": "policy blocked", "feedback_for_coder": "ポリシー違反",
        }

        orchestrator = self._make_orchestrator(tmp_path, agents)
        context = self._context_with_passing_tests(tmp_path)

        result = orchestrator.run_review_phase(context)

        call_kwargs = agents["guardian_agent"].review_and_commit.call_args.kwargs
        assert call_kwargs["allow_commit"] is False
        assert result.terminal_state == "NEEDS_HUMAN_REVIEW"
        report_path = tmp_path / "review_report.md"
        assert "ポリシー違反" in report_path.read_text(encoding="utf-8")
