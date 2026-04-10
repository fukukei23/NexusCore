import json
import os
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from nexuscore.gradio_app import revision_loop


def test_save_and_read_file(tmp_path):
    target = tmp_path / "file.txt"
    revision_loop.save_file(str(target), "hello")
    assert revision_loop.read_file(str(target)) == "hello"


def test_generate_prompt_contains_sections():
    prompt = revision_loop.generate_prompt(
        "main.py",
        "utils.py",
        "v1",
        "history",
        "tests failing",
        "extra instruction",
    )
    assert "main.py" in prompt
    assert "extra instruction" in prompt


def test_extract_code_and_reason():
    response = """【修正版コード】
```python
print("ok")
```
【修正理由・要約】
理由です
"""
    code, reason = revision_loop.extract_code_and_reason(response)
    assert 'print("ok")' in code
    assert "理由" in reason


def test_run_pytest_success(monkeypatch, tmp_path):
    revision_loop.TEST_FILE = str(tmp_path / "test_sample.py")
    revision_loop.RESULT_LOG = str(tmp_path / "result.log")

    def fake_run(cmd, **kwargs):
        assert cmd == ["pytest", revision_loop.TEST_FILE]
        return SimpleNamespace(stdout="ok", stderr="err", returncode=0)

    monkeypatch.setattr(revision_loop.subprocess, "run", fake_run)
    output = revision_loop.run_pytest()
    assert "ok" in output and "err" in output


def test_save_patch_history(tmp_path, monkeypatch):
    log_file = tmp_path / "result.log"
    log_file.write_text("pytest log", encoding="utf-8")
    revision_loop.RESULT_LOG = str(log_file)
    revision_loop.HISTORY_DIR = str(tmp_path / "patch_history")
    (tmp_path / "patch_history").mkdir(parents=True, exist_ok=True)

    revision_loop.save_patch_history("print('ok')", "reason", "prompt")

    files = list((tmp_path / "patch_history").glob("patch_*.json"))
    assert len(files) == 1
    data = json.loads(files[0].read_text(encoding="utf-8"))
    assert data["code"] == "print('ok')"
    assert data["reason"] == "reason"


class TestGetClient:
    def test_returns_cached_client(self, monkeypatch):
        mock_client = MagicMock()
        monkeypatch.setattr(revision_loop, "_client", mock_client)
        result = revision_loop.get_client()
        assert result is mock_client

    def test_raises_when_openai_missing(self, monkeypatch):
        monkeypatch.setattr(revision_loop, "_client", None)
        monkeypatch.setattr(revision_loop, "OpenAI", None)
        with pytest.raises(RuntimeError, match="openai SDK"):
            revision_loop.get_client()

    def test_raises_when_no_api_key(self, monkeypatch):
        monkeypatch.setattr(revision_loop, "_client", None)
        monkeypatch.setattr(revision_loop, "OpenAI", MagicMock)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
            revision_loop.get_client()

    def test_creates_client_with_api_key(self, monkeypatch):
        mock_openai = MagicMock()
        mock_instance = MagicMock()
        mock_openai.return_value = mock_instance
        monkeypatch.setattr(revision_loop, "_client", None)
        monkeypatch.setattr(revision_loop, "OpenAI", mock_openai)
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        result = revision_loop.get_client()
        assert result is mock_instance
        mock_openai.assert_called_once_with(api_key="test-key")
        monkeypatch.setattr(revision_loop, "_client", None)  # cleanup


class TestRunPytestException:
    def test_subprocess_error(self, monkeypatch):
        def raise_fn(*args, **kwargs):
            raise FileNotFoundError("no pytest")
        monkeypatch.setattr(revision_loop.subprocess, "run", raise_fn)
        output = revision_loop.run_pytest()
        assert "failed" in output


class TestCallGpt:
    def test_call_gpt_success(self, monkeypatch):
        mock_client = MagicMock()
        mock_msg = MagicMock()
        mock_msg.content = "  response text  "
        mock_choice = MagicMock()
        mock_choice.message = mock_msg
        mock_rsp = MagicMock()
        mock_rsp.choices = [mock_choice]
        mock_client.chat.completions.create.return_value = mock_rsp
        monkeypatch.setattr(revision_loop, "_client", mock_client)
        result = revision_loop.call_gpt("test prompt")
        assert result == "response text"


class TestLaunchRevisionUi:
    def test_launch_revision_ui_creates_row(self):
        gr = pytest.importorskip("gradio")
        result = revision_loop.launch_revision_ui()
        # Returns None (gr.Row context manager), but should not raise
        assert result is None or isinstance(result, gr.Row)
