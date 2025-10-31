# ファイル名例: realtime_whisper.py
# 必要なライブラリ: sounddevice, numpy, noisereduce, librosa, soundfile, openai, scipy
# インストール例:
# pip install sounddevice numpy noisereduce librosa soundfile openai scipy

import sounddevice as sd
import numpy as np
import threading
import time
import noisereduce as nr
import librosa
import soundfile as sf
import tempfile
import openai
from scipy.io.wavfile import write
import os

# Whisper APIキーは環境変数から取得
openai.api_key = os.getenv("OPENAI_API_KEY")

# --- メモ ---
# 1. エンターキーで録音終了、最大60秒まで録音
# 2. 録音後、ノイズリダクション＋音量正規化を自動実行
# 3. Whisper APIで日本語文字起こし
# 4. 一時ファイルは自動削除

def record_and_process_audio(max_duration=60, sample_rate=16000):
    print(f"録音開始: 最大{max_duration}秒、エンターキーで終了")
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
        input()  # エンターキー待ち
        event.set()

    t1 = threading.Thread(target=record_thread)
    t2 = threading.Thread(target=key_thread)
    t1.start()
    t2.start()
    t2.join(timeout=max_duration)
    t1.join(timeout=1)

    if not recording:
        return None

    audio_np = np.concatenate(recording, axis=0).flatten()

    # 一時ファイルに保存
    temp_wav = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
    write(temp_wav.name, sample_rate, audio_np)

    # ノイズ除去・音量正規化処理
    y, sr = librosa.load(temp_wav.name, sr=sample_rate)
    noise_sample = y[:int(sr*0.5)]  # 最初の0.5秒をノイズと仮定
    y_denoised = nr.reduce_noise(y=y, y_noise=noise_sample, sr=sr, stationary=False)
    y_normalized = librosa.util.normalize(y_denoised)

    # 処理後の音声を別ファイルに保存
    processed_wav = tempfile.NamedTemporaryFile(suffix='_processed.wav', delete=False)
    sf.write(processed_wav.name, y_normalized, sr)

    # 元の録音ファイルは削除
    temp_wav.close()
    os.unlink(temp_wav.name)

    return processed_wav.name

def transcribe_with_whisper(audio_path):
    with open(audio_path, "rb") as f:
        transcript = openai.audio.transcriptions.create(
            model="whisper-1",
            file=f,
            language="ja",
            response_format="text"
        )
    return transcript

if __name__ == '__main__':
    wav_path = record_and_process_audio(max_duration=60)
    if wav_path:
        print("録音・前処理完了、Whisperで文字起こし中...")
        text = transcribe_with_whisper(wav_path)
        print("認識結果:")
        print(text)
        os.unlink(wav_path)  # 処理後ファイル削除
    else:
        print("録音がキャンセルされました、または音声がありませんでした。")
