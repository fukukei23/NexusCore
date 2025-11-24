import asyncio

from nexuscore.gradio_app import streamlit_migrated_tab as smt


def test_call_gpt_async_import_error(monkeypatch):
    monkeypatch.setattr(smt, "OPENAI_API_KEY", "key")
    monkeypatch.delattr("nexuscore.gradio_app.streamlit_migrated_tab.AsyncOpenAI", raising=False)
    result = asyncio.run(smt.call_gpt_async("prompt"))
    assert "openai" in result or "エラー" in result
