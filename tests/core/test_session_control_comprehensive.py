"""
Comprehensive tests for session_control module.

Tests session lifecycle management including stop/pause/continue commands,
checkpoints, and state persistence.
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

from nexuscore.core.session_control import SessionController, SessionState


class TestSessionState:
    """Tests for SessionState dataclass."""

    def test_session_state_creation(self):
        """Test creating SessionState with all fields."""
        state = SessionState(
            session_id="test-123",
            status="running",
            last_phase="planning",
            last_updated=1234567890.0,
            metadata={"key": "value"},
        )

        assert state.session_id == "test-123"
        assert state.status == "running"
        assert state.last_phase == "planning"
        assert state.last_updated == 1234567890.0
        assert state.metadata == {"key": "value"}


class TestSessionControllerInit:
    """Tests for SessionController initialization."""

    def test_init_creates_session_controller(self):
        """Test SessionController initialization."""
        with tempfile.TemporaryDirectory() as tmpdir:
            controller = SessionController("test-session", root_dir=tmpdir)

            assert controller.session_id == "test-session"
            assert controller.root == Path(tmpdir)
            assert controller.control_file == Path(tmpdir) / "test-session.control.json"
            assert controller.state_file == Path(tmpdir) / "test-session.state.json"

    def test_init_creates_root_directory_if_not_exists(self):
        """Test initialization creates root directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            nested_dir = Path(tmpdir) / "nested" / "sessions"
            SessionController("test", root_dir=str(nested_dir))

            assert nested_dir.exists()

    def test_init_with_default_root_dir(self):
        """Test default root_dir is .nexus/sessions."""
        controller = SessionController("test-id")

        assert ".nexus/sessions" in str(controller.root)


class TestSessionControllerExternalCommands:
    """Tests for external control commands (UI/CLI/API)."""

    def test_request_stop_writes_stop_command(self):
        """Test request_stop writes stop command to control file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            controller = SessionController("test", root_dir=tmpdir)

            controller.request_stop()

            with controller.control_file.open("r") as f:
                data = json.load(f)
            assert data["command"] == "stop"

    def test_request_pause_writes_pause_command(self):
        """Test request_pause writes pause command to control file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            controller = SessionController("test", root_dir=tmpdir)

            controller.request_pause()

            with controller.control_file.open("r") as f:
                data = json.load(f)
            assert data["command"] == "pause"

    def test_request_continue_writes_continue_command(self):
        """Test request_continue writes continue command to control file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            controller = SessionController("test", root_dir=tmpdir)

            controller.request_continue()

            with controller.control_file.open("r") as f:
                data = json.load(f)
            assert data["command"] == "continue"

    def test_multiple_commands_overwrite_previous(self):
        """Test new commands overwrite previous commands."""
        with tempfile.TemporaryDirectory() as tmpdir:
            controller = SessionController("test", root_dir=tmpdir)

            controller.request_stop()
            controller.request_continue()

            with controller.control_file.open("r") as f:
                data = json.load(f)
            assert data["command"] == "continue"


class TestSessionControllerInternalMethods:
    """Tests for internal methods used by Orchestrator."""

    def test_should_stop_returns_true_for_stop_command(self):
        """Test should_stop returns True when stop command present."""
        with tempfile.TemporaryDirectory() as tmpdir:
            controller = SessionController("test", root_dir=tmpdir)
            controller.request_stop()

            assert controller.should_stop() is True

    def test_should_stop_returns_true_for_pause_command(self):
        """Test should_stop returns True when pause command present."""
        with tempfile.TemporaryDirectory() as tmpdir:
            controller = SessionController("test", root_dir=tmpdir)
            controller.request_pause()

            assert controller.should_stop() is True

    def test_should_stop_returns_false_for_continue_command(self):
        """Test should_stop returns False when continue command present."""
        with tempfile.TemporaryDirectory() as tmpdir:
            controller = SessionController("test", root_dir=tmpdir)
            controller.request_continue()

            assert controller.should_stop() is False

    def test_should_stop_returns_false_when_no_control_file(self):
        """Test should_stop returns False when no control file exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            controller = SessionController("test", root_dir=tmpdir)

            assert controller.should_stop() is False

    def test_checkpoint_creates_state_file(self):
        """Test checkpoint creates state file with correct structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            controller = SessionController("test-session", root_dir=tmpdir)

            with patch("time.time", return_value=1234567890.0):
                controller.checkpoint(phase="planning", metadata={"plan": "test plan"})

            assert controller.state_file.exists()
            with controller.state_file.open("r") as f:
                data = json.load(f)

            assert data["session_id"] == "test-session"
            assert data["status"] == "running"
            assert data["last_phase"] == "planning"
            assert data["last_updated"] == 1234567890.0
            assert data["metadata"]["plan"] == "test plan"

    def test_checkpoint_without_metadata(self):
        """Test checkpoint with no metadata uses empty dict."""
        with tempfile.TemporaryDirectory() as tmpdir:
            controller = SessionController("test", root_dir=tmpdir)

            controller.checkpoint(phase="coding")

            with controller.state_file.open("r") as f:
                data = json.load(f)

            assert data["metadata"] == {}

    def test_checkpoint_updates_timestamp(self):
        """Test checkpoint updates timestamp on each call."""
        with tempfile.TemporaryDirectory() as tmpdir:
            controller = SessionController("test", root_dir=tmpdir)

            with patch("time.time", return_value=1000.0):
                controller.checkpoint(phase="phase1")

            with patch("time.time", return_value=2000.0):
                controller.checkpoint(phase="phase2")

            with controller.state_file.open("r") as f:
                data = json.load(f)

            assert data["last_updated"] == 2000.0
            assert data["last_phase"] == "phase2"

    def test_checkpoint_preserves_session_id(self):
        """Test checkpoint preserves session_id across calls."""
        with tempfile.TemporaryDirectory() as tmpdir:
            controller = SessionController("my-session-id", root_dir=tmpdir)

            controller.checkpoint(phase="phase1")
            controller.checkpoint(phase="phase2")

            with controller.state_file.open("r") as f:
                data = json.load(f)

            assert data["session_id"] == "my-session-id"


class TestSessionControllerFileIO:
    """Tests for file I/O utility methods."""

    def test_write_control_creates_json_file(self):
        """Test _write_control creates properly formatted JSON."""
        with tempfile.TemporaryDirectory() as tmpdir:
            controller = SessionController("test", root_dir=tmpdir)

            controller._write_control({"command": "test", "extra": "data"})

            assert controller.control_file.exists()
            with controller.control_file.open("r") as f:
                data = json.load(f)

            assert data["command"] == "test"
            assert data["extra"] == "data"

    def test_read_control_returns_empty_dict_when_file_missing(self):
        """Test _read_control returns {} when control file doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            controller = SessionController("test", root_dir=tmpdir)

            result = controller._read_control()

            assert result == {}

    def test_read_control_returns_data_when_file_exists(self):
        """Test _read_control returns data from existing file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            controller = SessionController("test", root_dir=tmpdir)
            controller._write_control({"command": "pause"})

            result = controller._read_control()

            assert result["command"] == "pause"

    def test_read_control_handles_corrupted_file(self):
        """Test _read_control returns {} when file is corrupted."""
        with tempfile.TemporaryDirectory() as tmpdir:
            controller = SessionController("test", root_dir=tmpdir)

            # Write invalid JSON
            with controller.control_file.open("w") as f:
                f.write("{ invalid json }")

            result = controller._read_control()

            assert result == {}

    def test_write_state_creates_json_file(self):
        """Test _write_state creates properly formatted JSON."""
        with tempfile.TemporaryDirectory() as tmpdir:
            controller = SessionController("test", root_dir=tmpdir)

            state_data = {
                "session_id": "test",
                "status": "running",
                "last_phase": "coding",
                "last_updated": 12345.0,
                "metadata": {"key": "value"},
            }
            controller._write_state(state_data)

            assert controller.state_file.exists()
            with controller.state_file.open("r") as f:
                data = json.load(f)

            assert data["session_id"] == "test"
            assert data["status"] == "running"
            assert data["metadata"]["key"] == "value"

    def test_write_control_creates_directory_if_needed(self):
        """Test _write_control creates parent directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            nested_dir = Path(tmpdir) / "deep" / "nested" / "path"
            controller = SessionController("test", root_dir=str(nested_dir))

            controller._write_control({"command": "test"})

            assert nested_dir.exists()
            assert controller.control_file.exists()

    def test_write_state_creates_directory_if_needed(self):
        """Test _write_state creates parent directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            nested_dir = Path(tmpdir) / "deep" / "nested" / "path"
            controller = SessionController("test", root_dir=str(nested_dir))

            controller._write_state({"session_id": "test", "status": "running"})

            assert nested_dir.exists()
            assert controller.state_file.exists()


class TestSessionControllerIntegration:
    """Integration tests for SessionController."""

    def test_full_lifecycle_stop_workflow(self):
        """Test complete workflow: checkpoint -> request_stop -> should_stop."""
        with tempfile.TemporaryDirectory() as tmpdir:
            controller = SessionController("integration-test", root_dir=tmpdir)

            # Orchestrator checkpoints progress
            controller.checkpoint(phase="requirement", metadata={"specs": "test"})

            # External UI requests stop
            controller.request_stop()

            # Orchestrator checks if should stop
            assert controller.should_stop() is True

            # Verify state was saved
            with controller.state_file.open("r") as f:
                state = json.load(f)
            assert state["last_phase"] == "requirement"
            assert state["metadata"]["specs"] == "test"

    def test_multiple_checkpoints_preserve_latest(self):
        """Test multiple checkpoints save latest state."""
        with tempfile.TemporaryDirectory() as tmpdir:
            controller = SessionController("test", root_dir=tmpdir)

            controller.checkpoint(phase="phase1", metadata={"step": 1})
            controller.checkpoint(phase="phase2", metadata={"step": 2})
            controller.checkpoint(phase="phase3", metadata={"step": 3})

            with controller.state_file.open("r") as f:
                state = json.load(f)

            assert state["last_phase"] == "phase3"
            assert state["metadata"]["step"] == 3

    def test_command_changes_affect_should_stop(self):
        """Test changing commands affects should_stop result."""
        with tempfile.TemporaryDirectory() as tmpdir:
            controller = SessionController("test", root_dir=tmpdir)

            # Initially no command
            assert controller.should_stop() is False

            # Stop requested
            controller.request_stop()
            assert controller.should_stop() is True

            # Continue requested
            controller.request_continue()
            assert controller.should_stop() is False

            # Pause requested
            controller.request_pause()
            assert controller.should_stop() is True

    def test_concurrent_sessions_use_separate_files(self):
        """Test multiple sessions maintain separate control/state files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            session1 = SessionController("session-1", root_dir=tmpdir)
            session2 = SessionController("session-2", root_dir=tmpdir)

            session1.request_stop()
            session2.request_continue()

            session1.checkpoint(phase="phase1")
            session2.checkpoint(phase="phase2")

            # Verify session1
            assert session1.should_stop() is True
            with session1.state_file.open("r") as f:
                state1 = json.load(f)
            assert state1["last_phase"] == "phase1"

            # Verify session2
            assert session2.should_stop() is False
            with session2.state_file.open("r") as f:
                state2 = json.load(f)
            assert state2["last_phase"] == "phase2"

    def test_json_files_are_human_readable(self):
        """Test generated JSON files are properly indented."""
        with tempfile.TemporaryDirectory() as tmpdir:
            controller = SessionController("test", root_dir=tmpdir)

            controller.request_stop()
            controller.checkpoint(phase="test", metadata={"key": "value"})

            # Check control file formatting
            control_content = controller.control_file.read_text()
            assert "\n" in control_content  # Multi-line
            assert "  " in control_content  # Indented

            # Check state file formatting
            state_content = controller.state_file.read_text()
            assert "\n" in state_content
            assert "  " in state_content

    def test_checkpoint_with_complex_metadata(self):
        """Test checkpoint handles complex nested metadata."""
        with tempfile.TemporaryDirectory() as tmpdir:
            controller = SessionController("test", root_dir=tmpdir)

            complex_metadata = {
                "plan": {
                    "steps": ["step1", "step2", "step3"],
                    "details": {"complexity": "high", "estimated_time": 120},
                },
                "results": [1, 2, 3],
            }

            controller.checkpoint(phase="complex", metadata=complex_metadata)

            with controller.state_file.open("r") as f:
                state = json.load(f)

            assert state["metadata"]["plan"]["steps"] == ["step1", "step2", "step3"]
            assert state["metadata"]["plan"]["details"]["complexity"] == "high"
            assert state["metadata"]["results"] == [1, 2, 3]
