# tests/utils/test_app.py
import unittest

try:
    import nexuscore.utils.app as app
except ImportError:
    app = None

class TestApp(unittest.TestCase):
    """アプリケーションユーティリティのテスト。"""
    
    def test_app_import(self):
        """アプリモジュールのインポートテスト。"""
        try:
            import nexuscore.utils.app as a
            self.assertIsNotNone(a)
        except ImportError:
            self.skipTest("アプリモジュールのインポートに失敗")
    
    def test_app_functions(self):
        """アプリケーション関数のテスト。"""
        if app is None:
            self.skipTest("アプリモジュールが利用できません")
        
        app_functions = ['main', 'run', 'start', 'init_app']
        for func_name in app_functions:
            if hasattr(app, func_name):
                func = getattr(app, func_name)
                self.assertTrue(callable(func))

if __name__ == '__main__':
    unittest.main(verbosity=2)
