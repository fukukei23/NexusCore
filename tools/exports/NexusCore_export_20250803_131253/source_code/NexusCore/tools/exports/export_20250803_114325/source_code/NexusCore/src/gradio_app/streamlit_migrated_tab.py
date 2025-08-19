# src/gradio_app/streamlit_migrated_tab.py

import gradio as gr
import os
from whisper_handler import transcribe_audio
from modules.chat_handler import handle_chat  # ✅ モジュールから読み込み

def tab_streamlit_port():
    with gr.Blocks() as tab:
        gr.Markdown("### 📤 音声ファイルアップロード → Whisper文字起こし → GPTチャット対応")

        with gr.Row():
            audio_input = gr.Audio(label="🎧 音声ファイルアップロード", type="filepath")
            transcript_box = gr.Textbox(label="📝 Whisper文字起こし結果", lines=2)
            transcribe_btn = gr.Button("🗣 Whisper文字起こし")

        with gr.Row():
            user_input = gr.Textbox(label="💬 GPTへの質問", lines=2)
            chat_output = gr.Textbox(label="🤖 GPT応答", lines=10)
            send_btn = gr.Button("📨 送信")

        state = gr.State([])

        transcribe_btn.click(
            fn=lambda audio: transcribe_audio(audio) if audio else "⚠️ 音声ファイルが未指定です",
            inputs=audio_input,
            outputs=transcript_box
        )

        send_btn.click(
            fn=handle_chat,
            inputs=[user_input, state],
            outputs=[chat_output, state]
        )

    return tab
