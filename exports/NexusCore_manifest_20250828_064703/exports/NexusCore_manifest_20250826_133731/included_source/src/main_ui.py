import os
import sys
import gradio as gr

# src ディレクトリの相対パスから modules と gradio_app を含める
sys.path.append(os.path.join(os.path.dirname(__file__), "./gradio_app"))
sys.path.append(os.path.join(os.path.dirname(__file__), "./modules"))

# 各UIタブをインポート
from app_ui import launch_app_ui
from revision_loop import launch_revision_ui
from streamlit_migrated_tab import tab_streamlit_port
from nexuscore.modules.whisper_handler import transcribe_audio  # Whisper処理（明示的なインポート）

# interactive_generator が存在する場合にのみ読み込む
try:
    from interactive_generator import app as generator_app
    has_generator = True
except ImportError:
    has_generator = False

def launch_all_tabs():
    with gr.Blocks(title="OpenCodeInterpreter") as demo:
        with gr.Tab("🧠 コード修正 + テスト"):
            launch_app_ui()

        with gr.Tab("🔁 修正ループ"):
            launch_revision_ui()

        with gr.Tab("🎙️ Whisper + GPTチャット"):
            tab_streamlit_port()

        if has_generator:
            with gr.Tab("🪄 生成タブ（任意）"):
                demo += generator_app  # ← generator_app を .launch() ではなく Blocks としてマウント

    demo.launch()

if __name__ == "__main__":
    launch_all_tabs()
