# src/modules/chat_handler.py

import os
from typing import Any

import requests
from dotenv import load_dotenv

load_dotenv()


def _call_minimax(messages: list[dict], temperature: float = 0.2) -> str:
    """Call MiniMax chat completions API via HTTP."""
    api_key = os.getenv("MINIMAX_API_KEY")
    api_base = os.getenv("MINIMAX_API_BASE", "https://api.minimax.chat/v1")
    model = os.getenv("MINIMAX_MODEL", "MiniMax-M2.7")
    if not api_key:
        raise RuntimeError("MINIMAX_API_KEY is not set. Provide it via env or .env file.")
    response = requests.post(
        f"{api_base}/chat/completions",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={"model": model, "messages": messages, "temperature": temperature},
        timeout=120,
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"].strip()


# チャット履歴を元にMiniMax応答を取得
def handle_chat(message: str, history: list[dict[str, Any]]) -> tuple[str | None, list[dict[str, Any]]]:
    """チャット履歴を元にMiniMax応答を取得"""
    try:
        history.append({"role": "user", "content": message})
        assistant_msg = _call_minimax(history)
        history.append({"role": "assistant", "content": assistant_msg})
        return assistant_msg, history
    except Exception as e:  # pragma: no cover - error path for runtime failures
        return f"❌ エラー: {e}", history
