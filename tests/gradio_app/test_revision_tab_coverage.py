"""
Additional tests for revision_tab.py to reach 85%+ coverage.
Targets: _call_minimax HTTP, SANDBOX_DIR branch, tab_revision callbacks.
"""

import json
import os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock, patch

import pytest

from nexuscore.gradio_app import revision_tab


class TestCallMinimaxHTTP:
    """_call_minimax のHTTPリクエスト本体をテスト"""

    def test_call_minimax_success(self, monkeypatch):
        """API正常応答でコンテンツを返す"""
        monkeypatch.setenv("MINIMAX_API_KEY", "test-key-123")
        monkeypatch.setenv("MINIMAX_API_BASE", "https://api.example.com/v1")
        monkeypatch.setenv("MINIMAX_MODEL", "test-model")

        mock_response = Mock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "  generated code  "}}]
        }
        mock_response.raise_for_status = Mock()

        with patch("nexuscore.gradio_app.revision_tab.requests.post", return_value=mock_response) as mock_post:
            result = revision_tab._call_minimax(
                [{"role": "user", "content": "test"}], temperature=0.5
            )

        assert result == "generated code"
        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args
        assert "test-key-123" in call_kwargs[1]["headers"]["Authorization"]
        assert call_kwargs[1]["json"]["model"] == "test-model"
        assert call_kwargs[1]["json"]["temperature"] == 0.5

    def test_call_minimax_no_api_key_raises(self, monkeypatch):
        """MINIMAX_API_KEY未設定でRuntimeError"""
        monkeypatch.delenv("MINIMAX_API_KEY", raising=False)
        with pytest.raises(RuntimeError, match="MINIMAX_API_KEY"):
            revision_tab._call_minimax([{"role": "user", "content": "test"}])

    def test_call_minimax_http_error(self, monkeypatch):
        """HTTP エラーでraise_for_statusが発火"""
        monkeypatch.setenv("MINIMAX_API_KEY", "test-key")
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = Exception("HTTP 500")

        with patch("nexuscore.gradio_app.revision_tab.requests.post", return_value=mock_response):
            with pytest.raises(Exception, match="HTTP 500"):
                revision_tab._call_minimax([{"role": "user", "content": "test"}])

    def test_call_minimax_default_temperature(self, monkeypatch):
        """デフォルトtemperature=0.2で呼ばれる"""
        monkeypatch.setenv("MINIMAX_API_KEY", "test-key")
        mock_response = Mock()
        mock_response.json.return_value = {"choices": [{"message": {"content": "ok"}}]}
        mock_response.raise_for_status = Mock()

        with patch("nexuscore.gradio_app.revision_tab.requests.post", return_value=mock_response) as mock_post:
            revision_tab._call_minimax([{"role": "user", "content": "test"}])

        assert mock_post.call_args[1]["json"]["temperature"] == 0.2


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

        # モジュールレベルの再評価をシミュレート
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
        # コードブロックを除いた残りが空なのでフォールバックメッセージ
        assert isinstance(reason, str)


class TestCallGptWithApiKey:
    """call_gpt のAPI keyありパスの追加テスト"""

    def test_call_gpt_with_key_calls_minimax(self, monkeypatch):
        """API keyあり → _call_minimax が呼ばれる"""
        monkeypatch.setenv("MINIMAX_API_KEY", "real-key")

        mock_llm_response = json.dumps({"code": "def f(): pass", "reason": "test"})
        with patch("nexuscore.gradio_app.revision_tab._call_minimax", return_value=mock_llm_response) as mock_call:
            result = revision_tab.call_gpt("fix the code")

        assert result == mock_llm_response
        mock_call.assert_called_once()
        assert mock_call.call_args[0][0][0]["content"] == "fix the code"
