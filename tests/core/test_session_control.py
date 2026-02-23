"""session_control.py の包括的なテスト"""

import json
import os
import tempfile
import time
from pathlib import Path

from nexuscore.core.session_control import SessionController, SessionState


def test_session_state_creation():
    """SessionStateの作成テスト"""
    state = SessionState(
        session_id="test-001",
        status="running",
        last_phase="test_phase",
        last_updated=time.time(),
        metadata={"key": "value"},
    )

    assert state.session_id == "test-001"
    assert state.status == "running"
    assert state.last_phase == "test_phase"
    assert state.metadata["key"] == "value"


def test_session_controller_initialization():
    """SessionControllerの初期化テスト"""
    with tempfile.TemporaryDirectory() as tmpdir:
        controller = SessionController(
            session_id="test-session", root_dir=os.path.join(tmpdir, ".nexus", "sessions")
        )

        assert controller.session_id == "test-session"
        assert controller.root.exists()
        assert controller.control_file.name == "test-session.control.json"
        assert controller.state_file.name == "test-session.state.json"


def test_session_controller_checkpoint():
    """checkpointメソッドのテスト"""
    with tempfile.TemporaryDirectory() as tmpdir:
        controller = SessionController(
            session_id="test-checkpoint", root_dir=os.path.join(tmpdir, ".nexus", "sessions")
        )

        controller.checkpoint("phase1", {"step": 1})

        assert controller.state_file.exists()

        with controller.state_file.open("r", encoding="utf-8") as f:
            data = json.load(f)

        assert data["session_id"] == "test-checkpoint"
        assert data["last_phase"] == "phase1"
        assert data["metadata"]["step"] == 1
        assert data["status"] == "running"


def test_session_controller_checkpoint_no_metadata():
    """checkpointメソッド（メタデータなし）のテスト"""
    with tempfile.TemporaryDirectory() as tmpdir:
        controller = SessionController(
            session_id="test-checkpoint-empty", root_dir=os.path.join(tmpdir, ".nexus", "sessions")
        )

        controller.checkpoint("phase1")

        with controller.state_file.open("r", encoding="utf-8") as f:
            data = json.load(f)

        assert data["metadata"] == {}


def test_session_controller_should_stop_initial():
    """should_stopの初期状態テスト"""
    with tempfile.TemporaryDirectory() as tmpdir:
        controller = SessionController(
            session_id="test-should-stop", root_dir=os.path.join(tmpdir, ".nexus", "sessions")
        )

        assert not controller.should_stop()


def test_session_controller_request_stop():
    """request_stopメソッドのテスト"""
    with tempfile.TemporaryDirectory() as tmpdir:
        controller = SessionController(
            session_id="test-request-stop", root_dir=os.path.join(tmpdir, ".nexus", "sessions")
        )

        controller.request_stop()

        assert controller.control_file.exists()
        assert controller.should_stop()

        with controller.control_file.open("r", encoding="utf-8") as f:
            data = json.load(f)

        assert data["command"] == "stop"


def test_session_controller_request_pause():
    """request_pauseメソッドのテスト"""
    with tempfile.TemporaryDirectory() as tmpdir:
        controller = SessionController(
            session_id="test-request-pause", root_dir=os.path.join(tmpdir, ".nexus", "sessions")
        )

        controller.request_pause()

        assert controller.should_stop()  # pauseもshould_stopでTrueになる
        assert controller.control_file.exists()

        with controller.control_file.open("r", encoding="utf-8") as f:
            data = json.load(f)

        assert data["command"] == "pause"


def test_session_controller_request_continue():
    """request_continueメソッドのテスト"""
    with tempfile.TemporaryDirectory() as tmpdir:
        controller = SessionController(
            session_id="test-request-continue", root_dir=os.path.join(tmpdir, ".nexus", "sessions")
        )

        controller.request_stop()
        assert controller.should_stop()

        controller.request_continue()
        assert not controller.should_stop()

        with controller.control_file.open("r", encoding="utf-8") as f:
            data = json.load(f)

        assert data["command"] == "continue"


def test_session_controller_multiple_checkpoints():
    """複数のチェックポイント保存テスト"""
    with tempfile.TemporaryDirectory() as tmpdir:
        controller = SessionController(
            session_id="test-multiple-checkpoints",
            root_dir=os.path.join(tmpdir, ".nexus", "sessions"),
        )

        controller.checkpoint("phase1", {"step": 1})
        time.sleep(0.01)  # タイムスタンプの差を作る
        controller.checkpoint("phase2", {"step": 2})
        time.sleep(0.01)
        controller.checkpoint("phase3", {"step": 3})

        with controller.state_file.open("r", encoding="utf-8") as f:
            data = json.load(f)

        assert data["last_phase"] == "phase3"
        assert data["metadata"]["step"] == 3


def test_session_controller_read_control_nonexistent():
    """存在しないcontrol.jsonの読み込みテスト"""
    with tempfile.TemporaryDirectory() as tmpdir:
        controller = SessionController(
            session_id="test-read-nonexistent", root_dir=os.path.join(tmpdir, ".nexus", "sessions")
        )

        result = controller._read_control()
        assert result == {}


def test_session_controller_read_control_corrupted():
    """破損したcontrol.jsonの読み込みテスト"""
    with tempfile.TemporaryDirectory() as tmpdir:
        controller = SessionController(
            session_id="test-read-corrupted", root_dir=os.path.join(tmpdir, ".nexus", "sessions")
        )

        # 破損したJSONファイルを作成
        controller.control_file.parent.mkdir(parents=True, exist_ok=True)
        with controller.control_file.open("w", encoding="utf-8") as f:
            f.write("{ invalid json }")

        # 例外が発生せず、空のdictが返されることを確認
        result = controller._read_control()
        assert result == {}


def test_session_controller_write_state_creates_directory():
    """_write_stateがディレクトリを作成するテスト"""
    with tempfile.TemporaryDirectory() as tmpdir:
        root_dir = os.path.join(tmpdir, "new", "sessions", "path")
        controller = SessionController(session_id="test-create-dir", root_dir=root_dir)

        controller.checkpoint("test_phase")

        assert Path(root_dir).exists()
        assert controller.state_file.exists()


def test_session_controller_write_control_creates_directory():
    """_write_controlがディレクトリを作成するテスト"""
    with tempfile.TemporaryDirectory() as tmpdir:
        root_dir = os.path.join(tmpdir, "new", "control", "path")
        controller = SessionController(session_id="test-create-control-dir", root_dir=root_dir)

        controller.request_stop()

        assert Path(root_dir).exists()
        assert controller.control_file.exists()


def test_session_controller_checkpoint_timestamp():
    """checkpointのタイムスタンプ更新テスト"""
    with tempfile.TemporaryDirectory() as tmpdir:
        controller = SessionController(
            session_id="test-timestamp", root_dir=os.path.join(tmpdir, ".nexus", "sessions")
        )

        before = time.time()
        controller.checkpoint("phase1")
        after = time.time()

        with controller.state_file.open("r", encoding="utf-8") as f:
            data = json.load(f)

        timestamp = data["last_updated"]
        assert before <= timestamp <= after


def test_session_controller_complex_metadata():
    """複雑なメタデータの保存テスト"""
    with tempfile.TemporaryDirectory() as tmpdir:
        controller = SessionController(
            session_id="test-complex-metadata", root_dir=os.path.join(tmpdir, ".nexus", "sessions")
        )

        complex_metadata = {
            "nested": {"key": "value"},
            "list": [1, 2, 3],
            "number": 42,
            "boolean": True,
            "null": None,
        }

        controller.checkpoint("phase1", complex_metadata)

        with controller.state_file.open("r", encoding="utf-8") as f:
            data = json.load(f)

        assert data["metadata"]["nested"]["key"] == "value"
        assert data["metadata"]["list"] == [1, 2, 3]
        assert data["metadata"]["number"] == 42
        assert data["metadata"]["boolean"] is True
        assert data["metadata"]["null"] is None


def test_session_controller_stop_after_checkpoint():
    """チェックポイント後に停止指示を出すテスト"""
    with tempfile.TemporaryDirectory() as tmpdir:
        controller = SessionController(
            session_id="test-stop-after-checkpoint",
            root_dir=os.path.join(tmpdir, ".nexus", "sessions"),
        )

        controller.checkpoint("phase1", {"step": 1})
        assert not controller.should_stop()

        controller.request_stop()
        assert controller.should_stop()

        # state.jsonは残っていることを確認
        assert controller.state_file.exists()
        with controller.state_file.open("r", encoding="utf-8") as f:
            state_data = json.load(f)
        assert state_data["last_phase"] == "phase1"


def test_session_controller_unicode_metadata():
    """Unicode文字を含むメタデータのテスト"""
    with tempfile.TemporaryDirectory() as tmpdir:
        controller = SessionController(
            session_id="test-unicode", root_dir=os.path.join(tmpdir, ".nexus", "sessions")
        )

        unicode_metadata = {"japanese": "日本語テスト", "emoji": "🎉🚀", "chinese": "中文测试"}

        controller.checkpoint("phase1", unicode_metadata)

        with controller.state_file.open("r", encoding="utf-8") as f:
            data = json.load(f)

        assert data["metadata"]["japanese"] == "日本語テスト"
        assert data["metadata"]["emoji"] == "🎉🚀"
        assert data["metadata"]["chinese"] == "中文测试"


def test_session_controller_large_metadata():
    """大きなメタデータの保存テスト"""
    with tempfile.TemporaryDirectory() as tmpdir:
        controller = SessionController(
            session_id="test-large-metadata", root_dir=os.path.join(tmpdir, ".nexus", "sessions")
        )

        large_metadata = {
            "large_string": "x" * 10000,
            "large_list": list(range(1000)),
            "nested": {f"key_{i}": f"value_{i}" for i in range(100)},
        }

        controller.checkpoint("phase1", large_metadata)

        with controller.state_file.open("r", encoding="utf-8") as f:
            data = json.load(f)

        assert len(data["metadata"]["large_string"]) == 10000
        assert len(data["metadata"]["large_list"]) == 1000
        assert len(data["metadata"]["nested"]) == 100
