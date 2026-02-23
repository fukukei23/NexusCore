"""run_history.py のテスト"""

import json
import time
from pathlib import Path

from nexuscore.core.run_history import RunHistoryLogger, RunRecord


def test_run_record_creation():
    """RunRecordの作成テスト"""
    record = RunRecord(
        run_id="test-run-001",
        session_id="test-session-001",
        kind="self_healing",
        status="fixed",
        started_at=1000.0,
        finished_at=2000.0,
    )

    assert record.run_id == "test-run-001"
    assert record.session_id == "test-session-001"
    assert record.kind == "self_healing"
    assert record.status == "fixed"
    assert record.started_at == 1000.0
    assert record.finished_at == 2000.0


def test_run_record_with_optional_fields():
    """RunRecordのオプションフィールドのテスト"""
    record = RunRecord(
        run_id="test-run-002",
        session_id="test-session-002",
        kind="full_project",
        status="success",
        started_at=1000.0,
        finished_at=2000.0,
        repo_full_name="owner/repo",
        pr_number=123,
        head_sha="abc123",
        summary="Test summary",
        details={"key": "value"},
    )

    assert record.repo_full_name == "owner/repo"
    assert record.pr_number == 123
    assert record.head_sha == "abc123"
    assert record.summary == "Test summary"
    assert record.details == {"key": "value"}


def test_run_record_default_details():
    """RunRecordのdetailsデフォルト値のテスト"""
    record = RunRecord(
        run_id="test-run-003",
        session_id="test-session-003",
        kind="self_healing",
        status="no_issues",
        started_at=1000.0,
        finished_at=2000.0,
    )

    assert record.details == {}


def test_run_history_logger_initialization(tmp_path):
    """RunHistoryLoggerの初期化テスト"""
    logger = RunHistoryLogger(project_root=str(tmp_path))

    assert logger.project_root == Path(tmp_path)
    assert logger.history_dir.exists()
    assert logger.history_dir.name == "history"
    assert logger.history_dir.parent.name == ".nexus"
    assert logger.history_dir.parent.exists()


def test_log_run_creates_file(tmp_path):
    """log_runがファイルを作成するテスト"""
    logger = RunHistoryLogger(project_root=str(tmp_path))

    record = RunRecord(
        run_id="test-run-001",
        session_id="test-session-001",
        kind="self_healing",
        status="fixed",
        started_at=1000.0,
        finished_at=2000.0,
    )

    logger.log_run(record)

    log_file = logger.history_dir / "self_healing.log.jsonl"
    assert log_file.exists()

    # ファイル内容を確認
    with log_file.open("r", encoding="utf-8") as f:
        line = f.readline().strip()
        data = json.loads(line)
        assert data["run_id"] == "test-run-001"
        assert data["kind"] == "self_healing"
        assert data["status"] == "fixed"


def test_log_run_appends_multiple_records(tmp_path):
    """log_runが複数レコードを追記するテスト"""
    logger = RunHistoryLogger(project_root=str(tmp_path))

    record1 = RunRecord(
        run_id="test-run-001",
        session_id="test-session-001",
        kind="self_healing",
        status="fixed",
        started_at=1000.0,
        finished_at=2000.0,
    )

    record2 = RunRecord(
        run_id="test-run-002",
        session_id="test-session-002",
        kind="self_healing",
        status="not_fixed",
        started_at=2000.0,
        finished_at=3000.0,
    )

    logger.log_run(record1)
    logger.log_run(record2)

    log_file = logger.history_dir / "self_healing.log.jsonl"
    assert log_file.exists()

    # 2行あることを確認
    with log_file.open("r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]
        assert len(lines) == 2

        data1 = json.loads(lines[0])
        data2 = json.loads(lines[1])
        assert data1["run_id"] == "test-run-001"
        assert data2["run_id"] == "test-run-002"


def test_log_run_different_kinds(tmp_path):
    """異なるkindのログが別ファイルに保存されるテスト"""
    logger = RunHistoryLogger(project_root=str(tmp_path))

    record1 = RunRecord(
        run_id="test-run-001",
        session_id="test-session-001",
        kind="self_healing",
        status="fixed",
        started_at=1000.0,
        finished_at=2000.0,
    )

    record2 = RunRecord(
        run_id="test-run-002",
        session_id="test-session-002",
        kind="full_project",
        status="success",
        started_at=2000.0,
        finished_at=3000.0,
    )

    logger.log_run(record1)
    logger.log_run(record2)

    healing_file = logger.history_dir / "self_healing.log.jsonl"
    project_file = logger.history_dir / "full_project.log.jsonl"

    assert healing_file.exists()
    assert project_file.exists()

    # それぞれ1行ずつあることを確認
    with healing_file.open("r", encoding="utf-8") as f:
        assert len([l for l in f if l.strip()]) == 1

    with project_file.open("r", encoding="utf-8") as f:
        assert len([l for l in f if l.strip()]) == 1


def test_new_self_healing_record(tmp_path):
    """new_self_healing_recordのテスト"""
    logger = RunHistoryLogger(project_root=str(tmp_path))

    started_at = time.time()
    finished_at = started_at + 10.0

    record = logger.new_self_healing_record(
        run_id="test-run-001",
        session_id="test-session-001",
        repo_full_name="owner/repo",
        pr_number=123,
        head_sha="abc123",
        status="fixed",
        summary="Fixed the issue",
        details={"patch": "unified diff here"},
        started_at=started_at,
        finished_at=finished_at,
    )

    assert record.kind == "self_healing"
    assert record.run_id == "test-run-001"
    assert record.repo_full_name == "owner/repo"
    assert record.pr_number == 123
    assert record.head_sha == "abc123"
    assert record.status == "fixed"
    assert record.summary == "Fixed the issue"
    assert record.details == {"patch": "unified diff here"}


def test_load_runs_empty_file(tmp_path):
    """存在しないファイルからload_runsするテスト"""
    logger = RunHistoryLogger(project_root=str(tmp_path))

    records = logger.load_runs("nonexistent")

    assert records == []


def test_load_runs_single_record(tmp_path):
    """単一レコードをload_runsで読み込むテスト"""
    logger = RunHistoryLogger(project_root=str(tmp_path))

    record = RunRecord(
        run_id="test-run-001",
        session_id="test-session-001",
        kind="self_healing",
        status="fixed",
        started_at=1000.0,
        finished_at=2000.0,
    )

    logger.log_run(record)

    records = logger.load_runs("self_healing")

    assert len(records) == 1
    assert records[0]["run_id"] == "test-run-001"
    assert records[0]["status"] == "fixed"


def test_load_runs_multiple_records(tmp_path):
    """複数レコードをload_runsで読み込むテスト"""
    logger = RunHistoryLogger(project_root=str(tmp_path))

    for i in range(3):
        record = RunRecord(
            run_id=f"test-run-{i:03d}",
            session_id=f"test-session-{i:03d}",
            kind="self_healing",
            status="fixed" if i % 2 == 0 else "not_fixed",
            started_at=1000.0 + i * 100,
            finished_at=2000.0 + i * 100,
        )
        logger.log_run(record)

    records = logger.load_runs("self_healing")

    assert len(records) == 3
    assert records[0]["run_id"] == "test-run-000"
    assert records[1]["run_id"] == "test-run-001"
    assert records[2]["run_id"] == "test-run-002"


def test_load_runs_skips_corrupted_lines(tmp_path):
    """壊れた行をスキップしてload_runsするテスト"""
    logger = RunHistoryLogger(project_root=str(tmp_path))

    log_file = logger.history_dir / "self_healing.log.jsonl"

    # 正常なJSONと壊れたJSONを混在させる
    with log_file.open("w", encoding="utf-8") as f:
        f.write('{"run_id": "test-run-001", "status": "fixed"}\n')
        f.write("invalid json line\n")
        f.write('{"run_id": "test-run-002", "status": "not_fixed"}\n')
        f.write("\n")  # 空行
        f.write('{"run_id": "test-run-003", "status": "fixed"}\n')

    records = logger.load_runs("self_healing")

    # 壊れた行と空行はスキップされる
    assert len(records) == 3
    assert records[0]["run_id"] == "test-run-001"
    assert records[1]["run_id"] == "test-run-002"
    assert records[2]["run_id"] == "test-run-003"


def test_log_run_handles_write_failure(tmp_path, monkeypatch):
    """log_runが書き込み失敗を処理するテスト"""
    logger = RunHistoryLogger(project_root=str(tmp_path))

    record = RunRecord(
        run_id="test-run-001",
        session_id="test-session-001",
        kind="self_healing",
        status="fixed",
        started_at=1000.0,
        finished_at=2000.0,
    )

    # 書き込みを失敗させる
    def mock_open(*args, **kwargs):
        raise OSError("Disk full")

    monkeypatch.setattr("builtins.open", mock_open)

    # 例外が発生しても処理が継続されることを確認
    logger.log_run(record)

    # 例外が発生しなかったことを確認（握りつぶされている）


def test_run_record_with_complex_details(tmp_path):
    """複雑なdetailsを含むRunRecordのテスト"""
    logger = RunHistoryLogger(project_root=str(tmp_path))

    complex_details = {
        "patch": "--- a/file.py\n+++ b/file.py\n@@ -1,1 +1,1 @@\n-old\n+new",
        "changed_files": ["file.py"],
        "test_results": {"passed": 10, "failed": 2},
        "nested": {"key": "value", "list": [1, 2, 3]},
    }

    record = RunRecord(
        run_id="test-run-001",
        session_id="test-session-001",
        kind="self_healing",
        status="fixed",
        started_at=1000.0,
        finished_at=2000.0,
        details=complex_details,
    )

    logger.log_run(record)

    records = logger.load_runs("self_healing")

    assert len(records) == 1
    assert records[0]["details"]["patch"] == complex_details["patch"]
    assert records[0]["details"]["changed_files"] == ["file.py"]
    assert records[0]["details"]["test_results"]["passed"] == 10
    assert records[0]["details"]["nested"]["list"] == [1, 2, 3]


def test_run_record_unicode_content(tmp_path):
    """Unicode文字を含むRunRecordのテスト"""
    logger = RunHistoryLogger(project_root=str(tmp_path))

    record = RunRecord(
        run_id="test-run-001",
        session_id="test-session-001",
        kind="self_healing",
        status="fixed",
        started_at=1000.0,
        finished_at=2000.0,
        summary="日本語のサマリー🎉",
        details={"message": "エラーメッセージ: テスト", "emoji": "🚀"},
    )

    logger.log_run(record)

    records = logger.load_runs("self_healing")

    assert len(records) == 1
    assert records[0]["summary"] == "日本語のサマリー🎉"
    assert records[0]["details"]["message"] == "エラーメッセージ: テスト"
    assert records[0]["details"]["emoji"] == "🚀"


def test_load_runs_preserves_order(tmp_path):
    """load_runsが順序を保持するテスト"""
    logger = RunHistoryLogger(project_root=str(tmp_path))

    # 複数のレコードを時系列順に追加
    for i in range(5):
        record = RunRecord(
            run_id=f"test-run-{i:03d}",
            session_id="test-session-001",
            kind="self_healing",
            status="fixed",
            started_at=1000.0 + i,
            finished_at=2000.0 + i,
        )
        logger.log_run(record)

    records = logger.load_runs("self_healing")

    # 順序が保持されていることを確認
    assert len(records) == 5
    for i in range(5):
        assert records[i]["run_id"] == f"test-run-{i:03d}"
        assert records[i]["started_at"] == 1000.0 + i
