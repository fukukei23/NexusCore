#!/usr/bin/env python3
"""OpenAI API キー検証テスト"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))

from dotenv import load_dotenv
from openai import OpenAI

def test_api_key():
    """API キーの有効性をテスト"""
    print("🔑 OpenAI API キーをテストします...")
    
    # .env読み込み
    env_path = os.path.join(os.path.dirname(__file__), "../../.env")
    load_dotenv(dotenv_path=env_path)
    
    api_key = os.getenv("OPENAI_API_KEY")
    
    if not api_key:
        print("❌ API キーが設定されていません")
        return False
    
    print(f"✅ API キーを検出: {api_key[:10]}...")
    
    try:
        client = OpenAI(api_key=api_key)
        
        # 簡単なAPI呼び出しテスト
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "Hello"}],
            max_tokens=10
        )
        
        print("✅ API キーは有効です")
        print(f"✅ レスポンス: {response.choices[0].message.content}")
        return True
        
    except Exception as e:
        print(f"❌ API エラー: {e}")
        return False

if __name__ == "__main__":
    success = test_api_key()
    if success:
        print("🎉 API キーテスト完了 - 実機能テストに進めます！")
    else:
        print("⚠️ API キーを修正してから再テストしてください")
