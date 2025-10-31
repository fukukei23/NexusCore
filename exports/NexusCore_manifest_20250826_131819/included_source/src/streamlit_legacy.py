import streamlit as st
from openai import OpenAI
from dotenv import load_dotenv
import os
import io

# 音声録音用
from streamlit_mic_recorder import mic_recorder

# .envファイルからAPIキーを読み込む
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=api_key)

st.title("ChatGPT風チャット＋音声入力＋ファイルアップロード")

# セッションステートでチャット履歴を管理
if "messages" not in st.session_state:
    st.session_state.messages = []

# ファイルアップロード
uploaded_files = st.file_uploader("ファイルをアップロード（複数可）", accept_multiple_files=True)
if uploaded_files:
    for file in uploaded_files:
        st.write(f"アップロード: {file.name}")
        # テキストファイルは内容表示
        if file.type.startswith("text"):
            content = file.read().decode("utf-8", errors="ignore")
            st.text_area(f"{file.name}の内容", content, height=100)
        # バイナリの場合はファイル名のみ表示

# 音声入力（録音）
st.subheader("音声入力（録音→Whisperで文字起こし）")
audio_data = mic_recorder(
    start_prompt="録音開始",
    stop_prompt="録音停止",
    format="webm",
    key="mic"
)

if audio_data:
    st.audio(audio_data["bytes"], format="audio/webm")
    audio_bytes_io = io.BytesIO(audio_data["bytes"])
    audio_bytes_io.name = "audio.webm"
    try:
        transcript = client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_bytes_io,
            language="ja"
        )
        st.success("文字起こし結果:")
        st.write(transcript.text)
        # 文字起こし結果をチャット履歴に追加
        st.session_state.messages.append({"role": "user", "content": transcript.text})
    except Exception as e:
        st.error(f"文字起こしエラー: {e}")

# チャット履歴の表示
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# ユーザーからの入力受付
if prompt := st.chat_input("メッセージを入力してください"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # OpenAI APIでAI応答をストリーミング生成
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "あなたは有能なアシスタントです。"},
            *st.session_state.messages
        ],
        stream=True
    )

    with st.chat_message("assistant"):
        full_response = ""
        placeholder = st.empty()
        for chunk in response:
            content = getattr(chunk.choices[0].delta, "content", None)
            if content:
                full_response += content
                placeholder.markdown(full_response + "▌")
        placeholder.markdown(full_response)

    st.session_state.messages.append({"role": "assistant", "content": full_response})
