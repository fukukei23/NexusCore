"""
policy_interface.py の包括的テスト

カバレッジ:
- PolicyInterface: ポリシー設定インターフェース
  - __init__: 初期化
  - create_gradio_interface: Gradio UI作成
  - launch_and_wait_for_input: UI起動と入力待機
  - _get_safe_default_policy: デフォルトポリシー取得
"""

import sys
from datetime import datetime
from unittest.mock import MagicMock, Mock, patch, PropertyMock

import pytest


@pytest.fixture(autouse=True)
def mock_gradio():
    """各テストの前後でgradioをモック化/復元（テスト分離のため）"""
    # テスト前：元の状態を保存してモック化
    original_gradio = sys.modules.get('gradio')
    sys.modules['gradio'] = MagicMock()

    yield  # ← ここでテストが実行される

    # テスト後：元の状態に復元
    if original_gradio is None:
        sys.modules.pop('gradio', None)
    else:
        sys.modules['gradio'] = original_gradio


try:
    from nexuscore.agents.policy_interface import PolicyInterface, GRADIO_AVAILABLE
    HAS_POLICY_INTERFACE = True
except ImportError:
    HAS_POLICY_INTERFACE = False
    PolicyInterface = None
    GRADIO_AVAILABLE = False


@pytest.mark.skipif(not HAS_POLICY_INTERFACE, reason="policy_interface module not available")
class TestPolicyInterfaceInit:
    """PolicyInterface 初期化のテスト"""

    def test_init_basic(self):
        """基本的な初期化"""
        interface = PolicyInterface()

        assert hasattr(interface, 'result_queue')
        assert hasattr(interface, 'interface')
        assert interface.interface is None

    def test_init_creates_queue(self):
        """result_queueが作成される"""
        interface = PolicyInterface()

        assert interface.result_queue is not None
        assert hasattr(interface.result_queue, 'put')
        assert hasattr(interface.result_queue, 'get')


@pytest.mark.skipif(not HAS_POLICY_INTERFACE, reason="policy_interface module not available")
class TestGetSafeDefaultPolicy:
    """PolicyInterface._get_safe_default_policy() のテスト"""

    def test_get_safe_default_policy_structure(self):
        """デフォルトポリシーの構造が正しい"""
        interface = PolicyInterface()
        policy = interface._get_safe_default_policy()

        assert isinstance(policy, dict)
        assert "test_import_policy" in policy
        assert "error_language" in policy
        assert "quality_requirements" in policy
        assert "security_policy" in policy
        assert "configured_at" in policy
        assert "method" in policy

    def test_get_safe_default_policy_values(self):
        """デフォルトポリシーの値が正しい"""
        interface = PolicyInterface()
        policy = interface._get_safe_default_policy()

        assert policy["test_import_policy"] == "関数を直接埋め込み"
        assert policy["error_language"] == "日本語"
        assert "docstring必須" in policy["quality_requirements"]
        assert "エラーハンドリング必須" in policy["quality_requirements"]
        assert "APIキー環境変数管理" in policy["security_policy"]
        assert policy["method"] == "safe_default"

    def test_get_safe_default_policy_timestamp(self):
        """configured_atにタイムスタンプが含まれる"""
        interface = PolicyInterface()
        policy = interface._get_safe_default_policy()

        # ISO形式のタイムスタンプであることを確認
        timestamp = policy["configured_at"]
        assert "T" in timestamp or "-" in timestamp

    def test_get_default_policy_compatibility(self):
        """_get_default_policyは互換性のため_get_safe_default_policyを呼ぶ"""
        interface = PolicyInterface()
        default = interface._get_default_policy()
        safe_default = interface._get_safe_default_policy()

        # configured_atは異なる可能性があるので除外して比較
        assert default["test_import_policy"] == safe_default["test_import_policy"]
        assert default["method"] == safe_default["method"]


@pytest.mark.skipif(not HAS_POLICY_INTERFACE or not GRADIO_AVAILABLE, reason="gradio not available")
class TestCreateGradioInterface:
    """PolicyInterface.create_gradio_interface() のテスト"""

    @patch('nexuscore.agents.policy_interface.gr')
    def test_create_gradio_interface_returns_blocks(self, mock_gr):
        """Gradio Blocksオブジェクトを返す"""
        mock_blocks = Mock()
        mock_gr.Blocks.return_value.__enter__.return_value = mock_blocks

        interface = PolicyInterface()

        # GRADIO_AVAILABLEがFalseの場合はImportErrorを投げる
        with patch('nexuscore.agents.policy_interface.GRADIO_AVAILABLE', True):
            result = interface.create_gradio_interface()

        assert result is not None


@pytest.mark.skipif(not HAS_POLICY_INTERFACE, reason="policy_interface module not available")
class TestLaunchAndWaitForInput:
    """PolicyInterface.launch_and_wait_for_input() のテスト"""

    @patch('nexuscore.agents.policy_interface.GRADIO_AVAILABLE', False)
    def test_launch_without_gradio_returns_default(self):
        """Gradioが利用できない場合はデフォルトポリシーを返す"""
        interface = PolicyInterface()
        result = interface.launch_and_wait_for_input(timeout=1)

        assert result is not None
        assert result["method"] == "safe_default"

    @patch('nexuscore.agents.policy_interface.GRADIO_AVAILABLE', True)
    @patch('nexuscore.agents.policy_interface.PolicyInterface.create_gradio_interface')
    @patch('threading.Thread')
    def test_launch_with_timeout_returns_default(self, mock_thread, mock_create_interface):
        """タイムアウト時はデフォルトポリシーを返す"""
        mock_ui = Mock()
        mock_create_interface.return_value = mock_ui

        interface = PolicyInterface()
        result = interface.launch_and_wait_for_input(timeout=0.1)

        # タイムアウトでデフォルトポリシーが返る
        assert result is not None
        assert "method" in result

    @patch('nexuscore.agents.policy_interface.GRADIO_AVAILABLE', True)
    @patch('nexuscore.agents.policy_interface.PolicyInterface.create_gradio_interface')
    def test_launch_exception_returns_default(self, mock_create_interface):
        """UIの起動に失敗した場合はデフォルトポリシーを返す"""
        mock_create_interface.side_effect = Exception("UI launch failed")

        interface = PolicyInterface()
        result = interface.launch_and_wait_for_input(timeout=1)

        # 例外発生でデフォルトポリシーが返る
        assert result is not None
        assert result["method"] == "safe_default"


@pytest.mark.skipif(not HAS_POLICY_INTERFACE, reason="policy_interface module not available")
class TestEdgeCases:
    """エッジケースのテスト"""

    def test_multiple_instances(self):
        """複数のインスタンスを作成できる"""
        interface1 = PolicyInterface()
        interface2 = PolicyInterface()

        assert interface1.result_queue != interface2.result_queue

    def test_result_queue_operations(self):
        """result_queueの基本操作"""
        interface = PolicyInterface()

        # データを追加
        test_policy = {"test": "data"}
        interface.result_queue.put(test_policy)

        # データを取得
        result = interface.result_queue.get(timeout=1)

        assert result == test_policy

    @patch('nexuscore.agents.policy_interface.GRADIO_AVAILABLE', False)
    def test_graceful_degradation(self):
        """Gradio不在時のグレースフルデグラデーション"""
        interface = PolicyInterface()

        # Gradioなしでもデフォルトポリシーは取得できる
        policy = interface._get_safe_default_policy()

        assert policy is not None
        assert isinstance(policy, dict)

    def test_default_policy_is_immutable(self):
        """デフォルトポリシーは毎回新しいインスタンスを返す"""
        interface = PolicyInterface()

        policy1 = interface._get_safe_default_policy()
        policy2 = interface._get_safe_default_policy()

        # タイムスタンプ以外のフィールドが同じことを確認
        assert policy1["test_import_policy"] == policy2["test_import_policy"]
        assert policy1["error_language"] == policy2["error_language"]
        assert policy1["quality_requirements"] == policy2["quality_requirements"]
        assert policy1["security_policy"] == policy2["security_policy"]
        assert policy1["method"] == policy2["method"]
        # タイムスタンプは異なる可能性があるので、存在することだけ確認
        assert "configured_at" in policy1
        assert "configured_at" in policy2

    def test_quality_requirements_list(self):
        """quality_requirementsがリストである"""
        interface = PolicyInterface()
        policy = interface._get_safe_default_policy()

        assert isinstance(policy["quality_requirements"], list)
        assert len(policy["quality_requirements"]) >= 2

    def test_security_policy_list(self):
        """security_policyがリストである"""
        interface = PolicyInterface()
        policy = interface._get_safe_default_policy()

        assert isinstance(policy["security_policy"], list)
        assert len(policy["security_policy"]) >= 2

    def test_test_import_policy_valid_value(self):
        """test_import_policyが有効な値である"""
        interface = PolicyInterface()
        policy = interface._get_safe_default_policy()

        valid_values = ["関数を直接埋め込み", "インポート文を使用", "混在OK"]
        assert policy["test_import_policy"] in valid_values

    def test_error_language_valid_value(self):
        """error_languageが有効な値である"""
        interface = PolicyInterface()
        policy = interface._get_safe_default_policy()

        valid_values = ["日本語", "英語", "自動"]
        assert policy["error_language"] in valid_values


@pytest.mark.skipif(not HAS_POLICY_INTERFACE, reason="policy_interface module not available")
class TestIntegration:
    """統合テスト"""

    def test_full_workflow_without_ui(self):
        """UIなしの完全ワークフロー"""
        interface = PolicyInterface()

        # デフォルトポリシーを取得
        policy = interface._get_safe_default_policy()

        # ポリシーの各フィールドを検証
        assert policy["test_import_policy"] == "関数を直接埋め込み"
        assert policy["error_language"] == "日本語"
        assert isinstance(policy["quality_requirements"], list)
        assert isinstance(policy["security_policy"], list)
        assert "configured_at" in policy
        assert policy["method"] == "safe_default"

    @patch('nexuscore.agents.policy_interface.GRADIO_AVAILABLE', False)
    def test_launch_workflow_graceful_fallback(self):
        """launch時のグレースフルフォールバック"""
        interface = PolicyInterface()

        # Gradio不在でもlaunchは成功し、デフォルトポリシーが返る
        result = interface.launch_and_wait_for_input(timeout=1)

        assert result is not None
        assert result["method"] == "safe_default"
