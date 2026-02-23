"""
Comprehensive tests for run_history module.

Tests JSONL-based execution history logging for Self-Healing
and Orchestrator runs.
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

from nexuscore.core.run_history import RunHistoryLogger, RunRecord


class TestRunRecord:
    """Tests for RunRecord dataclass."""

    def test_create_run_record_with_all_fields(self):
        """Test creating RunRecord with all fields."""
        record = RunRecord(
            run_id="run-123",
            session_id="session-456",
            kind="self_healing",
            status="fixed",
            started_at=1000.0,
            finished_at=2000.0,
            repo_full_name="owner/repo",
            pr_number=42,
            head_sha="abc123",
            summary="Fixed 3 issues",
            details={"fixes": 3},
        )

        assert record.run_id == "run-123"
        assert record.session_id == "session-456"
        assert record.kind == "self_healing"
        assert record.status == "fixed"
        assert record.started_at == 1000.0
        assert record.finished_at == 2000.0
        assert record.repo_full_name == "owner/repo"
        assert record.pr_number == 42
        assert record.head_sha == "abc123"
        assert record.summary == "Fixed 3 issues"
        assert record.details == {"fixes": 3}

    def test_create_run_record_with_minimal_fields(self):
        """Test creating RunRecord with only required fields."""
        record = RunRecord(
            run_id="run-1",
            session_id="session-1",
            kind="full_project",
            status="completed",
            started_at=100.0,
            finished_at=200.0,
        )

        assert record.run_id == "run-1"
        assert record.repo_full_name is None
        assert record.pr_number is None
        assert record.head_sha is None
        assert record.summary is None
        assert record.details == {}

    def test_run_record_defaults(self):
        """Test RunRecord default values."""
        record = RunRecord(
            run_id="test",
            session_id="test",
            kind="test",
            status="test",
            started_at=0.0,
            finished_at=1.0,
        )

        assert record.details == {}


class TestRunHistoryLoggerInit:
    """Tests for RunHistoryLogger initialization."""

    def test_init_creates_logger(self):
        """Test initialization creates RunHistoryLogger."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = RunHistoryLogger(tmpdir)

            assert logger.project_root == Path(tmpdir)
            assert logger.history_dir == Path(tmpdir) / ".nexus" / "history"

    def test_init_creates_history_directory(self):
        """Test initialization creates .nexus/history directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = RunHistoryLogger(tmpdir)

            assert logger.history_dir.exists()
            assert logger.history_dir.is_dir()

    def test_init_with_nested_project_root(self):
        """Test initialization with nested project directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir) / "nested" / "project"
            project_path.mkdir(parents=True)

            logger = RunHistoryLogger(str(project_path))

            assert logger.history_dir.exists()
            assert logger.history_dir == project_path / ".nexus" / "history"


class TestLogRun:
    """Tests for log_run method."""

    def test_log_run_creates_jsonl_file(self):
        """Test log_run creates JSONL file for the kind."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = RunHistoryLogger(tmpdir)
            record = RunRecord(
                run_id="test-1",
                session_id="session-1",
                kind="self_healing",
                status="fixed",
                started_at=1000.0,
                finished_at=2000.0,
            )

            logger.log_run(record)

            log_file = logger.history_dir / "self_healing.log.jsonl"
            assert log_file.exists()

    def test_log_run_writes_json_line(self):
        """Test log_run writes valid JSON line."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = RunHistoryLogger(tmpdir)
            record = RunRecord(
                run_id="test-1",
                session_id="session-1",
                kind="test_kind",
                status="success",
                started_at=100.0,
                finished_at=200.0,
                summary="Test summary",
            )

            logger.log_run(record)

            log_file = logger.history_dir / "test_kind.log.jsonl"
            with log_file.open("r") as f:
                line = f.read().strip()
                data = json.loads(line)

            assert data["run_id"] == "test-1"
            assert data["status"] == "success"
            assert data["summary"] == "Test summary"

    def test_log_run_appends_to_existing_file(self):
        """Test log_run appends to existing JSONL file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = RunHistoryLogger(tmpdir)

            record1 = RunRecord(
                run_id="run-1",
                session_id="s1",
                kind="test",
                status="fixed",
                started_at=100.0,
                finished_at=200.0,
            )
            record2 = RunRecord(
                run_id="run-2",
                session_id="s2",
                kind="test",
                status="not_fixed",
                started_at=300.0,
                finished_at=400.0,
            )

            logger.log_run(record1)
            logger.log_run(record2)

            log_file = logger.history_dir / "test.log.jsonl"
            with log_file.open("r") as f:
                lines = f.readlines()

            assert len(lines) == 2
            data1 = json.loads(lines[0])
            data2 = json.loads(lines[1])
            assert data1["run_id"] == "run-1"
            assert data2["run_id"] == "run-2"

    def test_log_run_handles_write_error_gracefully(self):
        """Test log_run handles write errors without raising."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = RunHistoryLogger(tmpdir)
            record = RunRecord(
                run_id="test",
                session_id="s",
                kind="test",
                status="fixed",
                started_at=0.0,
                finished_at=1.0,
            )

            # Make history_dir read-only to cause write error
            logger.history_dir.chmod(0o444)

            try:
                # Should not raise exception
                logger.log_run(record)
            finally:
                # Restore permissions for cleanup
                logger.history_dir.chmod(0o755)

    def test_log_run_with_complex_details(self):
        """Test log_run handles complex details dictionary."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = RunHistoryLogger(tmpdir)
            record = RunRecord(
                run_id="test",
                session_id="s",
                kind="test",
                status="fixed",
                started_at=0.0,
                finished_at=1.0,
                details={
                    "fixes": [
                        {"file": "a.py", "lines": [1, 2, 3]},
                        {"file": "b.py", "lines": [10, 20]},
                    ],
                    "metadata": {"complexity": "high"},
                },
            )

            logger.log_run(record)

            log_file = logger.history_dir / "test.log.jsonl"
            with log_file.open("r") as f:
                data = json.loads(f.read())

            assert data["details"]["fixes"][0]["file"] == "a.py"
            assert data["details"]["metadata"]["complexity"] == "high"


class TestNewSelfHealingRecord:
    """Tests for new_self_healing_record helper."""

    def test_creates_self_healing_record(self):
        """Test creates properly formatted Self-Healing record."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = RunHistoryLogger(tmpdir)

            record = logger.new_self_healing_record(
                run_id="heal-123",
                session_id="session-456",
                repo_full_name="owner/repo",
                pr_number=42,
                head_sha="abc123",
                status="fixed",
                summary="Fixed 3 tests",
                details={"test_count": 3},
                started_at=1000.0,
                finished_at=2000.0,
            )

            assert record.run_id == "heal-123"
            assert record.kind == "self_healing"
            assert record.status == "fixed"
            assert record.repo_full_name == "owner/repo"
            assert record.pr_number == 42
            assert record.head_sha == "abc123"
            assert record.summary == "Fixed 3 tests"
            assert record.details == {"test_count": 3}


class TestLoadRuns:
    """Tests for load_runs method."""

    def test_load_runs_from_empty_file(self):
        """Test load_runs returns empty list when file doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = RunHistoryLogger(tmpdir)

            result = logger.load_runs("nonexistent")

            assert result == []

    def test_load_runs_reads_jsonl_file(self):
        """Test load_runs reads JSONL file correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = RunHistoryLogger(tmpdir)

            # Write some records
            records = [
                RunRecord("r1", "s1", "test", "fixed", 100.0, 200.0),
                RunRecord("r2", "s2", "test", "not_fixed", 300.0, 400.0),
                RunRecord("r3", "s3", "test", "no_issues", 500.0, 600.0),
            ]
            for rec in records:
                logger.log_run(rec)

            # Load them back
            loaded = logger.load_runs("test")

            assert len(loaded) == 3
            assert loaded[0]["run_id"] == "r1"
            assert loaded[1]["run_id"] == "r2"
            assert loaded[2]["run_id"] == "r3"

    def test_load_runs_handles_corrupted_lines(self):
        """Test load_runs skips corrupted JSON lines."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = RunHistoryLogger(tmpdir)
            log_file = logger.history_dir / "test.log.jsonl"

            # Write valid and invalid lines
            with log_file.open("w") as f:
                f.write('{"run_id": "r1", "status": "fixed"}\n')
                f.write("{ invalid json }\n")  # Corrupted
                f.write('{"run_id": "r2", "status": "not_fixed"}\n')

            loaded = logger.load_runs("test")

            # Should skip corrupted line
            assert len(loaded) == 2
            assert loaded[0]["run_id"] == "r1"
            assert loaded[1]["run_id"] == "r2"

    def test_load_runs_skips_empty_lines(self):
        """Test load_runs skips empty lines."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = RunHistoryLogger(tmpdir)
            log_file = logger.history_dir / "test.log.jsonl"

            with log_file.open("w") as f:
                f.write('{"run_id": "r1"}\n')
                f.write("\n")  # Empty line
                f.write("  \n")  # Whitespace only
                f.write('{"run_id": "r2"}\n')

            loaded = logger.load_runs("test")

            assert len(loaded) == 2


class TestGetLastSelfHealingRuns:
    """Tests for get_last_self_healing_runs method."""

    def test_get_last_runs_returns_recent_runs(self):
        """Test returns most recent runs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = RunHistoryLogger(tmpdir)

            # Create runs with different timestamps
            for i in range(5):
                record = RunRecord(
                    f"r{i}",
                    f"s{i}",
                    "self_healing",
                    "fixed",
                    started_at=float(i * 100),
                    finished_at=float(i * 100 + 50),
                )
                logger.log_run(record)

            result = logger.get_last_self_healing_runs(limit=3)

            # Should return 3 most recent (newest first)
            assert len(result) == 3
            assert result[0]["run_id"] == "r4"
            assert result[1]["run_id"] == "r3"
            assert result[2]["run_id"] == "r2"

    def test_get_last_runs_default_limit_is_30(self):
        """Test default limit is 30."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = RunHistoryLogger(tmpdir)

            # Create 50 runs
            for i in range(50):
                record = RunRecord(
                    f"r{i}",
                    f"s{i}",
                    "self_healing",
                    "fixed",
                    started_at=float(i),
                    finished_at=float(i + 1),
                )
                logger.log_run(record)

            result = logger.get_last_self_healing_runs()

            # Should return only 30
            assert len(result) == 30

    def test_get_last_runs_sorts_by_finished_at(self):
        """Test runs are sorted by finished_at descending."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = RunHistoryLogger(tmpdir)

            # Create runs in non-chronological order
            records = [
                RunRecord("r1", "s1", "self_healing", "fixed", 300.0, 400.0),
                RunRecord("r2", "s2", "self_healing", "fixed", 100.0, 200.0),
                RunRecord("r3", "s3", "self_healing", "fixed", 500.0, 600.0),
            ]
            for rec in records:
                logger.log_run(rec)

            result = logger.get_last_self_healing_runs(limit=10)

            # Should be sorted newest first
            assert result[0]["run_id"] == "r3"  # finished_at=600.0
            assert result[1]["run_id"] == "r1"  # finished_at=400.0
            assert result[2]["run_id"] == "r2"  # finished_at=200.0


class TestCalculateSuccessRate:
    """Tests for calculate_success_rate method."""

    def test_calculate_success_rate_all_fixed(self):
        """Test calculates 100% success rate when all fixed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = RunHistoryLogger(tmpdir)

            for i in range(10):
                record = RunRecord(
                    f"r{i}", f"s{i}", "self_healing", "fixed", float(i), float(i + 1)
                )
                logger.log_run(record)

            rate, success, total = logger.calculate_success_rate(limit=10)

            assert rate == 100.0
            assert success == 10
            assert total == 10

    def test_calculate_success_rate_none_fixed(self):
        """Test calculates 0% success rate when none fixed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = RunHistoryLogger(tmpdir)

            for i in range(5):
                record = RunRecord(
                    f"r{i}", f"s{i}", "self_healing", "not_fixed", float(i), float(i + 1)
                )
                logger.log_run(record)

            rate, success, total = logger.calculate_success_rate(limit=10)

            assert rate == 0.0
            assert success == 0
            assert total == 5

    def test_calculate_success_rate_mixed_results(self):
        """Test calculates correct success rate with mixed results."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = RunHistoryLogger(tmpdir)

            statuses = ["fixed", "fixed", "not_fixed", "fixed", "error"]
            for i, status in enumerate(statuses):
                record = RunRecord(f"r{i}", f"s{i}", "self_healing", status, float(i), float(i + 1))
                logger.log_run(record)

            rate, success, total = logger.calculate_success_rate(limit=10)

            # 3 fixed out of 5 = 60%
            assert rate == 60.0
            assert success == 3
            assert total == 5

    def test_calculate_success_rate_empty_history(self):
        """Test returns 0.0 when no history exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = RunHistoryLogger(tmpdir)

            rate, success, total = logger.calculate_success_rate()

            assert rate == 0.0
            assert success == 0
            assert total == 0

    def test_calculate_success_rate_respects_limit(self):
        """Test respects limit parameter."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = RunHistoryLogger(tmpdir)

            # Create 10 runs: first 5 fixed, last 5 not_fixed
            for i in range(10):
                status = "fixed" if i < 5 else "not_fixed"
                record = RunRecord(f"r{i}", f"s{i}", "self_healing", status, float(i), float(i + 1))
                logger.log_run(record)

            # Get last 5 (should be the not_fixed ones)
            rate, success, total = logger.calculate_success_rate(limit=5)

            assert rate == 0.0
            assert success == 0
            assert total == 5

    def test_calculate_success_rate_rounds_to_one_decimal(self):
        """Test success rate is rounded to 1 decimal place."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = RunHistoryLogger(tmpdir)

            # 1 fixed out of 3 = 33.333...%
            statuses = ["fixed", "not_fixed", "not_fixed"]
            for i, status in enumerate(statuses):
                record = RunRecord(f"r{i}", f"s{i}", "self_healing", status, float(i), float(i + 1))
                logger.log_run(record)

            rate, success, total = logger.calculate_success_rate()

            assert rate == 33.3
            assert success == 1
            assert total == 3


class TestSendNotification:
    """Tests for _send_notification method."""

    def test_send_notification_calls_notifier(self):
        """Test _send_notification calls notifier when available."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = RunHistoryLogger(tmpdir)
            record = RunRecord(
                "r1",
                "s1",
                "self_healing",
                "fixed",
                100.0,
                200.0,
                repo_full_name="owner/repo",
                pr_number=42,
                summary="Fixed tests",
            )

            mock_notifier = Mock()
            with patch("nexuscore.core.notifier.get_notifier", return_value=mock_notifier):
                logger.log_run(record)

            mock_notifier.notify_self_healing_complete.assert_called_once_with(
                repo_full_name="owner/repo",
                pr_number=42,
                status="fixed",
                summary="Fixed tests",
                run_id="r1",
                details={},
            )

    def test_send_notification_handles_no_notifier(self):
        """Test _send_notification handles None notifier gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = RunHistoryLogger(tmpdir)
            record = RunRecord("r1", "s1", "self_healing", "fixed", 100.0, 200.0)

            with patch("nexuscore.core.notifier.get_notifier", return_value=None):
                # Should not raise
                logger.log_run(record)

    def test_send_notification_handles_import_error(self):
        """Test _send_notification handles import errors gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = RunHistoryLogger(tmpdir)
            record = RunRecord("r1", "s1", "self_healing", "fixed", 100.0, 200.0)

            with patch("nexuscore.core.notifier.get_notifier", side_effect=ImportError):
                # Should not raise
                logger.log_run(record)

    def test_send_notification_only_for_self_healing(self):
        """Test notification only sent for self_healing kind."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = RunHistoryLogger(tmpdir)
            record = RunRecord("r1", "s1", "other_kind", "fixed", 100.0, 200.0)

            mock_notifier = Mock()
            with patch("nexuscore.core.notifier.get_notifier", return_value=mock_notifier):
                logger.log_run(record)

            # Should not call notify for non-self_healing kind
            mock_notifier.notify_self_healing_complete.assert_not_called()


class TestRunHistoryIntegration:
    """Integration tests for RunHistoryLogger."""

    def test_full_workflow_logging_and_loading(self):
        """Test full workflow: log multiple runs and load them back."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = RunHistoryLogger(tmpdir)

            # Log 3 Self-Healing runs
            for i in range(3):
                record = logger.new_self_healing_record(
                    run_id=f"heal-{i}",
                    session_id=f"session-{i}",
                    repo_full_name=f"owner/repo{i}",
                    pr_number=i + 1,
                    head_sha=f"sha{i}",
                    status="fixed" if i % 2 == 0 else "not_fixed",
                    summary=f"Summary {i}",
                    details={"count": i},
                    started_at=float(i * 100),
                    finished_at=float(i * 100 + 50),
                )
                logger.log_run(record)

            # Load and verify
            runs = logger.load_runs("self_healing")
            assert len(runs) == 3

            # Calculate success rate (runs 0 and 2 are fixed, 2 out of 3)
            rate, success, total = logger.calculate_success_rate()
            assert rate == 66.7
            assert success == 2
            assert total == 3

    def test_concurrent_kinds_separate_files(self):
        """Test different kinds use separate JSONL files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = RunHistoryLogger(tmpdir)

            record1 = RunRecord("r1", "s1", "self_healing", "fixed", 0.0, 1.0)
            record2 = RunRecord("r2", "s2", "full_project", "completed", 0.0, 1.0)

            logger.log_run(record1)
            logger.log_run(record2)

            # Should create separate files
            assert (logger.history_dir / "self_healing.log.jsonl").exists()
            assert (logger.history_dir / "full_project.log.jsonl").exists()

            # Load separately
            healing_runs = logger.load_runs("self_healing")
            project_runs = logger.load_runs("full_project")

            assert len(healing_runs) == 1
            assert len(project_runs) == 1
            assert healing_runs[0]["run_id"] == "r1"
            assert project_runs[0]["run_id"] == "r2"
