#!/usr/bin/env python3
# ==============================================================================
# ファイル名: run_tests.py
# 機能: NexusCoreプロジェクト用のカスタムテストランナー
# バージョン: 1.0.0
# 作成日: 2025-08-04
# 実行方法: python run_tests.py
# ==============================================================================

import unittest
import sys
from pathlib import Path

def run_all_tests():
    """
    プロジェクト全体のテストスイートを実行します。
    このスクリプトは、正しいモジュールパスを設定し、
    一貫したテスト環境を提供します。
    """
    # プロジェクトのルートディレクトリを取得
    project_root = Path(__file__).parent
    
    # 'src' ディレクトリをPythonの検索パスに追加
    # これにより、`from nexuscore.analyzer...` のようなインポートが可能になる
    src_path = project_root / 'src'
    if str(src_path) not in sys.path:
        sys.path.insert(0, str(src_path))
        print(f"✅ Added '{src_path}' to system path.")

    # テストローダーを作成
    # 'tests' ディレクトリから 'test_*.py' というパターンのファイルを探す
    loader = unittest.TestLoader()
    suite = loader.discover(start_dir='tests', pattern='test_*.py')
    
    # テストランナーを作成し、スイートを実行
    runner = unittest.TextTestRunner(verbosity=2)
    print("\n🚀 Starting NexusCore test suite...")
    print("=" * 70)
    
    result = runner.run(suite)
    
    print("=" * 70)
    print("✅ Test suite finished.")
    
    # CI/CDのために終了コードを返す
    if result.wasSuccessful():
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == '__main__':
    run_all_tests()
