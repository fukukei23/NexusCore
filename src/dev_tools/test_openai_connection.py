# test_llm_connection.py
"""MiniMax API接続テスト（旧test_openai_connection.pyから移行）"""
import os

import requests
from dotenv import load_dotenv

# .env から APIキーを読み込み
load_dotenv()
api_key = os.getenv("MINIMAX_API_KEY")
api_base = os.getenv("MINIMAX_API_BASE", "https://api.minimax.chat/v1")
model = os.getenv("MINIMAX_MODEL", "MiniMax-M2.7")

if not api_key:
    print("❌ .env に MINIMAX_API_KEY が定義されていません。")
    exit(1)

# MiniMax に簡単な質問を送信して動作確認
try:
    response = requests.post(
        f"{api_base}/chat/completions",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={
            "model": model,
            "messages": [{"role": "user", "content": "こんにちは！APIは正常に動いていますか？"}],
            "temperature": 0.2,
        },
        timeout=30,
    )
    response.raise_for_status()
    data = response.json()
    print("✅ 接続成功！レスポンス：\n")
    print(data["choices"][0]["message"]["content"])

except Exception as e:
    print(f"❌ エラーが発生しました：{e}")
