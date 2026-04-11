"""
policy_interface.py のカバレッジ向上テスト

未カバー行: 14-17, 32, 87-109, 138-175, 183-187, 189-202
"""

from __future__ import annotations

import queue
from datetime import datetime
from unittest.mock import MagicMock, Mock, patch

import pytest


class TestPolicyInterfaceInit:
    """PolicyInterface 初期化テスト"""

    def test_init(self):
        from nexuscore.agents.policy_interface import PolicyInterface

        pi = PolicyInterface()
        assert pi.result_queue is not None
        assert pi.interface is None


class TestGetSafeDefaultPolicy:
    """_get_safe_default_policy のテスト（行193-202）"""

    def test_returns_valid_dict(self):
        from nexuscore.agents.policy_interface import PolicyInterface

        pi = PolicyInterface()
        policy = pi._get_safe_default_policy()
        assert policy["test_import_policy"] == "関数を直接埋め込み"
        assert policy["error_language"] == "日本語"
        assert "docstring必須" in policy["quality_requirements"]
        assert "ハードコーディング禁止" in policy["security_policy"]
        assert policy["method"] == "safe_default"
        assert "configured_at" in policy

    def test_default_policy_has_all_keys(self):
        from nexuscore.agents.policy_interface import PolicyInterface

        pi = PolicyInterface()
        policy = pi._get_safe_default_policy()
        expected_keys = {
            "test_import_policy",
            "error_language",
            "quality_requirements",
            "security_policy",
            "configured_at",
            "method",
        }
        assert expected_keys.issubset(policy.keys())


class TestGetDefaultPolicy:
    """_get_default_policy のテスト（行189-191）"""

    def test_calls_safe_default(self):
        """_get_default_policy は _get_safe_default_policy と同じ内容を返す"""
        from nexuscore.agents.policy_interface import PolicyInterface

        pi = PolicyInterface()
        result = pi._get_default_policy()
        # configured_at が呼び出しごとに変わるので、キー存在チェックで検証
        assert result["method"] == "safe_default"
        assert result["test_import_policy"] == "関数を直接埋め込み"
        assert "configured_at" in result


class TestCreateGradioInterface:
    """create_gradio_interface のテスト（行29-132）"""

    @patch("nexuscore.agents.policy_interface.GRADIO_AVAILABLE", False)
    def test_raises_import_error_without_gradio(self):
        from nexuscore.agents.policy_interface import PolicyInterface

        pi = PolicyInterface()
        with pytest.raises(ImportError, match="Gradio"):
            pi.create_gradio_interface()


class TestLaunchAndWaitForInput:
    """launch_and_wait_for_input のテスト（行134-187）"""

    @patch("nexuscore.agents.policy_interface.GRADIO_AVAILABLE", False)
    def test_returns_default_when_no_gradio(self):
        """Gradio未インストール時はデフォルト設定を返す（行138-140）"""
        from nexuscore.agents.policy_interface import PolicyInterface

        pi = PolicyInterface()
        result = pi.launch_and_wait_for_input(timeout=5)
        assert result is not None
        assert result["method"] == "safe_default"

    def test_returns_queue_result(self):
        """キューに結果がある場合、即座に返す（行167-169）"""
        from nexuscore.agents.policy_interface import PolicyInterface

        pi = PolicyInterface()
        expected = {"test_import_policy": "test", "method": "queue_test"}
        pi.result_queue.put(expected)
        result = pi.launch_and_wait_for_input(timeout=5)
        assert result["method"] == "queue_test"

    def test_timeout_returns_default(self):
        """タイムアウト時はデフォルト設定を返す（行170-172）"""
        from nexuscore.agents.policy_interface import PolicyInterface

        pi = PolicyInterface()
        with patch.object(pi, "create_gradio_interface"):
            with patch("threading.Thread"):
                result = pi.launch_and_wait_for_input(timeout=0.01)
        assert result is not None
        assert result["method"] == "safe_default"

    def test_keyboard_interrupt_returns_default(self):
        """KeyboardInterrupt時はデフォルト設定を返す（行173-175）"""
        from nexuscore.agents.policy_interface import PolicyInterface

        pi = PolicyInterface()
        pi.result_queue = MagicMock()
        pi.result_queue.get.side_effect = KeyboardInterrupt()
        pi._get_safe_default_policy = Mock(return_value={"method": "safe_default"})

        result = pi.launch_and_wait_for_input(timeout=1)
        assert result["method"] == "safe_default"

    def test_general_exception_returns_default(self):
        """一般的な例外時はデフォルト設定を返す（行177-179）"""
        from nexuscore.agents.policy_interface import PolicyInterface

        pi = PolicyInterface()
        with patch.object(pi, "create_gradio_interface", side_effect=RuntimeError("fail")):
            result = pi.launch_and_wait_for_input(timeout=1)
        assert result is not None

    def test_gradio_close_error_handled(self):
        """Gradio close時のエラーハンドリング（行183-187）"""
        from nexuscore.agents.policy_interface import PolicyInterface

        pi = PolicyInterface()
        pi.interface = MagicMock()
        pi.interface.close.side_effect = RuntimeError("close error")
        pi._get_safe_default_policy = Mock(return_value={"method": "safe_default"})

        with patch.object(pi, "create_gradio_interface"):
            with patch("threading.Thread"):
                result = pi.launch_and_wait_for_input(timeout=0.01)

        # finally block で interface.close() が呼ばれる
        # エラーが発生しても結果は返る
        assert result is not None
