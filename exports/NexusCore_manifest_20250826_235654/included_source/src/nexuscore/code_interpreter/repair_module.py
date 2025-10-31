# 📁 ファイル: repair_module.py
# 📂 場所: /src/code_interpreter/repair_module.py

import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def generate_fix(code: str, traceback: str) -> str:
    prompt = f"""
以下はユーザーが書いたPythonコードと、その実行時に発生したエラーです。
エラーの原因を推論し、修正されたコードを出力してください。

--- 元のコード ---
{code}

--- エラー内容 ---
{traceback}

--- 修正済みコード ---
"""
    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "あなたは熟練のPythonエンジニアです。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"GPT修正エラー: {e}")
        return code  # フェイルセーフ：元コードを返す
