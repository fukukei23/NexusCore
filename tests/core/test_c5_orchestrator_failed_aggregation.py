"""C5: orchestrator の FAILED 集約検証（spec E+α改 T9・FR5・4.3）。

T9: orchestrator が伝播された例外を Run.status="FAILED" に集約する。

検証対象は orchestrator 内の集約口（run_full_project の except → _log_orch_event
"FAILED" 発火 + 再 raise）。呼出側での Run.status="FAILED" DB 反映は
tests/webapp/test_celery_app.py（例外経路・既存カバー）が担保しており役割分離。
"""

from unittest.mock import ANY, MagicMock

import pytest

from nexuscore.core.errors import ModelRateLimitError
from nexuscore.core.orchestrator import Orchestrator


@pytest.fixture
def mock_agents():
    """全エージェントのモック（tests/core/test_orchestrator.py と同一構成）。"""
    return {
        "requirement_agent": MagicMock(),
        "architect_agent": MagicMock(),
        "planner_agent": MagicMock(),
        "coder_agent": MagicMock(),
        "tester_agent": MagicMock(),
        "debugger_agent": MagicMock(),
        "guardian_agent": MagicMock(),
        "policy_agent": MagicMock(),
        "postmortem_agent": MagicMock(),
        "knowledge_curator_agent": MagicMock(),
        "patch_applier_agent": MagicMock(),
        "llm_router": MagicMock(),
    }


class TestT9OrchestratorFailedAggregation:
    """T9: 伝播例外の FAILED イベント集約（FR5）。"""

    def test_llm_failure_logs_failed_event_and_reraises(self, tmp_path, mock_agents, monkeypatch):
        """T9: retry枯渇後の ModelRateLimitError 伝播 → FAILED イベント発火 + 再 raise。"""
        monkeypatch.delenv("NEXUSCORE_ALLOW_STUB_FALLBACK", raising=False)
        # C5 伝播後の例外（retry 枯渇で convert 済み想定）を requirement フェーズで発生させる
        mock_agents["requirement_agent"].use_ui = False
        mock_agents["requirement_agent"].analyze_requirement = MagicMock(
            side_effect=ModelRateLimitError("Rate limit error: 429 Too Many Requests")
        )

        orchestrator = Orchestrator(
            project_path=str(tmp_path),
            constitution={"automation_policy": {"autonomy_level": 1}},
            **mock_agents,
        )
        orchestrator._log_orch_event = MagicMock()

        with pytest.raises(ModelRateLimitError, match="429"):
            orchestrator.run_full_project("Test requirement", run_db_id=123)

        # FAILED イベントが run_db_id=123 に対して発火される
        orchestrator._log_orch_event.assert_any_call(123, "orchestrator", "FAILED", ANY)

        # 誤成功（FINISHED）は発火されていない
        logged_statuses = [c.args[2] for c in orchestrator._log_orch_event.call_args_list]
        assert "FINISHED" not in logged_statuses

    def test_failed_event_message_contains_error(self, tmp_path, mock_agents, monkeypatch):
        """T9: FAILED メッセージに元エラー文が含まれる（切捨て200字）。"""
        monkeypatch.delenv("NEXUSCORE_ALLOW_STUB_FALLBACK", raising=False)
        mock_agents["requirement_agent"].use_ui = False
        mock_agents["requirement_agent"].analyze_requirement = MagicMock(
            side_effect=ModelRateLimitError("Rate limit error: quota exceeded")
        )

        orchestrator = Orchestrator(
            project_path=str(tmp_path),
            constitution={"automation_policy": {"autonomy_level": 1}},
            **mock_agents,
        )
        orchestrator._log_orch_event = MagicMock()

        with pytest.raises(ModelRateLimitError):
            orchestrator.run_full_project("Test requirement", run_db_id=7)

        failed_calls = [
            c for c in orchestrator._log_orch_event.call_args_list if c.args[2] == "FAILED"
        ]
        assert len(failed_calls) == 1
        assert "quota exceeded" in failed_calls[0].args[3]
