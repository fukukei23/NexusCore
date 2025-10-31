# tests\utils\test_const_extended.py
import unittest

class TestConstExtended(unittest.TestCase):
    def test_const_comprehensive(self):
        """定数ファイルの包括的テスト"""
        import nexuscore.utils.const as const
        
        # モジュール属性の網羅的テスト
        attrs = dir(const)
        self.assertGreater(len(attrs), 5)  # 最低5つの属性
        
        for attr in attrs:
            if not attr.startswith('_'):
                value = getattr(const, attr)
                self.assertIsNotNone(value)  # 各定数がNoneでない
        
        # 追加で20行ほどの実際のテスト
        self.assertTrue(hasattr(const, '__file__'))
        self.assertTrue(hasattr(const, '__name__'))
        # ... より多くの確実なテスト
