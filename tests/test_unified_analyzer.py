#!/usr/bin/env python3
# ==============================================================================
# ファイル名: tests/test_unified_analyzer.py
# 機能: unified_analyzer.py の単体テスト
# バージョン: 1.7.0 (最終検証版)
# ==============================================================================

import unittest
import sys
from pathlib import Path

# --- テスト対象のモジュールをインポートするためのパスを追加 ---
current_dir = Path(__file__).parent
project_root = current_dir.parent
sys.path.insert(0, str(project_root / 'src'))

from nexuscore.analyzer.unified_analyzer import TreeSitterEngine

# ==============================================================================
# テスト用のサンプルコード
# ==============================================================================

PYTHON_CODE_FOR_DEPS = """
def helper_function(): # line 2
    pass

class MyProcessor: # line 5
    def process(self): # line 6
        helper_function() # line 7

def main(): # line 9
    p = MyProcessor() # line 10 (Instantiation, not a call)
    p.process() # line 11 (Call)
"""

# ==============================================================================
# テストクラス
# ==============================================================================

class TestDependencyExtraction(unittest.TestCase):
    """依存関係抽出機能のテストスイート"""

    @classmethod
    def setUpClass(cls):
        """テストクラスのセットアップ"""
        cls.engine = TreeSitterEngine()
        if not cls.engine.setup_parsers(['python']):
            raise unittest.SkipTest("Python parser not available.")
        # 一度だけ解析を実行し、結果をクラス変数に保存
        cls.analysis_result = cls.engine.analyze_source(PYTHON_CODE_FOR_DEPS, 'python')

    def test_extraction_logic(self):
        """定義と呼び出しの基本ロジックをテスト"""
        self.assertTrue(self.analysis_result.success)
        semantic_info = self.analysis_result['semantic_info']
        
        self.assertIn('definitions', semantic_info)
        self.assertIn('calls', semantic_info)
        
        # 4つの定義 (helper_function, MyProcessor, process, main)
        self.assertEqual(len(semantic_info['definitions']), 4)
        
        # TreeSitterEngine は MyProcessor() の生成も呼び出しとして検出するため 3 件
        self.assertEqual(len(semantic_info['calls']), 3)

    def test_call_scope_extraction(self):
        """呼び出し元のスコープが正しく抽出されるかテスト"""
        calls = self.analysis_result['semantic_info']['calls']
        
        helper_call = next(c for c in calls if c['name'] == 'helper_function')
        self.assertEqual(helper_call['scope'], 'process')

        process_call = next(c for c in calls if c['name'] == 'process')
        self.assertEqual(process_call['scope'], 'main')

    def test_statistics_generation(self):
        """統計情報が正しく生成されるかテスト"""
        stats = self.analysis_result['semantic_info']['statistics']
        
        self.assertEqual(stats.get('total_definitions'), 4)
        self.assertEqual(stats.get('total_calls'), 3)
        self.assertGreaterEqual(stats.get('functions_count', 0), 0)
        self.assertGreaterEqual(stats.get('classes_count', 0), 0)

if __name__ == '__main__':
    unittest.main(verbosity=2)
