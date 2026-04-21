"""
tester.py 包括テスト
save_and_test_code() の正常系・エラー系・定数をカバー
"""
from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest

from nexuscore.modules.tester import RESULT_LOG, SAMPLE_FILE, SANDBOX_DIR, TEST_FILE, save_and_test_code


class TestTesterConstants:
    def test_sandbox_dir_is_absolute(self):
        assert os.path.isabs(SANDBOX_DIR)

    def test_sample_file_is_in_sandbox_dir(self):
        assert SAMPLE_FILE.startswith(SANDBOX_DIR)

    def test_test_file_is_in_sandbox_dir(self):
        assert TEST_FILE.startswith(SANDBOX_DIR)

    def test_result_log_is_in_sandbox_dir(self):
        assert RESULT_LOG.startswith(SANDBOX_DIR)


class TestSaveAndTestCode:
    @patch("nexuscore.modules.tester.subprocess.run")
    def test_returns_stdout_on_success(self, mock_run, tmp_path, monkeypatch):
        monkeypatch.setattr("nexuscore.modules.tester.SANDBOX_DIR", str(tmp_path))
        monkeypatch.setattr("nexuscore.modules.tester.SAMPLE_FILE", str(tmp_path / "sample.py"))
        monkeypatch.setattr("nexuscore.modules.tester.TEST_FILE", str(tmp_path / "test_sample.py"))
        monkeypatch.setattr("nexuscore.modules.tester.RESULT_LOG", str(tmp_path / "result.log"))

        mock_run.return_value = MagicMock(stdout="5 passed", stderr="")
        result = save_and_test_code("def foo():\n    pass")
        assert "5 passed" in result

    @patch("nexuscore.modules.tester.subprocess.run")
    def test_creates_sample_file_with_given_code(self, mock_run, tmp_path, monkeypatch):
        sample = str(tmp_path / "sample.py")
        monkeypatch.setattr("nexuscore.modules.tester.SANDBOX_DIR", str(tmp_path))
        monkeypatch.setattr("nexuscore.modules.tester.SAMPLE_FILE", sample)
        monkeypatch.setattr("nexuscore.modules.tester.TEST_FILE", str(tmp_path / "test_sample.py"))
        monkeypatch.setattr("nexuscore.modules.tester.RESULT_LOG", str(tmp_path / "result.log"))

        mock_run.return_value = MagicMock(stdout="ok", stderr="")
        code = "x = 42\nprint(x)"
        save_and_test_code(code)

        assert os.path.exists(sample)
        with open(sample) as f:
            assert f.read() == code

    @patch("nexuscore.modules.tester.subprocess.run")
    def test_auto_creates_test_file_when_missing(self, mock_run, tmp_path, monkeypatch):
        test_file = str(tmp_path / "test_sample.py")
        monkeypatch.setattr("nexuscore.modules.tester.SANDBOX_DIR", str(tmp_path))
        monkeypatch.setattr("nexuscore.modules.tester.SAMPLE_FILE", str(tmp_path / "sample.py"))
        monkeypatch.setattr("nexuscore.modules.tester.TEST_FILE", test_file)
        monkeypatch.setattr("nexuscore.modules.tester.RESULT_LOG", str(tmp_path / "result.log"))

        mock_run.return_value = MagicMock(stdout="ok", stderr="")
        save_and_test_code("x = 1")

        assert os.path.exists(test_file)
        with open(test_file) as f:
            content = f.read()
        assert "test_dummy" in content

    @patch("nexuscore.modules.tester.subprocess.run")
    def test_does_not_overwrite_existing_test_file(self, mock_run, tmp_path, monkeypatch):
        test_file = str(tmp_path / "test_sample.py")
        with open(test_file, "w") as f:
            f.write("# existing test")

        monkeypatch.setattr("nexuscore.modules.tester.SANDBOX_DIR", str(tmp_path))
        monkeypatch.setattr("nexuscore.modules.tester.SAMPLE_FILE", str(tmp_path / "sample.py"))
        monkeypatch.setattr("nexuscore.modules.tester.TEST_FILE", test_file)
        monkeypatch.setattr("nexuscore.modules.tester.RESULT_LOG", str(tmp_path / "result.log"))

        mock_run.return_value = MagicMock(stdout="ok", stderr="")
        save_and_test_code("x = 1")

        with open(test_file) as f:
            assert f.read() == "# existing test"

    @patch("nexuscore.modules.tester.subprocess.run")
    def test_writes_combined_output_to_result_log(self, mock_run, tmp_path, monkeypatch):
        log_file = str(tmp_path / "result.log")
        monkeypatch.setattr("nexuscore.modules.tester.SANDBOX_DIR", str(tmp_path))
        monkeypatch.setattr("nexuscore.modules.tester.SAMPLE_FILE", str(tmp_path / "sample.py"))
        monkeypatch.setattr("nexuscore.modules.tester.TEST_FILE", str(tmp_path / "test_sample.py"))
        monkeypatch.setattr("nexuscore.modules.tester.RESULT_LOG", log_file)

        mock_run.return_value = MagicMock(stdout="STDOUT_HERE", stderr="STDERR_HERE")
        save_and_test_code("x = 1")

        assert os.path.exists(log_file)
        with open(log_file) as f:
            log_content = f.read()
        assert "STDOUT_HERE" in log_content

    @patch("nexuscore.modules.tester.subprocess.run")
    def test_returns_combined_stdout_and_stderr(self, mock_run, tmp_path, monkeypatch):
        monkeypatch.setattr("nexuscore.modules.tester.SANDBOX_DIR", str(tmp_path))
        monkeypatch.setattr("nexuscore.modules.tester.SAMPLE_FILE", str(tmp_path / "sample.py"))
        monkeypatch.setattr("nexuscore.modules.tester.TEST_FILE", str(tmp_path / "test_sample.py"))
        monkeypatch.setattr("nexuscore.modules.tester.RESULT_LOG", str(tmp_path / "result.log"))

        mock_run.return_value = MagicMock(stdout="STDOUT_OUTPUT", stderr="STDERR_OUTPUT")
        result = save_and_test_code("x = 1")

        assert "STDOUT_OUTPUT" in result
        assert "STDERR_OUTPUT" in result

    @patch(
        "nexuscore.modules.tester.subprocess.run",
        side_effect=OSError("pytest not found"),
    )
    def test_subprocess_exception_returns_warning_string(self, mock_run, tmp_path, monkeypatch):
        monkeypatch.setattr("nexuscore.modules.tester.SANDBOX_DIR", str(tmp_path))
        monkeypatch.setattr("nexuscore.modules.tester.SAMPLE_FILE", str(tmp_path / "sample.py"))
        monkeypatch.setattr("nexuscore.modules.tester.TEST_FILE", str(tmp_path / "test_sample.py"))
        monkeypatch.setattr("nexuscore.modules.tester.RESULT_LOG", str(tmp_path / "result.log"))

        result = save_and_test_code("x = 1")
        assert "⚠️" in result or "Test failed" in result

    @patch("nexuscore.modules.tester.subprocess.run")
    def test_calls_pytest_with_test_file(self, mock_run, tmp_path, monkeypatch):
        test_file = str(tmp_path / "test_sample.py")
        monkeypatch.setattr("nexuscore.modules.tester.SANDBOX_DIR", str(tmp_path))
        monkeypatch.setattr("nexuscore.modules.tester.SAMPLE_FILE", str(tmp_path / "sample.py"))
        monkeypatch.setattr("nexuscore.modules.tester.TEST_FILE", test_file)
        monkeypatch.setattr("nexuscore.modules.tester.RESULT_LOG", str(tmp_path / "result.log"))

        mock_run.return_value = MagicMock(stdout="ok", stderr="")
        save_and_test_code("x = 1")

        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert "pytest" in call_args
        assert test_file in call_args
