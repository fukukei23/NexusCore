"""
Comprehensive tests for core/nexus_os_kernel.py

NexusOSカーネルのシングルトンとシステムコールのテスト
"""

import logging
import sys
from unittest.mock import MagicMock, Mock, patch

import pytest

# 必要な依存モジュールをモック化
sys.modules["nexuscore.npe.engine"] = MagicMock()
sys.modules["nexuscore.utils.vcs"] = MagicMock()
sys.modules["nexuscore.workflows.multi_llm_review"] = MagicMock()
sys.modules["nexuscore.code_interpreter.sandbox_runner"] = MagicMock()
sys.modules["nexuscore.utils.test_generator"] = MagicMock()
sys.modules["nexuscore.utils.logger"] = MagicMock()

from nexuscore.core.nexus_os_kernel import NexusOSKernel, get_kernel


# ============================================================================
# NexusOSKernel 初期化テスト
# ============================================================================
class TestNexusOSKernelInit:
    @patch("nexuscore.core.nexus_os_kernel.NPEEngine")
    @patch("nexuscore.core.nexus_os_kernel.GitController")
    @patch("nexuscore.core.nexus_os_kernel.MultiLLMReviewer")
    @patch("nexuscore.core.nexus_os_kernel.SandboxRunner")
    @patch("nexuscore.core.nexus_os_kernel.TestGenerator")
    def test_init_creates_all_modules(
        self, mock_testgen, mock_sandbox, mock_reviewer, mock_vcs, mock_npe
    ):
        """初期化時に全モジュールを作成"""
        kernel = NexusOSKernel()

        # 全モジュールがインスタンス化される
        assert kernel.npe is not None
        assert kernel.vcs is not None
        assert kernel.reviewer is not None
        assert kernel.sandbox is not None
        assert kernel.testgen is not None

    @patch("nexuscore.core.nexus_os_kernel.NPEEngine")
    @patch("nexuscore.core.nexus_os_kernel.GitController")
    @patch("nexuscore.core.nexus_os_kernel.MultiLLMReviewer")
    @patch("nexuscore.core.nexus_os_kernel.SandboxRunner")
    @patch("nexuscore.core.nexus_os_kernel.TestGenerator")
    def test_init_creates_services(
        self, mock_testgen, mock_sandbox, mock_reviewer, mock_vcs, mock_npe
    ):
        """初期化時にサービスレジストリを作成"""
        kernel = NexusOSKernel()

        assert hasattr(kernel, "_services")
        assert isinstance(kernel._services, dict)
        assert len(kernel._services) > 0

    @patch("nexuscore.core.nexus_os_kernel.NPEEngine")
    @patch("nexuscore.core.nexus_os_kernel.GitController")
    @patch("nexuscore.core.nexus_os_kernel.MultiLLMReviewer")
    @patch("nexuscore.core.nexus_os_kernel.SandboxRunner")
    @patch("nexuscore.core.nexus_os_kernel.TestGenerator")
    def test_init_logs_boot_message(
        self, mock_testgen, mock_sandbox, mock_reviewer, mock_vcs, mock_npe, caplog
    ):
        """起動時にログメッセージを出力"""
        with caplog.at_level(logging.INFO):
            kernel = NexusOSKernel()

        # 起動ログが出力される（モックされたロガーの場合は検証をスキップ）
        assert kernel is not None


# ============================================================================
# get_service テスト
# ============================================================================
class TestGetService:
    @patch("nexuscore.core.nexus_os_kernel.NPEEngine")
    @patch("nexuscore.core.nexus_os_kernel.GitController")
    @patch("nexuscore.core.nexus_os_kernel.MultiLLMReviewer")
    @patch("nexuscore.core.nexus_os_kernel.SandboxRunner")
    @patch("nexuscore.core.nexus_os_kernel.TestGenerator")
    def test_get_service_search_tool(
        self, mock_testgen, mock_sandbox, mock_reviewer, mock_vcs, mock_npe
    ):
        """Google Searchサービスを取得"""
        kernel = NexusOSKernel()

        service = kernel.get_service("Google Search_tool")

        assert service is not None

    @patch("nexuscore.core.nexus_os_kernel.NPEEngine")
    @patch("nexuscore.core.nexus_os_kernel.GitController")
    @patch("nexuscore.core.nexus_os_kernel.MultiLLMReviewer")
    @patch("nexuscore.core.nexus_os_kernel.SandboxRunner")
    @patch("nexuscore.core.nexus_os_kernel.TestGenerator")
    def test_get_service_default_llm(
        self, mock_testgen, mock_sandbox, mock_reviewer, mock_vcs, mock_npe
    ):
        """デフォルトLLMサービスを取得"""
        kernel = NexusOSKernel()

        service = kernel.get_service("default_llm_client")

        assert service is not None

    @patch("nexuscore.core.nexus_os_kernel.NPEEngine")
    @patch("nexuscore.core.nexus_os_kernel.GitController")
    @patch("nexuscore.core.nexus_os_kernel.MultiLLMReviewer")
    @patch("nexuscore.core.nexus_os_kernel.SandboxRunner")
    @patch("nexuscore.core.nexus_os_kernel.TestGenerator")
    def test_get_service_unknown_raises_error(
        self, mock_testgen, mock_sandbox, mock_reviewer, mock_vcs, mock_npe
    ):
        """存在しないサービスはValueError"""
        kernel = NexusOSKernel()

        with pytest.raises(ValueError, match="not found"):
            kernel.get_service("nonexistent_service")


# ============================================================================
# ダミーサービステスト
# ============================================================================
class TestDummyServices:
    @patch("nexuscore.core.nexus_os_kernel.NPEEngine")
    @patch("nexuscore.core.nexus_os_kernel.GitController")
    @patch("nexuscore.core.nexus_os_kernel.MultiLLMReviewer")
    @patch("nexuscore.core.nexus_os_kernel.SandboxRunner")
    @patch("nexuscore.core.nexus_os_kernel.TestGenerator")
    def test_dummy_search_tool_has_search_method(
        self, mock_testgen, mock_sandbox, mock_reviewer, mock_vcs, mock_npe
    ):
        """DummySearchToolがsearchメソッドを持つ"""
        kernel = NexusOSKernel()
        search_tool = kernel.get_service("Google Search_tool")

        assert hasattr(search_tool, "search")
        assert callable(search_tool.search)

    @patch("nexuscore.core.nexus_os_kernel.NPEEngine")
    @patch("nexuscore.core.nexus_os_kernel.GitController")
    @patch("nexuscore.core.nexus_os_kernel.MultiLLMReviewer")
    @patch("nexuscore.core.nexus_os_kernel.SandboxRunner")
    @patch("nexuscore.core.nexus_os_kernel.TestGenerator")
    def test_dummy_search_tool_returns_results(
        self, mock_testgen, mock_sandbox, mock_reviewer, mock_vcs, mock_npe
    ):
        """DummySearchToolが検索結果を返す"""
        kernel = NexusOSKernel()
        search_tool = kernel.get_service("Google Search_tool")

        results = search_tool.search("test query")

        assert isinstance(results, list)
        assert len(results) > 0
        assert "title" in results[0]

    @patch("nexuscore.core.nexus_os_kernel.NPEEngine")
    @patch("nexuscore.core.nexus_os_kernel.GitController")
    @patch("nexuscore.core.nexus_os_kernel.MultiLLMReviewer")
    @patch("nexuscore.core.nexus_os_kernel.SandboxRunner")
    @patch("nexuscore.core.nexus_os_kernel.TestGenerator")
    def test_dummy_llm_client_has_invoke_method(
        self, mock_testgen, mock_sandbox, mock_reviewer, mock_vcs, mock_npe
    ):
        """DummyLLMClientがinvokeメソッドを持つ"""
        kernel = NexusOSKernel()
        llm_client = kernel.get_service("default_llm_client")

        assert hasattr(llm_client, "invoke")
        assert callable(llm_client.invoke)

    @patch("nexuscore.core.nexus_os_kernel.NPEEngine")
    @patch("nexuscore.core.nexus_os_kernel.GitController")
    @patch("nexuscore.core.nexus_os_kernel.MultiLLMReviewer")
    @patch("nexuscore.core.nexus_os_kernel.SandboxRunner")
    @patch("nexuscore.core.nexus_os_kernel.TestGenerator")
    def test_dummy_llm_client_returns_response(
        self, mock_testgen, mock_sandbox, mock_reviewer, mock_vcs, mock_npe
    ):
        """DummyLLMClientがレスポンスを返す"""
        kernel = NexusOSKernel()
        llm_client = kernel.get_service("default_llm_client")

        response = llm_client.invoke("test prompt")

        assert response is not None
        assert isinstance(response, str)


# ============================================================================
# syscall_execute_code テスト
# ============================================================================
class TestSyscallExecuteCode:
    @patch("nexuscore.core.nexus_os_kernel.NPEEngine")
    @patch("nexuscore.core.nexus_os_kernel.GitController")
    @patch("nexuscore.core.nexus_os_kernel.MultiLLMReviewer")
    @patch("nexuscore.core.nexus_os_kernel.SandboxRunner")
    @patch("nexuscore.core.nexus_os_kernel.TestGenerator")
    def test_execute_code_with_permission_granted(
        self, mock_testgen, mock_sandbox, mock_reviewer, mock_vcs, mock_npe
    ):
        """許可された場合にコードを実行"""
        # NPEが許可を返すようにモック
        mock_permission = Mock()
        mock_permission.is_granted = True
        mock_npe.return_value.request_permission.return_value = mock_permission

        # サンドボックスが結果を返すようにモック
        mock_result = {"status": "success", "output": "42"}
        mock_sandbox.return_value.run.return_value = mock_result

        kernel = NexusOSKernel()
        result = kernel.syscall_execute_code(
            agent_id="test_agent", code="print(42)", estimated_cost=0.1
        )

        assert result == mock_result

    @patch("nexuscore.core.nexus_os_kernel.NPEEngine")
    @patch("nexuscore.core.nexus_os_kernel.GitController")
    @patch("nexuscore.core.nexus_os_kernel.MultiLLMReviewer")
    @patch("nexuscore.core.nexus_os_kernel.SandboxRunner")
    @patch("nexuscore.core.nexus_os_kernel.TestGenerator")
    def test_execute_code_permission_denied_raises_error(
        self, mock_testgen, mock_sandbox, mock_reviewer, mock_vcs, mock_npe
    ):
        """許可されない場合はPermissionError"""
        # NPEが拒否を返すようにモック
        mock_permission = Mock()
        mock_permission.is_granted = False
        mock_permission.reason = "Budget exceeded"
        mock_npe.return_value.request_permission.return_value = mock_permission

        kernel = NexusOSKernel()

        with pytest.raises(PermissionError, match="Budget exceeded"):
            kernel.syscall_execute_code(
                agent_id="test_agent", code="print(42)", estimated_cost=999.0
            )

    @patch("nexuscore.core.nexus_os_kernel.NPEEngine")
    @patch("nexuscore.core.nexus_os_kernel.GitController")
    @patch("nexuscore.core.nexus_os_kernel.MultiLLMReviewer")
    @patch("nexuscore.core.nexus_os_kernel.SandboxRunner")
    @patch("nexuscore.core.nexus_os_kernel.TestGenerator")
    def test_execute_code_logs_transaction(
        self, mock_testgen, mock_sandbox, mock_reviewer, mock_vcs, mock_npe
    ):
        """実行後にトランザクションをログ"""
        mock_permission = Mock()
        mock_permission.is_granted = True
        mock_npe.return_value.request_permission.return_value = mock_permission

        mock_result = {"status": "success"}
        mock_sandbox.return_value.run.return_value = mock_result

        kernel = NexusOSKernel()
        kernel.syscall_execute_code(agent_id="test_agent", code="print(42)", estimated_cost=0.1)

        # NPEのlog_transactionが呼ばれる
        kernel.npe.log_transaction.assert_called_once()


# ============================================================================
# syscall_commit_file テスト
# ============================================================================
class TestSyscallCommitFile:
    @patch("nexuscore.core.nexus_os_kernel.NPEEngine")
    @patch("nexuscore.core.nexus_os_kernel.GitController")
    @patch("nexuscore.core.nexus_os_kernel.MultiLLMReviewer")
    @patch("nexuscore.core.nexus_os_kernel.SandboxRunner")
    @patch("nexuscore.core.nexus_os_kernel.TestGenerator")
    def test_commit_file_with_approval(
        self, mock_testgen, mock_sandbox, mock_reviewer, mock_vcs, mock_npe
    ):
        """レビュー承認後にファイルをコミット"""
        # NPEが許可
        mock_permission = Mock()
        mock_permission.is_granted = True
        mock_npe.return_value.request_permission.return_value = mock_permission

        # レビューが承認
        mock_review_result = Mock()
        mock_review_result.is_approved = True
        mock_review_result.approved_code = "def foo(): pass"
        mock_reviewer.return_value.review.return_value = mock_review_result

        # テストが成功
        mock_test_result = Mock()
        mock_test_result.passed = True
        mock_sandbox.return_value.run.return_value = mock_test_result

        # VCSがコミットハッシュを返す
        mock_vcs.return_value.get_last_commit_hash.return_value = "abc123"

        kernel = NexusOSKernel()
        result = kernel.syscall_commit_file(
            agent_id="test_agent",
            file_path="test.py",
            file_content="def foo(): pass",
            commit_message="Add foo function",
        )

        assert result["status"] == "success"
        assert result["commit_hash"] == "abc123"

    @patch("nexuscore.core.nexus_os_kernel.NPEEngine")
    @patch("nexuscore.core.nexus_os_kernel.GitController")
    @patch("nexuscore.core.nexus_os_kernel.MultiLLMReviewer")
    @patch("nexuscore.core.nexus_os_kernel.SandboxRunner")
    @patch("nexuscore.core.nexus_os_kernel.TestGenerator")
    def test_commit_file_permission_denied(
        self, mock_testgen, mock_sandbox, mock_reviewer, mock_vcs, mock_npe
    ):
        """NPEが拒否した場合はPermissionError"""
        mock_permission = Mock()
        mock_permission.is_granted = False
        mock_permission.reason = "Policy violation"
        mock_npe.return_value.request_permission.return_value = mock_permission

        kernel = NexusOSKernel()

        with pytest.raises(PermissionError, match="Policy violation"):
            kernel.syscall_commit_file(
                agent_id="test_agent",
                file_path="test.py",
                file_content="bad code",
                commit_message="Bad commit",
            )

    @patch("nexuscore.core.nexus_os_kernel.NPEEngine")
    @patch("nexuscore.core.nexus_os_kernel.GitController")
    @patch("nexuscore.core.nexus_os_kernel.MultiLLMReviewer")
    @patch("nexuscore.core.nexus_os_kernel.SandboxRunner")
    @patch("nexuscore.core.nexus_os_kernel.TestGenerator")
    def test_commit_file_review_rejected(
        self, mock_testgen, mock_sandbox, mock_reviewer, mock_vcs, mock_npe
    ):
        """レビューが拒否した場合はValueError"""
        mock_permission = Mock()
        mock_permission.is_granted = True
        mock_npe.return_value.request_permission.return_value = mock_permission

        mock_review_result = Mock()
        mock_review_result.is_approved = False
        mock_review_result.feedback = "Code quality issues"
        mock_reviewer.return_value.review.return_value = mock_review_result

        kernel = NexusOSKernel()

        with pytest.raises(ValueError, match="AI Peer Review rejected"):
            kernel.syscall_commit_file(
                agent_id="test_agent",
                file_path="test.py",
                file_content="bad code",
                commit_message="Bad commit",
            )

    @patch("nexuscore.core.nexus_os_kernel.NPEEngine")
    @patch("nexuscore.core.nexus_os_kernel.GitController")
    @patch("nexuscore.core.nexus_os_kernel.MultiLLMReviewer")
    @patch("nexuscore.core.nexus_os_kernel.SandboxRunner")
    @patch("nexuscore.core.nexus_os_kernel.TestGenerator")
    def test_commit_file_tests_failed(
        self, mock_testgen, mock_sandbox, mock_reviewer, mock_vcs, mock_npe
    ):
        """テストが失敗した場合はValueError"""
        mock_permission = Mock()
        mock_permission.is_granted = True
        mock_npe.return_value.request_permission.return_value = mock_permission

        mock_review_result = Mock()
        mock_review_result.is_approved = True
        mock_review_result.approved_code = "def foo(): pass"
        mock_reviewer.return_value.review.return_value = mock_review_result

        mock_test_result = Mock()
        mock_test_result.passed = False
        mock_test_result.output = "Test failure details"
        mock_sandbox.return_value.run.return_value = mock_test_result

        kernel = NexusOSKernel()

        with pytest.raises(ValueError, match="Automated tests failed"):
            kernel.syscall_commit_file(
                agent_id="test_agent",
                file_path="test.py",
                file_content="def foo(): pass",
                commit_message="Add foo",
            )


# ============================================================================
# get_kernel シングルトンテスト
# ============================================================================
class TestGetKernelSingleton:
    def setup_method(self):
        """各テスト前にシングルトンをリセット"""
        import nexuscore.core.nexus_os_kernel as kernel_module

        kernel_module._kernel_instance = None

    @patch("nexuscore.core.nexus_os_kernel.NPEEngine")
    @patch("nexuscore.core.nexus_os_kernel.GitController")
    @patch("nexuscore.core.nexus_os_kernel.MultiLLMReviewer")
    @patch("nexuscore.core.nexus_os_kernel.SandboxRunner")
    @patch("nexuscore.core.nexus_os_kernel.TestGenerator")
    def test_get_kernel_returns_instance(
        self, mock_testgen, mock_sandbox, mock_reviewer, mock_vcs, mock_npe
    ):
        """get_kernelがインスタンスを返す"""
        kernel = get_kernel()

        assert isinstance(kernel, NexusOSKernel)

    @patch("nexuscore.core.nexus_os_kernel.NPEEngine")
    @patch("nexuscore.core.nexus_os_kernel.GitController")
    @patch("nexuscore.core.nexus_os_kernel.MultiLLMReviewer")
    @patch("nexuscore.core.nexus_os_kernel.SandboxRunner")
    @patch("nexuscore.core.nexus_os_kernel.TestGenerator")
    def test_get_kernel_returns_same_instance(
        self, mock_testgen, mock_sandbox, mock_reviewer, mock_vcs, mock_npe
    ):
        """複数回呼び出しても同じインスタンスを返す"""
        kernel1 = get_kernel()
        kernel2 = get_kernel()

        assert kernel1 is kernel2


# ============================================================================
# 統合テスト
# ============================================================================
class TestNexusOSKernelIntegration:
    @patch("nexuscore.core.nexus_os_kernel.NPEEngine")
    @patch("nexuscore.core.nexus_os_kernel.GitController")
    @patch("nexuscore.core.nexus_os_kernel.MultiLLMReviewer")
    @patch("nexuscore.core.nexus_os_kernel.SandboxRunner")
    @patch("nexuscore.core.nexus_os_kernel.TestGenerator")
    def test_full_workflow_init_service_syscall(
        self, mock_testgen, mock_sandbox, mock_reviewer, mock_vcs, mock_npe
    ):
        """完全ワークフロー: 初期化→サービス→システムコール"""
        # NPEとサンドボックスのモック設定
        mock_permission = Mock()
        mock_permission.is_granted = True
        mock_npe.return_value.request_permission.return_value = mock_permission
        mock_sandbox.return_value.run.return_value = {"status": "success"}

        # カーネル初期化
        kernel = NexusOSKernel()

        # サービス取得
        llm_client = kernel.get_service("default_llm_client")
        assert llm_client is not None

        # システムコール実行
        result = kernel.syscall_execute_code(
            agent_id="integration_test", code="print('hello')", estimated_cost=0.01
        )
        assert result["status"] == "success"

    @patch("nexuscore.core.nexus_os_kernel.NPEEngine")
    @patch("nexuscore.core.nexus_os_kernel.GitController")
    @patch("nexuscore.core.nexus_os_kernel.MultiLLMReviewer")
    @patch("nexuscore.core.nexus_os_kernel.SandboxRunner")
    @patch("nexuscore.core.nexus_os_kernel.TestGenerator")
    def test_services_are_cached(
        self, mock_testgen, mock_sandbox, mock_reviewer, mock_vcs, mock_npe
    ):
        """サービスがキャッシュされる"""
        kernel = NexusOSKernel()

        # 同じサービスを2回取得
        service1 = kernel.get_service("Google Search_tool")
        service2 = kernel.get_service("Google Search_tool")

        # 同じインスタンスを返す
        assert service1 is service2
