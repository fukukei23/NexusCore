import asyncio
from unittest.mock import patch

from nexuscore.gradio_app import streamlit_migrated_tab as smt


def test_call_gpt_async_minimax_error(monkeypatch):
    """MiniMax API呼び出しエラー時にエラーメッセージが返る"""
    monkeypatch.setattr(smt, "MINIMAX_API_KEY", "test-key")
    with patch("nexuscore.gradio_app.streamlit_migrated_tab._call_minimax_sync", side_effect=RuntimeError("API error")):
        result = asyncio.run(smt.call_gpt_async("prompt"))
        assert "エラー" in result or "error" in result.lower()
