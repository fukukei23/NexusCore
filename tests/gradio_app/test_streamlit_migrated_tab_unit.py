import asyncio
import os

from nexuscore.gradio_app import streamlit_migrated_tab


def test_extract_code_from_response_handles_python_block():
    resp = "text```python\nx=1\n```tail"
    code = streamlit_migrated_tab.extract_code_from_response(resp)
    assert code == "x=1"


def test_load_api_key_prefers_env(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "dummy-key-1234")
    key, source = streamlit_migrated_tab.load_api_key()
    assert key == "dummy-key-1234"
    assert "環境変数" in source


def test_call_gpt_async_without_key(monkeypatch):
    monkeypatch.setattr(streamlit_migrated_tab, "OPENAI_API_KEY", None)
    result = asyncio.run(streamlit_migrated_tab.call_gpt_async("hello"))
    assert "APIキー" in result or "エラー" in result


def test_load_api_key_from_dotenv(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY_FROM_DOTENV", raising=False)

    original_exists = streamlit_migrated_tab.os.path.exists

    def fake_exists(path):
        if str(path).endswith(".env"):
            return True
        return original_exists(path)

    monkeypatch.setattr(streamlit_migrated_tab.os.path, "exists", fake_exists)

    def fake_load(dotenv_path=None):
        os.environ["OPENAI_API_KEY_FROM_DOTENV"] = "from-dotenv"

    monkeypatch.setattr(streamlit_migrated_tab, "load_dotenv", fake_load)

    key, source = streamlit_migrated_tab.load_api_key()
    assert key == "from-dotenv"
    assert ".env" in source


def test_load_api_key_from_secrets(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY_FROM_DOTENV", raising=False)
    monkeypatch.setattr(streamlit_migrated_tab, "OPENAI_API_KEY", None)

    original_exists = streamlit_migrated_tab.os.path.exists

    def fake_exists(path):
        if str(path).endswith("secrets.py"):
            return True
        if str(path).endswith(".env"):
            return False
        return original_exists(path)

    monkeypatch.setattr(streamlit_migrated_tab.os.path, "exists", fake_exists)

    from importlib.machinery import ModuleSpec

    class Loader:
        def create_module(self, spec=None):
            import types

            return types.ModuleType("secrets")

        def exec_module(self, module):
            module.OPENAI_API_KEY = "secret-key"

    def fake_spec(name, location):
        return ModuleSpec(name="secrets", loader=Loader())

    monkeypatch.setattr(streamlit_migrated_tab.importlib.util, "spec_from_file_location", fake_spec)

    key, source = streamlit_migrated_tab.load_api_key()
    assert key == "secret-key"
    assert "secrets.py" in source
