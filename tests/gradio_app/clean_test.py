#!/usr/bin/env python3
"""クリーンなAPI キーテスト"""

import os
import sys

# 環境変数をクリア
if "OPENAI_API_KEY" in os.environ:
    del os.environ["OPENAI_API_KEY"]

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../src"))

from dotenv import load_dotenv
from openai import OpenAI


def clean_test():
    print("🧹 クリーンなAPIキーテストを開始...")

    # 強制的に.envから読み込み
    env_path = os.path.abspath(os.path.join(os.getcwd(), ".env"))
    print(f"📁 .envパス: {env_path}")

    load_dotenv(dotenv_path=env_path, override=True)

    api_key = os.getenv("OPENAI_API_KEY")
    print(f"🔑 読み込まれたキー: {api_key[:15]}...{api_key[-4:]}")

    try:
        client = OpenAI(api_key=api_key)

        response = client.chat.completions.create(
            model="gpt-3.5-turbo", messages=[{"role": "user", "content": "Hello"}], max_tokens=5
        )

        print("✅ API接続成功！")
        print(f"📝 レスポンス: {response.choices[0].message.content}")
        return True

    except Exception as e:
        print(f"❌ APIエラー: {e}")
        return False


if __name__ == "__main__":
    clean_test()
