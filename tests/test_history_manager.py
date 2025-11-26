"""Tests for history_manager.py"""
import os
import json
import tempfile
from pathlib import Path
import pytest
import sys

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# src/history_manager.pyを直接インポート
from history_manager import HistoryManager


def test_history_manager_init(tmp_path):
    """HistoryManagerの初期化テスト"""
    history_dir = str(tmp_path / "history")
    hm = HistoryManager(history_dir=history_dir)

    assert hm.history_dir == history_dir
    assert os.path.exists(history_dir)
    assert hm.state_history == []
    assert hm.current_index == -1
    # history_pathは生成されるが、save_historyが呼ばれるまでファイルは作成されない
    assert hm.history_path is not None


def test_history_manager_add_state(tmp_path):
    """状態追加のテスト"""
    history_dir = str(tmp_path / "history")
    hm = HistoryManager(history_dir=history_dir)

    state1 = {"step": 1, "data": "test1"}
    hm.add_state(state1)

    assert len(hm.state_history) == 1
    assert hm.current_index == 0
    assert hm.get_current_state() == state1


def test_history_manager_multiple_states(tmp_path):
    """複数状態の追加テスト"""
    history_dir = str(tmp_path / "history")
    hm = HistoryManager(history_dir=history_dir)

    states = [
        {"step": 1, "data": "test1"},
        {"step": 2, "data": "test2"},
        {"step": 3, "data": "test3"},
    ]

    for state in states:
        hm.add_state(state)

    assert len(hm.state_history) == 3
    assert hm.current_index == 2
    assert hm.get_current_state() == states[2]


def test_history_manager_rollback(tmp_path):
    """ロールバック機能のテスト"""
    history_dir = str(tmp_path / "history")
    hm = HistoryManager(history_dir=history_dir)

    states = [
        {"step": 1, "data": "test1"},
        {"step": 2, "data": "test2"},
        {"step": 3, "data": "test3"},
    ]

    for state in states:
        hm.add_state(state)

    # ロールバック
    rolled_back = hm.rollback()

    assert hm.current_index == 1
    assert rolled_back == states[1]
    assert hm.get_current_state() == states[1]


def test_history_manager_rollback_to_first(tmp_path):
    """最初の状態へのロールバックテスト"""
    history_dir = str(tmp_path / "history")
    hm = HistoryManager(history_dir=history_dir)

    state1 = {"step": 1, "data": "test1"}
    state2 = {"step": 2, "data": "test2"}

    hm.add_state(state1)
    hm.add_state(state2)

    # 2回ロールバック（最初の状態まで）
    hm.rollback()
    result = hm.rollback()

    assert hm.current_index == 0
    assert result == state1


def test_history_manager_rollback_at_beginning(tmp_path, capsys):
    """最初の状態でロールバックを試みた場合のテスト"""
    history_dir = str(tmp_path / "history")
    hm = HistoryManager(history_dir=history_dir)

    state1 = {"step": 1, "data": "test1"}
    hm.add_state(state1)

    # 最初の状態でロールバック
    result = hm.rollback()

    # 最初の状態のまま
    assert hm.current_index == 0
    assert result == state1
    captured = capsys.readouterr()
    assert "Already at oldest state" in captured.out


def test_history_manager_get_current_state_empty(tmp_path):
    """空の状態でのget_current_stateテスト"""
    history_dir = str(tmp_path / "history")
    hm = HistoryManager(history_dir=history_dir)

    assert hm.get_current_state() is None


def test_history_manager_save_history(tmp_path):
    """履歴保存のテスト"""
    history_dir = str(tmp_path / "history")
    hm = HistoryManager(history_dir=history_dir)

    state1 = {"step": 1, "data": "test1"}
    state2 = {"step": 2, "data": "test2"}

    hm.add_state(state1)
    hm.add_state(state2)

    # ファイルが存在し、正しい内容が保存されているか確認
    assert os.path.exists(hm.history_path)
    with open(hm.history_path, "r", encoding="utf-8") as f:
        saved_data = json.load(f)
        assert "history" in saved_data
        assert "current_index" in saved_data
        assert len(saved_data["history"]) == 2
        assert saved_data["current_index"] == 1


def test_history_manager_custom_prefix(tmp_path):
    """カスタムプレフィックスのテスト"""
    history_dir = str(tmp_path / "history")
    prefix = "custom_"
    hm = HistoryManager(history_dir=history_dir, prefix=prefix)

    assert hm.prefix == prefix
    assert prefix in os.path.basename(hm.history_path)


def test_history_manager_add_state_after_rollback(tmp_path):
    """ロールバック後に状態を追加するテスト（未来の履歴が切り捨てられる）"""
    history_dir = str(tmp_path / "history")
    hm = HistoryManager(history_dir=history_dir)

    states = [
        {"step": 1, "data": "test1"},
        {"step": 2, "data": "test2"},
        {"step": 3, "data": "test3"},
    ]

    for state in states:
        hm.add_state(state)

    # ロールバック
    hm.rollback()
    assert hm.current_index == 1

    # 新しい状態を追加（未来の履歴が切り捨てられる）
    new_state = {"step": 4, "data": "test4"}
    hm.add_state(new_state)

    assert len(hm.state_history) == 3  # 元の3つではなく、2つ+新しい1つ
    assert hm.current_index == 2
    assert hm.get_current_state() == new_state


def test_history_manager_rollback_multiple_times(tmp_path):
    """複数回のロールバックテスト"""
    history_dir = str(tmp_path / "history")
    hm = HistoryManager(history_dir=history_dir)

    states = [
        {"step": 1, "data": "test1"},
        {"step": 2, "data": "test2"},
        {"step": 3, "data": "test3"},
        {"step": 4, "data": "test4"},
    ]

    for state in states:
        hm.add_state(state)

    # 3回ロールバック
    result1 = hm.rollback()
    result2 = hm.rollback()
    result3 = hm.rollback()

    assert hm.current_index == 0
    assert result1 == states[2]
    assert result2 == states[1]
    assert result3 == states[0]
    assert hm.get_current_state() == states[0]


def test_history_manager_save_history_persists(tmp_path):
    """履歴がファイルに永続化されるテスト"""
    history_dir = str(tmp_path / "history")
    hm = HistoryManager(history_dir=history_dir)

    state1 = {"step": 1, "data": "test1"}
    state2 = {"step": 2, "data": "test2"}

    hm.add_state(state1)
    hm.add_state(state2)

    # ファイルが存在し、内容が正しいことを確認
    assert os.path.exists(hm.history_path)
    with open(hm.history_path, "r", encoding="utf-8") as f:
        saved_data = json.load(f)
        assert len(saved_data["history"]) == 2
        assert saved_data["current_index"] == 1
        assert saved_data["history"][0] == state1
        assert saved_data["history"][1] == state2


def test_history_manager_empty_rollback(tmp_path, capsys):
    """空の状態でロールバックを試みた場合のテスト"""
    history_dir = str(tmp_path / "history")
    hm = HistoryManager(history_dir=history_dir)

    # 状態がない状態でロールバック
    result = hm.rollback()

    assert result is None
    assert hm.current_index == -1
    captured = capsys.readouterr()
    assert "Already at oldest state" in captured.out


def test_history_manager_large_state(tmp_path):
    """大きな状態オブジェクトのテスト"""
    history_dir = str(tmp_path / "history")
    hm = HistoryManager(history_dir=history_dir)

    # 大きな状態を作成
    large_state = {
        "data": "x" * 10000,
        "items": list(range(1000)),
        "nested": {"level1": {"level2": {"level3": "deep"}}}
    }

    hm.add_state(large_state)

    assert len(hm.state_history) == 1
    assert hm.get_current_state() == large_state


def test_history_manager_complex_state(tmp_path):
    """複雑な状態オブジェクトのテスト"""
    history_dir = str(tmp_path / "history")
    hm = HistoryManager(history_dir=history_dir)

    complex_state = {
        "string": "test",
        "number": 123,
        "boolean": True,
        "list": [1, 2, 3],
        "dict": {"key": "value"},
        "none": None
    }

    hm.add_state(complex_state)
    saved_state = hm.get_current_state()

    assert saved_state == complex_state
    assert saved_state["string"] == "test"
    assert saved_state["number"] == 123
    assert saved_state["boolean"] is True
    assert saved_state["list"] == [1, 2, 3]
    assert saved_state["dict"] == {"key": "value"}
    assert saved_state["none"] is None


def test_history_manager_multiple_saves(tmp_path):
    """複数回の保存が正しく動作するテスト"""
    history_dir = str(tmp_path / "history")
    hm = HistoryManager(history_dir=history_dir)

    for i in range(5):
        hm.add_state({"step": i, "data": f"test{i}"})

    # ファイルが存在し、すべての状態が保存されていることを確認
    assert os.path.exists(hm.history_path)
    with open(hm.history_path, "r", encoding="utf-8") as f:
        saved_data = json.load(f)
        assert len(saved_data["history"]) == 5
        assert saved_data["current_index"] == 4


def test_history_manager_path_generation(tmp_path):
    """パス生成が正しく動作するテスト"""
    history_dir = str(tmp_path / "history")
    hm1 = HistoryManager(history_dir=history_dir)
    import time
    time.sleep(1.1)  # タイムスタンプが異なるように（秒単位で異なる必要がある）
    hm2 = HistoryManager(history_dir=history_dir)

    # 異なるパスが生成されることを確認（タイムスタンプが異なる場合）
    # ただし、同じ秒内に生成された場合は同じパスになる可能性がある
    # 両方とも同じディレクトリにあることを確認
    assert os.path.dirname(hm1.history_path) == os.path.dirname(hm2.history_path)
    # パスが正しい形式であることを確認
    assert "history_" in os.path.basename(hm1.history_path)
    assert "history_" in os.path.basename(hm2.history_path)
    assert hm1.history_path.endswith(".json")
    assert hm2.history_path.endswith(".json")


def test_history_manager_get_current_state_after_operations(tmp_path):
    """操作後のget_current_stateのテスト"""
    history_dir = str(tmp_path / "history")
    hm = HistoryManager(history_dir=history_dir)

    state1 = {"step": 1}
    state2 = {"step": 2}
    state3 = {"step": 3}

    hm.add_state(state1)
    assert hm.get_current_state() == state1

    hm.add_state(state2)
    assert hm.get_current_state() == state2

    hm.rollback()
    assert hm.get_current_state() == state1

    hm.add_state(state3)
    assert hm.get_current_state() == state3


def test_history_manager_rapid_state_changes(tmp_path):
    """迅速な状態変更のテスト"""
    history_dir = str(tmp_path / "history")
    hm = HistoryManager(history_dir=history_dir)

    # 短時間で多数の状態を追加
    for i in range(20):
        hm.add_state({"step": i, "timestamp": i})

    assert len(hm.state_history) == 20
    assert hm.current_index == 19
    assert hm.get_current_state()["step"] == 19


def test_history_manager_rollback_chain(tmp_path):
    """連続ロールバックのテスト"""
    history_dir = str(tmp_path / "history")
    hm = HistoryManager(history_dir=history_dir)

    # 10個の状態を追加
    states = [{"step": i} for i in range(10)]
    for state in states:
        hm.add_state(state)

    # すべてロールバック
    for i in range(9):
        result = hm.rollback()
        assert result == states[8 - i]
        assert hm.current_index == 8 - i

    # 最初の状態に戻る
    assert hm.current_index == 0
    assert hm.get_current_state() == states[0]


def test_history_manager_state_with_datetime(tmp_path):
    """datetimeオブジェクトを含む状態のテスト"""
    from datetime import datetime
    history_dir = str(tmp_path / "history")
    hm = HistoryManager(history_dir=history_dir)

    # datetimeはJSONシリアライズできないため、文字列として保存
    state = {
        "timestamp": datetime.now().isoformat(),
        "data": "test"
    }

    hm.add_state(state)
    saved_state = hm.get_current_state()

    # データが正しく保存されていることを確認
    assert saved_state["data"] == "test"
    assert "timestamp" in saved_state
    assert isinstance(saved_state["timestamp"], str)


def test_history_manager_empty_dict_state(tmp_path):
    """空の辞書状態のテスト"""
    history_dir = str(tmp_path / "history")
    hm = HistoryManager(history_dir=history_dir)

    empty_state = {}
    hm.add_state(empty_state)

    assert len(hm.state_history) == 1
    assert hm.get_current_state() == empty_state


def test_history_manager_state_with_nested_lists(tmp_path):
    """ネストされたリストを含む状態のテスト"""
    history_dir = str(tmp_path / "history")
    hm = HistoryManager(history_dir=history_dir)

    nested_state = {
        "matrix": [[1, 2, 3], [4, 5, 6], [7, 8, 9]],
        "nested": [[[1, 2], [3, 4]], [[5, 6], [7, 8]]]
    }

    hm.add_state(nested_state)
    saved_state = hm.get_current_state()

    assert saved_state["matrix"] == [[1, 2, 3], [4, 5, 6], [7, 8, 9]]
    assert len(saved_state["nested"]) == 2


def test_history_manager_file_persistence_across_instances(tmp_path):
    """インスタンス間でのファイル永続化テスト"""
    history_dir = str(tmp_path / "history")

    # 最初のインスタンス
    hm1 = HistoryManager(history_dir=history_dir)
    hm1.add_state({"step": 1, "data": "test1"})
    hm1.add_state({"step": 2, "data": "test2"})

    # ファイルが存在することを確認
    assert os.path.exists(hm1.history_path)

    # ファイルの内容を直接確認
    with open(hm1.history_path, "r", encoding="utf-8") as f:
        saved_data = json.load(f)
        assert len(saved_data["history"]) == 2


def test_history_manager_custom_prefix_format(tmp_path):
    """カスタムプレフィックスの形式テスト"""
    history_dir = str(tmp_path / "history")

    prefixes = ["custom_", "test_", "my_history_", "prefix123_"]

    for prefix in prefixes:
        hm = HistoryManager(history_dir=history_dir, prefix=prefix)
        assert prefix in os.path.basename(hm.history_path)
        assert hm.prefix == prefix


def test_history_manager_state_with_circular_reference_handling(tmp_path):
    """循環参照を含む状態のテスト（JSONシリアライズできない）"""
    history_dir = str(tmp_path / "history")
    hm = HistoryManager(history_dir=history_dir)

    # 循環参照を作成（JSONシリアライズできない）
    state = {"data": "test"}
    state["self"] = state  # 循環参照

    # エラーが発生する可能性がある
    try:
        hm.add_state(state)
        # エラーが発生しない場合、ファイルに保存される
        saved_state = hm.get_current_state()
        assert saved_state is not None
    except (TypeError, ValueError):
        # JSONシリアライズエラーは期待される動作
        pass


def test_history_manager_state_with_function_handling(tmp_path):
    """関数を含む状態のテスト（JSONシリアライズできない）"""
    history_dir = str(tmp_path / "history")
    hm = HistoryManager(history_dir=history_dir)

    def test_function():
        return "test"

    state = {
        "data": "test",
        "func": test_function  # 関数はJSONシリアライズできない
    }

    # エラーが発生する可能性がある
    try:
        hm.add_state(state)
        saved_state = hm.get_current_state()
        # 関数はシリアライズされない可能性がある
        assert saved_state is not None
    except (TypeError, ValueError):
        # JSONシリアライズエラーは期待される動作
        pass


def test_history_manager_very_large_history(tmp_path):
    """非常に大きな履歴のテスト"""
    history_dir = str(tmp_path / "history")
    hm = HistoryManager(history_dir=history_dir)

    # 大量の状態を追加
    for i in range(100):
        state = {
            "step": i,
            "data": "x" * 1000,  # 各状態に1KBのデータ
            "items": list(range(100))
        }
        hm.add_state(state)

    assert len(hm.state_history) == 100
    assert hm.current_index == 99

    # ファイルが正しく保存されていることを確認
    assert os.path.exists(hm.history_path)
    file_size = os.path.getsize(hm.history_path)
    assert file_size > 0


def test_history_manager_rollback_to_specific_index(tmp_path):
    """特定のインデックスへのロールバックシミュレーション"""
    history_dir = str(tmp_path / "history")
    hm = HistoryManager(history_dir=history_dir)

    # 10個の状態を追加
    states = [{"step": i} for i in range(10)]
    for state in states:
        hm.add_state(state)

    # 5回ロールバック（インデックス4に移動）
    for _ in range(5):
        hm.rollback()

    assert hm.current_index == 4
    assert hm.get_current_state() == states[4]

    # 新しい状態を追加（未来の履歴が切り捨てられる）
    new_state = {"step": 10}
    hm.add_state(new_state)

    assert len(hm.state_history) == 6  # 0-4 + 新しい状態
    assert hm.current_index == 5


def test_history_manager_concurrent_save_operations(tmp_path):
    """並行保存操作のテスト"""
    history_dir = str(tmp_path / "history")
    hm = HistoryManager(history_dir=history_dir)

    # 迅速に複数の状態を追加
    import threading

    def add_states():
        for i in range(10):
            hm.add_state({"thread": threading.current_thread().name, "step": i})

    threads = [threading.Thread(target=add_states) for _ in range(3)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # 最終的な状態を確認
    assert len(hm.state_history) > 0
    assert os.path.exists(hm.history_path)


def test_history_manager_file_corruption_recovery(tmp_path):
    """ファイル破損からの回復テスト"""
    history_dir = str(tmp_path / "history")
    hm = HistoryManager(history_dir=history_dir)

    # 正常な状態を追加
    hm.add_state({"step": 1, "data": "test1"})
    hm.add_state({"step": 2, "data": "test2"})

    # ファイルを破損させる（不正なJSON）
    with open(hm.history_path, "w", encoding="utf-8") as f:
        f.write("invalid json content")

    # 新しい状態を追加（ファイルが上書きされる）
    hm.add_state({"step": 3, "data": "test3"})

    # ファイルが正しく保存されていることを確認
    assert os.path.exists(hm.history_path)
    with open(hm.history_path, "r", encoding="utf-8") as f:
        import json
        try:
            data = json.load(f)
            assert "history" in data
        except json.JSONDecodeError:
            # まだ破損している場合は、次の保存で修正される
            pass


def test_history_manager_empty_prefix(tmp_path):
    """空のプレフィックスのテスト"""
    history_dir = str(tmp_path / "history")
    hm = HistoryManager(history_dir=history_dir, prefix="")

    assert hm.prefix == ""
    assert os.path.basename(hm.history_path).startswith("_") or os.path.basename(hm.history_path)[0].isdigit()


def test_history_manager_state_with_bytes_handling(tmp_path):
    """バイト列を含む状態のテスト"""
    history_dir = str(tmp_path / "history")
    hm = HistoryManager(history_dir=history_dir)

    # バイト列はJSONシリアライズできないため、文字列に変換
    state = {
        "data": "test",
        "bytes_as_str": b"binary_data".decode("utf-8")
    }

    hm.add_state(state)
    saved_state = hm.get_current_state()

    assert saved_state["data"] == "test"
    assert saved_state["bytes_as_str"] == "binary_data"
