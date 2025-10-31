# ファイル名: logicbridge_chatbot.py
# 必要ライブラリ: gradio, openai, python-dotenv, json
# .envファイルに OPENAI_API_KEY=sk-... を記載
# 機能: OpenAI Whisperで音声認識＋ChatGPTでAIチャット応答＋FAQ＋履歴保存

import gradio as gr
import json
import os
import openai
from dotenv import load_dotenv

# --- 設定 ---
HISTORY_FILE = "history.json"

# --- APIキーの読み込み ---
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

# --- FAQ例 ---
faq_examples = [
    "このサービスの使い方を教えて",
    "音声認識がうまくいかない場合は？",
    "料金体系を教えてください"
]

# --- 履歴の保存・読み込み ---
def save_history(history):
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False)

def load_history():
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return []

# --- 入力バリデーション ---
def validate_input(msg):
    if not msg or len(msg) < 3:
        return gr.update(value="", placeholder="3文字以上入力してください")
    return msg

# --- ChatGPTによるAIチャット応答 ---
def ai_respond(history, message):
    history = history or []
    if message:
        history.append({"role": "user", "content": message})
        # OpenAI Chat API呼び出し
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo", # 必要に応じてgpt-4等に変更
                messages=history,
                max_tokens=512,
                temperature=0.7
            )
            ai_reply = response.choices[0].message["content"].strip()
        except Exception as e:
            ai_reply = f"エラー: {e}"
        history.append({"role": "assistant", "content": ai_reply})
        save_history(history)
    return history, ""

# --- Whisper APIで音声認識 ---
def transcribe_with_whisper(audio_path):
    if audio_path is None:
        return ""
    try:
        with open(audio_path, "rb") as audio_file:
            transcript = openai.Audio.transcribe(
                "whisper-1",
                audio_file,
                language="ja"
            )
        return transcript["text"]
    except Exception as e:
        return f"音声認識エラー: {e}"

# --- Gradio UI ---
with gr.Blocks(
    theme=gr.themes.Soft(primary_hue="#0D1B2A"),
    title="LogicBridge",
    description="LogicBridge - コードと実行の橋渡しAIチャットボット。OpenAI Whisperで音声認識、ChatGPTでAI応答。"
) as demo:
    # ロゴ画像（logo.pngをルートに置いてください）
    gr.Image("logo.png", elem_id="logo", show_label=False)
    # FAQテンプレート
    faq_dropdown = gr.Dropdown(choices=faq_examples, label="FAQテンプレ", interactive=True)
    # 入力欄
    msg = gr.Textbox(label="メッセージを入力", placeholder="ここに入力...", scale=7, examples=faq_examples)
    send_btn = gr.Button("送信", variant="primary")
    clear_btn = gr.Button("クリア", variant="secondary")
    state = gr.State(load_history())
    # チャットボット表示
    chatbot = gr.Chatbot(
        height=600,
        label="LogicBridge",
        show_copy_button=True,
        type="messages"
    )
    # FAQ選択でテキストボックスに挿入
    faq_dropdown.change(lambda x: x, inputs=faq_dropdown, outputs=msg)
    # 入力バリデーション
    send_btn.click(validate_input, inputs=msg, outputs=msg)
    # チャット送信（AI応答）
    send_btn.click(
        ai_respond,
        inputs=[state, msg],
        outputs=[chatbot, msg]
    )
    # クリアボタン
    def clear_all():
        if os.path.exists(HISTORY_FILE):
            os.remove(HISTORY_FILE)
        return [], ""
    clear_btn.click(clear_all, inputs=[], outputs=[chatbot, msg])
    # Whisper音声認識
    audio_input = gr.Audio(source="microphone", type="filepath", label="音声入力")
    audio_input.change(transcribe_with_whisper, inputs=audio_input, outputs=msg)

demo.launch()
