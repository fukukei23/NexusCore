"""
JobStateMachine の統合テスト
"""
from __future__ import annotations

import tempfile
import time
from pathlib import Path

import pytest

from nexuscore.core.job_state_machine import (
    JobStateMachine,
    PendingState,
    RunningState,
    CompletedState,
    FailedState,
)
from nexuscore.core.session_control import SessionController
from nexuscore.core.run_history import RunHistoryLogger


class TestJobStateMachine:
    """JobStateMachine の基本機能テスト"""

    def test_initial_state_is_pending(self):
        """初期状態は PendingState であることを確認"""
        machine = JobStateMachine(job_id="test-job-1")
        assert isinstance(machine.state, PendingState)
        assert machine.get_current_state() == "pending"

    def test_transition_pending_to_running(self):
        """Pending → Running の遷移をテスト"""
        machine = JobStateMachine(job_id="test-job-2")
        machine.start()
        assert isinstance(machine.state, RunningState)
        assert machine.get_current_state() == "running"
        assert machine.metadata.started_at is not None

    def test_transition_running_to_completed(self):
        """Running → Completed の遷移をテスト"""
        machine = JobStateMachine(job_id="test-job-3")
        machine.start()
        machine.complete(details={"test": "data"})
        assert isinstance(machine.state, CompletedState)
        assert machine.get_current_state() == "completed"
        assert machine.metadata.finished_at is not None
        assert machine.metadata.details.get("test") == "data"

    def test_transition_running_to_failed(self):
        """Running → Failed の遷移をテスト"""
        machine = JobStateMachine(job_id="test-job-4")
        machine.start()
        error_msg = "Test error"
        machine.fail(error_message=error_msg, details={"error_code": 500})
        assert isinstance(machine.state, FailedState)
        assert machine.get_current_state() == "failed"
        assert machine.metadata.finished_at is not None
        assert machine.metadata.error == error_msg
        assert machine.metadata.details.get("error_code") == 500

    def test_invalid_transition_from_pending(self):
        """Pending から直接 Completed への遷移は不可"""
        machine = JobStateMachine(job_id="test-job-5")
        with pytest.raises(ValueError, match="Cannot complete job in state"):
            machine.complete()

    def test_invalid_transition_from_completed(self):
        """Completed は終端状態（遷移不可）"""
        machine = JobStateMachine(job_id="test-job-6")
        machine.start()
        machine.complete()
        # 終端状態からは遷移できない
        assert machine.state.can_transition_to(RunningState) is False

    def test_invalid_transition_from_failed(self):
        """Failed は終端状態（遷移不可）"""
        machine = JobStateMachine(job_id="test-job-7")
        machine.start()
        machine.fail("Test error")
        # 終端状態からは遷移できない
        assert machine.state.can_transition_to(RunningState) is False


class TestJobStateMachineWithSessionController:
    """SessionController との統合テスト"""

    def test_state_persisted_to_session(self):
        """状態遷移がセッションに保存されることを確認"""
        with tempfile.TemporaryDirectory() as tmpdir:
            session_controller = SessionController(
                session_id="test-session-1",
                root_dir=tmpdir,
            )
            machine = JobStateMachine(
                job_id="test-job-8",
                session_controller=session_controller,
            )

            # 状態遷移を実行
            machine.start()
            machine.complete()

            # セッション状態を確認
            state_file = Path(tmpdir) / "test-session-1.state.json"
            assert state_file.exists()

            import json
            with state_file.open() as f:
                state_data = json.load(f)
                assert state_data["last_phase"] == "state_completed"
                assert state_data["metadata"]["state"] == "completed"


class TestJobStateMachineWithHistoryLogger:
    """RunHistoryLogger との統合テスト"""

    def test_state_logged_to_history(self):
        """状態遷移が履歴に記録されることを確認"""
        with tempfile.TemporaryDirectory() as tmpdir:
            history_logger = RunHistoryLogger(project_root=tmpdir)
            machine = JobStateMachine(
                job_id="test-job-9",
                history_logger=history_logger,
                job_type="test_job",
            )

            # 状態遷移を実行
            machine.start()
            machine.complete(details={"test": "completed"})

            # 履歴を確認
            history_file = Path(tmpdir) / ".nexus" / "history" / "test_job.log.jsonl"
            assert history_file.exists()

            import json
            with history_file.open() as f:
                lines = [line.strip() for line in f if line.strip()]
                assert len(lines) == 1
                record = json.loads(lines[0])
                assert record["run_id"] == "test-job-9"
                assert record["kind"] == "test_job"
                assert record["status"] == "success"

    def test_failure_logged_to_history(self):
        """失敗が履歴に記録されることを確認"""
        with tempfile.TemporaryDirectory() as tmpdir:
            history_logger = RunHistoryLogger(project_root=tmpdir)
            machine = JobStateMachine(
                job_id="test-job-10",
                history_logger=history_logger,
                job_type="test_job",
            )

            # 失敗を記録
            machine.start()
            machine.fail("Test error", details={"error_code": 500})

            # 履歴を確認
            history_file = Path(tmpdir) / ".nexus" / "history" / "test_job.log.jsonl"
            assert history_file.exists()

            import json
            with history_file.open() as f:
                lines = [line.strip() for line in f if line.strip()]
                assert len(lines) == 1
                record = json.loads(lines[0])
                assert record["run_id"] == "test-job-10"
                assert record["status"] == "error"
                assert "Test error" in record["summary"]
                assert record["details"]["error"] == "Test error"


class TestJobStateMachineIntegration:
    """完全統合テスト（SessionController + RunHistoryLogger）"""

    def test_full_integration(self):
        """SessionController と RunHistoryLogger の完全統合テスト"""
        with tempfile.TemporaryDirectory() as tmpdir:
            session_controller = SessionController(
                session_id="test-session-2",
                root_dir=tmpdir,
            )
            history_logger = RunHistoryLogger(project_root=tmpdir)
            machine = JobStateMachine(
                job_id="test-job-11",
                session_controller=session_controller,
                history_logger=history_logger,
                job_type="integration_test",
            )

            # 完全なライフサイクルを実行
            assert machine.get_current_state() == "pending"
            machine.start()
            assert machine.get_current_state() == "running"
            machine.complete(details={"result": "success"})
            assert machine.get_current_state() == "completed"

            # セッション状態を確認
            state_file = Path(tmpdir) / "test-session-2.state.json"
            assert state_file.exists()

            # 履歴を確認
            history_file = Path(tmpdir) / ".nexus" / "history" / "integration_test.log.jsonl"
            assert history_file.exists()

            import json
            with history_file.open() as f:
                lines = [line.strip() for line in f if line.strip()]
                assert len(lines) == 1
                record = json.loads(lines[0])
                assert record["status"] == "success"
                assert record["details"]["result"] == "success"

