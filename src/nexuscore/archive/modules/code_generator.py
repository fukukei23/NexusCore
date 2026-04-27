# modules/code_generator.py

import os

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


def generate_code_from_text(natural_text: str) -> str:
    """
    自然言語から関数名付きのPythonコードをMiniMaxで生成

    Parameters:
        natural_text (str): ユーザーの意図や実装希望内容の自然文

    Returns:
        str: MiniMaxによるPythonコード（コードブロック付き）
    """
    prompt = f"""
以下の説明に基づいて、関数名・ドキュメント付きのPython関数コードを生成してください。

【説明】{natural_text}

# 出力フォーマット：
- コードブロック内に、コメント・関数定義・処理本体を含める
- print()などの使用例があれば最後に追加してもよい
- コード以外の文章は一切含めない

"""
    try:
        return _call_minimax([{"role": "user", "content": prompt}], temperature=0.2)
    except Exception as e:  # pragma: no cover - error path for runtime failures
        return f"⚠️ MiniMax code generation failed: {e}"
