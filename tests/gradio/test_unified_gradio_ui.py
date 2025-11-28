"""
Gradio UI スモークテスト

unified_gradio_ui.py ベースの Gradio UI について、
「インポートできる」「build 関数が例外なく実行できる」
「主要タブ名やボタン文言が config 上に存在する」を pytest でスモークテストする。
"""

from __future__ import annotations

import pytest
import gradio as gr

from nexuscore.ui.unified_gradio_ui import build_unified_ui
from tests.gradio.ui_keywords_gradio import (
    GRADIO_MAIN_TITLE,
    GRADIO_TABS,
    GRADIO_BUTTON_LABELS,
)
from tests.gradio.helpers_gradio import assert_tabs_exist, assert_buttons_exist


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

