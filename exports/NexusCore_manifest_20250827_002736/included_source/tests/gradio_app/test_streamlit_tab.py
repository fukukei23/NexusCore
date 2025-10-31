# test_streamlit_tab.py
import gradio as gr
from src.nexuscore.gradio_app.streamlit_migrated_tab import tab_streamlit_port

if __name__ == "__main__":
    # タブを単体でテスト
    demo = tab_streamlit_port()
    demo.launch(
        server_name="127.0.0.1",
        server_port=7860,
        share=False,
        debug=True
    )
