"""run_review_phase() の multi-LLM consensus 差し替え（L143配線）のテスト。

NEXUS_REVIEW_MODE=multi 時、初回レビューを MultiLLMReviewWorkflow の
run_consensus_review（glm+minimax 2機・契約中LLM構成）へ差し替える。
- 成功過半なら consensus の結果を guardian 互換 dict に変換
- max_severity=high なら REJECT（issues を feedback_for_coder へ）
- 失敗モデルが過半なら None を返し従来 guardian 単一レビューへ fallback
- default（single）は現行挙動を維持
失敗条件（fail条件・バックログL143）: 配線後に easy tier を実行し、ログ上の
2プロバイダ分の review 呼出が無ければ不成立 — 本テスト群は consensus 経由で
2機分の contributing_models が review_data に載ることを担保する。
"""

from typing import Any
from unittest.mock import Mock

from nexuscore.core.orchestrator import Orchestrator, OrchestratorContext
from nexuscore.llm.llm_router import LLMRouter
from nexuscore.workflows.multi_llm_review import ConsensusResult


def _create_mock_agents() -> dict[str, Any]:
    guardian_agent = Mock()
    guardian_agent.review = Mock(return_value={"decision": "APPROVE", "reason": "ok"})
    guardian_agent.review_and_commit = Mock(
        return_value={"decision": "APPROVE", "reason": "ok", "commit": "abc123"}
    )
    policy_agent = Mock()
    policy_agent.audit = Mock(return_value={"result": "APPROVED", "violations": []})
    return {
        "requirement_agent": Mock(),
        "architect_agent": Mock(),
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


def _make_consensus(
    issues: list[str],
    severity: str = "low",
    models: list[str] | None = None,
    confidence: float = 0.9,
) -> ConsensusResult:
    return ConsensusResult(
        issues=issues,
        confidence=confidence,
        contributing_models=models if models is not None else [
            "glm:glm-5.3",
            "minimax:MiniMax-M3",
        ],
        max_severity=severity,
    )


class TestConsensusToReviewData:
    """_consensus_to_review_data() の変換規則テスト（純関数）"""

    def test_high_severity_maps_to_reject_with_issues_as_feedback(self):
        from nexuscore.core.phase_runner_mixin import _consensus_to_review_data

        consensus = _make_consensus(
            issues=["SQL injection risk", "bare except swallows errors"],
            severity="high",
        )
        data = _consensus_to_review_data(consensus)
        assert data is not None
        assert data["decision"] == "REJECT"
        assert "SQL injection risk" in data["feedback_for_coder"]
        assert "bare except swallows errors" in data["feedback_for_coder"]
        assert data["consensus_models"] == ["glm:glm-5.3", "minimax:MiniMax-M3"]

    def test_low_severity_maps_to_approve_with_issues_attached(self):
        from nexuscore.core.phase_runner_mixin import _consensus_to_review_data

        consensus = _make_consensus(issues=["naming style"], severity="low")
        data = _consensus_to_review_data(consensus)
        assert data is not None
        assert data["decision"] == "APPROVE"
        assert data["consensus_issues"] == ["naming style"]

    def test_fail_majority_returns_none_for_fallback(self):
        from nexuscore.core.phase_runner_mixin import _consensus_to_review_data

        consensus = _make_consensus(
            issues=[],
            models=["glm:glm-5.3 (fail)", "minimax:MiniMax-M3 (fail)"],
        )
        assert _consensus_to_review_data(consensus) is None

    def test_empty_models_returns_none(self):
        from nexuscore.core.phase_runner_mixin import _consensus_to_review_data

        consensus = _make_consensus(issues=[], models=[])
        assert _consensus_to_review_data(consensus) is None

    def test_single_model_fail_is_not_majority(self):
        """2機中1機失敗は過半でない → 変換続行（残る1機の結果を採用）"""
        from nexuscore.core.phase_runner_mixin import _consensus_to_review_data

        consensus = _make_consensus(
            issues=["minor"],
            severity="low",
            models=["glm:glm-5.3 (fail)", "minimax:MiniMax-M3"],
        )
        data = _consensus_to_review_data(consensus)
        assert data is not None
        assert data["decision"] == "APPROVE"


class TestReviewPhaseMultiMode:
    """run_review_phase() の NEXUS_REVIEW_MODE=multi 統合テスト"""

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

    def _patch_consensus(self, monkeypatch, consensus: ConsensusResult):
        """LLM 呼出境界（run_consensus_review）のみモックし、非同期実行経路は実コードを使う"""
        async def fake_run_consensus_review(**kwargs):
            return consensus

        monkeypatch.setattr(
            "nexuscore.workflows.multi_llm_review.run_consensus_review",
            fake_run_consensus_review,
        )

    def test_multi_mode_uses_consensus_and_approves(self, tmp_path, monkeypatch):
        monkeypatch.setenv("NEXUS_REVIEW_MODE", "multi")
        self._patch_consensus(monkeypatch, _make_consensus(issues=["naming style"]))
        agents = _create_mock_agents()

        orchestrator = self._make_orchestrator(tmp_path, agents)
        context = self._context_with_passing_tests(tmp_path)

        result = orchestrator.run_review_phase(context)

        assert result.terminal_state == "APPROVED"
        # 初回レビューは guardian 単独では無く consensus を使う
        agents["guardian_agent"].review.assert_not_called()
        assert result.review["consensus_models"] == ["glm:glm-5.3", "minimax:MiniMax-M3"]

    def test_multi_mode_high_severity_rejects_then_guardian_retry(self, tmp_path, monkeypatch):
        """consensus の high severity REJECT → 既存 guardian ループで再レビュー"""
        monkeypatch.setenv("NEXUS_REVIEW_MODE", "multi")
        self._patch_consensus(
            monkeypatch,
            _make_consensus(issues=["SQL injection risk"], severity="high"),
        )
        agents = _create_mock_agents()
        agents["guardian_agent"].review.side_effect = [
            {"decision": "APPROVE", "reason": "ok"},
        ]
        agents["coder_agent"].implement_code.return_value = "fixed code"

        orchestrator = self._make_orchestrator(tmp_path, agents)
        context = self._context_with_passing_tests(tmp_path)

        result = orchestrator.run_review_phase(context)

        assert result.terminal_state == "APPROVED"
        assert result.review_retries == 1
        # consensus の issues が再実装フィードバックへ渡る
        reimpl_kwargs = agents["coder_agent"].implement_code.call_args.kwargs
        assert "SQL injection risk" in reimpl_kwargs["task_description"]
        # 再レビュー（REJECT後）は従来 guardian
        agents["guardian_agent"].review.assert_called_once()

    def test_multi_mode_fail_majority_falls_back_to_guardian(self, tmp_path, monkeypatch):
        monkeypatch.setenv("NEXUS_REVIEW_MODE", "multi")
        self._patch_consensus(
            monkeypatch,
            _make_consensus(issues=[], models=["glm:glm-5.3 (fail)", "minimax:MiniMax-M3 (fail)"]),
        )
        agents = _create_mock_agents()

        orchestrator = self._make_orchestrator(tmp_path, agents)
        context = self._context_with_passing_tests(tmp_path)

        result = orchestrator.run_review_phase(context)

        assert result.terminal_state == "APPROVED"
        # 失敗過半 → 従来 guardian 単一レビューへ fallback
        agents["guardian_agent"].review.assert_called_once()

    def test_default_multi_mode_uses_consensus(self, tmp_path, monkeypatch):
        """本番適用（2026-10-08 ふくけい承認）: 未設定時の default は multi"""
        monkeypatch.delenv("NEXUS_REVIEW_MODE", raising=False)
        self._patch_consensus(monkeypatch, _make_consensus(issues=[]))
        agents = _create_mock_agents()

        orchestrator = self._make_orchestrator(tmp_path, agents)
        context = self._context_with_passing_tests(tmp_path)

        result = orchestrator.run_review_phase(context)

        assert result.terminal_state == "APPROVED"
        agents["guardian_agent"].review.assert_not_called()

    def test_single_mode_optout_keeps_guardian(self, tmp_path, monkeypatch):
        """rollback経路: NEXUS_REVIEW_MODE=single で従来 guardian に戻せる"""
        monkeypatch.setenv("NEXUS_REVIEW_MODE", "single")
        agents = _create_mock_agents()

        # consensus が呼ばれたら fail させる（single では呼ばれない）
        async def _forbidden(**kwargs):
            raise AssertionError("single mode で consensus が呼ばれた")

        monkeypatch.setattr(
            "nexuscore.workflows.multi_llm_review.run_consensus_review", _forbidden
        )

        orchestrator = self._make_orchestrator(tmp_path, agents)
        context = self._context_with_passing_tests(tmp_path)

        result = orchestrator.run_review_phase(context)

        assert result.terminal_state == "APPROVED"
        agents["guardian_agent"].review.assert_called_once()


class TestConsensusMaxSeverity:
    """ConsensusResult への max_severity 集約（_merge_consensus 拡張）"""

    def test_merge_consensus_takes_max_severity(self):
        from nexuscore.workflows.multi_llm_review import ModelReview, _merge_consensus

        reviews = [
            ModelReview(
                model="glm:glm-5.3",
                summary={"issues": [{"title": "a"}], "severity": "medium", "confidence": 0.8},
            ),
            ModelReview(
                model="minimax:MiniMax-M3",
                summary={"issues": [{"title": "b"}], "severity": "high", "confidence": 0.9},
            ),
        ]
        result = _merge_consensus(reviews)
        assert result.max_severity == "high"

    def test_merge_consensus_default_low(self):
        from nexuscore.workflows.multi_llm_review import ModelReview, _merge_consensus

        reviews = [
            ModelReview(
                model="glm:glm-5.3",
                summary={"issues": [], "severity": "low", "confidence": 0.9},
            ),
        ]
        result = _merge_consensus(reviews)
        assert result.max_severity == "low"
