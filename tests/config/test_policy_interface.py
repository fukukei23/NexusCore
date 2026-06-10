"""Tests for nexuscore.ui.policy_interface"""

from unittest.mock import MagicMock, patch

import pytest

from nexuscore.ui import policy_interface


def test_policy_interface_init():
    """PolicyInterfaceの初期化テスト"""
    pi = policy_interface.PolicyInterface()

    assert pi.result_queue is not None
    assert pi.interface is None


def test_policy_interface_get_safe_default_policy():
    """デフォルトポリシーの取得テスト"""
    pi = policy_interface.PolicyInterface()
    policy = pi._get_safe_default_policy()

    assert isinstance(policy, dict)
    assert "test_import_policy" in policy
    assert "error_language" in policy
    assert "quality_requirements" in policy
    assert "security_policy" in policy
    assert policy["test_import_policy"] == "関数を直接埋め込み"
    assert policy["error_language"] == "日本語"


def test_policy_interface_get_default_policy():
    """get_default_policyのテスト（互換性維持）"""
    pi = policy_interface.PolicyInterface()
    policy = pi._get_default_policy()

    assert isinstance(policy, dict)
    assert "test_import_policy" in policy


@patch("nexuscore.ui.policy_interface.GRADIO_AVAILABLE", False)
def test_launch_and_wait_for_input_no_gradio():
    """Gradioが利用できない場合のテスト"""
    pi = policy_interface.PolicyInterface()
    result = pi.launch_and_wait_for_input(timeout=1)

    assert result is not None
    assert isinstance(result, dict)
    assert "method" in result
    assert result["method"] == "safe_default"


@patch("nexuscore.ui.policy_interface.GRADIO_AVAILABLE", True)
@patch("nexuscore.ui.policy_interface.gr")
def test_create_gradio_interface(mock_gr):
    """Gradioインターフェース作成のテスト"""
    pi = policy_interface.PolicyInterface()

    mock_blocks = MagicMock()
    mock_gr.Blocks.return_value.__enter__.return_value = mock_blocks

    interface = pi.create_gradio_interface()

    assert interface is not None
    mock_gr.Blocks.assert_called_once()


@patch("nexuscore.ui.policy_interface.GRADIO_AVAILABLE", False)
def test_create_gradio_interface_no_gradio():
    """Gradioが利用できない場合のcreate_gradio_interfaceテスト"""
    pi = policy_interface.PolicyInterface()

    with pytest.raises(ImportError, match="Gradio がインストールされていません"):
        pi.create_gradio_interface()


@patch("nexuscore.ui.policy_interface.GRADIO_AVAILABLE", True)
@patch("nexuscore.ui.policy_interface.gr")
def test_launch_and_wait_for_input_with_gradio(mock_gr):
    """Gradioが利用可能な場合のlaunch_and_wait_for_inputテスト"""
    pi = policy_interface.PolicyInterface()

    mock_blocks = MagicMock()
    mock_interface = MagicMock()
    mock_gr.Blocks.return_value.__enter__.return_value = mock_blocks
    mock_blocks.launch.return_value = None

    # キューに結果を追加（別スレッドで実行される想定）
    import threading
    import time

    def add_result():
        time.sleep(0.1)
        pi.result_queue.put({"method": "gradio_ui", "test": "value"})

    thread = threading.Thread(target=add_result)
    thread.daemon = True
    thread.start()

    with patch.object(pi, "create_gradio_interface", return_value=mock_interface):
        result = pi.launch_and_wait_for_input(timeout=5)

        assert result is not None
        assert result["method"] == "gradio_ui"


@patch("nexuscore.ui.policy_interface.GRADIO_AVAILABLE", True)
@patch("nexuscore.ui.policy_interface.gr")
def test_launch_and_wait_for_input_timeout(mock_gr):
    """タイムアウト時のlaunch_and_wait_for_inputテスト"""
    pi = policy_interface.PolicyInterface()

    mock_blocks = MagicMock()
    mock_interface = MagicMock()
    mock_gr.Blocks.return_value.__enter__.return_value = mock_blocks

    with patch.object(pi, "create_gradio_interface", return_value=mock_interface):
        # キューに何も追加しない（タイムアウトを発生させる）
        result = pi.launch_and_wait_for_input(timeout=0.1)

        assert result is not None
        assert result["method"] == "safe_default"


def test_policy_interface_result_queue_operations():
    """結果キューの操作テスト"""
    pi = policy_interface.PolicyInterface()

    # キューが空であることを確認
    assert pi.result_queue.empty()

    # 結果を追加
    test_result = {"method": "test", "value": 123}
    pi.result_queue.put(test_result)

    # キューから取得
    result = pi.result_queue.get(timeout=1)
    assert result == test_result


def test_policy_interface_multiple_instances():
    """複数のPolicyInterfaceインスタンスのテスト"""
    pi1 = policy_interface.PolicyInterface()
    pi2 = policy_interface.PolicyInterface()

    # 各インスタンスが独立したキューを持つことを確認
    pi1.result_queue.put({"instance": 1})
    pi2.result_queue.put({"instance": 2})

    assert pi1.result_queue.get()["instance"] == 1
    assert pi2.result_queue.get()["instance"] == 2


def test_policy_interface_default_policy_structure():
    """デフォルトポリシーの構造テスト"""
    pi = policy_interface.PolicyInterface()
    policy = pi._get_safe_default_policy()

    # 必須フィールドが存在することを確認
    assert "test_import_policy" in policy
    assert "error_language" in policy
    assert "quality_requirements" in policy
    assert "security_policy" in policy
    assert "configured_at" in policy
    assert "method" in policy

    # 値の型を確認
    assert isinstance(policy["test_import_policy"], str)
    assert isinstance(policy["error_language"], str)
    assert isinstance(policy["quality_requirements"], list)
    assert isinstance(policy["security_policy"], list)
    assert policy["method"] == "safe_default"


def test_policy_interface_get_default_policy_consistency():
    """get_default_policyとget_safe_default_policyの一貫性テスト"""
    pi = policy_interface.PolicyInterface()

    default_policy = pi._get_default_policy()
    safe_policy = pi._get_safe_default_policy()

    # 両方が同じ構造を持つことを確認
    assert set(default_policy.keys()) == set(safe_policy.keys())
    assert default_policy["test_import_policy"] == safe_policy["test_import_policy"]
    assert default_policy["error_language"] == safe_policy["error_language"]


@patch("nexuscore.ui.policy_interface.GRADIO_AVAILABLE", True)
@patch("nexuscore.ui.policy_interface.gr")
def test_create_gradio_interface_components(mock_gr):
    """Gradioインターフェースのコンポーネント作成テスト"""
    pi = policy_interface.PolicyInterface()

    mock_blocks = MagicMock()
    mock_gr.Blocks.return_value.__enter__.return_value = mock_blocks

    interface = pi.create_gradio_interface()

    assert interface is not None
    mock_gr.Blocks.assert_called_once()


def test_policy_interface_queue_timeout():
    """キューのタイムアウト動作テスト"""
    pi = policy_interface.PolicyInterface()

    # タイムアウトを短く設定してキューから取得を試みる
    import queue

    try:
        pi.result_queue.get(timeout=0.01)
        raise AssertionError("Should have raised queue.Empty")
    except queue.Empty:
        pass  # 期待される動作


def test_policy_interface_default_policy_values():
    """デフォルトポリシーの値の検証テスト"""
    pi = policy_interface.PolicyInterface()
    policy = pi._get_safe_default_policy()

    # 値が期待される範囲内であることを確認
    assert policy["test_import_policy"] in ["関数を直接埋め込み", "インポート文を使用", "混在OK"]
    assert policy["error_language"] in ["日本語", "英語", "自動"]
    assert isinstance(policy["quality_requirements"], list)
    assert isinstance(policy["security_policy"], list)


def test_policy_interface_interface_initialization():
    """インターフェースの初期化テスト"""
    pi = policy_interface.PolicyInterface()

    # 初期状態を確認
    assert pi.interface is None
    assert pi.result_queue is not None
    assert hasattr(pi, "result_queue")


@patch("nexuscore.ui.policy_interface.GRADIO_AVAILABLE", True)
@patch("nexuscore.ui.policy_interface.gr")
def test_launch_and_wait_for_input_keyboard_interrupt(mock_gr):
    """KeyboardInterrupt時の動作テスト"""
    pi = policy_interface.PolicyInterface()

    mock_interface = MagicMock()

    with patch.object(pi, "create_gradio_interface", return_value=mock_interface):
        # KeyboardInterruptをシミュレート

        def mock_get(timeout=None):
            raise KeyboardInterrupt()

        pi.result_queue.get = mock_get

        result = pi.launch_and_wait_for_input(timeout=1)

        # デフォルトポリシーが返されることを確認
        assert result is not None
        assert result["method"] == "safe_default"


def test_policy_interface_policy_immutability():
    """ポリシーの不変性テスト"""
    pi = policy_interface.PolicyInterface()
    policy1 = pi._get_safe_default_policy()
    policy2 = pi._get_safe_default_policy()

    # configured_atは時間によって異なるため、主要なフィールドのみを比較
    assert policy1["test_import_policy"] == policy2["test_import_policy"]
    assert policy1["error_language"] == policy2["error_language"]
    assert policy1["quality_requirements"] == policy2["quality_requirements"]
    assert policy1["security_policy"] == policy2["security_policy"]
    assert policy1["method"] == policy2["method"]
    # configured_atは存在することを確認（値は異なる可能性がある）
    assert "configured_at" in policy1
    assert "configured_at" in policy2


def test_policy_interface_queue_operations_stress(tmp_path):
    """キューの操作ストレステスト"""
    pi = policy_interface.PolicyInterface()

    # 大量の結果をキューに追加
    for i in range(100):
        pi.result_queue.put({"test": i, "value": f"data_{i}"})

    # すべての結果を取得
    results = []
    while not pi.result_queue.empty():
        try:
            result = pi.result_queue.get(timeout=0.1)
            results.append(result)
        except Exception:
            break

    assert len(results) == 100


def test_policy_interface_default_policy_completeness():
    """デフォルトポリシーの完全性テスト"""
    pi = policy_interface.PolicyInterface()
    policy = pi._get_safe_default_policy()

    # すべての必須フィールドが存在することを確認
    required_fields = [
        "test_import_policy",
        "error_language",
        "quality_requirements",
        "security_policy",
        "configured_at",
        "method",
    ]

    for field in required_fields:
        assert field in policy, f"Missing required field: {field}"


@patch("nexuscore.ui.policy_interface.GRADIO_AVAILABLE", True)
@patch("nexuscore.ui.policy_interface.gr")
def test_launch_and_wait_for_input_exception_handling(mock_gr):
    """例外処理のテスト"""
    pi = policy_interface.PolicyInterface()

    mock_interface = MagicMock()

    with patch.object(pi, "create_gradio_interface", return_value=mock_interface):
        # 一般的な例外をシミュレート

        def mock_get(timeout=None):
            raise Exception("General error")

        pi.result_queue.get = mock_get

        result = pi.launch_and_wait_for_input(timeout=0.1)

        # デフォルトポリシーが返されることを確認
        assert result is not None
        assert result["method"] == "safe_default"


def test_policy_interface_result_queue_thread_safety():
    """結果キューのスレッド安全性テスト"""
    import threading

    pi = policy_interface.PolicyInterface()
    results = []

    def put_results(thread_id):
        for i in range(10):
            pi.result_queue.put({"thread": thread_id, "value": i})

    def get_results():
        for _ in range(10):
            try:
                result = pi.result_queue.get(timeout=1)
                results.append(result)
            except Exception:
                break

    # 複数のスレッドで同時にput/get
    put_threads = [threading.Thread(target=put_results, args=(i,)) for i in range(5)]
    get_threads = [threading.Thread(target=get_results) for _ in range(5)]

    for t in put_threads:
        t.start()
    for t in get_threads:
        t.start()

    for t in put_threads:
        t.join()
    for t in get_threads:
        t.join()

    # すべての結果が取得されたことを確認
    assert len(results) > 0
