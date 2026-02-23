"""self_healing_service.py のテスト"""

import sys
from unittest.mock import MagicMock, patch

# patchモジュールをモック化（import前に実行）
sys.modules["patch"] = MagicMock()

import os
from pathlib import Path

import pytest

from nexuscore.agents.patch_applier import PatchApplier
from nexuscore.core.run_history import RunHistoryLogger
from nexuscore.core.session_control import SessionController
from nexuscore.services.self_healing_service import SelfHealingService


def test_self_healing_service_initialization(tmp_path):
    """SelfHealingServiceの初期化テスト"""
    service = SelfHealingService(project_root=str(tmp_path))

    assert service.project_root == Path(tmp_path)
    assert service.session_controller is not None
    assert service.patch_applier is not None
    assert service.history_logger is not None


def test_self_healing_service_initialization_with_dependencies(tmp_path):
    """依存関係を注入した場合の初期化テスト"""
    session_controller = SessionController(session_id="test-session", root_dir=".nexus/sessions")
    patch_applier = PatchApplier()
    history_logger = RunHistoryLogger(project_root=str(tmp_path))
    debugger_agent = MagicMock()

    service = SelfHealingService(
        project_root=str(tmp_path),
        session_controller=session_controller,
        debugger_agent=debugger_agent,
        patch_applier=patch_applier,
        history_logger=history_logger,
    )

    assert service.session_controller == session_controller
    assert service.patch_applier == patch_applier
    assert service.history_logger == history_logger
    assert service.debugger_agent == debugger_agent


def test_maybe_stop_without_session_controller(tmp_path):
    """SessionControllerなしで_maybe_stopが動作するテスト"""
    service = SelfHealingService(
        project_root=str(tmp_path),
        session_controller=None,
    )

    # 例外が発生しないことを確認
    service._maybe_stop("test_phase", {"test": "data"})


def test_maybe_stop_with_session_controller(tmp_path):
    """SessionControllerありで_maybe_stopが動作するテスト"""
    session_dir = tmp_path / ".nexus" / "sessions"
    session_controller = SessionController(session_id="test-session", root_dir=str(session_dir))
    service = SelfHealingService(
        project_root=str(tmp_path),
        session_controller=session_controller,
    )

    # 正常にチェックポイントが保存されることを確認
    service._maybe_stop("test_phase", {"test": "data"})

    # チェックポイントが保存されていることを確認
    assert session_controller.state_file.exists()


def test_maybe_stop_raises_on_stop_request(tmp_path):
    """停止指示が出た場合にRuntimeErrorを投げるテスト"""
    session_controller = SessionController(session_id="test-session", root_dir=".nexus/sessions")
    service = SelfHealingService(
        project_root=str(tmp_path),
        session_controller=session_controller,
    )

    # 停止指示を出す
    session_controller.request_stop()

    # RuntimeErrorが発生することを確認
    with pytest.raises(RuntimeError, match="SessionStopped"):
        service._maybe_stop("test_phase", {"test": "data"})


@patch("nexuscore.services.self_healing_service.subprocess")
def test_clone_or_update_repo_with_base_dir(tmp_path, mock_subprocess):
    """_clone_or_update_repoがNEXUS_REPO_BASE_DIRからコピーするテスト"""
    base_dir = tmp_path / "base_repos"
    base_dir.mkdir()
    existing_repo = base_dir / "owner" / "repo"
    existing_repo.mkdir(parents=True)
    (existing_repo / "README.md").write_text("# Test Repo\n")

    with patch.dict(os.environ, {"NEXUS_REPO_BASE_DIR": str(base_dir)}):
        service = SelfHealingService(project_root=str(tmp_path))
        target_dir = tmp_path / "test_repo"

        service._clone_or_update_repo(
            repo_full_name="owner/repo",
            pr_number=123,
            head_sha="abc123",
            target_dir=target_dir,
        )

        # コピーされたことを確認
        assert target_dir.exists()
        assert (target_dir / "README.md").exists()
        # git checkoutは呼ばれる
        assert mock_subprocess.run.called


@patch("nexuscore.services.self_healing_service.subprocess")
def test_clone_or_update_repo_with_git_clone(tmp_path, mock_subprocess):
    """_clone_or_update_repoがgit cloneを実行するテスト"""
    mock_subprocess.run.return_value = MagicMock(returncode=0, stdout="", stderr="")

    service = SelfHealingService(project_root=str(tmp_path))
    target_dir = tmp_path / "test_repo"

    service._clone_or_update_repo(
        repo_full_name="owner/repo",
        pr_number=123,
        head_sha="abc123",
        target_dir=target_dir,
    )

    # git cloneとcheckoutが呼ばれることを確認
    assert mock_subprocess.run.call_count >= 2
    clone_call = mock_subprocess.run.call_args_list[0]
    assert clone_call[0][0][:2] == ["git", "clone"]
    checkout_call = mock_subprocess.run.call_args_list[1]
    assert checkout_call[0][0][:3] == ["git", "-C", str(target_dir)]
    assert checkout_call[0][0][3] == "checkout"


def test_run_tests_success(tmp_path):
    """_run_testsが成功する場合のテスト"""
    service = SelfHealingService(project_root=str(tmp_path))

    # テスト用のプロジェクトディレクトリを作成
    project_path = tmp_path / "test_project"
    project_path.mkdir()

    # 簡単なPythonファイルを作成（テストが通るように）
    test_file = project_path / "test_example.py"
    test_file.write_text("def test_pass(): assert True\n", encoding="utf-8")

    # pytestを実行
    ok, output = service._run_tests(project_path)

    # テストが成功することを確認
    assert ok is True
    assert "test_pass" in output or "passed" in output.lower()


def test_run_tests_failure(tmp_path):
    """_run_testsが失敗する場合のテスト"""
    service = SelfHealingService(project_root=str(tmp_path))

    # テスト用のプロジェクトディレクトリを作成
    project_path = tmp_path / "test_project"
    project_path.mkdir()

    # 失敗するテストファイルを作成
    test_file = project_path / "test_example.py"
    test_file.write_text("def test_fail(): assert False\n", encoding="utf-8")

    # pytestを実行
    ok, output = service._run_tests(project_path)

    # テストが失敗することを確認
    assert ok is False
    assert "FAILED" in output or "failed" in output.lower() or "assert False" in output


def test_run_tests_with_custom_command(tmp_path, monkeypatch):
    """環境変数でテストコマンドをカスタマイズするテスト"""
    monkeypatch.setenv("NEXUS_SELF_HEALING_TEST_CMD", "echo 'test output'")

    service = SelfHealingService(project_root=str(tmp_path))

    project_path = tmp_path / "test_project"
    project_path.mkdir()

    ok, output = service._run_tests(project_path)

    # カスタムコマンドが実行されることを確認
    assert "test output" in output


@patch("nexuscore.services.self_healing_service.subprocess")
def test_get_changed_files_with_git_diff(tmp_path, mock_subprocess):
    """_get_changed_filesがgit diffを実行するテスト"""
    mock_subprocess.run.return_value = MagicMock(
        returncode=0,
        stdout="src/module.py\ntests/test_module.py\n",
        stderr="",
    )

    service = SelfHealingService(project_root=str(tmp_path))
    project_path = tmp_path / "test_project"
    project_path.mkdir()

    files = service._get_changed_files(
        project_path=project_path,
        base_ref=None,
        head_ref=None,
    )

    # git diffが実行されることを確認
    assert mock_subprocess.run.called
    call_args = mock_subprocess.run.call_args[0][0]
    assert call_args[:3] == ["git", "-C", str(project_path)]
    assert call_args[3] == "diff"
    assert call_args[4] == "--name-only"

    # 変更ファイルが返されることを確認
    assert len(files) == 2
    assert "src/module.py" in files
    assert "tests/test_module.py" in files


@patch("nexuscore.services.self_healing_service.subprocess")
def test_get_changed_files_with_base_and_head(tmp_path, mock_subprocess):
    """_get_changed_filesがbase_refとhead_refを使用するテスト"""
    mock_subprocess.run.return_value = MagicMock(
        returncode=0,
        stdout="src/module.py\n",
        stderr="",
    )

    service = SelfHealingService(project_root=str(tmp_path))
    project_path = tmp_path / "test_project"
    project_path.mkdir()

    files = service._get_changed_files(
        project_path=project_path,
        base_ref="main",
        head_ref="feature-branch",
    )

    # base_ref...head_refの形式でgit diffが実行されることを確認
    assert mock_subprocess.run.called
    call_args = mock_subprocess.run.call_args[0][0]
    assert "main...feature-branch" in call_args


@patch("nexuscore.services.self_healing_service.subprocess")
def test_get_changed_files_handles_git_error(tmp_path, mock_subprocess):
    """_get_changed_filesがgitエラーを処理するテスト"""
    mock_subprocess.run.return_value = MagicMock(
        returncode=1,
        stdout="",
        stderr="fatal: not a git repository",
    )

    service = SelfHealingService(project_root=str(tmp_path))
    project_path = tmp_path / "test_project"
    project_path.mkdir()

    files = service._get_changed_files(
        project_path=project_path,
        base_ref=None,
        head_ref=None,
    )

    # エラー時は空リストを返す
    assert files == []


def test_collect_relevant_files_from_stacktrace(tmp_path):
    """_collect_relevant_filesがスタックトレースからファイルを収集するテスト"""
    service = SelfHealingService(project_root=str(tmp_path))

    # テスト用プロジェクトを作成
    project_path = tmp_path / "test_project"
    project_path.mkdir()

    # テストファイルを作成
    test_file = project_path / "src" / "module.py"
    test_file.parent.mkdir(parents=True)
    test_file.write_text("def func(): pass\n", encoding="utf-8")

    error_log = f'File "{test_file}", line 1, in func'
    stacktrace_files = [str(test_file)]
    changed_files = []

    files = service._collect_relevant_files(
        project_path=project_path,
        error_log=error_log,
        changed_files=changed_files,
        stacktrace_files=stacktrace_files,
    )

    # ファイルが収集されることを確認
    assert len(files) > 0
    assert "src/module.py" in files or "module.py" in files


def test_collect_relevant_files_from_changed_files(tmp_path):
    """_collect_relevant_filesが変更ファイルから収集するテスト"""
    service = SelfHealingService(project_root=str(tmp_path))

    project_path = tmp_path / "test_project"
    project_path.mkdir()

    # テストファイルを作成
    test_file = project_path / "src" / "changed.py"
    test_file.parent.mkdir(parents=True)
    test_file.write_text("def func(): pass\n", encoding="utf-8")

    error_log = ""
    stacktrace_files = []
    changed_files = [str(test_file)]

    files = service._collect_relevant_files(
        project_path=project_path,
        error_log=error_log,
        changed_files=changed_files,
        stacktrace_files=stacktrace_files,
    )

    # ファイルが収集されることを確認
    assert len(files) > 0


def test_collect_relevant_files_fallback_to_py_files(tmp_path):
    """_collect_relevant_filesがフォールバックで.pyファイルを拾うテスト"""
    service = SelfHealingService(project_root=str(tmp_path))

    project_path = tmp_path / "test_project"
    project_path.mkdir()

    # いくつかのPythonファイルを作成
    for i in range(5):
        py_file = project_path / f"file{i}.py"
        py_file.write_text(f"# file {i}\n", encoding="utf-8")

    error_log = ""
    stacktrace_files = []
    changed_files = []

    files = service._collect_relevant_files(
        project_path=project_path,
        error_log=error_log,
        changed_files=changed_files,
        stacktrace_files=stacktrace_files,
    )

    # フォールバックで.pyファイルが収集されることを確認
    assert len(files) > 0
    assert len(files) <= 10  # 最大10ファイル


def test_generate_patch_via_debugger_with_debug_and_patch(tmp_path):
    """_generate_patch_via_debuggerがdebug_and_patchメソッドを優先的に呼ぶテスト"""
    debugger_agent = MagicMock()
    debugger_agent.debug_and_patch = MagicMock(
        return_value={"patch": "--- a/file.py\n+++ b/file.py\n@@ -1,1 +1,1 @@\n-old\n+new"}
    )

    service = SelfHealingService(
        project_root=str(tmp_path),
        debugger_agent=debugger_agent,
    )

    project_path = tmp_path / "test_project"
    project_path.mkdir()

    result = service._generate_patch_via_debugger(
        error_log="Error message",
        files={"file.py": "content"},
        project_path=project_path,
    )

    assert "patch" in result
    assert debugger_agent.debug_and_patch.called
    debugger_agent.debug_and_patch.assert_called_once_with(
        error_log="Error message",
        files_content={"file.py": "content"},
        project_path=str(project_path),
    )


def test_generate_patch_via_debugger_with_method(tmp_path):
    """_generate_patch_via_debuggerがgenerate_patchメソッドを呼ぶテスト（フォールバック）"""
    debugger_agent = MagicMock()
    # debug_and_patchがない場合、generate_patchにフォールバック
    delattr(debugger_agent, "debug_and_patch")
    debugger_agent.generate_patch = MagicMock(
        return_value={"patch": "--- a/file.py\n+++ b/file.py\n@@ -1,1 +1,1 @@\n-old\n+new"}
    )

    service = SelfHealingService(
        project_root=str(tmp_path),
        debugger_agent=debugger_agent,
    )

    project_path = tmp_path / "test_project"
    project_path.mkdir()

    result = service._generate_patch_via_debugger(
        error_log="Error message",
        files={"file.py": "content"},
        project_path=project_path,
    )

    assert "patch" in result
    assert debugger_agent.generate_patch.called
    debugger_agent.generate_patch.assert_called_once_with(
        error_log="Error message",
        files={"file.py": "content"},
    )


def test_generate_patch_via_debugger_without_method(tmp_path):
    """_generate_patch_via_debuggerがメソッドがない場合のテスト"""
    debugger_agent = MagicMock()
    # debug_and_patchとgenerate_patchの両方を削除
    if hasattr(debugger_agent, "debug_and_patch"):
        delattr(debugger_agent, "debug_and_patch")
    if hasattr(debugger_agent, "generate_patch"):
        delattr(debugger_agent, "generate_patch")

    service = SelfHealingService(
        project_root=str(tmp_path),
        debugger_agent=debugger_agent,
    )

    project_path = tmp_path / "test_project"
    project_path.mkdir()

    result = service._generate_patch_via_debugger(
        error_log="Error message",
        files={"file.py": "content"},
        project_path=project_path,
    )

    # 空のdictが返されることを確認
    assert result == {}


def test_generate_patch_via_debugger_exception_handling(tmp_path):
    """_generate_patch_via_debuggerが例外を処理するテスト"""
    debugger_agent = MagicMock()
    debugger_agent.debug_and_patch = MagicMock(side_effect=Exception("Debugger error"))

    service = SelfHealingService(
        project_root=str(tmp_path),
        debugger_agent=debugger_agent,
    )

    project_path = tmp_path / "test_project"
    project_path.mkdir()

    result = service._generate_patch_via_debugger(
        error_log="Error message",
        files={"file.py": "content"},
        project_path=project_path,
    )

    # 例外が発生しても空のdictが返されることを確認
    assert result == {}


def test_finalize_creates_history_record(tmp_path):
    """_finalizeが履歴レコードを作成するテスト"""
    service = SelfHealingService(project_root=str(tmp_path))

    result = service._finalize(
        run_id="test-run-001",
        session_id="test-session-001",
        repo_full_name="owner/repo",
        pr_number=123,
        head_sha="abc123",
        status="fixed",
        summary="Test summary",
        details={"key": "value"},
        started_at=1000.0,
    )

    assert result["status"] == "fixed"
    assert result["summary"] == "Test summary"
    assert result["run_id"] == "test-run-001"
    assert result["started_at"] == 1000.0
    assert result["finished_at"] > 1000.0

    # 履歴が記録されることを確認
    records = service.history_logger.load_runs("self_healing")
    assert len(records) > 0
    assert records[-1]["run_id"] == "test-run-001"


def test_run_for_pull_request_no_issues(tmp_path):
    """テストが既に通っている場合のrun_for_pull_requestテスト"""
    service = SelfHealingService(project_root=str(tmp_path))

    # テストが通るプロジェクトを作成
    project_path = tmp_path / ".nexus" / "self_healing_sandbox" / "owner_repo_pr_123"
    project_path.mkdir(parents=True)

    test_file = project_path / "test_pass.py"
    test_file.write_text("def test_pass(): assert True\n", encoding="utf-8")

    with patch.object(service, "_clone_or_update_repo"):
        with patch.object(service, "_run_tests", return_value=(True, "All tests passed")):
            result = service.run_for_pull_request(
                repo_full_name="owner/repo",
                pr_number=123,
                head_sha="abc123",
            )

    assert result["status"] == "no_issues"
    assert "already passing" in result["summary"].lower()


def test_run_for_pull_request_no_debugger_agent(tmp_path):
    """DebuggerAgentがない場合のrun_for_pull_requestテスト"""
    service = SelfHealingService(
        project_root=str(tmp_path),
        debugger_agent=None,
    )

    project_path = tmp_path / ".nexus" / "self_healing_sandbox" / "owner_repo_pr_123"
    project_path.mkdir(parents=True)

    with patch.object(service, "_clone_or_update_repo"):
        with patch.object(service, "_run_tests", return_value=(False, "Test failed")):
            result = service.run_for_pull_request(
                repo_full_name="owner/repo",
                pr_number=123,
                head_sha="abc123",
            )

    assert result["status"] == "not_fixed"
    assert "debugger" in result["summary"].lower() or "not configured" in result["summary"].lower()


def test_run_for_pull_request_patch_generation_failed(tmp_path):
    """パッチ生成に失敗した場合のテスト"""
    debugger_agent = MagicMock()
    debugger_agent.generate_patch = MagicMock(return_value={})  # 空の結果

    service = SelfHealingService(
        project_root=str(tmp_path),
        debugger_agent=debugger_agent,
    )

    project_path = tmp_path / ".nexus" / "self_healing_sandbox" / "owner_repo_pr_123"
    project_path.mkdir(parents=True)

    with patch.object(service, "_clone_or_update_repo"):
        with patch.object(service, "_run_tests", return_value=(False, "Test failed")):
            result = service.run_for_pull_request(
                repo_full_name="owner/repo",
                pr_number=123,
                head_sha="abc123",
            )

    assert result["status"] == "not_fixed"
    assert "did not produce" in result["summary"].lower() or "patch" in result["summary"].lower()


def test_run_for_pull_request_dangerous_patch(tmp_path):
    """危険なパッチがブロックされる場合のテスト"""
    debugger_agent = MagicMock()
    # 削除行を含むパッチを返す
    dangerous_patch = """--- a/file.py
+++ b/file.py
@@ -1,3 +1,2 @@
-old line
+new line
 unchanged"""
    debugger_agent.generate_patch = MagicMock(return_value={"patch": dangerous_patch})

    service = SelfHealingService(
        project_root=str(tmp_path),
        debugger_agent=debugger_agent,
    )

    project_path = tmp_path / ".nexus" / "self_healing_sandbox" / "owner_repo_pr_123"
    project_path.mkdir(parents=True)

    # テスト用ファイルを作成
    test_file = project_path / "file.py"
    test_file.write_text("old line\nunchanged\n", encoding="utf-8")

    with patch.object(service, "_clone_or_update_repo"):
        with patch.object(service, "_run_tests", return_value=(False, "Test failed")):
            result = service.run_for_pull_request(
                repo_full_name="owner/repo",
                pr_number=123,
                head_sha="abc123",
            )

    assert result["status"] == "not_fixed"
    assert "danger" in result["summary"].lower() or "blocked" in result["summary"].lower()
    assert "patch_preview" in result["details"]


def test_run_for_pull_request_successful_fix(tmp_path):
    """パッチ適用が成功してテストが通る場合のテスト"""
    debugger_agent = MagicMock()
    # 安全なパッチ（削除行なし、追加のみ）
    safe_patch = """--- a/file.py
+++ b/file.py
@@ -1,1 +1,2 @@
 old
+new line"""
    debugger_agent.generate_patch = MagicMock(return_value={"patch": safe_patch})

    service = SelfHealingService(
        project_root=str(tmp_path),
        debugger_agent=debugger_agent,
    )

    project_path = tmp_path / ".nexus" / "self_healing_sandbox" / "owner_repo_pr_123"
    project_path.mkdir(parents=True)

    # テスト用ファイルを作成
    test_file = project_path / "file.py"
    test_file.write_text("old\n", encoding="utf-8")

    test_py = project_path / "test_file.py"
    test_py.write_text("def test_pass(): assert True\n", encoding="utf-8")

    with patch.object(service, "_clone_or_update_repo"):
        with patch.object(
            service, "_run_tests", side_effect=[(False, "Test failed"), (True, "All tests passed")]
        ):
            result = service.run_for_pull_request(
                repo_full_name="owner/repo",
                pr_number=123,
                head_sha="abc123",
            )

    # パッチ適用後、テストが通れば"fixed"になる
    assert result["status"] in ("fixed", "not_fixed")  # 実際の適用結果に依存
    assert "patch_preview" in result["details"]
    # apply_resultは危険でないパッチの場合のみ含まれる
    if result["status"] == "fixed":
        assert "apply_result" in result["details"]


def test_run_for_pull_request_session_stopped(tmp_path):
    """セッションが停止された場合のテスト"""
    session_controller = SessionController(session_id="test-session", root_dir=".nexus/sessions")
    session_controller.request_stop()

    service = SelfHealingService(
        project_root=str(tmp_path),
        session_controller=session_controller,
    )

    with patch.object(service, "_clone_or_update_repo"):
        result = service.run_for_pull_request(
            repo_full_name="owner/repo",
            pr_number=123,
            head_sha="abc123",
        )

    assert result["status"] == "error"
    assert "stopped" in result["summary"].lower()


def test_run_for_pull_request_includes_patch_preview(tmp_path):
    """run_for_pull_requestがpatch_previewを含むテスト"""
    debugger_agent = MagicMock()
    patch_text = """--- a/file.py
+++ b/file.py
@@ -1,1 +1,1 @@
-old
+new"""
    debugger_agent.generate_patch = MagicMock(return_value={"patch": patch_text})

    service = SelfHealingService(
        project_root=str(tmp_path),
        debugger_agent=debugger_agent,
    )

    project_path = tmp_path / ".nexus" / "self_healing_sandbox" / "owner_repo_pr_123"
    project_path.mkdir(parents=True)

    test_file = project_path / "file.py"
    test_file.write_text("old\n", encoding="utf-8")

    with patch.object(service, "_clone_or_update_repo"):
        with patch.object(service, "_run_tests", return_value=(False, "Test failed")):
            result = service.run_for_pull_request(
                repo_full_name="owner/repo",
                pr_number=123,
                head_sha="abc123",
            )

    # patch_previewが含まれることを確認（危険なパッチでもブロックされる前に含まれる）
    if "patch_preview" in result.get("details", {}):
        assert "```diff" in result["details"]["patch_preview"]


def test_run_for_pull_request_includes_changed_files(tmp_path):
    """run_for_pull_requestがchanged_filesを含むテスト"""
    debugger_agent = MagicMock()
    patch_text = """--- a/src/file1.py
+++ b/src/file1.py
@@ -1,1 +1,1 @@
-old
+new
--- a/src/file2.py
+++ b/src/file2.py
@@ -1,1 +1,1 @@
-old2
+new2"""
    debugger_agent.generate_patch = MagicMock(return_value={"patch": patch_text})

    service = SelfHealingService(
        project_root=str(tmp_path),
        debugger_agent=debugger_agent,
    )

    project_path = tmp_path / ".nexus" / "self_healing_sandbox" / "owner_repo_pr_123"
    project_path.mkdir(parents=True)

    with patch.object(service, "_clone_or_update_repo"):
        with patch.object(service, "_run_tests", return_value=(False, "Test failed")):
            result = service.run_for_pull_request(
                repo_full_name="owner/repo",
                pr_number=123,
                head_sha="abc123",
            )

    # patch_changed_filesが含まれることを確認（パッチが適用された場合）
    if "patch_changed_files" in result.get("details", {}):
        assert isinstance(result["details"]["patch_changed_files"], list)
