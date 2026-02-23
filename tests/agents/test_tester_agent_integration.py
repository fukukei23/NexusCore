"""
test_tester_agent_integration.py

TesterAgent のテスト戦略統合機能のテスト。
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

from nexuscore.agents.tester_agent import TesterAgent


class TestTesterAgentIntegration:
    """TesterAgent の統合機能テスト"""

    def test_init_with_project_root(self):
        """project_root を指定して初期化"""
        with tempfile.TemporaryDirectory() as tmpdir:
            agent = TesterAgent(project_root=tmpdir)

            assert agent.project_root == Path(tmpdir).resolve()
            assert agent.strategy_manager is not None
            assert agent.test_metrics is not None

    def test_init_without_project_root(self):
        """project_root を指定せずに初期化（環境変数から取得）"""
        agent = TesterAgent()

        assert agent.project_root is not None
        assert isinstance(agent.project_root, Path)

    def test_generate_tests_for_module_skips_non_auto_generation(self):
        """自動生成が無効な戦略のモジュールはスキップ"""
        with tempfile.TemporaryDirectory() as tmpdir:
            agent = TesterAgent(project_root=tmpdir)

            # sandbox_runner は human_design + ai_augment なので自動生成不可
            result = agent.generate_tests_for_module(
                module_name="sandbox_runner",
                target_file_path="src/nexuscore/core/sandbox_runner.py",
                target_code="def run(): pass",
            )

            assert result is None

    def test_generate_tests_for_module_with_auto_generation(self):
        """自動生成が有効なモジュールでテスト生成"""
        with tempfile.TemporaryDirectory() as tmpdir:
            agent = TesterAgent(project_root=tmpdir)

            # LLM 呼び出しをモック
            mock_response = json.dumps(
                {
                    "test_code": "def test_example(): assert True",
                    "testimony": "Basic test",
                }
            )

            with patch.object(agent, "execute_llm_task", return_value=mock_response):
                result = agent.generate_tests_for_module(
                    module_name="file_utils",  # ランクB、自動生成可
                    target_file_path="src/nexuscore/utils/file_utils.py",
                    target_code="def hello(): return 'world'",
                )

            # 結果が返される（実際のファイル書き込みは行われる）
            assert result is not None
            assert "test_code" in result
            assert "test_file_path" in result

    def test_infer_module_name_from_path(self):
        """ファイルパスからモジュール名を推定"""
        agent = TesterAgent()

        assert (
            agent._infer_module_name_from_path("src/nexuscore/utils/file_utils.py") == "file_utils"
        )
        assert agent._infer_module_name_from_path("sandbox_runner.py") == "sandbox_runner"

    def test_resolve_test_file_path(self):
        """テストファイルパスの解決"""
        with tempfile.TemporaryDirectory() as tmpdir:
            agent = TesterAgent(project_root=tmpdir)

            test_path = agent._resolve_test_file_path("src/nexuscore/utils/file_utils.py")
            expected = Path(tmpdir) / "tests" / "nexuscore" / "utils" / "test_file_utils.py"

            assert test_path == expected

    def test_count_test_functions(self):
        """テスト関数のカウント"""
        agent = TesterAgent()

        test_code = """
def test_example():
    assert True

def test_another():
    assert False

def helper_function():
    pass
"""
        count = agent._count_test_functions(test_code)
        assert count == 2

    def test_extract_test_code_from_response_json(self):
        """JSON レスポンスからテストコードを抽出"""
        agent = TesterAgent()

        response = json.dumps({"test_code": "def test(): pass", "testimony": "test"})
        code = agent._extract_test_code_from_response(response)

        assert code == "def test(): pass"

    def test_extract_test_code_from_response_plain(self):
        """プレーンテキストレスポンスからテストコードを抽出"""
        agent = TesterAgent()

        response = "def test(): pass"
        code = agent._extract_test_code_from_response(response)

        assert code == "def test(): pass"

    def test_handle_changed_files(self):
        """変更ファイルリストの処理"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # テスト用のファイルを作成
            test_file = Path(tmpdir) / "src" / "example.py"
            test_file.parent.mkdir(parents=True, exist_ok=True)
            test_file.write_text("def hello(): return 'world'", encoding="utf-8")

            agent = TesterAgent(project_root=tmpdir)

            # LLM 呼び出しをモック
            mock_response = json.dumps(
                {
                    "test_code": "def test_hello(): assert hello() == 'world'",
                    "testimony": "test",
                }
            )

            with patch.object(agent, "execute_llm_task", return_value=mock_response):
                results = agent.handle_changed_files(
                    [
                        "src/example.py",
                    ]
                )

            assert "example" in results
            # sandbox_runner など自動生成不可のモジュールは None になる可能性がある
            # ここでは example が処理されたことを確認
