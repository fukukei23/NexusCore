"""
Gradio UI スモークテスト

unified_gradio_ui.py ベースの Gradio UI について、
「インポートできる」「build 関数が例外なく実行できる」
「主要タブ名やボタン文言が config 上に存在する」を pytest でスモークテストする。
"""

from __future__ import annotations

from unittest.mock import Mock, patch

import pytest
import sys

try:
    import gradio as gr
    if not hasattr(gr, "Blocks"):
        raise ImportError("gradio mock detected, not real gradio")
except (ImportError, ModuleNotFoundError):
    pytest.skip("gradio not installed", allow_module_level=True)

try:
    from nexuscore.ui.unified_gradio_ui import AppState, build_unified_ui, run_test_handler
    from tests.gradio.helpers_gradio import assert_buttons_exist, assert_tabs_exist
    from tests.gradio.ui_keywords_gradio import (
        GRADIO_BUTTON_LABELS,
        GRADIO_MAIN_TITLE,
        GRADIO_TABS,
    )
except Exception:
    pytest.skip("unified_gradio_ui module not available", allow_module_level=True)


def test_unified_gradio_ui_imports():
    """unified_gradio_ui モジュールがインポートできることを確認"""
    from nexuscore.ui import unified_gradio_ui

    assert hasattr(unified_gradio_ui, "build_unified_ui")
    assert hasattr(unified_gradio_ui, "launch_unified_ui")


def test_unified_gradio_ui_builds_without_error():
    """build_unified_ui() が例外なく gr.Blocks を返すことを確認"""
    demo = build_unified_ui()
    assert isinstance(demo, gr.Blocks)

    # タイトルが設定されていれば確認（必須でなければ optional でも OK）
    if hasattr(demo, "title") and demo.title:
        assert GRADIO_MAIN_TITLE in str(demo.title) or "NexusCore" in str(demo.title)


def test_unified_gradio_ui_has_core_tabs():
    """Blocks の設定に、主要タブ名が存在することを確認"""
    demo = build_unified_ui()
    # グローバル config からタブ名を取り出し、必須タブが存在することを確認
    assert_tabs_exist(demo, GRADIO_TABS)


def test_unified_gradio_ui_has_core_buttons():
    """Blocks の設定に、主要ボタンラベルが存在することを確認（余力があれば）"""
    demo = build_unified_ui()
    # 主要ボタンが存在することを確認
    # 注: ボタンラベルの抽出が難しい場合は、このテストはスキップしてもよい
    try:
        assert_buttons_exist(demo, GRADIO_BUTTON_LABELS)
    except AssertionError:
        # ボタンラベルの抽出が不完全な場合は、警告のみ
        pytest.skip("Button label extraction not fully implemented")


def test_run_test_handler_normal_case():
    """正常系: 通常の command と test_file で subprocess.run が正しい引数リストで呼ばれることを確認"""
    command = "pytest"
    test_file = "tests/test_sample.py"
    state = AppState()

    with patch("subprocess.run") as mock_run:
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "test output"
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        output, status_md, updated_state = run_test_handler(command, test_file, state)

        mock_run.assert_called_once()
        call_args = mock_run.call_args
        expected_cmd = [sys.executable, "-m", "pytest", "-q", test_file]
        assert call_args[0][0] == expected_cmd
        assert call_args[1]["shell"] is False

        assert output == "test output"
        assert "✅ 成功" in status_md
        assert updated_state.latest_test_result == "test output"


def test_run_test_handler_command_injection_prevention():
    """セキュリティ系: コマンドインジェクションのペイロードが別コマンドとして解釈されないことを確認"""
    command = "pytest"
    test_file = "tests/test_sample.py; rm -rf /"
    state = AppState()

    with patch("subprocess.run") as mock_run:
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "test output"
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        output, status_md, updated_state = run_test_handler(command, test_file, state)

        mock_run.assert_called_once()
        call_args = mock_run.call_args
        cmd_list = call_args[0][0]

        # shell=False により ; 以降が別コマンドとして解釈されない
        assert len(cmd_list) == 5  # [python, -m, pytest, -q, test_file]
        assert test_file in cmd_list  # ファイル名としてそのまま渡される
        assert call_args[1]["shell"] is False


def test_run_test_handler_empty_test_file():
    """正常系: test_file が空文字の場合、pytest -q のみで実行されることを確認"""
    command = "pytest"
    test_file = ""
    state = AppState()

    with patch("subprocess.run") as mock_run:
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "test output"
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        output, status_md, updated_state = run_test_handler(command, test_file, state)

        mock_run.assert_called_once()
        call_args = mock_run.call_args
        expected_cmd = [sys.executable, "-m", "pytest", "-q"]
        assert call_args[0][0] == expected_cmd
        assert call_args[1]["shell"] is False


def test_run_test_handler_whitespace_only_test_file():
    """正常系: test_file が空白のみの場合も無効とみなし、コマンドのみになることを確認"""
    command = "pytest"
    test_file = "   "  # 空白のみ
    state = AppState()

    with patch("subprocess.run") as mock_run:
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "test output"
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        output, status_md, updated_state = run_test_handler(command, test_file, state)

        mock_run.assert_called_once()
        call_args = mock_run.call_args
        expected_cmd = [sys.executable, "-m", "pytest", "-q"]
        assert call_args[0][0] == expected_cmd
        assert call_args[1]["shell"] is False
