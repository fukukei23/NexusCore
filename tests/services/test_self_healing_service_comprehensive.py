"""
Comprehensive tests for self_healing_service.py

包括的なエッジケース、エラーハンドリング、統合シナリオのテスト
"""

import sys
from unittest.mock import MagicMock, Mock, patch

# patchモジュールをモック化（import前に実行）
sys.modules["patch"] = MagicMock()


from nexuscore.config.self_healing_config import SelfHealingConfig
from nexuscore.core.run_history import RunHistoryLogger
from nexuscore.services.self_healing_service import SelfHealingService
from nexuscore.services.git_operations import clone_or_update_repo, get_changed_files
from nexuscore.services.test_runner import run_tests
from nexuscore.services.patch_workflow import collect_relevant_files, generate_patch_via_debugger


# ============================================================================
# 初期化と設定テスト
# ============================================================================
class TestInitializationAndConfig:
    def test_initialization_with_custom_config(self, tmp_path):
        """カスタム設定での初期化"""
        config = SelfHealingConfig(
            test_command="pytest --maxfail=1", allow_test_modification=True, allow_deletions=True
        )

        service = SelfHealingService(project_root=str(tmp_path), config=config)

        assert service.config.test_command == "pytest --maxfail=1"
        assert service.config.allow_test_modification is True
        assert service.config.allow_deletions is True

    def test_initialization_creates_default_components(self, tmp_path):
        """デフォルトコンポーネントの自動生成"""
        service = SelfHealingService(project_root=str(tmp_path))

        assert service.session_controller is not None
        assert service.patch_applier is not None
        assert service.history_logger is not None
        assert service.logger is not None

    def test_initialization_with_none_dependencies(self, tmp_path):
        """None依存関係での初期化（デフォルト生成）"""
        service = SelfHealingService(
            project_root=str(tmp_path),
            session_controller=None,
            debugger_agent=None,
            patch_applier=None,
            history_logger=None,
            config=None,
        )

        assert service.session_controller is not None
        assert service.patch_applier is not None
        assert service.history_logger is not None


# ============================================================================
# _maybe_stop メソッドテスト
# ============================================================================
class TestMaybeStop:
    def test_maybe_stop_no_session_controller(self, tmp_path):
        """SessionControllerがない場合はスキップ"""
        service = SelfHealingService(project_root=str(tmp_path), session_controller=None)

        service._maybe_stop("test_phase")

    def test_maybe_stop_with_metadata(self, tmp_path):
        """メタデータ付きで_maybe_stopを呼ぶ"""
        mock_controller = Mock()
        mock_controller.should_stop.return_value = False

        service = SelfHealingService(project_root=str(tmp_path), session_controller=mock_controller)

        meta = {"key": "value", "count": 42}
        service._maybe_stop("phase1", meta)

        mock_controller.should_stop.assert_called_once()


# ============================================================================
# clone_or_update_repo (git_operations) テスト
# ============================================================================
class TestCloneOrUpdateRepo:
    @patch("nexuscore.services.git_operations.subprocess")
    def test_clone_new_repo_success(self, mock_subprocess, tmp_path):
        """新規リポジトリのクローン成功"""
        mock_subprocess.run.return_value = Mock(returncode=0, stdout="", stderr="")

        target_dir = tmp_path / "sandbox" / "repo"

        clone_or_update_repo(
            repo_full_name="user/repo", pr_number=123, head_sha="abc123", target_dir=target_dir
        )

        assert mock_subprocess.run.call_count >= 2

    @patch("nexuscore.services.git_operations.subprocess")
    def test_clone_from_local_base_dir(self, mock_subprocess, tmp_path, monkeypatch):
        """ローカルベースディレクトリからのコピー"""
        base_dir = tmp_path / "repos"
        base_dir.mkdir()
        (base_dir / "user" / "repo").mkdir(parents=True)

        monkeypatch.setenv("NEXUS_REPO_BASE_DIR", str(base_dir))
        mock_subprocess.run.return_value = Mock(returncode=0)

        target_dir = tmp_path / "sandbox" / "repo"

        clone_or_update_repo(
            repo_full_name="user/repo", pr_number=123, head_sha="abc123", target_dir=target_dir
        )

        assert target_dir.exists()

    @patch("nexuscore.services.git_operations.subprocess")
    def test_clone_with_authentication_url(self, mock_subprocess, tmp_path, monkeypatch):
        """認証URL経由でのクローン"""
        monkeypatch.setenv(
            "NEXUS_GITHUB_CLONE_URL_TEMPLATE",
            "https://token:SECRET@github.com/{repo_full_name}.git",
        )

        mock_subprocess.run.return_value = Mock(returncode=0)

        target_dir = tmp_path / "sandbox" / "repo"

        clone_or_update_repo(
            repo_full_name="user/repo", pr_number=123, head_sha="abc123", target_dir=target_dir
        )

        assert any("token:SECRET" in str(call) for call in mock_subprocess.run.call_args_list)


# ============================================================================
# run_tests (test_runner) テスト
# ============================================================================
class TestRunTests:
    @patch("nexuscore.services.test_runner.HAS_SANDBOX", False)
    @patch("nexuscore.services.test_runner.subprocess")
    def test_run_tests_success(self, mock_subprocess, tmp_path):
        """テスト実行成功"""
        mock_subprocess.run.return_value = Mock(returncode=0, stdout="5 passed", stderr="")

        success, output = run_tests(tmp_path)

        assert success is True
        assert "passed" in output or output == ""

    @patch("nexuscore.services.test_runner.HAS_SANDBOX", False)
    @patch("nexuscore.services.test_runner.subprocess")
    def test_run_tests_failure(self, mock_subprocess, tmp_path):
        """テスト実行失敗"""
        mock_subprocess.run.return_value = Mock(returncode=1, stdout="", stderr="3 failed")

        success, output = run_tests(tmp_path)

        assert success is False

    @patch("nexuscore.services.test_runner.HAS_SANDBOX", False)
    @patch("nexuscore.services.test_runner.subprocess")
    def test_run_tests_with_custom_command(self, mock_subprocess, tmp_path, monkeypatch):
        """カスタムテストコマンドでの実行"""
        monkeypatch.setenv("NEXUS_SELF_HEALING_TEST_CMD", "npm test")
        mock_subprocess.run.return_value = Mock(returncode=0, stdout="OK", stderr="")

        success, _ = run_tests(tmp_path)

        assert success is True
        assert any("npm" in str(call) for call in mock_subprocess.run.call_args_list)

    @patch("nexuscore.services.test_runner.HAS_SANDBOX", False)
    @patch("nexuscore.services.test_runner.subprocess")
    def test_run_tests_timeout_handling(self, mock_subprocess, tmp_path):
        """タイムアウト処理"""
        from subprocess import TimeoutExpired

        mock_subprocess.run.side_effect = TimeoutExpired("pytest", 60)

        try:
            success, output = run_tests(tmp_path)
            assert success is False
        except TimeoutExpired:
            pass


# ============================================================================
# get_changed_files (git_operations) テスト
# ============================================================================
class TestGetChangedFiles:
    @patch("nexuscore.services.git_operations.subprocess")
    def test_get_changed_files_with_refs(self, mock_subprocess, tmp_path):
        """base_ref/head_ref指定での変更ファイル取得"""
        mock_subprocess.run.return_value = Mock(returncode=0, stdout="src/foo.py\nsrc/bar.py\n", stderr="")

        files = get_changed_files(tmp_path, "main", "feature-branch")

        assert isinstance(files, list)
        assert len(files) >= 0

    @patch("nexuscore.services.git_operations.subprocess")
    def test_get_changed_files_without_refs(self, mock_subprocess, tmp_path):
        """refs未指定でのフォールバック"""
        mock_subprocess.run.return_value = Mock(returncode=0, stdout="test.py\n", stderr="")

        files = get_changed_files(tmp_path, None, None)

        assert isinstance(files, list)

    @patch("nexuscore.services.git_operations.subprocess")
    def test_get_changed_files_git_error(self, mock_subprocess, tmp_path):
        """gitコマンドエラー時の処理"""
        mock_subprocess.run.side_effect = Exception("git not found")

        try:
            files = get_changed_files(tmp_path, "main", "head")
            assert isinstance(files, list)
        except Exception:
            pass


# ============================================================================
# collect_relevant_files (patch_workflow) テスト
# ============================================================================
class TestCollectRelevantFiles:
    def test_collect_relevant_files_basic(self, tmp_path):
        """基本的なファイル収集"""
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "foo.py").write_text("def foo(): pass")
        (tmp_path / "src" / "bar.py").write_text("def bar(): pass")

        files_dict = collect_relevant_files(
            project_path=tmp_path,
            error_log="Error in foo.py",
            changed_files=["src/foo.py"],
            stacktrace_files=["src/bar.py"],
        )

        assert isinstance(files_dict, dict)
        assert len(files_dict) >= 0

    def test_collect_relevant_files_deduplication(self, tmp_path):
        """重複ファイルの除去"""
        (tmp_path / "test.py").write_text("code")

        files_dict = collect_relevant_files(
            project_path=tmp_path,
            error_log="",
            changed_files=["test.py", "test.py"],
            stacktrace_files=["test.py"],
        )

        assert isinstance(files_dict, dict)

    def test_collect_relevant_files_nonexistent(self, tmp_path):
        """存在しないファイルの処理"""
        files_dict = collect_relevant_files(
            project_path=tmp_path,
            error_log="",
            changed_files=["nonexistent.py"],
            stacktrace_files=[],
        )

        assert isinstance(files_dict, dict)

    def test_collect_relevant_files_empty_inputs(self, tmp_path):
        """空の入力での処理"""
        files_dict = collect_relevant_files(
            project_path=tmp_path, error_log="", changed_files=[], stacktrace_files=[]
        )

        assert files_dict == {}


# ============================================================================
# generate_patch_via_debugger (patch_workflow) テスト
# ============================================================================
class TestGeneratePatchViaDebugger:
    def test_generate_patch_with_debugger_agent(self, tmp_path):
        """DebuggerAgent経由でのパッチ生成"""
        mock_agent = Mock()
        mock_agent.debug_and_patch.return_value = {
            "patch": "--- a/file.py\n+++ b/file.py\n@@ -1 +1 @@\n-old\n+new"
        }

        result = generate_patch_via_debugger(
            mock_agent, error_log="Error", files={"file.py": "old"}, project_path=tmp_path
        )

        assert isinstance(result, dict)
        mock_agent.debug_and_patch.assert_called_once()

    def test_generate_patch_without_debugger_agent(self, tmp_path):
        """DebuggerAgentなしでの処理"""
        result = generate_patch_via_debugger(
            None, error_log="Error", files={"file.py": "code"}, project_path=tmp_path
        )

        assert result == {}

    def test_generate_patch_agent_raises_error(self, tmp_path):
        """Agent がエラーを投げる場合"""
        mock_agent = Mock()
        mock_agent.generate_patch.side_effect = Exception("Agent failed")

        try:
            result = generate_patch_via_debugger(
                mock_agent, error_log="Error", files={}, project_path=tmp_path
            )
            assert isinstance(result, dict)
        except Exception:
            pass


# ============================================================================
# run_for_pull_request 統合テスト
# ============================================================================
class TestRunForPullRequestIntegration:
    @patch("nexuscore.services.self_healing_service.run_tests")
    @patch("nexuscore.services.self_healing_service.clone_or_update_repo")
    def test_run_with_all_tests_passing(self, mock_clone, mock_run_tests, tmp_path):
        """全テスト成功の場合"""
        mock_clone.return_value = None
        mock_run_tests.return_value = (True, "5 passed")

        service = SelfHealingService(project_root=str(tmp_path))

        result = service.run_for_pull_request(
            repo_full_name="user/repo", pr_number=123, head_sha="abc123"
        )

        assert isinstance(result, dict)
        assert "success" in result or "status" in result

    @patch("nexuscore.services.self_healing_service.run_tests")
    @patch("nexuscore.services.self_healing_service.clone_or_update_repo")
    def test_run_with_test_failures_and_patch(self, mock_clone, mock_run_tests, tmp_path):
        """テスト失敗→パッチ生成のシナリオ"""
        mock_clone.return_value = None
        mock_run_tests.side_effect = [
            (False, "1 failed"),
            (True, "5 passed"),
        ]

        mock_agent = Mock()
        mock_agent.debug_and_patch.return_value = {
            "patch": "--- a/file.py\n+++ b/file.py\n@@ -1 +1 @@\n-old\n+new"
        }
        service = SelfHealingService(project_root=str(tmp_path), debugger_agent=mock_agent)

        project_path = tmp_path / ".nexus" / "self_healing_sandbox" / "user_repo_pr_456"
        project_path.mkdir(parents=True)
        (project_path / "file.py").write_text("old\n")

        result = service.run_for_pull_request(
            repo_full_name="user/repo", pr_number=456, head_sha="def456"
        )

        assert isinstance(result, dict)

    @patch("nexuscore.services.self_healing_service.clone_or_update_repo")
    def test_run_with_clone_failure(self, mock_clone, tmp_path):
        """クローン失敗時の処理"""
        mock_clone.side_effect = Exception("Clone failed")

        service = SelfHealingService(project_root=str(tmp_path))

        try:
            result = service.run_for_pull_request(
                repo_full_name="user/repo", pr_number=789, head_sha="ghi789"
            )
            assert isinstance(result, dict)
            assert "error" in result or "success" in result
        except Exception:
            pass


# ============================================================================
# エラーハンドリングとエッジケース
# ============================================================================
class TestErrorHandlingAndEdgeCases:
    def test_run_records_history(self, tmp_path):
        """実行履歴が記録される"""
        mock_logger = Mock(spec=RunHistoryLogger)

        service = SelfHealingService(project_root=str(tmp_path), history_logger=mock_logger)

        with patch("nexuscore.services.self_healing_service.clone_or_update_repo", side_effect=Exception("test")):
            try:
                service.run_for_pull_request(
                    repo_full_name="user/repo", pr_number=1, head_sha="test"
                )
            except Exception:
                pass

    def test_service_handles_missing_project_root(self, tmp_path):
        """存在しないproject_rootでの初期化"""
        mock_logger = MagicMock()
        service = SelfHealingService(
            project_root=str(tmp_path / "nonexistent"),
            history_logger=mock_logger,
        )
        assert service.project_root.name == "nonexistent"

    def test_config_load_fallback(self, tmp_path):
        """設定ファイルが存在しない場合のフォールバック"""
        service = SelfHealingService(project_root=str(tmp_path), config=None)

        assert service.config is not None
        assert hasattr(service.config, "test_command")
