"""
CR-003: サンドボックス実行の最低限のセキュリティ強化テスト

リソース制限と危険モジュール検出のテスト。
"""

import os
from unittest.mock import MagicMock, patch

import pytest

from nexuscore.core.errors import SandboxSecurityError
from nexuscore.core.sandbox_executor import (
    _CPU_TIME_LIMIT_SEC,
    _MEMORY_LIMIT_MB,
    SandboxExecutor,
    _apply_resource_limits,
    _check_forbidden_modules,
)


@pytest.fixture
def executor():
    """SandboxExecutor インスタンス"""
    return SandboxExecutor()


def test_apply_resource_limits_on_posix(monkeypatch):
    """POSIX環境でリソース制限が適用されることを確認"""
    monkeypatch.setattr(os, "name", "posix")

    with patch("nexuscore.core.sandbox_executor.resource") as mock_resource:
        mock_resource.RLIMIT_AS = 9  # 仮の値
        mock_resource.RLIMIT_CPU = 0  # 仮の値

        _apply_resource_limits()

        # setrlimit が2回呼ばれることを確認（メモリとCPU）
        assert mock_resource.setrlimit.call_count == 2

        # メモリ制限の確認
        memory_calls = [
            call
            for call in mock_resource.setrlimit.call_args_list
            if call[0][0] == mock_resource.RLIMIT_AS
        ]
        assert len(memory_calls) == 1
        expected_memory = _MEMORY_LIMIT_MB * 1024 * 1024
        assert memory_calls[0][0][1] == (expected_memory, expected_memory)

        # CPU制限の確認
        cpu_calls = [
            call
            for call in mock_resource.setrlimit.call_args_list
            if call[0][0] == mock_resource.RLIMIT_CPU
        ]
        assert len(cpu_calls) == 1
        assert cpu_calls[0][0][1] == (_CPU_TIME_LIMIT_SEC, _CPU_TIME_LIMIT_SEC)


def test_apply_resource_limits_on_non_posix(monkeypatch):
    """非POSIX環境ではリソース制限が適用されないことを確認"""
    monkeypatch.setattr(os, "name", "nt")

    with patch("nexuscore.core.sandbox_executor.resource") as mock_resource:
        _apply_resource_limits()

        # setrlimit が呼ばれないことを確認
        mock_resource.setrlimit.assert_not_called()


def test_apply_resource_limits_when_resource_unavailable(monkeypatch):
    """resourceモジュールが利用できない場合は例外を投げないことを確認"""
    monkeypatch.setattr(os, "name", "posix")
    monkeypatch.setattr("nexuscore.core.sandbox_executor.resource", None)

    # 例外が発生しないことを確認
    _apply_resource_limits()


def test_apply_resource_limits_on_resource_error(monkeypatch):
    """resource.setrlimit がエラーを投げても例外を投げないことを確認"""
    monkeypatch.setattr(os, "name", "posix")

    with patch("nexuscore.core.sandbox_executor.resource") as mock_resource:
        mock_resource.RLIMIT_AS = 9
        mock_resource.RLIMIT_CPU = 0
        mock_resource.setrlimit.side_effect = OSError("Permission denied")

        # 例外が発生しないことを確認
        _apply_resource_limits()


def test_check_forbidden_modules_detects_import_os():
    """import os が検出されることを確認"""
    code = "import os\nprint('hello')"

    with pytest.raises(SandboxSecurityError) as exc_info:
        _check_forbidden_modules(code)

    assert "os" in str(exc_info.value).lower()


def test_check_forbidden_modules_detects_from_import():
    """from os import が検出されることを確認"""
    code = "from os import path\nprint('hello')"

    with pytest.raises(SandboxSecurityError) as exc_info:
        _check_forbidden_modules(code)

    assert "os" in str(exc_info.value).lower()


def test_check_forbidden_modules_detects_import_as():
    """import os as が検出されることを確認"""
    code = "import os as operating_system\nprint('hello')"

    with pytest.raises(SandboxSecurityError) as exc_info:
        _check_forbidden_modules(code)

    assert "os" in str(exc_info.value).lower()


def test_check_forbidden_modules_detects_multiple_modules():
    """複数の禁止モジュールが検出されることを確認"""
    code = "import os\nimport subprocess\nprint('hello')"

    with pytest.raises(SandboxSecurityError) as exc_info:
        _check_forbidden_modules(code)

    error_msg = str(exc_info.value).lower()
    assert "os" in error_msg
    assert "subprocess" in error_msg


def test_check_forbidden_modules_allows_safe_code():
    """安全なコードは通過することを確認"""
    code = "import json\nimport sys\nprint('hello')"

    # 例外が発生しないことを確認
    _check_forbidden_modules(code)


def test_check_forbidden_modules_case_insensitive():
    """大文字小文字を区別しないことを確認"""
    code = "IMPORT OS\nprint('hello')"

    with pytest.raises(SandboxSecurityError):
        _check_forbidden_modules(code)


def test_sandbox_applies_resource_limits_before_execution(monkeypatch, executor):
    """sandbox実行時にリソース制限が適用されることを確認"""
    monkeypatch.setattr(os, "name", "posix")

    with patch("nexuscore.core.sandbox_executor.subprocess.run") as mock_run:
        mock_result = MagicMock()
        mock_result.stdout = "output"
        mock_result.stderr = ""
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        executor.run_in_sandbox(["python", "-c", "print('hello')"])

        # preexec_fn が設定されていることを確認
        assert mock_run.called
        call_kwargs = mock_run.call_args[1]
        assert "preexec_fn" in call_kwargs
        assert call_kwargs["preexec_fn"] is _apply_resource_limits


def test_sandbox_no_preexec_fn_on_non_posix(monkeypatch, executor):
    """非POSIX環境では preexec_fn が設定されないことを確認"""
    monkeypatch.setattr(os, "name", "nt")

    with patch("nexuscore.core.sandbox_executor.subprocess.run") as mock_run:
        mock_result = MagicMock()
        mock_result.stdout = "output"
        mock_result.stderr = ""
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        executor.run_in_sandbox(["python", "-c", "print('hello')"])

        # preexec_fn が設定されていないことを確認
        assert mock_run.called
        call_kwargs = mock_run.call_args[1]
        assert call_kwargs.get("preexec_fn") is None
