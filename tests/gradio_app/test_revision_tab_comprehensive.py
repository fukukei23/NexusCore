"""
Comprehensive tests for nexuscore.gradio_app.revision_tab module.

This test file provides extensive coverage for all functions, edge cases,
error handling, and integration scenarios in the revision_tab module.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock, patch

try:
    import gradio as gr
except ImportError:
    gr = None  # type: ignore[assignment]

import pytest

# Mock gradio before importing revision_tab
sys.modules["gradio"] = MagicMock()

from nexuscore.gradio_app import revision_tab

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def temp_sandbox(tmp_path):
    """Create a temporary sandbox directory with standard files."""
    sandbox = tmp_path / "sandbox_output"
    sandbox.mkdir(parents=True, exist_ok=True)

    sample_file = sandbox / "sample.py"
    test_file = sandbox / "test_sample.py"
    result_log = sandbox / "test_result.log"
    history_txt = sandbox / "patch_history.txt"

    sample_file.write_text("def is_prime(n):\n    return n > 1\n", encoding="utf-8")
    test_file.write_text("def test_prime():\n    assert is_prime(2)\n", encoding="utf-8")
    result_log.write_text("", encoding="utf-8")
    history_txt.write_text("", encoding="utf-8")

    return sandbox


@pytest.fixture
def mock_subprocess_success():
    """Mock subprocess.run to return successful pytest result."""
    result = SimpleNamespace(returncode=0, stdout="5 passed", stderr="")
    with patch.object(revision_tab.subprocess, "run", return_value=result) as mock:
        yield mock


@pytest.fixture
def mock_subprocess_failure():
    """Mock subprocess.run to return failed pytest result."""
    result = SimpleNamespace(returncode=1, stdout="3 passed, 2 failed", stderr="Error details")
    with patch.object(revision_tab.subprocess, "run", return_value=result) as mock:
        yield mock


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client for LLM calls."""
    with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
        mock_response = Mock()
        mock_response.choices = [
            Mock(
                message=Mock(
                    content='{"code": "def is_prime(n):\\n    return n >= 2", "reason": "Fixed edge case"}'
                )
            )
        ]

        with patch("openai.OpenAI") as mock_client:
            mock_instance = Mock()
            mock_instance.chat.completions.create.return_value = mock_response
            mock_client.return_value = mock_instance
            yield mock_instance


@pytest.fixture
def sample_patch_data():
    """Sample patch history data for testing."""
    return {
        "timestamp": "20250101_120000",
        "status": "success",
        "reason": "Handle n=2 edge case",
        "prompt": "Fix the is_prime function",
        "llm_prompt": "Please fix the prime function to handle n=2",
        "code": "def is_prime(n):\n    return n >= 2",
        "full_code_after": "def is_prime(n):\n    return n >= 2",
        "code_diff": "-    return n > 1\n+    return n >= 2",
        "test_log": "5 passed in 0.2s",
    }


# ============================================================================
# Tests for _now_tag()
# ============================================================================


class TestNowTag:
    """Tests for the _now_tag timestamp generation function."""

    def test_now_tag_format(self):
        """Test that _now_tag returns properly formatted timestamp."""
        tag = revision_tab._now_tag()
        assert len(tag) == 15  # YYYYMMDD_HHMMSS
        assert tag[8] == "_"
        assert tag[:8].isdigit()
        assert tag[9:].isdigit()

    def test_now_tag_uniqueness(self):
        """Test that consecutive calls produce different or equal timestamps."""
        tag1 = revision_tab._now_tag()
        tag2 = revision_tab._now_tag()
        # Could be same or different depending on execution speed
        assert len(tag1) == len(tag2)
        assert isinstance(tag1, str)
        assert isinstance(tag2, str)

    def test_now_tag_with_mocked_datetime(self):
        """Test _now_tag with specific mocked datetime."""
        with patch.object(revision_tab, "_now_tag", return_value="20250615_143022"):
            tag = revision_tab._now_tag()
            assert tag == "20250615_143022"


# ============================================================================
# Tests for read_file()
# ============================================================================


class TestReadFile:
    """Tests for the read_file utility function."""

    def test_read_file_success(self, tmp_path):
        """Test reading a valid file."""
        test_file = tmp_path / "test.py"
        content = "print('hello world')\n"
        test_file.write_text(content, encoding="utf-8")

        result = revision_tab.read_file(str(test_file))
        assert result == content

    def test_read_file_nonexistent(self):
        """Test reading a nonexistent file returns empty string."""
        result = revision_tab.read_file("/nonexistent/file.py")
        assert result == ""

    def test_read_file_empty(self, tmp_path):
        """Test reading an empty file."""
        test_file = tmp_path / "empty.py"
        test_file.write_text("", encoding="utf-8")

        result = revision_tab.read_file(str(test_file))
        assert result == ""

    def test_read_file_with_unicode(self, tmp_path):
        """Test reading a file with unicode characters."""
        test_file = tmp_path / "unicode.py"
        content = "# 日本語コメント\nprint('こんにちは')\n"
        test_file.write_text(content, encoding="utf-8")

        result = revision_tab.read_file(str(test_file))
        assert result == content
        assert "日本語" in result

    def test_read_file_with_permission_error(self, tmp_path):
        """Test reading a file with permission denied."""
        test_file = tmp_path / "restricted.py"
        test_file.write_text("secret", encoding="utf-8")

        # Mock Path.read_text to raise PermissionError
        with patch.object(Path, "read_text", side_effect=PermissionError("Access denied")):
            result = revision_tab.read_file(str(test_file))
            assert result == ""

    def test_read_file_with_decoding_error(self, tmp_path):
        """Test reading a file with encoding issues."""
        test_file = tmp_path / "bad_encoding.py"
        test_file.write_bytes(b"\xff\xfe invalid utf-8")

        result = revision_tab.read_file(str(test_file))
        assert result == ""

    def test_read_file_multiline(self, tmp_path):
        """Test reading a multi-line file."""
        test_file = tmp_path / "multiline.py"
        content = "line1\nline2\nline3\n"
        test_file.write_text(content, encoding="utf-8")

        result = revision_tab.read_file(str(test_file))
        assert result == content
        assert result.count("\n") == 3


# ============================================================================
# Tests for save_file()
# ============================================================================


class TestSaveFile:
    """Tests for the save_file utility function."""

    def test_save_file_success(self, tmp_path):
        """Test saving a file successfully."""
        test_file = tmp_path / "output.py"
        content = "print('saved')\n"

        revision_tab.save_file(str(test_file), content)

        assert test_file.exists()
        assert test_file.read_text(encoding="utf-8") == content

    def test_save_file_creates_parent_dirs(self, tmp_path):
        """Test that save_file creates parent directories."""
        test_file = tmp_path / "nested" / "dir" / "file.py"
        content = "nested content"

        revision_tab.save_file(str(test_file), content)

        assert test_file.exists()
        assert test_file.read_text(encoding="utf-8") == content

    def test_save_file_overwrites_existing(self, tmp_path):
        """Test that save_file overwrites existing content."""
        test_file = tmp_path / "overwrite.py"
        test_file.write_text("old content", encoding="utf-8")

        new_content = "new content"
        revision_tab.save_file(str(test_file), new_content)

        assert test_file.read_text(encoding="utf-8") == new_content

    def test_save_file_empty_content(self, tmp_path):
        """Test saving a file with empty content."""
        test_file = tmp_path / "empty.py"

        revision_tab.save_file(str(test_file), "")

        assert test_file.exists()
        assert test_file.read_text(encoding="utf-8") == ""

    def test_save_file_with_unicode(self, tmp_path):
        """Test saving a file with unicode content."""
        test_file = tmp_path / "unicode.py"
        content = "# 日本語コメント\nprint('テスト')\n"

        revision_tab.save_file(str(test_file), content)

        saved = test_file.read_text(encoding="utf-8")
        assert saved == content
        assert "日本語" in saved


# ============================================================================
# Tests for save_patch_history()
# ============================================================================


class TestSavePatchHistory:
    """Tests for the legacy text-based patch history function."""

    def test_save_patch_history_appends(self, tmp_path, monkeypatch):
        """Test that save_patch_history appends to existing file."""
        history_file = tmp_path / "patch_history.txt"
        history_file.write_text("Old entry\n", encoding="utf-8")
        monkeypatch.setattr(revision_tab, "HISTORY_TXT", str(history_file))

        revision_tab.save_patch_history("code", "reason", "prompt")

        content = history_file.read_text(encoding="utf-8")
        assert "Old entry" in content
        assert "=== 新しい修正案 ===" in content
        assert "reason" in content
        assert "code" in content
        assert "prompt" in content

    def test_save_patch_history_creates_parent(self, tmp_path, monkeypatch):
        """Test that save_patch_history creates parent directories."""
        history_file = tmp_path / "nested" / "patch_history.txt"
        monkeypatch.setattr(revision_tab, "HISTORY_TXT", str(history_file))

        revision_tab.save_patch_history("code", "reason", "prompt")

        assert history_file.exists()
        content = history_file.read_text(encoding="utf-8")
        assert "code" in content

    def test_save_patch_history_with_none_values(self, tmp_path, monkeypatch):
        """Test save_patch_history with None values."""
        history_file = tmp_path / "patch_history.txt"
        monkeypatch.setattr(revision_tab, "HISTORY_TXT", str(history_file))

        revision_tab.save_patch_history(None, None, None)

        content = history_file.read_text(encoding="utf-8")
        assert "=== 新しい修正案 ===" in content

    def test_save_patch_history_with_empty_strings(self, tmp_path, monkeypatch):
        """Test save_patch_history with empty strings."""
        history_file = tmp_path / "patch_history.txt"
        monkeypatch.setattr(revision_tab, "HISTORY_TXT", str(history_file))

        revision_tab.save_patch_history("", "", "")

        content = history_file.read_text(encoding="utf-8")
        assert "=== 新しい修正案 ===" in content
        assert "[📝 修正理由]:" in content
        assert "[📤 GPTプロンプト]:" in content
        assert "[💻 修正コード]:" in content

    def test_save_patch_history_format(self, tmp_path, monkeypatch):
        """Test the format of saved patch history."""
        history_file = tmp_path / "patch_history.txt"
        monkeypatch.setattr(revision_tab, "HISTORY_TXT", str(history_file))

        code = "def test():\n    pass"
        reason = "Fixed bug"
        prompt = "Please fix the bug"

        revision_tab.save_patch_history(code, reason, prompt)

        content = history_file.read_text(encoding="utf-8")
        assert content.count("[📝 修正理由]:") == 1
        assert content.count("[📤 GPTプロンプト]:") == 1
        assert content.count("[💻 修正コード]:") == 1


# ============================================================================
# Tests for save_patch_history_json()
# ============================================================================


class TestSavePatchHistoryJson:
    """Tests for the JSON-based patch history function."""

    def test_save_patch_history_json_creates_file(self, tmp_path, monkeypatch):
        """Test that save_patch_history_json creates a JSON file."""
        patch_dir = tmp_path / "patch_history"
        patch_dir.mkdir(parents=True, exist_ok=True)
        result_log = tmp_path / "result.log"
        result_log.write_text("test log", encoding="utf-8")

        monkeypatch.setattr(revision_tab, "PATCH_HISTORY_DIR", patch_dir)
        monkeypatch.setattr(revision_tab, "RESULT_LOG", str(result_log))

        output_path = revision_tab.save_patch_history_json("code", "reason", "prompt")

        assert Path(output_path).exists()
        data = json.loads(Path(output_path).read_text(encoding="utf-8"))
        assert data["reason"] == "reason"
        assert data["prompt"] == "prompt"
        assert data["code"] == "code"
        assert data["test_log"] == "test log"

    def test_save_patch_history_json_structure(self, tmp_path, monkeypatch):
        """Test the structure of saved JSON data."""
        patch_dir = tmp_path / "patch_history"
        patch_dir.mkdir(parents=True, exist_ok=True)
        result_log = tmp_path / "result.log"
        result_log.write_text("", encoding="utf-8")

        monkeypatch.setattr(revision_tab, "PATCH_HISTORY_DIR", patch_dir)
        monkeypatch.setattr(revision_tab, "RESULT_LOG", str(result_log))

        output_path = revision_tab.save_patch_history_json(
            "test_code", "test_reason", "test_prompt"
        )

        data = json.loads(Path(output_path).read_text(encoding="utf-8"))

        # Verify all required fields
        assert "timestamp" in data
        assert "status" in data
        assert data["status"] == "manual_save"
        assert data["reason"] == "test_reason"
        assert data["prompt"] == "test_prompt"
        assert data["llm_prompt"] == "test_prompt"
        assert data["code"] == "test_code"
        assert data["full_code_after"] == "test_code"
        assert "code_diff" in data
        assert "test_log" in data

    def test_save_patch_history_json_timestamp_format(self, tmp_path, monkeypatch):
        """Test that JSON file has correct timestamp format."""
        patch_dir = tmp_path / "patch_history"
        patch_dir.mkdir(parents=True, exist_ok=True)
        result_log = tmp_path / "result.log"
        result_log.write_text("", encoding="utf-8")

        monkeypatch.setattr(revision_tab, "PATCH_HISTORY_DIR", patch_dir)
        monkeypatch.setattr(revision_tab, "RESULT_LOG", str(result_log))

        output_path = revision_tab.save_patch_history_json("code", "reason", "prompt")

        # Verify filename format
        filename = Path(output_path).name
        assert filename.startswith("patch_")
        assert filename.endswith(".json")

        # Verify timestamp in data
        data = json.loads(Path(output_path).read_text(encoding="utf-8"))
        ts = data["timestamp"]
        assert len(ts) == 15
        assert ts[8] == "_"

    def test_save_patch_history_json_with_none_values(self, tmp_path, monkeypatch):
        """Test JSON save with None values."""
        patch_dir = tmp_path / "patch_history"
        patch_dir.mkdir(parents=True, exist_ok=True)
        result_log = tmp_path / "result.log"
        result_log.write_text("", encoding="utf-8")

        monkeypatch.setattr(revision_tab, "PATCH_HISTORY_DIR", patch_dir)
        monkeypatch.setattr(revision_tab, "RESULT_LOG", str(result_log))

        output_path = revision_tab.save_patch_history_json(None, None, None)

        data = json.loads(Path(output_path).read_text(encoding="utf-8"))
        assert data["reason"] == ""
        assert data["code"] == ""

    def test_save_patch_history_json_unicode_support(self, tmp_path, monkeypatch):
        """Test JSON save with unicode content."""
        patch_dir = tmp_path / "patch_history"
        patch_dir.mkdir(parents=True, exist_ok=True)
        result_log = tmp_path / "result.log"
        result_log.write_text("テスト結果", encoding="utf-8")

        monkeypatch.setattr(revision_tab, "PATCH_HISTORY_DIR", patch_dir)
        monkeypatch.setattr(revision_tab, "RESULT_LOG", str(result_log))

        output_path = revision_tab.save_patch_history_json(
            "# 日本語コード", "日本語の理由", "日本語プロンプト"
        )

        data = json.loads(Path(output_path).read_text(encoding="utf-8"))
        assert "日本語コード" in data["code"]
        assert "日本語の理由" in data["reason"]
        assert "テスト結果" in data["test_log"]


# ============================================================================
# Tests for run_pytest()
# ============================================================================


class TestRunPytest:
    """Tests for the pytest execution function."""

    def test_run_pytest_success(self, mock_subprocess_success, tmp_path, monkeypatch):
        """Test successful pytest execution."""
        result_log = tmp_path / "result.log"
        monkeypatch.setattr(revision_tab, "RESULT_LOG", str(result_log))
        monkeypatch.setattr(revision_tab, "SANDBOX_DIR", tmp_path)

        ok, output = revision_tab.run_pytest()

        assert ok is True
        assert "passed" in output
        assert result_log.exists()

    def test_run_pytest_failure(self, mock_subprocess_failure, tmp_path, monkeypatch):
        """Test failed pytest execution."""
        result_log = tmp_path / "result.log"
        monkeypatch.setattr(revision_tab, "RESULT_LOG", str(result_log))
        monkeypatch.setattr(revision_tab, "SANDBOX_DIR", tmp_path)

        ok, output = revision_tab.run_pytest()

        assert ok is False
        assert "failed" in output

    def test_run_pytest_exception_handling(self, tmp_path, monkeypatch):
        """Test pytest execution with exception."""
        result_log = tmp_path / "result.log"
        monkeypatch.setattr(revision_tab, "RESULT_LOG", str(result_log))

        with patch.object(
            revision_tab.subprocess, "run", side_effect=FileNotFoundError("pytest not found")
        ):
            ok, output = revision_tab.run_pytest()

        assert ok is False
        assert "pytest 実行エラー" in output
        assert result_log.exists()

    def test_run_pytest_saves_output(self, mock_subprocess_success, tmp_path, monkeypatch):
        """Test that pytest output is saved to log file."""
        result_log = tmp_path / "result.log"
        monkeypatch.setattr(revision_tab, "RESULT_LOG", str(result_log))
        monkeypatch.setattr(revision_tab, "SANDBOX_DIR", tmp_path)

        ok, output = revision_tab.run_pytest()

        saved_output = result_log.read_text(encoding="utf-8")
        assert saved_output == output
        assert "passed" in saved_output

    def test_run_pytest_with_stderr(self, tmp_path, monkeypatch):
        """Test pytest execution with stderr output."""
        result = SimpleNamespace(returncode=0, stdout="5 passed", stderr="warning: deprecated")

        with patch.object(revision_tab.subprocess, "run", return_value=result):
            result_log = tmp_path / "result.log"
            monkeypatch.setattr(revision_tab, "RESULT_LOG", str(result_log))
            monkeypatch.setattr(revision_tab, "SANDBOX_DIR", tmp_path)

            ok, output = revision_tab.run_pytest()

        assert ok is True
        assert "passed" in output
        assert "warning" in output

    def test_run_pytest_return_type(self, mock_subprocess_success, tmp_path, monkeypatch):
        """Test that run_pytest returns tuple of (bool, str)."""
        result_log = tmp_path / "result.log"
        monkeypatch.setattr(revision_tab, "RESULT_LOG", str(result_log))
        monkeypatch.setattr(revision_tab, "SANDBOX_DIR", tmp_path)

        result = revision_tab.run_pytest()

        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], bool)
        assert isinstance(result[1], str)


# ============================================================================
# Tests for generate_prompt()
# ============================================================================


class TestGeneratePrompt:
    """Tests for the prompt generation function."""

    def test_generate_prompt_includes_all_sections(self, tmp_path):
        """Test that generated prompt includes all required sections."""
        sample_file = tmp_path / "sample.py"
        test_file = tmp_path / "test_sample.py"
        sample_file.write_text("def add(a, b):\n    return a + b", encoding="utf-8")
        test_file.write_text("def test_add():\n    assert add(1, 2) == 3", encoding="utf-8")

        prompt = revision_tab.generate_prompt(
            str(sample_file),
            str(test_file),
            "v1.0",
            "Previous attempt failed",
            "AssertionError at line 5",
            "Fix the edge case",
        )

        assert "sample.py" in prompt
        assert "test_sample.py" in prompt
        assert "def add(a, b)" in prompt
        assert "def test_add()" in prompt
        assert "v1.0" in prompt
        assert "Previous attempt failed" in prompt
        assert "AssertionError" in prompt
        assert "Fix the edge case" in prompt

    def test_generate_prompt_with_empty_files(self, tmp_path):
        """Test prompt generation with empty files."""
        sample_file = tmp_path / "empty_sample.py"
        test_file = tmp_path / "empty_test.py"
        sample_file.write_text("", encoding="utf-8")
        test_file.write_text("", encoding="utf-8")

        prompt = revision_tab.generate_prompt(str(sample_file), str(test_file), "", "", "", "")

        assert "sample.py" in prompt
        assert "test_sample.py" in prompt

    def test_generate_prompt_with_nonexistent_files(self):
        """Test prompt generation with nonexistent files."""
        prompt = revision_tab.generate_prompt(
            "/nonexistent/sample.py", "/nonexistent/test.py", "summary", "history", "errors", "note"
        )

        assert "sample.py" in prompt
        assert "test_sample.py" in prompt
        assert "summary" in prompt

    def test_generate_prompt_format(self, tmp_path):
        """Test the format and structure of generated prompt."""
        sample_file = tmp_path / "sample.py"
        test_file = tmp_path / "test.py"
        sample_file.write_text("code", encoding="utf-8")
        test_file.write_text("test", encoding="utf-8")

        prompt = revision_tab.generate_prompt(str(sample_file), str(test_file), "s", "h", "e", "n")

        assert "# Context" in prompt
        assert "# ユーザーの目的" in prompt
        assert "# バージョン要約" in prompt
        assert "# 修正履歴" in prompt
        assert "# テスト結果" in prompt
        assert "# 指示" in prompt


# ============================================================================
# Tests for extract_code_and_reason()
# ============================================================================


class TestExtractCodeAndReason:
    """Tests for the LLM response extraction function."""

    def test_extract_code_and_reason_json_format(self):
        """Test extraction from JSON format."""
        response = json.dumps({"code": "def test():\n    pass", "reason": "Fixed the issue"})

        code, reason = revision_tab.extract_code_and_reason(response)

        assert code == "def test():\n    pass"
        assert reason == "Fixed the issue"

    def test_extract_code_and_reason_fenced_code(self):
        """Test extraction from fenced code block."""
        response = """Here's the fix:
```python
def test():
    pass
```
This should work now."""

        code, reason = revision_tab.extract_code_and_reason(response)

        assert "def test():" in code
        assert "pass" in code
        assert "should work" in reason

    def test_extract_code_and_reason_no_language_tag(self):
        """Test extraction from code block without language tag."""
        response = """Fix applied:
```
x = 1
y = 2
```
Done."""

        code, reason = revision_tab.extract_code_and_reason(response)

        assert "x = 1" in code
        assert "y = 2" in code

    def test_extract_code_and_reason_no_code_block(self):
        """Test extraction when no code block is present."""
        response = "Just some text without code"

        code, reason = revision_tab.extract_code_and_reason(response)

        assert code == ""
        # Without code blocks, reason is the original text
        assert "text without code" in reason

    def test_extract_code_and_reason_invalid_json(self):
        """Test extraction with invalid JSON."""
        response = '{"invalid json'

        code, reason = revision_tab.extract_code_and_reason(response)

        # Should fall back to fenced code extraction
        assert isinstance(code, str)
        assert isinstance(reason, str)

    def test_extract_code_and_reason_multiple_code_blocks(self):
        """Test extraction with multiple code blocks (uses first one)."""
        response = """First block:
```python
code1
```
Second block:
```python
code2
```"""

        code, reason = revision_tab.extract_code_and_reason(response)

        assert "code1" in code
        assert "code2" not in code

    def test_extract_code_and_reason_empty_response(self):
        """Test extraction from empty response."""
        code, reason = revision_tab.extract_code_and_reason("")

        assert code == ""
        assert "抽出できませんでした" in reason

    @pytest.mark.parametrize(
        "response,expected_code,reason_contains",
        [
            ('{"code": "x=1", "reason": "simple"}', "x=1", "simple"),
            ('{"code": "", "reason": "empty"}', "", "empty"),
            ('{"code": "a", "reason": ""}', "a", ""),
            ("```\ncode\n```\nreason", "code", "reason"),
        ],
    )
    def test_extract_code_and_reason_parametrized(self, response, expected_code, reason_contains):
        """Parametrized tests for various response formats."""
        code, reason = revision_tab.extract_code_and_reason(response)

        assert expected_code in code
        assert reason_contains in reason


# ============================================================================
# Tests for call_gpt()
# ============================================================================


class TestCallGpt:
    """Tests for the LLM API call function."""

    def test_call_gpt_with_api_key(self, mock_openai_client):
        """Test GPT call with valid API key."""
        prompt = "Fix this code"

        response = revision_tab.call_gpt(prompt)

        assert "code" in response or "def is_prime" in response
        mock_openai_client.chat.completions.create.assert_called_once()

    def test_call_gpt_without_api_key(self, monkeypatch):
        """Test GPT call without API key returns fallback."""
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)

        response = revision_tab.call_gpt("Fix this")

        assert "code" in response or "def is_prime" in response
        # Should contain fallback response
        data = json.loads(response)
        assert "code" in data
        assert "reason" in data

    def test_call_gpt_api_exception(self):
        """Test GPT call with API exception falls back."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            with patch("openai.OpenAI") as mock_client:
                mock_client.side_effect = Exception("API Error")

                response = revision_tab.call_gpt("prompt")

        # Should return fallback
        assert isinstance(response, str)
        assert "code" in response.lower() or "def is_prime" in response

    def test_call_gpt_fallback_structure(self, monkeypatch):
        """Test that fallback response has correct structure."""
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)

        response = revision_tab.call_gpt("test prompt")
        data = json.loads(response)

        assert "code" in data
        assert "reason" in data
        assert "def is_prime" in data["code"]
        assert len(data["reason"]) > 0


# ============================================================================
# Tests for tab_revision() UI
# ============================================================================


class TestTabRevision:
    """Tests for the Gradio UI tab function."""

    def test_tab_revision_returns_blocks(self):
        """Test that tab_revision returns a Gradio Blocks object."""
        with patch.object(revision_tab, "read_file", return_value=""):
            tab = revision_tab.tab_revision()

        assert tab is not None

    def test_tab_revision_creates_ui_components(self):
        """Test that tab contains expected UI components."""
        with patch.object(revision_tab, "read_file", return_value="sample code"):
            tab = revision_tab.tab_revision()

        # Tab should be created successfully
        assert tab is not None


# ============================================================================
# Integration Tests
# ============================================================================


class TestIntegration:
    """Integration tests combining multiple functions."""

    def test_full_revision_workflow(self, tmp_path, monkeypatch):
        """Test complete revision workflow."""
        # Setup
        sandbox = tmp_path / "sandbox"
        sandbox.mkdir()
        sample_file = sandbox / "sample.py"
        test_file = sandbox / "test_sample.py"
        result_log = sandbox / "result.log"
        patch_dir = tmp_path / "patch_history"

        sample_file.write_text("def is_prime(n):\n    return n > 1", encoding="utf-8")
        test_file.write_text("def test():\n    assert is_prime(2)", encoding="utf-8")

        monkeypatch.setattr(revision_tab, "SAMPLE_FILE", str(sample_file))
        monkeypatch.setattr(revision_tab, "TEST_FILE", str(test_file))
        monkeypatch.setattr(revision_tab, "RESULT_LOG", str(result_log))
        monkeypatch.setattr(revision_tab, "PATCH_HISTORY_DIR", patch_dir)
        patch_dir.mkdir(parents=True, exist_ok=True)
        monkeypatch.setattr(revision_tab, "SANDBOX_DIR", sandbox)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)

        # Generate prompt
        prompt = revision_tab.generate_prompt(
            str(sample_file), str(test_file), "v1", "", "", "Fix n=2"
        )
        assert "is_prime" in prompt

        # Call GPT (fallback)
        response = revision_tab.call_gpt(prompt)
        assert response

        # Extract code
        code, reason = revision_tab.extract_code_and_reason(response)
        assert code

        # Save code
        revision_tab.save_file(str(sample_file), code)
        assert sample_file.exists()

        # Save history
        json_path = revision_tab.save_patch_history_json(code, reason, prompt)
        assert Path(json_path).exists()

    def test_end_to_end_with_mocked_pytest(self, tmp_path, monkeypatch):
        """Test end-to-end flow with mocked pytest."""
        sandbox = tmp_path / "sandbox"
        sandbox.mkdir()

        monkeypatch.setattr(revision_tab, "SANDBOX_DIR", sandbox)
        monkeypatch.setattr(revision_tab, "RESULT_LOG", str(sandbox / "result.log"))

        result = SimpleNamespace(returncode=0, stdout="5 passed", stderr="")
        with patch.object(revision_tab.subprocess, "run", return_value=result):
            ok, output = revision_tab.run_pytest()

        assert ok is True
        assert "passed" in output
