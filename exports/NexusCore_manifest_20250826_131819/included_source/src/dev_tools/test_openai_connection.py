# test_openai_connection.py
import os
from openai import OpenAI
from dotenv import load_dotenv

# .env から APIキーを読み込み
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    print("❌ .env に OPENAI_API_KEY が定義されていません。")
    exit(1)

client = OpenAI(api_key=api_key)

# GPT-4 に簡単な質問を送信して動作確認
try:
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "user", "content": "こんにちは！APIは正常に動いていますか？"}
        ]
    )
    print("✅ 接続成功！レスポンス：\n")
    print(response.choices[0].message.content)

except Exception as e:
    print(f"❌ エラーが発生しました：{e}")
