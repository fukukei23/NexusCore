# src/modules/chat_handler.py

import os
from typing import Any, Optional

from dotenv import load_dotenv

try:
    from openai import OpenAI
except Exception:  # pragma: no cover - fallback when openai is not installed
    OpenAI = None

# .env 読み込みは遅延のためここだけ（クライアント生成は関数内で行う）
load_dotenv()
_client: Optional["OpenAI"] = None


def get_client() -> "OpenAI":
    """
    Instantiate OpenAI client lazily to avoid import-time failures when API key is absent.
    Raises a clear error if key or library is missing.
    """
    global _client
    if _client is not None:
        return _client
    if OpenAI is None:
        raise RuntimeError("openai SDK is not installed. Please install `openai`.")
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set. Provide it via env or .env file.")
    _client = OpenAI(api_key=api_key)
    return _client


# チャット履歴を元にGPT応答を取得（LLM Router 未統合版）
def handle_chat(message: str, history: list[dict[str, Any]]) -> tuple[str, list[dict[str, Any]]]:
    """
    Keep lazy client creation so import時にAPIキーが無くてもテストを落とさない。
    """
    try:
        client = get_client()
        history.append({"role": "user", "content": message})
        response = client.chat.completions.create(model="gpt-4", messages=history)
        assistant_msg = response.choices[0].message.content
        history.append({"role": "assistant", "content": assistant_msg})
        return assistant_msg, history
    except Exception as e:  # pragma: no cover - error path for runtime failures
        return f"❌ エラー: {e}", history
