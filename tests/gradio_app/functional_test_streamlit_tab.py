#!/usr/bin/env python3
"""streamlit_migrated_tab.pyの実機能テスト"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../src"))

from nexuscore.gradio_app.streamlit_migrated_tab import generate_code, tab_streamlit_port


def test_actual_functionality():
    """実際の機能をテスト"""
    print("🧪 実機能テストを開始...")

    try:
        # タブを作成
        tab_streamlit_port()
        print("✅ タブ作成: 成功")

        # コード生成機能をテスト
        result = generate_code("2つの数を足す関数を作って")
        print(f"✅ コード生成: 成功\n{result[:100]}...")

        print("🎉 すべての実機能テストが成功しました！")
        return True

    except Exception as e:
        print(f"❌ エラー: {e}")
        return False


if __name__ == "__main__":
    test_actual_functionality()
