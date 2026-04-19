import asyncio
import os
from unittest.mock import patch

from nexuscore.gradio_app import streamlit_migrated_tab


def test_extract_code_from_response_handles_python_block():
    resp = "text```python\nx=1\n```tail"
    code = streamlit_migrated_tab.extract_code_from_response(resp)
    assert code == "x=1"


def test_load_api_key_prefers_env(monkeypatch):
    monkeypatch.setenv("MINIMAX_API_KEY", "dummy-key-1234")
    key, source = streamlit_migrated_tab.load_api_key()
    assert key == "dummy-key-1234"
    assert "環境変数" in source


def test_call_gpt_async_without_key(monkeypatch):
    monkeypatch.setattr(streamlit_migrated_tab, "MINIMAX_API_KEY", None)
    result = asyncio.run(streamlit_migrated_tab.call_gpt_async("hello"))
    assert "APIキー" in result or "エラー" in result or "キー" in result


def test_load_api_key_from_dotenv(monkeypatch):
    monkeypatch.delenv("MINIMAX_API_KEY", raising=False)

    original_exists = streamlit_migrated_tab.os.path.exists

    def fake_exists(path):
        if str(path).endswith(".env"):
            return True
        return original_exists(path)

    monkeypatch.setattr(streamlit_migrated_tab.os.path, "exists", fake_exists)

    def fake_load(dotenv_path=None):
        os.environ["MINIMAX_API_KEY"] = "from-dotenv"

    monkeypatch.setattr(streamlit_migrated_tab, "load_dotenv", fake_load)

    key, source = streamlit_migrated_tab.load_api_key()
    assert key == "from-dotenv"
    assert ".env" in source


def test_load_api_key_returns_none_when_missing(monkeypatch):
    monkeypatch.delenv("MINIMAX_API_KEY", raising=False)

    original_exists = streamlit_migrated_tab.os.path.exists

    def fake_exists(path):
        if str(path).endswith(".env"):
            return False
        return original_exists(path)

    monkeypatch.setattr(streamlit_migrated_tab.os.path, "exists", fake_exists)

    key, source = streamlit_migrated_tab.load_api_key()
    assert key is None
    assert "見つかりません" in source
