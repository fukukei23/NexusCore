"""
Comprehensive tests for ui/unified_gradio_ui.py

Unified Gradio UI の AppState とヘルパー関数のテスト
"""
import sys
from unittest.mock import Mock, MagicMock, patch

import pytest

# GradioとWhisperのモック化
sys.modules['gradio'] = MagicMock()
sys.modules['nexuscore.modules.whisper_handler'] = MagicMock()
sys.modules['nexuscore.services.self_healing_service'] = MagicMock()
sys.modules['nexuscore.agents.debugger_agent'] = MagicMock()
sys.modules['nexuscore.integration.github_pr_comment'] = MagicMock()

from nexuscore.ui.unified_gradio_ui import AppState


# ============================================================================
# AppState データクラステスト
# ============================================================================
class TestAppState:
    def test_appstate_creation_default(self):
        """デフォルト値でAppStateを作成"""
        state = AppState()

        assert state.current_file_path is None
        assert state.generated_code is None
        assert state.latest_test_result is None
        assert state.latest_run_id is None
        assert state.before_code == {}
        assert state.after_code == {}

    def test_appstate_creation_with_values(self):
        """値を指定してAppStateを作成"""
        state = AppState(
            current_file_path="/test/file.py",
            generated_code="print('hello')",
            latest_test_result="All tests passed",
            latest_run_id="run_123"
        )

        assert state.current_file_path == "/test/file.py"
        assert state.generated_code == "print('hello')"
        assert state.latest_test_result == "All tests passed"
        assert state.latest_run_id == "run_123"

    def test_appstate_before_code_dict(self):
        """before_code辞書の操作"""
        state = AppState()

        state.before_code["file1.py"] = "original code 1"
        state.before_code["file2.py"] = "original code 2"

        assert len(state.before_code) == 2
        assert state.before_code["file1.py"] == "original code 1"
        assert state.before_code["file2.py"] == "original code 2"

    def test_appstate_after_code_dict(self):
        """after_code辞書の操作"""
        state = AppState()

        state.after_code["file1.py"] = "modified code 1"
        state.after_code["file2.py"] = "modified code 2"

        assert len(state.after_code) == 2
        assert state.after_code["file1.py"] == "modified code 1"
        assert state.after_code["file2.py"] == "modified code 2"

    def test_appstate_update_file_path(self):
        """ファイルパスの更新"""
        state = AppState()

        state.current_file_path = "/initial/path.py"
        assert state.current_file_path == "/initial/path.py"

        state.current_file_path = "/updated/path.py"
        assert state.current_file_path == "/updated/path.py"

    def test_appstate_update_generated_code(self):
        """生成コードの更新"""
        state = AppState()

        state.generated_code = "def foo(): pass"
        assert state.generated_code == "def foo(): pass"

        state.generated_code = "def bar(): return 42"
        assert state.generated_code == "def bar(): return 42"

    def test_appstate_update_test_result(self):
        """テスト結果の更新"""
        state = AppState()

        state.latest_test_result = "Tests failed"
        assert state.latest_test_result == "Tests failed"

        state.latest_test_result = "Tests passed"
        assert state.latest_test_result == "Tests passed"

    def test_appstate_update_run_id(self):
        """Run IDの更新"""
        state = AppState()

        state.latest_run_id = "run_001"
        assert state.latest_run_id == "run_001"

        state.latest_run_id = "run_002"
        assert state.latest_run_id == "run_002"

    def test_appstate_multiple_before_after_codes(self):
        """複数ファイルのbefore/afterコード"""
        state = AppState()

        # 複数ファイルの変更を記録
        files = ["module1.py", "module2.py", "module3.py"]
        for i, file in enumerate(files):
            state.before_code[file] = f"original code {i}"
            state.after_code[file] = f"modified code {i}"

        assert len(state.before_code) == 3
        assert len(state.after_code) == 3

        for i, file in enumerate(files):
            assert state.before_code[file] == f"original code {i}"
            assert state.after_code[file] == f"modified code {i}"


# ============================================================================
# AppState フィールド型テスト
# ============================================================================
class TestAppStateTypes:
    def test_appstate_file_path_accepts_none(self):
        """current_file_pathがNoneを受け入れる"""
        state = AppState(current_file_path=None)
        assert state.current_file_path is None

    def test_appstate_file_path_accepts_string(self):
        """current_file_pathが文字列を受け入れる"""
        state = AppState(current_file_path="/path/to/file.py")
        assert isinstance(state.current_file_path, str)

    def test_appstate_generated_code_accepts_none(self):
        """generated_codeがNoneを受け入れる"""
        state = AppState(generated_code=None)
        assert state.generated_code is None

    def test_appstate_generated_code_accepts_string(self):
        """generated_codeが文字列を受け入れる"""
        state = AppState(generated_code="code")
        assert isinstance(state.generated_code, str)

    def test_appstate_dicts_are_independent(self):
        """before_codeとafter_codeが独立している"""
        state = AppState()

        state.before_code["test.py"] = "before"
        state.after_code["test.py"] = "after"

        assert state.before_code["test.py"] != state.after_code["test.py"]


# ============================================================================
# AppState エッジケーステスト
# ============================================================================
class TestAppStateEdgeCases:
    def test_appstate_empty_string_file_path(self):
        """空文字列のファイルパス"""
        state = AppState(current_file_path="")
        assert state.current_file_path == ""

    def test_appstate_empty_string_code(self):
        """空文字列のコード"""
        state = AppState(generated_code="")
        assert state.generated_code == ""

    def test_appstate_very_long_code(self):
        """非常に長いコード"""
        long_code = "x = 1\n" * 10000
        state = AppState(generated_code=long_code)
        assert len(state.generated_code) == len(long_code)

    def test_appstate_special_characters_in_code(self):
        """特殊文字を含むコード"""
        special_code = "print('こんにちは\\n\\t\"quoted\"')"
        state = AppState(generated_code=special_code)
        assert state.generated_code == special_code

    def test_appstate_unicode_file_path(self):
        """Unicodeを含むファイルパス"""
        unicode_path = "/プロジェクト/ファイル.py"
        state = AppState(current_file_path=unicode_path)
        assert state.current_file_path == unicode_path

    def test_appstate_many_files_in_dicts(self):
        """多数のファイルを辞書に格納"""
        state = AppState()

        for i in range(100):
            state.before_code[f"file_{i}.py"] = f"before_{i}"
            state.after_code[f"file_{i}.py"] = f"after_{i}"

        assert len(state.before_code) == 100
        assert len(state.after_code) == 100


# ============================================================================
# AppState 統合テスト
# ============================================================================
class TestAppStateIntegration:
    def test_appstate_full_workflow(self):
        """完全なワークフロー"""
        state = AppState()

        # 1. ファイルパス設定
        state.current_file_path = "/project/main.py"

        # 2. コード生成
        state.generated_code = "def main():\n    print('Hello')"

        # 3. before/afterコード記録
        state.before_code[state.current_file_path] = ""
        state.after_code[state.current_file_path] = state.generated_code

        # 4. テスト実行
        state.latest_test_result = "All tests passed"

        # 5. Run ID記録
        state.latest_run_id = "workflow_run_1"

        # 検証
        assert state.current_file_path == "/project/main.py"
        assert state.generated_code is not None
        assert state.latest_test_result == "All tests passed"
        assert state.latest_run_id == "workflow_run_1"
        assert len(state.before_code) == 1
        assert len(state.after_code) == 1

    def test_appstate_multiple_iterations(self):
        """複数回の編集イテレーション"""
        state = AppState()

        iterations = [
            ("iteration1.py", "code v1", "test result v1", "run_1"),
            ("iteration2.py", "code v2", "test result v2", "run_2"),
            ("iteration3.py", "code v3", "test result v3", "run_3"),
        ]

        for file_path, code, test_result, run_id in iterations:
            state.current_file_path = file_path
            state.generated_code = code
            state.latest_test_result = test_result
            state.latest_run_id = run_id

            state.before_code[file_path] = f"before {code}"
            state.after_code[file_path] = code

        # 最後のイテレーションの値を確認
        assert state.current_file_path == "iteration3.py"
        assert state.generated_code == "code v3"
        assert state.latest_test_result == "test result v3"
        assert state.latest_run_id == "run_3"

        # 全イテレーションの記録を確認
        assert len(state.before_code) == 3
        assert len(state.after_code) == 3

    def test_appstate_reset_workflow(self):
        """状態のリセットワークフロー"""
        state = AppState()

        # 初期状態設定
        state.current_file_path = "/test.py"
        state.generated_code = "code"
        state.latest_test_result = "passed"
        state.latest_run_id = "run_1"
        state.before_code["test.py"] = "before"
        state.after_code["test.py"] = "after"

        # リセット
        state.current_file_path = None
        state.generated_code = None
        state.latest_test_result = None
        state.latest_run_id = None
        # 辞書は手動でクリア
        state.before_code.clear()
        state.after_code.clear()

        # リセット後の確認
        assert state.current_file_path is None
        assert state.generated_code is None
        assert state.latest_test_result is None
        assert state.latest_run_id is None
        assert len(state.before_code) == 0
        assert len(state.after_code) == 0


# ============================================================================
# モジュールインポートテスト
# ============================================================================
class TestModuleImports:
    def test_has_whisper_flag(self):
        """HAS_WHISPER フラグの存在確認"""
        from nexuscore.ui import unified_gradio_ui
        assert hasattr(unified_gradio_ui, 'HAS_WHISPER')

    def test_has_self_healing_flag(self):
        """HAS_SELF_HEALING フラグの存在確認"""
        from nexuscore.ui import unified_gradio_ui
        assert hasattr(unified_gradio_ui, 'HAS_SELF_HEALING')

    def test_appstate_class_exists(self):
        """AppStateクラスの存在確認"""
        from nexuscore.ui import unified_gradio_ui
        assert hasattr(unified_gradio_ui, 'AppState')

    def test_tab_builder_functions_exist(self):
        """タブビルダー関数の存在確認"""
        from nexuscore.ui import unified_gradio_ui

        # Tab 1関数
        assert hasattr(unified_gradio_ui, 'build_code_prompt_tab')


# ============================================================================
# AppState 比較テスト
# ============================================================================
class TestAppStateComparison:
    def test_two_empty_states_are_different_objects(self):
        """2つの空状態は異なるオブジェクト"""
        state1 = AppState()
        state2 = AppState()

        assert state1 is not state2
        assert state1.before_code is not state2.before_code
        assert state1.after_code is not state2.after_code

    def test_state_copy_behavior(self):
        """状態のコピー動作"""
        state1 = AppState(current_file_path="/test.py")
        state1.before_code["test.py"] = "code"

        # 新しい状態を作成（コピーではない）
        state2 = AppState(current_file_path=state1.current_file_path)
        state2.before_code.update(state1.before_code)

        # 値は同じだがオブジェクトは別
        assert state1.current_file_path == state2.current_file_path
        assert state1.before_code["test.py"] == state2.before_code["test.py"]
        assert state1.before_code is not state2.before_code
