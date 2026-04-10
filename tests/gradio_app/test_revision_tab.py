"""
Tests for nexuscore.gradio_app.revision_tab module.
"""

import json
import os
from unittest.mock import MagicMock, patch

import pytest

from nexuscore.gradio_app import revision_tab


class TestNowTag:
    def test_format(self):
        result = revision_tab._now_tag()
        assert len(result) == 15
        assert "_" in result
        parts = result.split("_")
        assert len(parts[0]) == 8  # YYYYMMDD
        assert len(parts[1]) == 6  # HHMMSS


class TestReadFile:
    def test_read_existing(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("hello", encoding="utf-8")
        assert revision_tab.read_file(str(f)) == "hello"

    def test_read_nonexistent(self, tmp_path):
        assert revision_tab.read_file(str(tmp_path / "nope.txt")) == ""


class TestSaveFile:
    def test_creates_parent_dirs(self, tmp_path):
        target = tmp_path / "a" / "b" / "file.txt"
        revision_tab.save_file(str(target), "content")
        assert target.read_text(encoding="utf-8") == "content"

    def test_overwrites(self, tmp_path):
        target = tmp_path / "f.txt"
        revision_tab.save_file(str(target), "first")
        revision_tab.save_file(str(target), "second")
        assert target.read_text(encoding="utf-8") == "second"


class TestSavePatchHistory:
    def test_appends(self, tmp_path):
        history_file = str(tmp_path / "history.txt")
        with patch.object(revision_tab, "HISTORY_TXT", history_file):
            revision_tab.save_patch_history("code1", "reason1", "prompt1")
            revision_tab.save_patch_history("code2", "reason2", "prompt2")
        content = open(history_file).read()
        assert "code1" in content
        assert "code2" in content

    def test_format(self, tmp_path):
        history_file = str(tmp_path / "history.txt")
        with patch.object(revision_tab, "HISTORY_TXT", history_file):
            revision_tab.save_patch_history("my_code", "my_reason", "my_prompt")
        content = open(history_file).read()
        assert "my_code" in content
        assert "my_reason" in content
        assert "my_prompt" in content


class TestSavePatchHistoryJson:
    def test_creates_json(self, tmp_path):
        patch_dir = tmp_path / "patches"
        patch_dir.mkdir()
        with patch.object(revision_tab, "PATCH_HISTORY_DIR", patch_dir):
            with patch.object(revision_tab, "RESULT_LOG", str(tmp_path / "result.log")):
                path = revision_tab.save_patch_history_json("code", "reason", "prompt")
        assert os.path.exists(path)
        data = json.loads(open(path).read())
        assert data["code"] == "code"
        assert data["reason"] == "reason"
        assert data["prompt"] == "prompt"
        assert "timestamp" in data

    def test_reads_result_log(self, tmp_path):
        patch_dir = tmp_path / "patches"
        patch_dir.mkdir()
        result_log = tmp_path / "result.log"
        result_log.write_text("test output here")
        with patch.object(revision_tab, "PATCH_HISTORY_DIR", patch_dir):
            with patch.object(revision_tab, "RESULT_LOG", str(result_log)):
                path = revision_tab.save_patch_history_json("c", "r", "p")
        data = json.loads(open(path).read())
        assert data["test_log"] == "test output here"


class TestRunPytest:
    def test_success(self):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "1 passed"
        mock_result.stderr = ""
        with patch("subprocess.run", return_value=mock_result):
            with patch.object(revision_tab, "RESULT_LOG", "/tmp/dummy.log"):
                with patch.object(revision_tab, "save_file"):
                    ok, output = revision_tab.run_pytest()
        assert ok is True
        assert "1 passed" in output

    def test_failure(self):
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = "1 failed"
        mock_result.stderr = "err"
        with patch("subprocess.run", return_value=mock_result):
            with patch.object(revision_tab, "RESULT_LOG", "/tmp/dummy.log"):
                with patch.object(revision_tab, "save_file"):
                    ok, output = revision_tab.run_pytest()
        assert ok is False
        assert "failed" in output.lower()

    def test_exception(self):
        with patch("subprocess.run", side_effect=FileNotFoundError("no pytest")):
            with patch.object(revision_tab, "RESULT_LOG", "/tmp/dummy.log"):
                with patch.object(revision_tab, "save_file"):
                    ok, output = revision_tab.run_pytest()
        assert ok is False
        assert "pytest" in output.lower() or "Error" in output


class TestGeneratePrompt:
    def test_contains_sections(self, tmp_path):
        sample = tmp_path / "sample.py"
        test = tmp_path / "test.py"
        sample.write_text("def foo(): pass")
        test.write_text("def test_foo(): pass")
        result = revision_tab.generate_prompt(
            str(sample), str(test), "summary", "history", "error_log", "user_note"
        )
        assert "def foo(): pass" in result
        assert "def test_foo(): pass" in result
        assert "summary" in result
        assert "history" in result
        assert "error_log" in result
        assert "user_note" in result


class TestExtractCodeAndReason:
    def test_json_format(self):
        response = '{"code": "x=1", "reason": "fix"}'
        code, reason = revision_tab.extract_code_and_reason(response)
        assert code == "x=1"
        assert reason == "fix"

    def test_fenced_code(self):
        response = 'Some text\n```python\ndef f(): pass\n```\nReason: fix'
        code, reason = revision_tab.extract_code_and_reason(response)
        assert "def f(): pass" in code
        assert len(reason) > 0

    def test_no_code(self):
        code, reason = revision_tab.extract_code_and_reason("just text")
        assert code == ""
        assert len(reason) > 0


class TestCallGpt:
    def test_fallback_no_api_key(self):
        with patch.dict(os.environ, {}, clear=True):
            result = revision_tab.call_gpt("test")
        data = json.loads(result)
        assert "code" in data
        assert "reason" in data
        assert "is_prime" in data["code"]

    def test_api_error_fallback(self):
        with patch.dict(os.environ, {"OPENAI_API_KEY": "fake"}, clear=True):
            with patch.dict("sys.modules", {"openai": None, "openai.OpenAI": None}):
                result = revision_tab.call_gpt("test")
        data = json.loads(result)
        assert "is_prime" in data["code"]

    def test_openai_success(self):
        mock_msg = MagicMock()
        mock_msg.content = "  result text  "
        mock_choice = MagicMock()
        mock_choice.message = mock_msg
        mock_rsp = MagicMock()
        mock_rsp.choices = [mock_choice]
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_rsp
        with patch.dict(os.environ, {"OPENAI_API_KEY": "fake"}, clear=True):
            with patch("openai.OpenAI", return_value=mock_client):
                result = revision_tab.call_gpt("test prompt")
        assert result == "result text"

    def test_openai_none_content(self):
        mock_msg = MagicMock()
        mock_msg.content = None
        mock_choice = MagicMock()
        mock_choice.message = mock_msg
        mock_rsp = MagicMock()
        mock_rsp.choices = [mock_choice]
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_rsp
        with patch.dict(os.environ, {"OPENAI_API_KEY": "fake"}, clear=True):
            with patch("openai.OpenAI", return_value=mock_client):
                result = revision_tab.call_gpt("test")
        assert result == ""


class TestTabRevision:
    @pytest.mark.skip(reason="Gradio Blocks context conflict in full suite")
    def test_returns_blocks(self):
        gr = pytest.importorskip("gradio")
        with patch.object(revision_tab, "read_file", return_value=""):
            blocks = revision_tab.tab_revision()
        assert isinstance(blocks, gr.Blocks)

    @pytest.mark.skip(reason="Gradio Blocks context conflict in full suite")
    def test_blocks_renderable(self):
        pytest.importorskip("gradio")
        with patch.object(revision_tab, "read_file", return_value=""):
            blocks = revision_tab.tab_revision()
            blocks.render()
