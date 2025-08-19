import os
from dotenv import load_dotenv
import openai
import sounddevice as sd
from scipy.io.wavfile import write
import numpy as np
import threading
import time
import tempfile

# .envファイルから環境変数を読み込む
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

def record_until_keypress(max_duration=60, sample_rate=16000):
    """
    エンターキーが押されるか、最大max_duration秒まで録音
    """
    print(f"録音中... 最大{max_duration}秒、エンターキーで終了します")
    recording = []
    event = threading.Event()
    start_time = time.time()

    def callback(indata, frames, t, status):
        # 最大時間を超えたら録音停止
        if time.time() - start_time > max_duration:
            event.set()
            raise sd.CallbackAbort
        recording.append(indata.copy())

    def record_thread():
        with sd.InputStream(samplerate=sample_rate, channels=1, callback=callback):
            event.wait()

    def key_thread():
        input()  # エンターキー待ち
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

def transcribe_with_whisper(audio_path):
    """Whisper APIで音声ファイルを文字起こし"""
    with open(audio_path, "rb") as f:
        transcript = openai.audio.transcriptions.create(
            model="whisper-1",
            file=f,
            language="ja",
            response_format="text"
        )
    return transcript

if __name__ == "__main__":
    audio_data, fs = record_until_keypress(max_duration=60)
    if audio_data is not None:
        print(f"録音終了: {len(audio_data)/fs:.2f}秒の音声を録音しました")
        # 一時ファイルに保存
        temp_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        write(temp_file.name, fs, audio_data)
        try:
            # Whisper APIで文字起こし
            text = transcribe_with_whisper(temp_file.name)
            print("\nWhisper認識結果:")
            print(text)
        finally:
            os.unlink(temp_file.name)
    else:
        print("録音データがありません")
