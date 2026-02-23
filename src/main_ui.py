import os
import sys

import gradio as gr

# src ディレクトリの相対パスから modules と gradio_app を含める
sys.path.append(os.path.join(os.path.dirname(__file__), "./gradio_app"))
sys.path.append(os.path.join(os.path.dirname(__file__), "./modules"))

# 4.5: 統合 Gradio UI を優先的に使用
try:
    from nexuscore.ui.unified_gradio_ui import build_unified_ui, launch_unified_ui

    HAS_UNIFIED_UI = True
except ImportError:
    HAS_UNIFIED_UI = False
    launch_unified_ui = None  # type: ignore

# 既存のUIタブ（フォールバック用）
try:
    from app_ui import launch_app_ui
    from revision_loop import launch_revision_ui
    from streamlit_migrated_tab import tab_streamlit_port

    from nexuscore.modules.whisper_handler import (
        transcribe_audio,
    )  # Whisper処理（明示的なインポート）

    HAS_LEGACY_UI = True
except ImportError:
    HAS_LEGACY_UI = False

# interactive_generator が存在する場合にのみ読み込む
try:
    from interactive_generator import app as generator_app

    has_generator = True
except ImportError:
    has_generator = False


def launch_all_tabs():
    """
    4.5: 統合 Gradio UI を起動（フォールバック: 既存のタブ構成）
    """
    if HAS_UNIFIED_UI and launch_unified_ui:
        # 4.5: 統合 UI を使用
        launch_unified_ui()
    elif HAS_LEGACY_UI:
        # フォールバック: 既存のタブ構成
        with gr.Blocks(title="OpenCodeInterpreter") as demo:
            with gr.Tab("🧠 コード修正 + テスト"):
                launch_app_ui()

            with gr.Tab("🔁 修正ループ"):
                launch_revision_ui()

            with gr.Tab("🎙️ Whisper + GPTチャット"):
                tab_streamlit_port()

            if has_generator:
                with gr.Tab("🪄 生成タブ（任意）"):
                    demo += (
                        generator_app  # ← generator_app を .launch() ではなく Blocks としてマウント
                    )

        demo.launch()
    else:
        print("Error: No UI available. Please check imports.")


if __name__ == "__main__":
    launch_all_tabs()
