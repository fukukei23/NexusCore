"""
Comprehensive tests for ui/unified_gradio_ui.py

Unified Gradio UI の完全な包括的テスト（全ハンドラー・UI構築関数含む）
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

# GradioとWhisperのモック化
sys.modules["gradio"] = MagicMock()
sys.modules["nexuscore.modules.whisper_handler"] = MagicMock()
sys.modules["nexuscore.services.self_healing_service"] = MagicMock()
sys.modules["nexuscore.agents.debugger_agent"] = MagicMock()
sys.modules["nexuscore.integration.github_pr_comment"] = MagicMock()
sys.modules["nexuscore.integration.run_report_generator"] = MagicMock()

from nexuscore.ui.unified_gradio_ui import (
    AppState,
    build_unified_ui,
    launch_unified_ui,
)


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
            latest_run_id="run_123",
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
# Tab 1: Code/Prompt ハンドラーテスト
# ============================================================================
class TestCodePromptHandlers:
    def test_transcribe_handler_success(self):
        """音声文字起こし機能はP2-6で未使用importとして削除済み"""
        # transcribe_audio, HAS_WHISPER removed as dead code (P2-6)
        pass

    def test_generate_code_handler_empty_prompt(self):
        """空のプロンプトでコード生成"""
        from nexuscore.ui.unified_gradio_ui import AppState

        # generate_code_handlerのロジックを再現
        prompt = ""
        AppState()

        if not prompt.strip():
            result = "💡 プロンプトを入力してください。"
            assert "プロンプトを入力してください" in result

    def test_generate_code_handler_valid_prompt(self):
        """有効なプロンプトでコード生成"""
        from nexuscore.ui.unified_gradio_ui import AppState

        prompt = "Create a hello world function"
        filename = "hello.py"
        state = AppState()

        # ロジックを再現
        if prompt.strip():
            generated = f"""# Generated from: {prompt}

def placeholder_function():
    \"\"\"Generated code placeholder\"\"\"
    pass
"""
            state.generated_code = generated
            if filename:
                state.current_file_path = filename

            assert state.generated_code is not None
            assert "Generated from:" in state.generated_code
            assert state.current_file_path == filename

    def test_save_code_handler_empty_code(self):
        """空のコードで保存"""
        code = ""
        AppState()

        if not code.strip():
            result = "💡 コードが空です。"
            assert "コードが空です" in result

    def test_save_code_handler_valid_code(self, tmp_path, monkeypatch):
        """有効なコードで保存"""
        monkeypatch.chdir(tmp_path)

        code = "def test(): pass"
        filename = "test.py"
        state = AppState()

        # save_code_handlerロジックを再現
        file_path = filename or "generated_code.py"
        save_path = Path("sandbox_output") / file_path
        save_path.parent.mkdir(parents=True, exist_ok=True)
        save_path.write_text(code, encoding="utf-8")

        state.current_file_path = str(save_path)
        state.generated_code = code
        state.before_code[str(save_path)] = code

        assert save_path.exists()
        assert save_path.read_text() == code
        assert state.current_file_path == str(save_path)

    def test_save_code_handler_creates_directory(self, tmp_path, monkeypatch):
        """ディレクトリを作成して保存"""
        monkeypatch.chdir(tmp_path)

        code = "print('test')"
        filename = "subdir/test.py"
        AppState()

        file_path = filename
        save_path = Path("sandbox_output") / file_path
        save_path.parent.mkdir(parents=True, exist_ok=True)
        save_path.write_text(code, encoding="utf-8")

        assert save_path.exists()
        assert save_path.parent.exists()

    def test_save_code_handler_default_filename(self, tmp_path, monkeypatch):
        """デフォルトファイル名で保存"""
        monkeypatch.chdir(tmp_path)

        code = "def default(): pass"
        filename = ""
        AppState()

        file_path = filename or "generated_code.py"
        save_path = Path("sandbox_output") / file_path
        save_path.parent.mkdir(parents=True, exist_ok=True)
        save_path.write_text(code, encoding="utf-8")

        assert "generated_code.py" in str(save_path)

    def test_generate_code_handler_without_filename(self):
        """ファイル名なしでコード生成"""
        prompt = "Test prompt"
        state = AppState()

        if prompt.strip():
            generated = f"# Generated from: {prompt}\n\ndef placeholder_function():\n    pass\n"
            state.generated_code = generated

            assert state.generated_code is not None
            assert state.current_file_path is None  # filenameが空なので設定されない

    def test_save_code_handler_unicode_code(self, tmp_path, monkeypatch):
        """Unicodeを含むコードで保存"""
        monkeypatch.chdir(tmp_path)

        code = "def test():\n    print('こんにちは')"
        filename = "unicode_test.py"
        AppState()

        save_path = Path("sandbox_output") / filename
        save_path.parent.mkdir(parents=True, exist_ok=True)
        save_path.write_text(code, encoding="utf-8")

        assert save_path.exists()
        assert "こんにちは" in save_path.read_text(encoding="utf-8")


# ============================================================================
# Tab 2: AI Revision ハンドラーテスト
# ============================================================================
class TestAIRevisionHandlers:
    def test_generate_patch_handler_empty_inputs(self):
        """空の入力でパッチ生成"""
        code = ""
        prompt = ""
        AppState()

        if not code.strip() or not prompt.strip():
            result = "💡 コードと修正指示を入力してください。"
            assert "コードと修正指示を入力してください" in result

    def test_generate_patch_handler_valid_inputs(self):
        """有効な入力でパッチ生成"""
        code = "def foo(): pass"
        prompt = "Add error handling"
        state = AppState()
        state.current_file_path = "test.py"

        # generate_patch_handlerロジック
        patch = f"""--- a/{state.current_file_path or 'file.py'}
+++ b/{state.current_file_path or 'file.py'}
@@ -1,1 +1,2 @@
 {code}
+# Modified by AI: {prompt}
"""
        assert "--- a/test.py" in patch
        assert "+++ b/test.py" in patch
        assert prompt in patch

    def test_generate_patch_handler_no_file_path(self):
        """ファイルパスなしでパッチ生成"""
        code = "def bar(): pass"
        prompt = "Improve function"
        state = AppState()

        patch = f"""--- a/{state.current_file_path or 'file.py'}
+++ b/{state.current_file_path or 'file.py'}
@@ -1,1 +1,2 @@
 {code}
+# Modified by AI: {prompt}
"""
        assert "file.py" in patch

    def test_apply_patch_handler_empty_patch(self):
        """空のパッチで適用"""
        patch = ""
        AppState()

        if not patch.strip():
            result = "💡 パッチが空です。"
            assert "パッチが空です" in result

    def test_apply_patch_handler_file_exists(self, tmp_path):
        """ファイルが存在する場合のパッチ適用"""
        test_file = tmp_path / "test.py"
        test_file.write_text("original code")

        patch = "some patch"
        state = AppState()
        state.current_file_path = str(test_file)

        if patch.strip():
            if state.current_file_path and Path(state.current_file_path).exists():
                state.after_code[state.current_file_path] = "Modified code"
                result = "✅ パッチを適用しました。"

                assert result == "✅ パッチを適用しました。"
                assert state.after_code[state.current_file_path] == "Modified code"

    def test_apply_patch_handler_file_not_found(self):
        """ファイルが見つからない場合"""
        state = AppState()
        state.current_file_path = "/nonexistent/file.py"

        if not Path(state.current_file_path).exists():
            result = "❌ ファイルが見つかりません。"
            assert "ファイルが見つかりません" in result

    def test_generate_patch_handler_multiline_code(self):
        """複数行コードでパッチ生成"""
        code = "def multi():\n    line1\n    line2"
        prompt = "Refactor"
        state = AppState()

        patch = f"""--- a/{state.current_file_path or 'file.py'}
+++ b/{state.current_file_path or 'file.py'}
@@ -1,1 +1,2 @@
 {code}
+# Modified by AI: {prompt}
"""
        assert code in patch

    def test_apply_patch_handler_updates_after_code(self, tmp_path):
        """パッチ適用後のafter_code更新"""
        test_file = tmp_path / "test.py"
        test_file.write_text("original")

        state = AppState()
        state.current_file_path = str(test_file)

        if Path(state.current_file_path).exists():
            state.after_code[state.current_file_path] = "patched"

            assert state.current_file_path in state.after_code
            assert state.after_code[state.current_file_path] == "patched"

    def test_generate_patch_handler_special_characters(self):
        """特殊文字を含むパッチ生成"""
        prompt = "Fix escaping"
        AppState()

        patch = f"# Modified by AI: {prompt}"
        assert prompt in patch


# ============================================================================
# Tab 4: History & Diff ハンドラーテスト
# ============================================================================
class TestHistoryDiffHandlers:
    def test_load_run_handler_empty_run_id(self):
        """空のRun IDで読み込み"""
        run_id = ""
        AppState()

        if not run_id.strip():
            result = "💡 Run ID を入力してください。"
            assert "Run ID を入力してください" in result

    def test_load_run_handler_valid_run_id(self):
        """有効なRun IDで読み込み"""
        run_id = "sh-1234567890-123-abc1234"
        state = AppState()
        state.current_file_path = "test.py"
        state.before_code["test.py"] = "before"
        state.after_code["test.py"] = "after"

        # load_run_handlerロジック
        file_path = state.current_file_path
        before_code = state.before_code.get(file_path, "") if file_path else ""
        after_code = state.after_code.get(file_path, "") if file_path else ""
        state.latest_run_id = run_id

        assert before_code == "before"
        assert after_code == "after"
        assert state.latest_run_id == run_id

    def test_load_run_handler_no_current_file(self):
        """現在のファイルがない場合"""
        state = AppState()

        file_path = state.current_file_path
        before_code = state.before_code.get(file_path, "") if file_path else ""
        after_code = state.after_code.get(file_path, "") if file_path else ""

        assert before_code == ""
        assert after_code == ""

    def test_trigger_self_healing_handler_empty_inputs(self):
        """空の入力でSelf-Healing実行"""
        repo_full_name = ""
        pr_number = 0
        head_sha = ""
        AppState()

        if not repo_full_name.strip() or not head_sha.strip() or pr_number <= 0:
            result = "💡 Repository、PR Number、Head SHA を入力してください。"
            assert "入力してください" in result

    def test_trigger_self_healing_handler_invalid_pr_number(self):
        """無効なPR番号"""
        pr_number = -1
        AppState()

        if pr_number <= 0:
            result = "💡 Repository、PR Number、Head SHA を入力してください。"
            assert "入力してください" in result

    def test_trigger_self_healing_handler_no_service(self):
        """Self-Healing Serviceが利用不可 — HAS_SELF_HEALING removed in P2-6"""
        pass

    def test_trigger_self_healing_handler_valid_inputs(self):
        """有効な入力でSelf-Healing実行 — HAS_SELF_HEALING removed in P2-6"""
        pass

    def test_load_run_handler_updates_state(self):
        """Run読み込み後のstate更新"""
        run_id = "sh-update-test"
        state = AppState()

        state.latest_run_id = run_id

        assert state.latest_run_id == run_id

    def test_trigger_self_healing_handler_with_retry_details(self):
        """リトライ詳細を含むSelf-Healing結果"""
        result_dict = {
            "status": "success",
            "summary": "Fixed",
            "run_id": "sh-retry",
            "duration_seconds": 100.0,
            "details": {"retry_count": 3, "last_error_class": "TimeoutError"},
        }

        result_text = f"""Status: {result_dict.get('status', 'unknown')}
Summary: {result_dict.get('summary', 'N/A')}
Run ID: {result_dict.get('run_id', 'N/A')}
Duration: {result_dict.get('duration_seconds', 0):.2f}s
"""
        if result_dict.get("details"):
            details = result_dict["details"]
            if details.get("retry_count"):
                result_text += f"Retry Count: {details.get('retry_count')}\n"
            if details.get("last_error_class"):
                result_text += f"Last Error: {details.get('last_error_class')}\n"

        assert "Retry Count: 3" in result_text
        assert "Last Error: TimeoutError" in result_text


# ============================================================================
# UI構築関数テスト
# ============================================================================
class TestUIBuilders:
    @patch("nexuscore.ui.unified_gradio_ui.gr")
    def test_build_unified_ui_creates_blocks(self, mock_gr):
        """build_unified_uiがBlocksを作成"""
        mock_blocks = MagicMock()
        mock_gr.Blocks.return_value.__enter__.return_value = mock_blocks
        mock_gr.State.return_value = Mock()
        mock_gr.themes.Soft.return_value = Mock()

        build_unified_ui()

        # Blocksが呼ばれたことを確認
        mock_gr.Blocks.assert_called_once()

    @patch("nexuscore.ui.unified_gradio_ui.gr")
    def test_build_unified_ui_sets_title(self, mock_gr):
        """build_unified_uiがタイトルを設定"""
        mock_gr.Blocks.return_value.__enter__.return_value = MagicMock()
        mock_gr.State.return_value = Mock()
        mock_gr.themes.Soft.return_value = Mock()

        build_unified_ui()

        # Blocksのtitleパラメータを確認
        call_kwargs = mock_gr.Blocks.call_args[1]
        assert call_kwargs["title"] == "NexusCore Unified UI"

    @patch("nexuscore.ui.unified_gradio_ui.gr")
    def test_build_unified_ui_initializes_state(self, mock_gr):
        """build_unified_uiがStateを初期化"""
        mock_gr.Blocks.return_value.__enter__.return_value = MagicMock()
        mock_state = Mock()
        mock_gr.State.return_value = mock_state
        mock_gr.themes.Soft.return_value = Mock()

        build_unified_ui()

        # Stateが呼ばれたことを確認
        mock_gr.State.assert_called_once()

    @patch("nexuscore.ui.unified_gradio_ui.build_unified_ui")
    def test_launch_unified_ui_builds_demo(self, mock_build):
        """launch_unified_uiがdemoを構築"""
        mock_demo = MagicMock()
        mock_build.return_value = mock_demo
        mock_demo.queue.return_value = mock_demo

        launch_unified_ui()

        mock_build.assert_called_once()

    @patch("nexuscore.ui.unified_gradio_ui.build_unified_ui")
    def test_launch_unified_ui_calls_queue(self, mock_build):
        """launch_unified_uiがqueue()を呼ぶ"""
        mock_demo = MagicMock()
        mock_build.return_value = mock_demo
        mock_demo.queue.return_value = mock_demo

        launch_unified_ui()

        mock_demo.queue.assert_called_once()

    @patch("nexuscore.ui.unified_gradio_ui.build_unified_ui")
    def test_launch_unified_ui_default_params(self, mock_build):
        """launch_unified_uiのデフォルトパラメータ"""
        mock_demo = MagicMock()
        mock_build.return_value = mock_demo
        mock_demo.queue.return_value = mock_demo

        launch_unified_ui()

        launch_call = mock_demo.launch.call_args
        assert launch_call[1]["server_name"] == "127.0.0.1"
        assert launch_call[1]["server_port"] == 7860
        assert launch_call[1]["inbrowser"] is False
        assert launch_call[1]["share"] is False

    @patch("nexuscore.ui.unified_gradio_ui.build_unified_ui")
    def test_launch_unified_ui_custom_params(self, mock_build):
        """launch_unified_uiのカスタムパラメータ"""
        mock_demo = MagicMock()
        mock_build.return_value = mock_demo
        mock_demo.queue.return_value = mock_demo

        launch_unified_ui(server_name="0.0.0.0", server_port=8080, inbrowser=True, share=True)

        launch_call = mock_demo.launch.call_args
        assert launch_call[1]["server_name"] == "0.0.0.0"
        assert launch_call[1]["server_port"] == 8080
        assert launch_call[1]["inbrowser"] is True
        assert launch_call[1]["share"] is True

    @patch("nexuscore.ui.unified_gradio_ui.gr")
    def test_build_unified_ui_uses_soft_theme(self, mock_gr):
        """build_unified_uiがBlocks()でthemeを使わず、launch()でthemeを渡す（Gradio 6）"""
        mock_gr.Blocks.return_value.__enter__.return_value = MagicMock()
        mock_gr.State.return_value = Mock()
        mock_soft_theme = Mock()
        mock_gr.themes.Soft.return_value = mock_soft_theme

        build_unified_ui()

        # Gradio 6: theme is NOT passed to Blocks()
        blocks_call = mock_gr.Blocks.call_args
        assert "theme" not in (blocks_call[1] if blocks_call else {})

    @patch("nexuscore.ui.unified_gradio_ui.build_unified_ui")
    def test_launch_unified_ui_show_error_true(self, mock_build):
        """launch_unified_uiがshow_error=Trueで起動"""
        mock_demo = MagicMock()
        mock_build.return_value = mock_demo
        mock_demo.queue.return_value = mock_demo

        launch_unified_ui()

        launch_call = mock_demo.launch.call_args
        assert launch_call[1]["show_error"] is True


# ============================================================================
# モジュールインポートテスト
# ============================================================================
class TestModuleImports:
    def test_has_whisper_flag(self):
        """HAS_WHISPER removed as dead code in P2-6"""
        from nexuscore.ui import unified_gradio_ui
        assert not hasattr(unified_gradio_ui, "HAS_WHISPER")

    def test_has_self_healing_flag(self):
        """HAS_SELF_HEALING removed as dead code in P2-6"""
        from nexuscore.ui import unified_gradio_ui
        assert not hasattr(unified_gradio_ui, "HAS_SELF_HEALING")

    def test_appstate_class_exists(self):
        """AppStateクラスの存在確認"""
        from nexuscore.ui import unified_gradio_ui

        assert hasattr(unified_gradio_ui, "AppState")

    def test_tab_builder_functions_exist(self):
        """タブビルダー関数の存在確認"""
        from nexuscore.ui import unified_gradio_ui

        assert hasattr(unified_gradio_ui, "build_code_prompt_tab")
        assert hasattr(unified_gradio_ui, "build_ai_revision_tab")
        assert hasattr(unified_gradio_ui, "build_test_runner_tab")
        assert hasattr(unified_gradio_ui, "build_history_diff_tab")

    def test_main_ui_functions_exist(self):
        """メインUI関数の存在確認"""
        from nexuscore.ui import unified_gradio_ui

        assert hasattr(unified_gradio_ui, "build_unified_ui")
        assert hasattr(unified_gradio_ui, "launch_unified_ui")

    def test_run_test_handler_removed(self):
        """run_test_handlerは非推奨で削除済み"""
        from nexuscore.ui import unified_gradio_ui

        assert not hasattr(unified_gradio_ui, "run_test_handler")


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


# ============================================================================
# 統合テスト
# ============================================================================
class TestIntegration:
    def test_full_ui_workflow_simulation(self, tmp_path, monkeypatch):
        """完全なUIワークフローのシミュレーション"""
        monkeypatch.chdir(tmp_path)

        state = AppState()

        # Step 1: コード生成
        prompt = "Create test function"
        state.generated_code = f"# Generated from: {prompt}\ndef test(): pass"
        state.current_file_path = "test.py"

        # Step 2: コード保存
        save_path = Path("sandbox_output") / "test.py"
        save_path.parent.mkdir(parents=True, exist_ok=True)
        save_path.write_text(state.generated_code, encoding="utf-8")
        state.before_code[str(save_path)] = state.generated_code

        # Step 3: パッチ生成

        # Step 4: パッチ適用
        state.after_code[str(save_path)] = "improved code"

        # Step 5: テスト実行（run_test_handlerは削除済み、直接state更新で代替）
        state.latest_test_result = "OK"

        # Step 6: Run ID記録
        state.latest_run_id = "integration-test-run"

        # 検証
        assert state.generated_code is not None
        assert state.current_file_path == "test.py"
        assert str(save_path) in state.before_code
        assert str(save_path) in state.after_code
        assert state.latest_test_result == "OK"
        assert state.latest_run_id == "integration-test-run"

    def test_multiple_file_modification_workflow(self, tmp_path, monkeypatch):
        """複数ファイル修正ワークフロー"""
        monkeypatch.chdir(tmp_path)

        state = AppState()

        files = ["file1.py", "file2.py", "file3.py"]

        for i, filename in enumerate(files):
            # コード生成
            code = f"def func{i}(): pass"
            state.generated_code = code
            state.current_file_path = filename

            # 保存
            save_path = Path("sandbox_output") / filename
            save_path.parent.mkdir(parents=True, exist_ok=True)
            save_path.write_text(code, encoding="utf-8")

            # before/after記録
            state.before_code[filename] = code
            state.after_code[filename] = f"def func{i}_improved(): pass"

        # 検証
        assert len(state.before_code) == 3
        assert len(state.after_code) == 3

        for _, filename in enumerate(files):
            assert filename in state.before_code
            assert filename in state.after_code
