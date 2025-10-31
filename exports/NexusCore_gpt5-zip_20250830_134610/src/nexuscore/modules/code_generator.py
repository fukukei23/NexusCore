# modules/code_generator.py

from openai import OpenAI
import os
from dotenv import load_dotenv

# .envからAPIキーを読み込む
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

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
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"⚠️ GPT code generation failed: {e}"
