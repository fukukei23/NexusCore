"""
Comprehensive tests for job_state_machine module.

Tests state machine implementation for job progress management
with SessionController and RunHistoryLogger integration.
"""

import tempfile
import time
from unittest.mock import Mock, patch, MagicMock, call
import pytest

from nexuscore.core.job_state_machine import (
    State,
    PendingState,
    RunningState,
    CompletedState,
    FailedState,
    JobMetadata,
    JobStateMachine,
)
from nexuscore.core.session_control import SessionController
from nexuscore.core.run_history import RunHistoryLogger


class TestStateClasses:
    """Tests for individual State classes."""

    def test_pending_state_handle(self):
        """Test PendingState.handle() updates metadata."""
        machine = Mock(job_id="job-1")
        state = PendingState(machine)

        state.handle()

        machine._update_state_metadata.assert_called_once_with({
            "status": "pending",
            "message": "Job is waiting to start"
        })

    def test_pending_state_name(self):
        """Test PendingState.get_state_name() returns 'pending'."""
        machine = Mock()
        state = PendingState(machine)

        assert state.get_state_name() == "pending"

    def test_pending_state_can_transition_to_running(self):
        """Test PendingState can transition to RunningState."""
        machine = Mock()
        state = PendingState(machine)

        assert state.can_transition_to(RunningState) is True

    def test_pending_state_cannot_transition_to_completed(self):
        """Test PendingState cannot transition to CompletedState."""
        machine = Mock()
        state = PendingState(machine)

        assert state.can_transition_to(CompletedState) is False

    def test_running_state_handle(self):
        """Test RunningState.handle() updates metadata."""
        machine = Mock(job_id="job-1")
        state = RunningState(machine)

        state.handle()

        machine._update_state_metadata.assert_called_once_with({
            "status": "running",
            "message": "Job is executing"
        })

    def test_running_state_name(self):
        """Test RunningState.get_state_name() returns 'running'."""
        machine = Mock()
        state = RunningState(machine)

        assert state.get_state_name() == "running"

    def test_running_state_can_transition_to_completed(self):
        """Test RunningState can transition to CompletedState."""
        machine = Mock()
        state = RunningState(machine)

        assert state.can_transition_to(CompletedState) is True

    def test_running_state_can_transition_to_failed(self):
        """Test RunningState can transition to FailedState."""
        machine = Mock()
        state = RunningState(machine)

        assert state.can_transition_to(FailedState) is True

    def test_running_state_cannot_transition_to_pending(self):
        """Test RunningState cannot transition back to PendingState."""
        machine = Mock()
        state = RunningState(machine)

        assert state.can_transition_to(PendingState) is False

    def test_completed_state_handle(self):
        """Test CompletedState.handle() updates metadata and records completion."""
        machine = Mock(job_id="job-1")
        state = CompletedState(machine)

        state.handle()

        machine._update_state_metadata.assert_called_once_with({
            "status": "completed",
            "message": "Job completed successfully"
        })
        machine._record_completion.assert_called_once()

    def test_completed_state_name(self):
        """Test CompletedState.get_state_name() returns 'completed'."""
        machine = Mock()
        state = CompletedState(machine)

        assert state.get_state_name() == "completed"

    def test_completed_state_is_terminal(self):
        """Test CompletedState is terminal (no transitions allowed)."""
        machine = Mock()
        state = CompletedState(machine)

        assert state.can_transition_to(PendingState) is False
        assert state.can_transition_to(RunningState) is False
        assert state.can_transition_to(FailedState) is False

    def test_failed_state_handle(self):
        """Test FailedState.handle() updates metadata and records failure."""
        machine = Mock(job_id="job-1")
        state = FailedState(machine, error_message="Test error")

        state.handle()

        machine._update_state_metadata.assert_called_once_with({
            "status": "failed",
            "message": "Job execution failed",
            "error": "Test error"
        })
        machine._record_failure.assert_called_once_with("Test error")

    def test_failed_state_default_error_message(self):
        """Test FailedState uses default error message if not provided."""
        machine = Mock(job_id="job-1")
        state = FailedState(machine)

        assert state.error_message == "Unknown error"

    def test_failed_state_name(self):
        """Test FailedState.get_state_name() returns 'failed'."""
        machine = Mock()
        state = FailedState(machine)

        assert state.get_state_name() == "failed"

    def test_failed_state_is_terminal(self):
        """Test FailedState is terminal (no transitions allowed)."""
        machine = Mock()
        state = FailedState(machine)

        assert state.can_transition_to(PendingState) is False
        assert state.can_transition_to(RunningState) is False
        assert state.can_transition_to(CompletedState) is False


class TestJobMetadata:
    """Tests for JobMetadata dataclass."""

    def test_job_metadata_creation_with_defaults(self):
        """Test JobMetadata creation with default values."""
        metadata = JobMetadata(job_id="job-1")

        assert metadata.job_id == "job-1"
        assert metadata.job_type == "orchestrator"
        assert metadata.started_at is None
        assert metadata.finished_at is None
        assert metadata.status == "pending"
        assert metadata.message == ""
        assert metadata.error is None
        assert metadata.details == {}

    def test_job_metadata_creation_with_custom_values(self):
        """Test JobMetadata creation with custom values."""
        metadata = JobMetadata(
            job_id="job-2",
            job_type="self_healing",
            started_at=100.0,
            finished_at=200.0,
            status="running",
            message="Test message",
            error="Test error",
            details={"key": "value"}
        )

        assert metadata.job_id == "job-2"
        assert metadata.job_type == "self_healing"
        assert metadata.started_at == 100.0
        assert metadata.finished_at == 200.0
        assert metadata.status == "running"
        assert metadata.message == "Test message"
        assert metadata.error == "Test error"
        assert metadata.details == {"key": "value"}


class TestJobStateMachineInit:
    """Tests for JobStateMachine initialization."""

    def test_init_creates_state_machine(self):
        """Test initialization creates JobStateMachine."""
        machine = JobStateMachine("job-1")

        assert machine.job_id == "job-1"
        assert machine.job_type == "orchestrator"
        assert isinstance(machine.state, PendingState)
        assert machine.metadata.job_id == "job-1"
        assert machine.session_controller is None
        assert machine.history_logger is None

    def test_init_with_custom_job_type(self):
        """Test initialization with custom job type."""
        machine = JobStateMachine("job-1", job_type="self_healing")

        assert machine.job_type == "self_healing"
        assert machine.metadata.job_type == "self_healing"

    def test_init_with_session_controller(self):
        """Test initialization with SessionController."""
        with tempfile.TemporaryDirectory() as tmpdir:
            controller = SessionController("session-1", root_dir=tmpdir)
            machine = JobStateMachine("job-1", session_controller=controller)

            assert machine.session_controller is controller

    def test_init_with_history_logger(self):
        """Test initialization with RunHistoryLogger."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = RunHistoryLogger(tmpdir)
            machine = JobStateMachine("job-1", history_logger=logger)

            assert machine.history_logger is logger

    def test_init_calls_initial_state_handle(self):
        """Test initialization calls handle() on initial state."""
        with patch.object(PendingState, 'handle') as mock_handle:
            machine = JobStateMachine("job-1")

            mock_handle.assert_called_once()


class TestJobStateMachineTransitions:
    """Tests for state transition methods."""

    def test_transition_to_valid_state(self):
        """Test transition_to() with valid transition."""
        machine = JobStateMachine("job-1")

        machine.transition_to(RunningState)

        assert isinstance(machine.state, RunningState)
        assert machine.get_current_state() == "running"

    def test_transition_to_invalid_state_raises_error(self):
        """Test transition_to() with invalid transition raises ValueError."""
        machine = JobStateMachine("job-1")

        with pytest.raises(ValueError, match="Cannot transition from pending"):
            machine.transition_to(CompletedState)

    def test_transition_to_calls_new_state_handle(self):
        """Test transition_to() calls handle() on new state."""
        machine = JobStateMachine("job-1")

        with patch.object(RunningState, 'handle') as mock_handle:
            machine.transition_to(RunningState)

            mock_handle.assert_called_once()

    def test_transition_to_with_state_kwargs(self):
        """Test transition_to() passes kwargs to state constructor."""
        machine = JobStateMachine("job-1")
        machine.transition_to(RunningState)

        machine.transition_to(FailedState, error_message="Custom error")

        assert machine.state.error_message == "Custom error"

    def test_transition_to_updates_session_controller(self):
        """Test transition_to() updates SessionController."""
        with tempfile.TemporaryDirectory() as tmpdir:
            controller = SessionController("session-1", root_dir=tmpdir)
            machine = JobStateMachine("job-1", session_controller=controller)

            machine.transition_to(RunningState)

            # Verify checkpoint was called
            assert controller.state_file.exists()

    def test_transition_sequence_pending_running_completed(self):
        """Test full transition sequence: Pending → Running → Completed."""
        machine = JobStateMachine("job-1")
        assert machine.get_current_state() == "pending"

        machine.transition_to(RunningState)
        assert machine.get_current_state() == "running"

        machine.transition_to(CompletedState)
        assert machine.get_current_state() == "completed"

    def test_transition_sequence_pending_running_failed(self):
        """Test full transition sequence: Pending → Running → Failed."""
        machine = JobStateMachine("job-1")
        assert machine.get_current_state() == "pending"

        machine.transition_to(RunningState)
        assert machine.get_current_state() == "running"

        machine.transition_to(FailedState, error_message="Test error")
        assert machine.get_current_state() == "failed"


class TestJobStateMachineConvenienceMethods:
    """Tests for convenience methods (start, complete, fail)."""

    def test_start_transitions_to_running(self):
        """Test start() transitions from Pending to Running."""
        machine = JobStateMachine("job-1")

        with patch('time.time', return_value=1000.0):
            machine.start()

        assert machine.get_current_state() == "running"
        assert machine.metadata.started_at == 1000.0

    def test_start_raises_error_if_not_pending(self):
        """Test start() raises error if not in Pending state."""
        machine = JobStateMachine("job-1")
        machine.start()

        with pytest.raises(ValueError, match="Cannot start job in state running"):
            machine.start()

    def test_complete_transitions_to_completed(self):
        """Test complete() transitions from Running to Completed."""
        machine = JobStateMachine("job-1")
        machine.start()

        with patch('time.time', return_value=2000.0):
            machine.complete()

        assert machine.get_current_state() == "completed"
        assert machine.metadata.finished_at == 2000.0

    def test_complete_with_details(self):
        """Test complete() updates metadata details."""
        machine = JobStateMachine("job-1")
        machine.start()

        machine.complete(details={"result": "success", "count": 42})

        assert machine.metadata.details["result"] == "success"
        assert machine.metadata.details["count"] == 42

    def test_complete_raises_error_if_not_running(self):
        """Test complete() raises error if not in Running state."""
        machine = JobStateMachine("job-1")

        with pytest.raises(ValueError, match="Cannot complete job in state pending"):
            machine.complete()

    def test_fail_transitions_to_failed(self):
        """Test fail() transitions from Running to Failed."""
        machine = JobStateMachine("job-1")
        machine.start()

        with patch('time.time', return_value=2000.0):
            machine.fail("Test error occurred")

        assert machine.get_current_state() == "failed"
        assert machine.metadata.finished_at == 2000.0

    def test_fail_with_details(self):
        """Test fail() updates metadata details."""
        machine = JobStateMachine("job-1")
        machine.start()

        machine.fail("Error", details={"error_code": 500})

        assert machine.metadata.details["error_code"] == 500

    def test_fail_raises_error_if_not_running(self):
        """Test fail() raises error if not in Running state."""
        machine = JobStateMachine("job-1")

        with pytest.raises(ValueError, match="Cannot fail job in state pending"):
            machine.fail("Error")


class TestJobStateMachineMetadata:
    """Tests for metadata management."""

    def test_get_current_state(self):
        """Test get_current_state() returns current state name."""
        machine = JobStateMachine("job-1")
        assert machine.get_current_state() == "pending"

        machine.start()
        assert machine.get_current_state() == "running"

    def test_get_metadata(self):
        """Test get_metadata() returns JobMetadata."""
        machine = JobStateMachine("job-1")

        metadata = machine.get_metadata()

        assert isinstance(metadata, JobMetadata)
        assert metadata.job_id == "job-1"

    def test_update_state_metadata_updates_status(self):
        """Test _update_state_metadata() updates status."""
        machine = JobStateMachine("job-1")

        machine._update_state_metadata({"status": "custom_status"})

        assert machine.metadata.status == "custom_status"

    def test_update_state_metadata_updates_message(self):
        """Test _update_state_metadata() updates message."""
        machine = JobStateMachine("job-1")

        machine._update_state_metadata({"message": "Custom message"})

        assert machine.metadata.message == "Custom message"

    def test_update_state_metadata_updates_error(self):
        """Test _update_state_metadata() updates error."""
        machine = JobStateMachine("job-1")

        machine._update_state_metadata({"error": "Error message"})

        assert machine.metadata.error == "Error message"

    def test_update_state_metadata_updates_details(self):
        """Test _update_state_metadata() updates details."""
        machine = JobStateMachine("job-1")

        machine._update_state_metadata({"details": {"key": "value"}})

        assert machine.metadata.details["key"] == "value"


class TestSessionControllerIntegration:
    """Tests for SessionController integration."""

    def test_transition_creates_checkpoint(self):
        """Test state transitions create checkpoints in SessionController."""
        with tempfile.TemporaryDirectory() as tmpdir:
            controller = SessionController("session-1", root_dir=tmpdir)
            machine = JobStateMachine("job-1", session_controller=controller)

            machine.start()

            # Verify checkpoint file exists
            assert controller.state_file.exists()

    def test_checkpoint_contains_state_info(self):
        """Test checkpoint contains state information."""
        with tempfile.TemporaryDirectory() as tmpdir:
            controller = SessionController("session-1", root_dir=tmpdir)
            machine = JobStateMachine("job-1", session_controller=controller, job_type="test_job")

            machine.start()

            import json
            with controller.state_file.open("r") as f:
                data = json.load(f)

            assert data["last_phase"] == "state_running"
            assert data["metadata"]["state"] == "running"
            assert data["metadata"]["job_id"] == "job-1"
            assert data["metadata"]["job_type"] == "test_job"


class TestHistoryLoggerIntegration:
    """Tests for RunHistoryLogger integration."""

    def test_record_completion_logs_run(self):
        """Test _record_completion() logs to RunHistoryLogger."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = RunHistoryLogger(tmpdir)
            machine = JobStateMachine("job-1", history_logger=logger, job_type="test_job")

            machine.start()
            machine.complete()

            # Verify log file exists
            log_file = logger.history_dir / "test_job.log.jsonl"
            assert log_file.exists()

            # Verify log content
            with log_file.open("r") as f:
                import json
                data = json.loads(f.read())

            assert data["run_id"] == "job-1"
            assert data["status"] == "success"
            assert data["kind"] == "test_job"

    def test_record_failure_logs_run(self):
        """Test _record_failure() logs to RunHistoryLogger."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = RunHistoryLogger(tmpdir)
            machine = JobStateMachine("job-1", history_logger=logger, job_type="test_job")

            machine.start()
            machine.fail("Test error")

            # Verify log content
            log_file = logger.history_dir / "test_job.log.jsonl"
            with log_file.open("r") as f:
                import json
                data = json.loads(f.read())

            assert data["run_id"] == "job-1"
            assert data["status"] == "error"
            assert data["summary"] == "Job failed: Test error"
            assert data["details"]["error"] == "Test error"

    def test_record_completion_without_logger_does_nothing(self):
        """Test _record_completion() without logger doesn't raise."""
        machine = JobStateMachine("job-1")

        machine.start()
        # Should not raise
        machine.complete()

    def test_record_failure_without_logger_does_nothing(self):
        """Test _record_failure() without logger doesn't raise."""
        machine = JobStateMachine("job-1")

        machine.start()
        # Should not raise
        machine.fail("Error")


class TestJobStateMachineIntegration:
    """Integration tests for JobStateMachine."""

    def test_full_successful_job_workflow(self):
        """Test complete successful job workflow with all integrations."""
        with tempfile.TemporaryDirectory() as tmpdir:
            controller = SessionController("session-1", root_dir=tmpdir)
            logger = RunHistoryLogger(tmpdir)

            machine = JobStateMachine(
                "job-1",
                session_controller=controller,
                history_logger=logger,
                job_type="integration_test"
            )

            # Start job
            with patch('time.time', return_value=1000.0):
                machine.start()

            assert machine.get_current_state() == "running"
            assert machine.metadata.started_at == 1000.0

            # Complete job
            with patch('time.time', return_value=2000.0):
                machine.complete(details={"result": "success"})

            assert machine.get_current_state() == "completed"
            assert machine.metadata.finished_at == 2000.0

            # Verify history logged
            runs = logger.load_runs("integration_test")
            assert len(runs) == 1
            assert runs[0]["status"] == "success"

    def test_full_failed_job_workflow(self):
        """Test complete failed job workflow with all integrations."""
        with tempfile.TemporaryDirectory() as tmpdir:
            controller = SessionController("session-1", root_dir=tmpdir)
            logger = RunHistoryLogger(tmpdir)

            machine = JobStateMachine(
                "job-1",
                session_controller=controller,
                history_logger=logger,
                job_type="integration_test"
            )

            machine.start()
            machine.fail("Something went wrong", details={"error_code": 500})

            assert machine.get_current_state() == "failed"

            # Verify history logged
            runs = logger.load_runs("integration_test")
            assert len(runs) == 1
            assert runs[0]["status"] == "error"
            assert "Something went wrong" in runs[0]["summary"]

    def test_invalid_transition_sequence(self):
        """Test invalid transition sequence raises appropriate errors."""
        machine = JobStateMachine("job-1")

        # Cannot go directly from Pending to Completed
        with pytest.raises(ValueError):
            machine.transition_to(CompletedState)

        # Cannot complete without starting
        with pytest.raises(ValueError):
            machine.complete()

        # Start properly
        machine.start()

        # Cannot start again
        with pytest.raises(ValueError):
            machine.start()

        # Complete properly
        machine.complete()

        # Cannot transition from terminal state
        with pytest.raises(ValueError):
            machine.transition_to(RunningState)
