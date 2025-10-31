# 📁 ファイル名: opencodeinterpreter_webui.py
# 📂 フォルダ構成: /src/opencodeinterpreter_webui.py
# 🕠 目的: Gradio UIにユニットテスト生成 + 修正サイクル + テスト一括実行を統合

import gradio as gr
import os
import logging
from dotenv import load_dotenv
from openai import OpenAI
from uuid import uuid4

# --- 独自モジュール ---
from nexuscore.code_interpreter.sandbox_runner import run_and_repair, run_test_and_repair
from nexuscore.utils.diff_tools import generate_diff_report, score_code_improvement
from nexuscore.utils.test_generator import generate_unit_tests
from nexuscore.utils.file_utils import (
    extract_file_content,
    handle_uploaded_files,
    file_list_display,
    extract_zip_texts,
    download_history,
)

# --- Whisper 音声認識用 ---
def process_audio(audio_file):
    try:
        if audio_file is None:
            raise gr.Warning("録音がキャンセルされました。")
        with open(audio_file, "rb") as f:
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=f,
                language="ja",
                response_format="text"
            )
        return transcript
    except gr.Warning as w:
        raise w
    except Exception as e:
        logging.error(f"音声処理エラー: {str(e)}")
        raise gr.Error(f"音声処理エラー: {e}")

# --- Gradioユーティリティ関数 ---
def update_uuid(dialog_info):
    new_uuid = str(uuid4())
    logging.info(f"allocating new uuid {new_uuid} for conversation...")
    return [new_uuid, dialog_info[1]]

def history_to_messages(history):
    messages = []
    for msg in history:
        if isinstance(msg, dict) and "role" in msg and "content" in msg:
            messages.append(msg)
        elif isinstance(msg, (list, tuple)) and len(msg) == 2:
            messages.append({"role": "user", "content": msg[0]})
            messages.append({"role": "assistant", "content": msg[1]})
    return messages

def bot(user_message, files, history, dialog_info, frontend_preview):
    try:
        if files is None:
            files = []
        file_info, file_content, file_types, frontend_preview_str = handle_uploaded_files(files)
        user_input = user_message
        if file_info:
            user_input += "\n" + file_info
        if file_content:
            user_input += f"\n[\u30d5\u30a1\u30a4\u30eb\u5185\u5bb9（4000\u6587\u5b57\u307e\u3067）]\n{file_content[:4000]}"

        prev_messages = history if history and isinstance(history[0], dict) else history_to_messages(history)
        ai_response = "ファイルまたはテキストを受け取りました。"

        chatbot_value = prev_messages + [
            {"role": "user", "content": user_message},
            {"role": "assistant", "content": ai_response}
        ]
        return chatbot_value, chatbot_value, dialog_info, frontend_preview_str

    except Exception as e:
        logging.error(f"bot error: {e}")
        raise gr.Error(f"エラー: {e}")

def reset_textbox():
    return gr.update(value="")

def clear_history(history, dialog_info):
    return [], [], update_uuid(dialog_info), ""

# --- ユニットテスト生成 ---
def generate_and_show_tests(code: str) -> str:
    try:
        return generate_unit_tests(code)
    except Exception as e:
        logging.error(f"ユニットテスト生成失敗: {e}")
        return f"エラー: {e}"

# --- Gradio UI構成 ---
def gradio_launch():
    with gr.Blocks() as demo:
        with gr.Tabs():
            # タブ1: 修正・テスト
            with gr.Tab("🛠 修正サイクル"):
                code_input = gr.Textbox(label="💡 入力コード（エラーあり可）", lines=10)
                btn_testgen = gr.Button("🧪 ユニットテスト生成")
                test_output = gr.Code(label="📄 生成されたユニットテスト")
                btn_run_repair = gr.Button("🔁 修正のみ実行")
                btn_run_test_repair = gr.Button("🧪 修正+\u30c6スト一括")
                output_code = gr.Code(label="✅ 修正済みコード or レポート")

                btn_testgen.click(fn=generate_and_show_tests, inputs=code_input, outputs=test_output)
                btn_run_repair.click(fn=run_and_repair, inputs=code_input, outputs=output_code)
                btn_run_test_repair.click(fn=run_test_and_repair, inputs=code_input, outputs=output_code)

            # タブ2: チャット＋ファイル分析
            with gr.Tab("💬 Chat + ファイル分析"):
                chatbot = gr.Chatbot(label="OpenCodeInterpreter", height=600, type="messages")
                msg = gr.Textbox(placeholder="メッセージ入力 or 音声録音", scale=5)
                file_input = gr.File(file_types=[".py", ".txt", ".md", ".json", ".zip"], file_count="multiple")
                file_list = gr.Textbox(label="アップロードファイル一覧", interactive=False, max_lines=10)
                audio_input = gr.Audio(sources="microphone", type="filepath", label="音声録音")
                frontend_preview = gr.Textbox(label="ファイル先頭プレビュー（100字）")
                submit = gr.Button("Submit")
                clear = gr.Button("Clear")
                download_btn = gr.DownloadButton("履歴ダウンロード")
                session_state = gr.State([])
                dialog_info = gr.State(["", 0])

                demo.load(update_uuid, dialog_info, dialog_info)
                file_input.change(file_list_display, inputs=file_input, outputs=file_list)
                audio_input.change(process_audio, inputs=audio_input, outputs=msg)
                submit.click(bot, [msg, file_input, session_state, dialog_info, frontend_preview], [chatbot, session_state, dialog_info, frontend_preview])
                clear.click(lambda h, d: ([], [], update_uuid(d), ""), [session_state, dialog_info], [chatbot, session_state, dialog_info, frontend_preview])
                download_btn.click(download_history, [session_state], download_btn)

        demo.queue(max_size=20)
        demo.launch(share=True, inbrowser=True)

# --- 起動 ---
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY が未設定です。.envを確認してください。")
    client = OpenAI(api_key=api_key)
    gradio_launch()
