#!/usr/bin/env python3
"""API キー詳細診断スクリプト"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))

from dotenv import load_dotenv
from openai import OpenAI

def debug_api_key():
    """詳細なAPI キー診断"""
    print("🔍 API キー詳細診断を開始...")
    
    # 1. 複数のパスで.envを探す
    possible_paths = [
        os.path.join(os.path.dirname(__file__), "../../.env"),
        os.path.join(os.getcwd(), ".env"),
        ".env"
    ]
    
    print("\n📁 .envファイル検索:")
    for i, path in enumerate(possible_paths, 1):
        abs_path = os.path.abspath(path)
        exists = os.path.exists(abs_path)
        print(f"  {i}. {abs_path} : {'✅ 存在' if exists else '❌ なし'}")
        
        if exists:
            # .envファイルの内容確認
            try:
                with open(abs_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    api_key_line = [line for line in content.split('\n') if 'OPENAI_API_KEY' in line]
                    if api_key_line:
                        print(f"     🔑 API キー行: {api_key_line[0][:30]}...")
                    load_dotenv(dotenv_path=abs_path)
            except Exception as e:
                print(f"     ❌ 読み込みエラー: {e}")
    
    # 2. 環境変数の確認
    print("\n🌍 環境変数確認:")
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        print(f"  ✅ 検出されたキー: {api_key[:15]}...{api_key[-4:]}")
        print(f"  📏 キー長: {len(api_key)}")
        print(f"  🔤 プレフィックス: {api_key[:8]}")
    else:
        print("  ❌ 環境変数でAPIキーが見つかりません")
    
    # 3. 直接.envから読み込みテスト
    print("\n📖 直接.envファイル読み込みテスト:")
    env_file_path = os.path.join(os.getcwd(), ".env")
    if os.path.exists(env_file_path):
        try:
            with open(env_file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                for line in lines:
                    if 'OPENAI_API_KEY' in line:
                        key_part = line.split('=', 1)[1].strip()
                        print(f"  📄 ファイル内キー: {key_part[:15]}...{key_part[-4:]}")
                        break
        except Exception as e:
            print(f"  ❌ ファイル読み込みエラー: {e}")
    
    # 4. OpenAI APIテスト
    print("\n🚀 OpenAI API接続テスト:")
    if api_key:
        try:
            client = OpenAI(api_key=api_key)
            
            # モデル一覧取得（軽いAPI呼び出し）
            response = client.models.list()
            print("  ✅ API接続成功")
            
            # 実際のチャット呼び出し
            chat_response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": "テスト"}],
                max_tokens=5
            )
            print("  ✅ チャット呼び出し成功")
            
        except Exception as e:
            print(f"  ❌ API エラー: {e}")
            
            # エラーの詳細分析
            error_str = str(e)
            if "401" in error_str:
                print("  💡 401エラー = APIキーが無効または期限切れ")
            elif "429" in error_str:
                print("  💡 429エラー = レート制限またはクォータ不足")
            elif "403" in error_str:
                print("  💡 403エラー = 権限なし")

if __name__ == "__main__":
    debug_api_key()
