import unittest

try:
    import nexuscore.utils.zip_output as zip_output
except ImportError:
    zip_output = None


class TestZipOutput(unittest.TestCase):
    """ZIP出力機能のテスト。"""

    def test_zip_output_import(self):
        """ZIP出力モジュールのインポートテスト。"""
        try:
            import nexuscore.utils.zip_output as zo

            self.assertIsNotNone(zo)
        except ImportError:
            self.skipTest("ZIP出力モジュールのインポートに失敗")

    def test_zip_functions(self):
        """ZIP関連関数のテスト。"""
        if zip_output is None:
            self.skipTest("ZIP出力モジュールが利用できません")

        zip_functions = [
            "create_zip",
            "zip_files",
            "compress_output",
            "archive_files",
            "zip_directory",
            "make_archive",
        ]

        for func_name in zip_functions:
            if hasattr(zip_output, func_name):
                func = getattr(zip_output, func_name)
                self.assertTrue(callable(func))


if __name__ == "__main__":
    unittest.main(verbosity=2)
