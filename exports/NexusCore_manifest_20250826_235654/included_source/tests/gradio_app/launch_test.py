#!/usr/bin/env python3
"""Gradioアプリ起動テスト"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))

from nexuscore.gradio_app.streamlit_migrated_tab import tab_streamlit_port

if __name__ == "__main__":
    print("🚀 Gradioアプリを起動します...")
    app = tab_streamlit_port()
    app.launch(
        server_name="127.0.0.1", 
        server_port=7863, 
        share=False,
        debug=True
    )
