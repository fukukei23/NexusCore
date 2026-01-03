"""
============================================================================
Comprehensive Tests for sandbox_executor.py
============================================================================
高品質テストの原則:
- 外部依存（subprocess、ファイルシステム、webapp）をモック
- 実際のサンドボックス実行ロジックとリトライ戦略をテスト
- エッジケースとエラー条件をカバー
============================================================================
"""
import pytest
import subprocess
import time
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, mock_open, call

from nexuscore.core.sandbox_executor import (
    load_sandbox_policy,
    SandboxExceptionType,
    SandboxResult,
    SandboxExecutor,
    run_in_sandbox,
)

try:
    import yaml
except ImportError:
    yaml = None


# ============================================================================
# Tests: load_sandbox_policy
# ============================================================================


class TestLoadSandboxPolicy:
    def test_load_policy_default_when_yaml_not_available(self):
        """YAMLがない場合のデフォルトポリシー"""
        with patch('nexuscore.core.sandbox_executor.yaml', None):
            policy = load_sandbox_policy()

            assert "resource_limits" in policy
            assert "retry_policy" in policy
            assert "network" in policy
            assert "filesystem" in policy
            assert policy["resource_limits"]["cpu_time_seconds"] == 30

    def test_load_policy_file_not_found(self):
        """ポリシーファイルが見つからない場合"""
        policy = load_sandbox_policy("/nonexistent/policy.yml")

        assert policy["resource_limits"]["wall_time_seconds"] == 60
        assert policy["retry_policy"]["max_retries"] == 1

    @patch.dict('os.environ', {'NEXUSCORE_SANDBOX_POLICY': '/custom/policy.yml'})
    def test_load_policy_from_env_var(self):
        """環境変数からポリシーパスを取得"""
        with patch('pathlib.Path.exists', return_value=False):
            policy = load_sandbox_policy()

            # ファイルが見つからないのでデフォルトが返される
            assert "resource_limits" in policy

    @pytest.mark.skipif(yaml is None, reason="PyYAML not installed")
    def test_load_policy_from_file(self, tmp_path):
        """YAMLファイルからポリシーをロード"""
        if yaml is None:
            pytest.skip("PyYAML not installed")

        policy_file = tmp_path / "sandbox_policy.yml"
        policy_content = """
resource_limits:
  cpu_time_seconds: 60
  memory_mb: 2048
retry_policy:
  max_retries: 3
"""
        policy_file.write_text(policy_content)

        policy = load_sandbox_policy(str(policy_file))

        assert policy["resource_limits"]["cpu_time_seconds"] == 60
        assert policy["resource_limits"]["memory_mb"] == 2048
        assert policy["retry_policy"]["max_retries"] == 3

    @pytest.mark.skipif(yaml is None, reason="PyYAML not installed")
    def test_load_policy_merge_with_defaults(self, tmp_path):
        """部分的なYAMLとデフォルトのマージ"""
        if yaml is None:
            pytest.skip("PyYAML not installed")

        policy_file = tmp_path / "partial_policy.yml"
        policy_content = """
resource_limits:
  cpu_time_seconds: 120
"""
        policy_file.write_text(policy_content)

        policy = load_sandbox_policy(str(policy_file))

        # カスタム値
        assert policy["resource_limits"]["cpu_time_seconds"] == 120
        # デフォルト値
        assert policy["resource_limits"]["wall_time_seconds"] == 60
        assert "retry_policy" in policy

    def test_load_policy_invalid_yaml(self, tmp_path):
        """無効なYAMLファイルの処理"""
        policy_file = tmp_path / "invalid.yml"
        policy_file.write_text("{ invalid yaml content")

        policy = load_sandbox_policy(str(policy_file))

        # デフォルトポリシーが返される
        assert "resource_limits" in policy


# ============================================================================
# Tests: SandboxResult
# ============================================================================


class TestSandboxResult:
    def test_sandbox_result_creation(self):
        """SandboxResult作成"""
        result = SandboxResult(
            stdout="test output",
            stderr="",
            returncode=0,
            timed_out=False,
            execution_time_sec=1.5,
        )

        assert result.stdout == "test output"
        assert result.returncode == 0
        assert result.timed_out is False
        assert result.execution_time_sec == 1.5

    def test_sandbox_result_with_timeout(self):
        """タイムアウトしたSandboxResult"""
        result = SandboxResult(
            stdout="",
            stderr="Timeout",
            returncode=-1,
            timed_out=True,
            exception_type=SandboxExceptionType.TIMEOUT,
        )

        assert result.timed_out is True
        assert result.exception_type == SandboxExceptionType.TIMEOUT


# ============================================================================
# Tests: SandboxExecutor.__init__
# ============================================================================


class TestSandboxExecutorInit:
    def test_init_with_defaults(self):
        """デフォルト値で初期化"""
        executor = SandboxExecutor()

        assert executor.default_timeout_sec == 60
        assert executor.max_retries == 1
        assert executor.policy is not None

    def test_init_with_custom_values(self):
        """カスタム値で初期化"""
        executor = SandboxExecutor(
            default_timeout_sec=120,
            max_retries=5,
            retry_delay_sec=2.0,
        )

        assert executor.default_timeout_sec == 60  # ポリシーから上書き
        assert executor.max_retries == 1  # ポリシーから上書き
        assert executor.retry_delay_sec == 2.0

    def test_init_with_custom_policy(self):
        """カスタムポリシーで初期化"""
        custom_policy = {
            "resource_limits": {"wall_time_seconds": 180},
            "retry_policy": {"max_retries": 10},
        }

        executor = SandboxExecutor(policy=custom_policy)

        assert executor.default_timeout_sec == 180
        assert executor.max_retries == 10


# ============================================================================
# Tests: SandboxExecutor.run_in_sandbox
# ============================================================================


class TestRunInSandbox:
    @patch('nexuscore.core.sandbox_executor.subprocess.run')
    def test_run_in_sandbox_success(self, mock_run):
        """正常実行"""
        mock_result = Mock()
        mock_result.stdout = "success output"
        mock_result.stderr = ""
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        executor = SandboxExecutor()
        result = executor.run_in_sandbox(["echo", "test"])

        assert result.returncode == 0
        assert result.stdout == "success output"
        assert result.timed_out is False

    @patch('nexuscore.core.sandbox_executor.subprocess.run')
    def test_run_in_sandbox_with_timeout(self, mock_run):
        """カスタムタイムアウト"""
        mock_run.side_effect = subprocess.TimeoutExpired(["sleep", "10"], 5)

        executor = SandboxExecutor()
        result = executor.run_in_sandbox(["sleep", "10"], timeout_sec=5)

        assert result.timed_out is True
        assert result.exception_type == SandboxExceptionType.TIMEOUT

    @patch('nexuscore.core.sandbox_executor.subprocess.run')
    def test_run_in_sandbox_with_cwd(self, mock_run):
        """作業ディレクトリ指定"""
        mock_result = Mock(stdout="", stderr="", returncode=0)
        mock_run.return_value = mock_result

        executor = SandboxExecutor()
        executor.run_in_sandbox(["ls"], cwd="/tmp")

        mock_run.assert_called_once()
        assert mock_run.call_args[1]["cwd"] == "/tmp"

    @patch('nexuscore.core.sandbox_executor.subprocess.run')
    def test_run_in_sandbox_with_env(self, mock_run):
        """環境変数指定"""
        mock_result = Mock(stdout="", stderr="", returncode=0)
        mock_run.return_value = mock_result

        executor = SandboxExecutor()
        custom_env = {"TEST_VAR": "value"}
        executor.run_in_sandbox(["env"], env=custom_env)

        mock_run.assert_called_once()
        assert mock_run.call_args[1]["env"] == custom_env

    @patch('nexuscore.core.sandbox_executor.subprocess.run')
    @patch('nexuscore.core.sandbox_executor.time.sleep')
    def test_run_in_sandbox_with_retry(self, mock_sleep, mock_run):
        """リトライ機能"""
        # 最初の2回は失敗、3回目で成功
        mock_run.side_effect = [
            Exception("Network error"),
            Exception("Network error"),
            Mock(stdout="success", stderr="", returncode=0),
        ]

        executor = SandboxExecutor(max_retries=2)
        executor.max_retries = 2  # ポリシーを上書き
        result = executor.run_in_sandbox(["test"], retry_on_errors=True)

        assert result.returncode == 0
        assert mock_run.call_count == 3
        assert mock_sleep.call_count == 2  # 2回リトライ

    @patch('nexuscore.core.sandbox_executor.subprocess.run')
    def test_run_in_sandbox_no_retry_on_execution_error(self, mock_run):
        """実行エラーの場合はリトライしない"""
        mock_run.side_effect = Exception("syntax error")

        executor = SandboxExecutor()
        result = executor.run_in_sandbox(["python", "bad.py"], retry_on_errors=True)

        assert result.exception_type == SandboxExceptionType.EXECUTION_ERROR
        assert mock_run.call_count == 1  # リトライしない

    @patch('nexuscore.core.sandbox_executor.subprocess.run')
    def test_run_in_sandbox_no_retry_when_disabled(self, mock_run):
        """retry_on_errors=Falseの場合"""
        mock_run.side_effect = Exception("error")

        executor = SandboxExecutor()
        result = executor.run_in_sandbox(["test"], retry_on_errors=False)

        assert mock_run.call_count == 1
        assert result.returncode == -1


# ============================================================================
# Tests: SandboxExecutor._execute_once
# ============================================================================


class TestExecuteOnce:
    @patch('nexuscore.core.sandbox_executor.subprocess.run')
    def test_execute_once_success(self, mock_run):
        """1回の実行成功"""
        mock_result = Mock(stdout="output", stderr="", returncode=0)
        mock_run.return_value = mock_result

        executor = SandboxExecutor()
        result = executor._execute_once(["test"], 60, None, None)

        assert result.returncode == 0
        assert result.stdout == "output"
        # execution_time_sec is real time, just check it's >= 0
        assert result.execution_time_sec >= 0

    @patch('nexuscore.core.sandbox_executor.subprocess.run')
    def test_execute_once_timeout(self, mock_run):
        """タイムアウト発生"""
        mock_run.side_effect = subprocess.TimeoutExpired(["sleep"], 5)

        executor = SandboxExecutor()

        with pytest.raises(subprocess.TimeoutExpired):
            executor._execute_once(["sleep", "10"], 5, None, None)


# ============================================================================
# Tests: SandboxExecutor._classify_exception
# ============================================================================


class TestClassifyException:
    def test_classify_rate_limit_error(self):
        """レート制限エラーの分類"""
        executor = SandboxExecutor()

        exc1 = Exception("Rate limit exceeded")
        exc2 = Exception("HTTP 429 Too Many Requests")

        assert executor._classify_exception(exc1) == SandboxExceptionType.RATE_LIMIT
        assert executor._classify_exception(exc2) == SandboxExceptionType.RATE_LIMIT

    def test_classify_network_error(self):
        """ネットワークエラーの分類"""
        executor = SandboxExecutor()

        exc1 = Exception("Connection refused")
        exc2 = Exception("DNS resolution failed")

        assert executor._classify_exception(exc1) == SandboxExceptionType.NETWORK_ERROR
        assert executor._classify_exception(exc2) == SandboxExceptionType.NETWORK_ERROR

    def test_classify_timeout_error(self):
        """タイムアウトエラーの分類（timeoutはnetwork_errorに分類される）"""
        executor = SandboxExecutor()

        exc = Exception("Request timeout")

        # "timeout"はnetwork errorのキーワードに含まれるため、NETWORK_ERRORになる
        assert executor._classify_exception(exc) == SandboxExceptionType.NETWORK_ERROR

    def test_classify_execution_error(self):
        """実行エラーの分類"""
        executor = SandboxExecutor()

        exc = Exception("Syntax error in code")

        assert executor._classify_exception(exc) == SandboxExceptionType.EXECUTION_ERROR


# ============================================================================
# Tests: SandboxExecutor._log_sandbox_error
# ============================================================================


class TestLogSandboxError:
    def test_log_sandbox_error_with_webapp(self):
        """webappがある場合のログ記録"""
        # webapp モジュールをモック
        import sys
        from unittest.mock import MagicMock

        mock_webapp = MagicMock()
        mock_log_func = MagicMock()
        mock_webapp.logging_service.log_execution_event = mock_log_func

        sys.modules['nexuscore.webapp'] = mock_webapp
        sys.modules['nexuscore.webapp.logging_service'] = mock_webapp.logging_service

        try:
            executor = SandboxExecutor()

            executor._log_sandbox_error(
                run_db_id=123,
                error_type=SandboxExceptionType.TIMEOUT,
                message="Test timeout",
                payload={"cmd": ["test"]},
            )

            mock_log_func.assert_called_once()
            call_kwargs = mock_log_func.call_args[1]
            assert call_kwargs["run_id"] == 123
            assert call_kwargs["level"] == "ERROR"
            assert call_kwargs["message"] == "Test timeout"
        finally:
            # クリーンアップ
            sys.modules.pop('nexuscore.webapp', None)
            sys.modules.pop('nexuscore.webapp.logging_service', None)

    def test_log_sandbox_error_without_webapp(self):
        """webappがない場合（ImportErrorが発生してもスキップされる）"""
        # ImportErrorをシミュレート
        import sys
        webapp_module = sys.modules.get('nexuscore.webapp.logging_service')
        if 'nexuscore.webapp.logging_service' in sys.modules:
            del sys.modules['nexuscore.webapp.logging_service']

        try:
            executor = SandboxExecutor()

            # 例外が発生しないことを確認
            executor._log_sandbox_error(
                run_db_id=None,
                error_type=SandboxExceptionType.TIMEOUT,
                message="Test",
            )
        finally:
            # モジュールを復元
            if webapp_module is not None:
                sys.modules['nexuscore.webapp.logging_service'] = webapp_module


# ============================================================================
# Tests: run_in_sandbox (global function)
# ============================================================================


class TestGlobalRunInSandbox:
    @patch('nexuscore.core.sandbox_executor.subprocess.run')
    def test_global_run_in_sandbox(self, mock_run):
        """グローバル関数でのサンドボックス実行"""
        mock_result = Mock(stdout="output", stderr="", returncode=0)
        mock_run.return_value = mock_result

        result = run_in_sandbox(["echo", "test"], timeout_sec=30)

        assert result.returncode == 0
        assert result.stdout == "output"


# ============================================================================
# Tests: Integration scenarios
# ============================================================================


class TestIntegrationScenarios:
    @patch('nexuscore.core.sandbox_executor.subprocess.run')
    @patch('nexuscore.core.sandbox_executor.time.sleep')
    def test_full_retry_workflow(self, mock_sleep, mock_run):
        """完全なリトライワークフロー"""
        # 最初2回失敗、3回目成功
        mock_run.side_effect = [
            Exception("Connection error"),
            Exception("Network error"),
            Mock(stdout="success", stderr="", returncode=0),
        ]

        executor = SandboxExecutor(max_retries=2, retry_delay_sec=1.0)
        executor.max_retries = 2  # ポリシーを上書き

        result = executor.run_in_sandbox(["test"], retry_on_errors=True)

        assert result.returncode == 0
        assert result.stdout == "success"

        # リトライ間隔の確認（指数バックオフ）
        assert mock_sleep.call_count == 2
        sleep_calls = [call[0][0] for call in mock_sleep.call_args_list]
        assert sleep_calls[0] == 1.0  # 1回目のリトライ
        assert sleep_calls[1] == 2.0  # 2回目のリトライ（2倍）

    @patch('nexuscore.core.sandbox_executor.subprocess.run')
    def test_timeout_no_retry(self, mock_run):
        """タイムアウトはリトライしない"""
        mock_run.side_effect = subprocess.TimeoutExpired(["sleep"], 5)

        executor = SandboxExecutor(max_retries=3)
        result = executor.run_in_sandbox(["sleep", "10"], timeout_sec=5)

        assert result.timed_out is True
        assert mock_run.call_count == 1  # リトライしない

    @patch('nexuscore.core.sandbox_executor.subprocess.run')
    def test_execution_error_no_retry(self, mock_run):
        """実行エラーはリトライしない"""
        mock_run.side_effect = Exception("SyntaxError: invalid syntax")

        executor = SandboxExecutor(max_retries=3)
        result = executor.run_in_sandbox(["python", "bad.py"])

        assert result.exception_type == SandboxExceptionType.EXECUTION_ERROR
        assert mock_run.call_count == 1

    @patch('nexuscore.core.sandbox_executor.subprocess.run')
    def test_measure_execution_time(self, mock_run):
        """実行時間の測定"""
        mock_result = Mock(stdout="", stderr="", returncode=0)
        mock_run.return_value = mock_result

        executor = SandboxExecutor()
        result = executor.run_in_sandbox(["test"])

        # execution_time_sec should be measured and >= 0
        assert result.execution_time_sec >= 0
        assert result.returncode == 0
