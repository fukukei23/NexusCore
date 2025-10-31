# ファイル名: chatgpt_whisper_chatbot.py
# メモ:
# - OpenAIのChatGPT APIとWhisper APIを使った日本語対応チャットボット
# - テキスト入力も音声入力（Whisperで文字起こし）もOK
# - GradioでWeb UI
# - チャット履歴はGradio形式で管理
# - .envファイルに OPENAI_API_KEY=sk-... を記載しておくこと

import gradio as gr
from openai import OpenAI
import os
from dotenv import load_dotenv
import logging
import tempfile
import sounddevice as sd
import numpy as np
from scipy.io.wavfile import write
import threading
import time

# --- 環境変数・APIキー読み込み ---
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEYが設定されていません。.envファイルを確認してください。")

client = OpenAI(api_key=OPENAI_API_KEY)

logging.basicConfig(level=logging.INFO)

# --- Whisper APIで音声ファイルを文字起こし ---
def transcribe_with_whisper(audio_path):
    try:
        with open(audio_path, "rb") as f:
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=f,
                language="ja"
            )
        return transcript.text
    except Exception as e:
        raise gr.Error(f"Whisper APIエラー: {e}")

# --- ChatGPTでAIチャット応答（Gradio履歴形式に対応） ---
def chatgpt_respond(history, message):
    # history: [[user, ai], ...] 形式
    # OpenAI API用の履歴に変換
    api_history = []
    for pair in history:
        if pair[0] is not None:
            api_history.append({"role": "user", "content": pair[0]})
        if pair[1] is not None:
            api_history.append({"role": "assistant", "content": pair[1]})
    if message:
        api_history.append({"role": "user", "content": message})
        try:
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=api_history,
                max_tokens=512,
                temperature=0.7
            )
            ai_reply = response.choices[0].message.content.strip()
        except Exception as e:
            raise gr.Error(f"ChatGPT APIエラー: {e}")
        # Gradio用履歴に追加
        history.append([message, ai_reply])
    return history, ""

# --- 音声録音（エンターで終了） ---
def record_until_keypress(max_duration=60, sample_rate=16000):
    logging.info(f"録音中... 最大{max_duration}秒、エンターキーで終了")
    recording = []
    event = threading.Event()
    start_time = time.time()

    def callback(indata, frames, t, status):
        if time.time() - start_time > max_duration:
            event.set()
            raise sd.CallbackAbort
        recording.append(indata.copy())

    def record_thread():
        with sd.InputStream(samplerate=sample_rate, channels=1, callback=callback):
            event.wait()

    def key_thread():
        input()  # エンターキー入力待ち
        event.set()

    t1 = threading.Thread(target=record_thread)
    t2 = threading.Thread(target=key_thread)
    t1.start()
    t2.start()
    t2.join(timeout=max_duration)
    t1.join(timeout=1)
    if recording:
        return np.concatenate(recording, axis=0), sample_rate
    return None, sample_rate

def process_audio():
    """音声を録音→Whisperで文字起こし→テキスト返却"""
    try:
        audio_data, fs = record_until_keypress(max_duration=60)
        if audio_data is None:
            raise gr.Warning("録音がキャンセルされました。")
        temp_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        write(temp_file.name, fs, audio_data)
        text = transcribe_with_whisper(temp_file.name)
        os.unlink(temp_file.name)
        return text
    except gr.Warning as w:
        raise w
    except Exception as e:
        logging.error(f"音声処理エラー: {str(e)}")
        raise gr.Error(f"音声処理エラー: {e}")

# --- Gradio UI（日本語化） ---
with gr.Blocks(title="ChatGPT＋Whisperチャットボット", theme=gr.themes.Soft(primary_hue="blue")) as demo:
    gr.Markdown(
        """
        # ChatGPT＋Whisper チャットボット
        - テキストまたは音声でメッセージを入力できます
        - Whisper（音声認識API）＋ChatGPT（AI応答API）両対応
        """
    )
    chatbot = gr.Chatbot(height=600, label="チャット履歴", show_copy_button=True)
    with gr.Group():
        with gr.Row():
            msg = gr.Textbox(
                container=False,
                show_label=False,
                label="メッセージを入力",
                placeholder="テキストを入力、または音声を録音...",
                scale=7,
                autofocus=True
            )
            sub = gr.Button("送信", variant="primary", scale=1, min_width=100)
            record_btn = gr.Button("🎤 録音", variant="secondary", scale=1, min_width=100)
    with gr.Row():
        clear = gr.Button("🗑️ 履歴クリア", variant="secondary")

    session_state = gr.State([])

    # 音声録音ボタン
    record_btn.click(
        process_audio,
        [],
        [msg]
    )

    # チャット送信（AI応答）
    sub.click(
        chatgpt_respond,
        inputs=[session_state, msg],
        outputs=[chatbot, msg]
    )

    # クリアボタン
    def clear_all():
        return [], ""
    clear.click(clear_all, inputs=[], outputs=[chatbot, msg])

demo.launch()
