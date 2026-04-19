import asyncio

from nexuscore.gradio_app import streamlit_migrated_tab as smt


def test_load_api_key_all_missing(monkeypatch):
    monkeypatch.setenv("MINIMAX_API_KEY", "")
    key, source = smt.load_api_key()
    assert key is None or key == ""
    assert "見つかりません" in source


def test_extract_code_from_response_no_block():
    code = smt.extract_code_from_response("no fences here")
    assert code == "no fences here"


def test_call_gpt_async_handles_no_key(monkeypatch):
    monkeypatch.setattr(smt, "MINIMAX_API_KEY", None)
    result = asyncio.run(smt.call_gpt_async("prompt"))
    assert "キー" in result or "エラー" in result
