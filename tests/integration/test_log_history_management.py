"""
ログと履歴管理の統合テスト

RunHistoryLogger と SessionController の連携を確認し、
ジョブの履歴やログが正しく保存されることを検証する。
"""
from __future__ import annotations

import json
import tempfile
import time
from pathlib import Path

import pytest

from nexuscore.core.run_history import RunHistoryLogger, RunRecord
from nexuscore.core.session_control import SessionController
from nexuscore.core.job_state_machine import JobStateMachine


class TestLogHistoryManagement:
    """ログと履歴管理の基本テスト"""

    def test_job_history_saved_to_jsonl(self):
        """ジョブの履歴が JSONL 形式で保存されることを確認"""
        with tempfile.TemporaryDirectory() as tmpdir:
            history_logger = RunHistoryLogger(project_root=tmpdir)

            # ジョブ履歴を記録
            record = RunRecord(
                run_id="test-run-001",
                session_id="test-session-001",
                kind="orchestrator",
                status="success",
                started_at=time.time() - 100,
                finished_at=time.time(),
                summary="Test job completed successfully",
                details={"result": "success"},
            )
            history_logger.log_run(record)

            # 履歴ファイルが作成されていることを確認
            history_file = Path(tmpdir) / ".nexus" / "history" / "orchestrator.log.jsonl"
            assert history_file.exists()

            # 履歴の内容を確認
            with history_file.open("r", encoding="utf-8") as f:
                lines = [line.strip() for line in f if line.strip()]
                assert len(lines) == 1
                saved_record = json.loads(lines[0])
                assert saved_record["run_id"] == "test-run-001"
                assert saved_record["status"] == "success"
                assert saved_record["summary"] == "Test job completed successfully"

    def test_job_state_transitions_logged(self):
        """ジョブの状態遷移が履歴に記録されることを確認"""
        with tempfile.TemporaryDirectory() as tmpdir:
            history_logger = RunHistoryLogger(project_root=tmpdir)
            session_controller = SessionController(
                session_id="test-session-002",
                root_dir=tmpdir,
            )

            state_machine = JobStateMachine(
                job_id="test-job-002",
                session_controller=session_controller,
                history_logger=history_logger,
                job_type="orchestrator",
            )

            # 状態遷移を実行: Pending → Running → Completed
            state_machine.start()
            state_machine.complete(details={"result": "success"})

            # 履歴が記録されていることを確認
            history_file = Path(tmpdir) / ".nexus" / "history" / "orchestrator.log.jsonl"
            assert history_file.exists()

            # 履歴の内容を確認
            with history_file.open("r", encoding="utf-8") as f:
                lines = [line.strip() for line in f if line.strip()]
                assert len(lines) == 1
                record = json.loads(lines[0])
                assert record["run_id"] == "test-job-002"
                assert record["status"] == "success"
                assert record["kind"] == "orchestrator"

    def test_error_handling_logged(self):
        """エラーハンドリング時に履歴が適切に記録されることを確認"""
        with tempfile.TemporaryDirectory() as tmpdir:
            history_logger = RunHistoryLogger(project_root=tmpdir)
            session_controller = SessionController(
                session_id="test-session-003",
                root_dir=tmpdir,
            )

            state_machine = JobStateMachine(
                job_id="test-job-003",
                session_controller=session_controller,
                history_logger=history_logger,
                job_type="orchestrator",
            )

            # 状態遷移を実行: Pending → Running → Failed
            state_machine.start()
            error_message = "Test error occurred"
            state_machine.fail(error_message=error_message, details={"error_code": 500})

            # 履歴が記録されていることを確認
            history_file = Path(tmpdir) / ".nexus" / "history" / "orchestrator.log.jsonl"
            assert history_file.exists()

            # 履歴の内容を確認
            with history_file.open("r", encoding="utf-8") as f:
                lines = [line.strip() for line in f if line.strip()]
                assert len(lines) == 1
                record = json.loads(lines[0])
                assert record["run_id"] == "test-job-003"
                assert record["status"] == "error"
                assert error_message in record["summary"]
                assert record["details"]["error"] == error_message


class TestSessionControllerIntegration:
    """SessionController との統合テスト"""

    def test_session_state_saved_on_checkpoint(self):
        """チェックポイント時にセッション状態が保存されることを確認"""
        with tempfile.TemporaryDirectory() as tmpdir:
            session_controller = SessionController(
                session_id="test-session-004",
                root_dir=tmpdir,
            )

            # チェックポイントを保存
            session_controller.checkpoint(
                phase="after_planning",
                metadata={"plan_summary": "Test plan", "files_count": 5},
            )

            # セッション状態ファイルが作成されていることを確認
            state_file = Path(tmpdir) / "test-session-004.state.json"
            assert state_file.exists()

            # セッション状態の内容を確認
            with state_file.open("r", encoding="utf-8") as f:
                state_data = json.load(f)
                assert state_data["session_id"] == "test-session-004"
                assert state_data["last_phase"] == "after_planning"
                assert state_data["metadata"]["plan_summary"] == "Test plan"
                assert state_data["metadata"]["files_count"] == 5

    def test_session_resumed_from_checkpoint(self):
        """チェックポイントからセッションが復元されることを確認"""
        with tempfile.TemporaryDirectory() as tmpdir:
            session_controller = SessionController(
                session_id="test-session-005",
                root_dir=tmpdir,
            )

            # チェックポイントを保存
            session_controller.checkpoint(
                phase="after_coding",
                metadata={"code_files": ["file1.py", "file2.py"]},
            )

            # 新しいセッションコントローラーで状態を読み込む（再開をシミュレート）
            resumed_controller = SessionController(
                session_id="test-session-005",
                root_dir=tmpdir,
            )

            # 状態ファイルが存在することを確認
            state_file = Path(tmpdir) / "test-session-005.state.json"
            assert state_file.exists()

            # 状態の内容を確認
            with state_file.open("r", encoding="utf-8") as f:
                state_data = json.load(f)
                assert state_data["last_phase"] == "after_coding"
                assert "file1.py" in state_data["metadata"]["code_files"]


class TestRunHistoryLoggerSessionControllerIntegration:
    """RunHistoryLogger と SessionController の統合テスト"""

    def test_full_integration_job_lifecycle(self):
        """完全なジョブライフサイクルでの統合テスト"""
        with tempfile.TemporaryDirectory() as tmpdir:
            history_logger = RunHistoryLogger(project_root=tmpdir)
            session_controller = SessionController(
                session_id="test-session-006",
                root_dir=tmpdir,
            )

            state_machine = JobStateMachine(
                job_id="test-job-006",
                session_controller=session_controller,
                history_logger=history_logger,
                job_type="orchestrator",
            )

            # 完全なライフサイクルを実行
            # 1. 開始
            state_machine.start()
            session_controller.checkpoint(phase="state_running", metadata={"step": "started"})

            # 2. 計画フェーズ
            session_controller.checkpoint(phase="after_planning", metadata={"plan": "created"})

            # 3. コーディングフェーズ
            session_controller.checkpoint(phase="after_coding", metadata={"files": ["file1.py"]})

            # 4. 完了
            state_machine.complete(details={"result": "success", "files_created": 1})

            # セッション状態が保存されていることを確認
            state_file = Path(tmpdir) / "test-session-006.state.json"
            assert state_file.exists()

            with state_file.open("r", encoding="utf-8") as f:
                state_data = json.load(f)
                assert state_data["last_phase"] == "state_completed"
                assert state_data["metadata"]["state"] == "completed"

            # 履歴が記録されていることを確認
            history_file = Path(tmpdir) / ".nexus" / "history" / "orchestrator.log.jsonl"
            assert history_file.exists()

            with history_file.open("r", encoding="utf-8") as f:
                lines = [line.strip() for line in f if line.strip()]
                assert len(lines) == 1
                record = json.loads(lines[0])
                assert record["run_id"] == "test-job-006"
                assert record["status"] == "success"
                assert record["details"]["result"] == "success"
                assert record["details"]["files_created"] == 1

    def test_multiple_jobs_history_accumulation(self):
        """複数のジョブの履歴が蓄積されることを確認"""
        with tempfile.TemporaryDirectory() as tmpdir:
            history_logger = RunHistoryLogger(project_root=tmpdir)

            # 複数のジョブを記録
            for i in range(3):
                record = RunRecord(
                    run_id=f"test-run-{i:03d}",
                    session_id=f"test-session-{i:03d}",
                    kind="orchestrator",
                    status="success" if i % 2 == 0 else "error",
                    started_at=time.time() - (3 - i) * 100,
                    finished_at=time.time() - (3 - i) * 100 + 50,
                    summary=f"Test job {i}",
                )
                history_logger.log_run(record)

            # 履歴ファイルに3つのレコードが記録されていることを確認
            history_file = Path(tmpdir) / ".nexus" / "history" / "orchestrator.log.jsonl"
            assert history_file.exists()

            with history_file.open("r", encoding="utf-8") as f:
                lines = [line.strip() for line in f if line.strip()]
                assert len(lines) == 3

                # 各レコードを確認
                for i, line in enumerate(lines):
                    record = json.loads(line)
                    assert record["run_id"] == f"test-run-{i:03d}"
                    assert record["session_id"] == f"test-session-{i:03d}"

            # load_runs メソッドで履歴を読み込めることを確認
            records = history_logger.load_runs("orchestrator")
            assert len(records) == 3

    def test_history_logger_calculates_success_rate(self):
        """履歴ロガーが成功率を計算できることを確認"""
        with tempfile.TemporaryDirectory() as tmpdir:
            history_logger = RunHistoryLogger(project_root=tmpdir)

            # 10個のジョブを記録（6個成功、4個失敗）
            for i in range(10):
                record = RunRecord(
                    run_id=f"test-run-{i:03d}",
                    session_id=f"test-session-{i:03d}",
                    kind="self_healing",
                    status="fixed" if i < 6 else "not_fixed",
                    started_at=time.time() - (10 - i) * 10,
                    finished_at=time.time() - (10 - i) * 10 + 5,
                )
                history_logger.log_run(record)

            # 成功率を計算
            success_rate, success_count, total_count = history_logger.calculate_success_rate(limit=10)

            assert total_count == 10
            assert success_count == 6
            assert success_rate == 60.0

