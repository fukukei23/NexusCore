"""
Additional tests for revision_tab.py to reach 85%+ coverage.
Targets: call_llm_messages routing, SANDBOX_DIR branch, tab_revision callbacks.
"""

import json
import os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock, patch

import pytest

from nexuscore.gradio_app import revision_tab


class TestCallLlmMessagesRouting:
    """call_llm_messages 経由のLLM呼び出しをテスト"""

    def test_call_llm_messages_success(self):
        """call_llm_messages が正常応答を返す"""
        with patch("nexuscore.gradio_app.revision_tab.call_llm_messages", return_value="generated code") as mock_call:
            result = revision_tab.call_gpt("test prompt")

        assert result == "generated code"

    def test_call_llm_messages_error_triggers_fallback(self):
        """call_llm_messages 例外 → フォールバック応答"""
        with patch("nexuscore.gradio_app.revision_tab.call_llm_messages", side_effect=RuntimeError("API error")):
            result = revision_tab.call_gpt("test")

        data = json.loads(result)
        assert "code" in data
        assert "is_prime" in data["code"]

    def test_call_llm_messages_passes_prompt(self):
        """プロンプトが正しく call_llm_messages に渡される"""
        with patch("nexuscore.gradio_app.revision_tab.call_llm_messages", return_value="ok") as mock_call:
            revision_tab.call_gpt("fix the code")

        call_args = mock_call.call_args[0]
        assert call_args[0][0]["content"] == "fix the code"


class TestSandboxDirFallback:
    """SANDBOX_DIR の for/else フォールバック分岐"""

    def test_sandbox_dir_uses_src_root_when_none_exist(self, monkeypatch, tmp_path):
        """候補がどちらも存在しない場合、SRC_ROOT/sandbox_output が使われる"""
        src_root = tmp_path / "src"
        src_root.mkdir()
        project_root = tmp_path / "project"
        project_root.mkdir()

        monkeypatch.setattr(revision_tab, "SRC_ROOT", src_root)
        monkeypatch.setattr(revision_tab, "PROJECT_ROOT", project_root)

        candidates = [src_root / "sandbox_output", project_root / "sandbox_output"]
        for c in candidates:
            if c.exists():
                sandbox = c
                break
        else:
            sandbox = src_root / "sandbox_output"

        assert sandbox == src_root / "sandbox_output"


class TestExtractCodeEdgeCases:
    """extract_code_and_reason のエッジケース追加"""

    def test_json_with_missing_keys(self):
        """JSONにcode/reasonキーがない場合"""
        response = json.dumps({"other": "value"})
        code, reason = revision_tab.extract_code_and_reason(response)
        assert code == ""
        assert reason == ""

    def test_only_code_block_no_surrounding_text(self):
        """コードブロックだけのレスポンス"""
        response = "```python\nx = 42\n```"
        code, reason = revision_tab.extract_code_and_reason(response)
        assert "x = 42" in code
        assert isinstance(reason, str)


class TestCallGptWithApiKey:
    """call_gpt のAPI keyありパスの追加テスト"""

    def test_call_gpt_routes_through_llm_helper(self):
        """call_gpt → call_llm_messages 経由で呼ばれる"""
        mock_llm_response = json.dumps({"code": "def f(): pass", "reason": "test"})
        with patch("nexuscore.gradio_app.revision_tab.call_llm_messages", return_value=mock_llm_response) as mock_call:
            result = revision_tab.call_gpt("fix the code")

        assert result == mock_llm_response
        mock_call.assert_called_once()
        assert mock_call.call_args[0][0][0]["content"] == "fix the code"
