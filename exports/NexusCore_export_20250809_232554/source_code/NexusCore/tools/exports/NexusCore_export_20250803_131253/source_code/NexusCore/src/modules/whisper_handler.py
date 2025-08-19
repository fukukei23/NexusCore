import whisper

model = whisper.load_model("small")

def transcribe_audio(audio_path: str) -> str:
    try:
        result = model.transcribe(audio_path)
        return result["text"]
    except Exception as e:
        return f"文字起こし中にエラーが発生しました: {e}"
