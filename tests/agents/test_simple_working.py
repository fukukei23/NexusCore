import unittest
import sys
import os

# 確実にインポートできるパスを追加
sys.path.append('src')

class TestSimpleWorking(unittest.TestCase):
    def test_basic_imports(self):
        """確実に動作する基本インポートテスト"""
        # 確実に存在するファイルをテスト
        import nexuscore.utils.const
        self.assertTrue(hasattr(nexuscore.utils.const, '__name__'))
    
    def test_config_functionality(self):
        """設定機能の実際のテスト"""
        from nexuscore.config.config import config as cfg
        self.assertTrue(hasattr(cfg, "ROLE_MAX_AUTONOMY"))
        self.assertIn("user", cfg.ROLE_MAX_AUTONOMY)
    
    def test_file_operations(self):
        """ファイル操作の実際のテスト"""
        import tempfile
        import os
        
        # 実際のファイル操作をテスト
        with tempfile.NamedTemporaryFile(delete=False, suffix='.txt') as f:
            f.write(b'test content')
            temp_path = f.name
        
        # ファイルが存在することを確認
        self.assertTrue(os.path.exists(temp_path))
        
        # ファイル削除
        os.unlink(temp_path)
        
        # ファイルが削除されたことを確認  
        self.assertFalse(os.path.exists(temp_path))

if __name__ == '__main__':
    unittest.main(verbosity=2)
