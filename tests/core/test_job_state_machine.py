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
        # メタデータも確認
        metadata = machine.get_metadata()
        assert metadata.job_id == "test-job-1"
        assert metadata.status == "pending"

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

    def test_invalid_transition_raises_value_error(self):
        """不正な遷移を試みると ValueError が発生"""
        machine = JobStateMachine(job_id="test-job-7b")
        # PendingState から CompletedState への直接遷移は不可
        with pytest.raises(ValueError, match="Cannot transition from pending to CompletedState"):
            machine.transition_to(CompletedState)

    def test_cannot_start_from_running_state(self):
        """Running 状態から start() を呼ぶと ValueError"""
        machine = JobStateMachine(job_id="test-job-7c")
        machine.start()
        with pytest.raises(ValueError, match="Cannot start job in state running"):
            machine.start()

    def test_cannot_fail_from_pending_state(self):
        """Pending 状態から fail() を呼ぶと ValueError"""
        machine = JobStateMachine(job_id="test-job-7d")
        with pytest.raises(ValueError, match="Cannot fail job in state pending"):
            machine.fail("Test error")

    def test_metadata_updates_through_lifecycle(self):
        """ライフサイクル全体でメタデータが正しく更新される"""
        machine = JobStateMachine(job_id="test-job-7e", job_type="metadata_test")

        # 初期状態
        assert machine.metadata.status == "pending"
        assert machine.metadata.message == "Job is waiting to start"
        assert machine.metadata.started_at is None

        # 開始
        machine.start()
        assert machine.metadata.status == "running"
        assert machine.metadata.message == "Job is executing"
        assert machine.metadata.started_at is not None

        # 完了
        machine.complete(details={"result": "success", "count": 42})
        assert machine.metadata.status == "completed"
        assert machine.metadata.message == "Job completed successfully"
        assert machine.metadata.finished_at is not None
        assert machine.metadata.details["result"] == "success"
        assert machine.metadata.details["count"] == 42

    def test_failed_state_with_custom_error_message(self):
        """FailedState がカスタムエラーメッセージを保持"""
        machine = JobStateMachine(job_id="test-job-7f")
        machine.start()
        error_msg = "Custom error message"
        machine.fail(error_message=error_msg)

        # FailedState がエラーメッセージを保持
        assert isinstance(machine.state, FailedState)
        assert machine.state.error_message == error_msg
        assert machine.metadata.error == error_msg


class TestStateClasses:
    """State クラス個別のテスト"""

    def test_pending_state_name(self):
        """PendingState の状態名"""
        machine = JobStateMachine(job_id="test-state-1")
        assert machine.state.get_state_name() == "pending"

    def test_running_state_name(self):
        """RunningState の状態名"""
        machine = JobStateMachine(job_id="test-state-2")
        machine.start()
        assert machine.state.get_state_name() == "running"

    def test_completed_state_name(self):
        """CompletedState の状態名"""
        machine = JobStateMachine(job_id="test-state-3")
        machine.start()
        machine.complete()
        assert machine.state.get_state_name() == "completed"

    def test_failed_state_name(self):
        """FailedState の状態名"""
        machine = JobStateMachine(job_id="test-state-4")
        machine.start()
        machine.fail("Test error")
        assert machine.state.get_state_name() == "failed"

    def test_pending_state_transition_rules(self):
        """PendingState の遷移ルール"""
        machine = JobStateMachine(job_id="test-state-5")
        # RunningState への遷移は可能
        assert machine.state.can_transition_to(RunningState) is True
        # CompletedState への遷移は不可
        assert machine.state.can_transition_to(CompletedState) is False
        # FailedState への遷移は不可
        assert machine.state.can_transition_to(FailedState) is False

    def test_running_state_transition_rules(self):
        """RunningState の遷移ルール"""
        machine = JobStateMachine(job_id="test-state-6")
        machine.start()
        # CompletedState への遷移は可能
        assert machine.state.can_transition_to(CompletedState) is True
        # FailedState への遷移は可能
        assert machine.state.can_transition_to(FailedState) is True
        # PendingState への遷移は不可
        assert machine.state.can_transition_to(PendingState) is False


class TestJobStateMachineWithoutDependencies:
    """SessionController と RunHistoryLogger なしでの動作テスト"""

    def test_state_machine_without_session_controller(self):
        """SessionController なしでも正常に動作"""
        machine = JobStateMachine(job_id="test-no-session")
        machine.start()
        machine.complete(details={"test": "data"})
        assert machine.get_current_state() == "completed"

    def test_state_machine_without_history_logger(self):
        """RunHistoryLogger なしでも正常に動作"""
        machine = JobStateMachine(job_id="test-no-history")
        machine.start()
        machine.fail("Test error")
        assert machine.get_current_state() == "failed"


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

