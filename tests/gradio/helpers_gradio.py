"""
Gradio スモークテスト共通ヘルパー

Gradio Blocks の config からタブ名やボタンラベルを抽出し、検証を共通化。
"""

from __future__ import annotations

import gradio as gr


def assert_tabs_exist(demo: gr.Blocks, expected_tabs: list[str]) -> None:
    """
    Gradio Blocks の config からタブ名を取得し、
    expected_tabs がすべて含まれていることを確認する。

    Args:
        demo: Gradio Blocks インスタンス
        expected_tabs: 期待されるタブ名のリスト

    Raises:
        AssertionError: タブが含まれていない場合
    """
    # Gradio の config を取得
    config = demo.get_config() if hasattr(demo, "get_config") else demo.config

    # config 構造からタブタイトルを抽出
    titles: list[str] = []

    # Gradio の config 構造に応じてタブタイトルを抽出
    # config は通常 dict で、components や blocks の中にタブ情報が含まれる
    if isinstance(config, dict):
        # components を探索してタブを探す
        components = config.get("components", [])
        for comp in components:
            if isinstance(comp, dict):
                # Tab コンポーネントの場合
                if comp.get("type") == "tabs":
                    # tabs の中の children を探索
                    children = comp.get("children", [])
                    for child in children:
                        if isinstance(child, dict):
                            label = child.get("props", {}).get("label", "")
                            if label:
                                titles.append(label)
                # 個別の Tab コンポーネントの場合
                elif comp.get("type") == "tab":
                    label = comp.get("props", {}).get("label", "")
                    if label:
                        titles.append(label)

    # タブが見つからない場合は、blocks を直接探索
    if not titles and hasattr(demo, "blocks"):
        for block in demo.blocks.values():
            if isinstance(block, gr.Tabs):
                # Tabs の子要素を探索
                if hasattr(block, "children"):
                    for child in block.children:
                        if isinstance(child, gr.Tab):
                            if hasattr(child, "label"):
                                titles.append(child.label)
                            elif hasattr(child, "props") and "label" in child.props:
                                titles.append(child.props["label"])

    # 期待されるタブがすべて含まれていることを確認
    for tab in expected_tabs:
        # 部分一致でも OK（絵文字や空白の違いを許容）
        found = any(tab in t or t in tab for t in titles)
        assert found, f"Missing Gradio tab: {tab} (found: {titles})"


def assert_buttons_exist(demo: gr.Blocks, expected_buttons: list[str]) -> None:
    """
    Gradio Blocks の config からボタンラベルを取得し、
    expected_buttons がすべて含まれていることを確認する。

    Args:
        demo: Gradio Blocks インスタンス
        expected_buttons: 期待されるボタンラベルのリスト

    Raises:
        AssertionError: ボタンが含まれていない場合
    """
    # Gradio の config を取得
    config = demo.get_config() if hasattr(demo, "get_config") else demo.config

    # config 構造からボタンラベルを抽出
    labels: list[str] = []

    if isinstance(config, dict):
        components = config.get("components", [])
        for comp in components:
            if isinstance(comp, dict):
                # Button コンポーネントの場合
                if comp.get("type") == "button":
                    label = comp.get("props", {}).get("value", "")
                    if label:
                        labels.append(label)

    # blocks を直接探索
    if hasattr(demo, "blocks"):
        for block in demo.blocks.values():
            if isinstance(block, gr.Button):
                if hasattr(block, "value"):
                    labels.append(block.value)
                elif hasattr(block, "props") and "value" in block.props:
                    labels.append(block.props["value"])

    # 期待されるボタンがすべて含まれていることを確認
    for button in expected_buttons:
        # 部分一致でも OK
        found = any(button in lbl or lbl in button for lbl in labels)
        assert found, f"Missing Gradio button: {button} (found: {labels})"
