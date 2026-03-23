# modules/code_generator.py

import os
from typing import TYPE_CHECKING, Optional

from dotenv import load_dotenv

if TYPE_CHECKING:
    from openai import OpenAI
else:
    try:
        from openai import OpenAI
    except Exception:  # pragma: no cover - fallback when openai is missing
        OpenAI = None  # type: ignore[assignment,misc]

# .env 読み込みのみ先に済ませ、クライアント生成は遅延させる
load_dotenv()
_client: Optional["OpenAI"] = None


def get_client() -> "OpenAI":
    """
    Lazily create OpenAI client to avoid import-time API key errors.
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


def generate_code_from_text(natural_text: str) -> str:
    """
    自然言語から関数名付きのPythonコードをGPTで生成

    Parameters:
        natural_text (str): ユーザーの意図や実装希望内容の自然文

    Returns:
        str: GPTによるPythonコード（コードブロック付き）
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
        client = get_client()
        response = client.chat.completions.create(
            model="gpt-4", messages=[{"role": "user", "content": prompt}], temperature=0.2
        )
        return (response.choices[0].message.content or "").strip()
    except Exception as e:  # pragma: no cover - error path for runtime failures
        return f"⚠️ GPT code generation failed: {e}"
