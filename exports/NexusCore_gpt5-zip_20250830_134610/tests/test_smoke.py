# ==============================================================================
# フォルダ: tests
# ファイル名: test_smoke.py (最終修正版)
# メモ: インポート文を、インストールされたパッケージ構造に合わせて修正。
# ==============================================================================
import unittest
# 'src' も 'nexuscore' も付けず、srcの中身(core)を直接インポート
from nexuscore.core.orchestrator import Orchestrator

class TestSmoke(unittest.TestCase):
    def test_smoke_initialization(self):
        """
        プロジェクトの基本コンポーネントがインポート可能であることを確認するスモークテスト。
        このテストが通ることは、テスト環境が正しく設定されていることの証です。
        """
        self.assertTrue(True, "Smoke test passed.")

