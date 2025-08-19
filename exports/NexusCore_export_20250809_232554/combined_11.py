
# === NexusCore/src\realtime_whisper.py ===
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

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\src\realtime_whisper.py ===
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

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\src\realtime_whisper.py ===
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

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\tools\exports\export_20250803_114325\source_code\NexusCore\src\realtime_whisper.py ===
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

# === NexusCore/src\nexuscore\agents\base_agent.py ===
# ==============================================================================
# フォルダ: src/nexuscore/agents/
# ファイル名: base_agent.py
# メモ: 【統合・最終版】
#      - お客様の既存コードと、提案したLLMRouterアーキテクチャを完全に統合。
#      - このファイルをそのままコピペで置き換えることで、すべてのエージェントが
#        タスクに応じて最適なLLMを自動で使い分ける能力を手にします。
# ==============================================================================
import logging
import sys
import os

# --- パス設定とLLMRouterのインポート ---
# このファイル(src/nexuscore/agents/base_agent.py)からの相対パスでプロジェクトルートを解決
current_dir = os.path.dirname(os.path.abspath(__file__))
# current_dir = src/nexuscore/agents
# src_path = src/nexuscore
src_path = os.path.dirname(current_dir)
if src_path not in sys.path:
    # sys.pathに src/nexuscore を追加
    sys.path.insert(0, src_path)

# さらに一つ上の階層 (src) もパスに追加
# これにより、 from nexuscore.llm.llm_router import LLMRouter のような絶対インポートが可能になる
grandparent_dir = os.path.dirname(src_path)
if grandparent_dir not in sys.path:
    sys.path.insert(0, grandparent_dir)


try:
    # 新しく作成したLLMRouterをインポート
    from nexuscore.llm.llm_router import LLMRouter
except ImportError as e:
    print(f"エラー: LLMRouterをインポートできませんでした: {e}")
    print("src/nexuscore/llm/llm_router.py が正しい場所に存在するか確認してください。")
    sys.exit(1)
except Exception as e:
    print(f"予期せぬエラーが発生しました: {e}")
    sys.exit(1)


class BaseAgent:
    """
    すべてのエージェントの基底クラス。
    LLMRouterを内蔵し、タスクに応じた最適なLLMの選択を自動化する。
    """
    # 各エージェント固有のシステムプロンプトを、それぞれのクラスで上書きして使用する
    SYSTEM_PROMPT = "あなたは、有能なAIアシスタントです。"

    def __init__(self):
        """
        BaseAgentを初期化する。
        APIキーやモデル名の管理はすべてLLMRouterに委任するため、引数は不要。
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # ★★★★★ ここがアーキテクチャの核心 ★★★★★
        # APIキーやモデル名を直接扱わず、LLMRouterのインスタンスを保持するだけ。
        # これにより、このBaseAgent自身は、どのLLMが使われるかを一切知る必要がなくなる。
        try:
            self.llm_router = LLMRouter()
            self.logger.info(f"Agent initialized with LLMRouter.")
        except Exception as e:
            self.logger.critical(f"LLMRouterの初期化に失敗しました。アプリケーションを起動できません。: {e}")
            # secrets.pyの読み込み失敗など、致命的なエラーの場合はプログラムを終了させる
            raise e
        # ★★★★★ ここまで ★★★★★

    def execute_llm_task(self, prompt: str, **kwargs) -> str:
        """
        タスク（プロンプト）に最適なLLMを選択し、実行する。
        
        Args:
            prompt (str): LLMに与える具体的な指示。
            **kwargs: as_json (bool), temperature (float) などのオプション。
        
        Returns:
            str: LLMからの応答テキスト。
        """
        try:
            # 1. ルーターにタスク内容を伝え、最適なLLMクライアントを取得
            #    プロンプト自体をタスク説明として利用する
            optimal_llm_client = self.llm_router.get_llm_for_task(prompt)
            
            self.logger.info(f"Executing task with optimal LLM: {optimal_llm_client.model_name}")
            
            # 2. 取得したクライアントを使ってタスクを実行
            #    SYSTEM_PROMPTは、このエージェント自身のものを使用する
            return optimal_llm_client.execute(
                prompt=prompt,
                system_prompt=self.SYSTEM_PROMPT,
                **kwargs
            )
        except Exception as e:
            self.logger.error(f"LLMタスクの実行中にエラーが発生しました: {e}", exc_info=True)
            # エラーが発生した場合でも、システムの動作を止めないように空文字列を返す
            return ""

# === NexusCore/src\nexuscore\utils\code_analyzer.py ===
# src/utils/code_analyzer.py

import subprocess
import re
import json

def run_pylint(file_path: str) -> float:
    """指定されたファイルに対してPylintを実行し、スコアを返す"""
    print(f"🔬 Running Pylint on {file_path}...")
    command = ["pylint", file_path]
    try:
        result = subprocess.run(command, capture_output=True, text=True, encoding='utf-8')
        output = result.stdout
        match = re.search(r"Your code has been rated at (\d+\.\d+)/10", output)
        if match:
            score = float(match.group(1))
            print(f"✅ Pylint score: {score}/10")
            return score
        print(f"⚠️ Pylint score not found in output.")
        return 0.0
    except Exception as e:
        print(f"🚨 An error occurred while running Pylint: {e}")
        return 0.0

def run_mypy(file_path: str) -> tuple[bool, str]:
    """指定されたファイルに対してMyPyを実行し、(成功フラグ, 結果メッセージ)を返す"""
    print(f"🔬 Running MyPy on {file_path}...")
    command = ["mypy", file_path]
    try:
        result = subprocess.run(command, capture_output=True, text=True, encoding='utf-8')
        output = result.stdout + result.stderr
        if "Success: no issues found" in output:
            print("✅ MyPy found no issues.")
            return True, "Passed"
        else:
            error_summary = "\n".join(line for line in output.splitlines() if "error:" in line)
            print(f"❌ MyPy found issues.")
            return False, error_summary
    except Exception as e:
        print(f"🚨 An error occurred while running MyPy: {e}")
        return False, str(e)

def run_bandit(target_path: str) -> tuple[bool, str]:
    """指定されたパスに対してBanditを実行し、(成功フラグ, 結果メッセージ)を返す"""
    print(f"🔬 Running Bandit security scan on {target_path}...")
    command = ["bandit", "-r", target_path, "-f", "json"]
    try:
        result = subprocess.run(command, capture_output=True, text=True, encoding='utf-8')
        report = json.loads(result.stdout)
        high_medium_issues = [
            f"- {res['issue_text']} (Severity: {res['issue_severity']}, File: {res['filename']}:{res['line_number']})"
            for res in report["results"]
            if res["issue_severity"] in ["HIGH", "MEDIUM"]
        ]
        if not high_medium_issues:
            print("✅ Bandit: No high or medium severity issues found.")
            return True, "Passed"
        else:
            issue_summary = "\n".join(high_medium_issues)
            print("❌ Bandit found security issues.")
            return False, issue_summary
    except json.JSONDecodeError:
        print("✅ Bandit: No security issues reported.")
        return True, "Passed"
    except Exception as e:
        print(f"🚨 An error occurred while running Bandit: {e}")
        return False, str(e)

def run_pytest_cov(project_path: str) -> float:
    """
    指定されたプロジェクトパスを基準にテストとカバレッジ計測を実行する。
    設定はpyproject.tomlから読み込まれる。
    """
    print(f"🔬 Running pytest-cov on {project_path}...")
    # 設定ファイルがあるので、コマンドはシンプルに 'pytest' だけで良い
    command = ["pytest"]
    try:
        # cwdを指定して、対象プロジェクトのルートでコマンドを実行する
        result = subprocess.run(
            command,
            cwd=project_path,  # これが重要！
            capture_output=True,
            text=True,
            encoding='utf-8'
        )
        output = result.stdout
        match = re.search(r"TOTAL\s+\d+\s+\d+\s+(\d+)%", output)
        if match:
            coverage = float(match.group(1))
            print(f"✅ Pytest-cov coverage: {coverage}%")
            return coverage
        print(f"⚠️ Pytest-cov coverage not found. Output:\n{output}")
        return 0.0
    except Exception as e:
        print(f"🚨 An error occurred while running pytest-cov: {e}")
        return 0.0

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\src\utils\code_analyzer.py ===
# src/utils/code_analyzer.py

import subprocess
import re
import json

def run_pylint(file_path: str) -> float:
    """指定されたファイルに対してPylintを実行し、スコアを返す"""
    print(f"🔬 Running Pylint on {file_path}...")
    command = ["pylint", file_path]
    try:
        result = subprocess.run(command, capture_output=True, text=True, encoding='utf-8')
        output = result.stdout
        match = re.search(r"Your code has been rated at (\d+\.\d+)/10", output)
        if match:
            score = float(match.group(1))
            print(f"✅ Pylint score: {score}/10")
            return score
        print(f"⚠️ Pylint score not found in output.")
        return 0.0
    except Exception as e:
        print(f"🚨 An error occurred while running Pylint: {e}")
        return 0.0

def run_mypy(file_path: str) -> tuple[bool, str]:
    """指定されたファイルに対してMyPyを実行し、(成功フラグ, 結果メッセージ)を返す"""
    print(f"🔬 Running MyPy on {file_path}...")
    command = ["mypy", file_path]
    try:
        result = subprocess.run(command, capture_output=True, text=True, encoding='utf-8')
        output = result.stdout + result.stderr
        if "Success: no issues found" in output:
            print("✅ MyPy found no issues.")
            return True, "Passed"
        else:
            error_summary = "\n".join(line for line in output.splitlines() if "error:" in line)
            print(f"❌ MyPy found issues.")
            return False, error_summary
    except Exception as e:
        print(f"🚨 An error occurred while running MyPy: {e}")
        return False, str(e)

def run_bandit(target_path: str) -> tuple[bool, str]:
    """指定されたパスに対してBanditを実行し、(成功フラグ, 結果メッセージ)を返す"""
    print(f"🔬 Running Bandit security scan on {target_path}...")
    command = ["bandit", "-r", target_path, "-f", "json"]
    try:
        result = subprocess.run(command, capture_output=True, text=True, encoding='utf-8')
        report = json.loads(result.stdout)
        high_medium_issues = [
            f"- {res['issue_text']} (Severity: {res['issue_severity']}, File: {res['filename']}:{res['line_number']})"
            for res in report["results"]
            if res["issue_severity"] in ["HIGH", "MEDIUM"]
        ]
        if not high_medium_issues:
            print("✅ Bandit: No high or medium severity issues found.")
            return True, "Passed"
        else:
            issue_summary = "\n".join(high_medium_issues)
            print("❌ Bandit found security issues.")
            return False, issue_summary
    except json.JSONDecodeError:
        print("✅ Bandit: No security issues reported.")
        return True, "Passed"
    except Exception as e:
        print(f"🚨 An error occurred while running Bandit: {e}")
        return False, str(e)

def run_pytest_cov(project_path: str) -> float:
    """
    指定されたプロジェクトパスを基準にテストとカバレッジ計測を実行する。
    設定はpyproject.tomlから読み込まれる。
    """
    print(f"🔬 Running pytest-cov on {project_path}...")
    # 設定ファイルがあるので、コマンドはシンプルに 'pytest' だけで良い
    command = ["pytest"]
    try:
        # cwdを指定して、対象プロジェクトのルートでコマンドを実行する
        result = subprocess.run(
            command,
            cwd=project_path,  # これが重要！
            capture_output=True,
            text=True,
            encoding='utf-8'
        )
        output = result.stdout
        match = re.search(r"TOTAL\s+\d+\s+\d+\s+(\d+)%", output)
        if match:
            coverage = float(match.group(1))
            print(f"✅ Pytest-cov coverage: {coverage}%")
            return coverage
        print(f"⚠️ Pytest-cov coverage not found. Output:\n{output}")
        return 0.0
    except Exception as e:
        print(f"🚨 An error occurred while running pytest-cov: {e}")
        return 0.0

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\src\utils\code_analyzer.py ===
# src/utils/code_analyzer.py

import subprocess
import re
import json

def run_pylint(file_path: str) -> float:
    """指定されたファイルに対してPylintを実行し、スコアを返す"""
    print(f"🔬 Running Pylint on {file_path}...")
    command = ["pylint", file_path]
    try:
        result = subprocess.run(command, capture_output=True, text=True, encoding='utf-8')
        output = result.stdout
        match = re.search(r"Your code has been rated at (\d+\.\d+)/10", output)
        if match:
            score = float(match.group(1))
            print(f"✅ Pylint score: {score}/10")
            return score
        print(f"⚠️ Pylint score not found in output.")
        return 0.0
    except Exception as e:
        print(f"🚨 An error occurred while running Pylint: {e}")
        return 0.0

def run_mypy(file_path: str) -> tuple[bool, str]:
    """指定されたファイルに対してMyPyを実行し、(成功フラグ, 結果メッセージ)を返す"""
    print(f"🔬 Running MyPy on {file_path}...")
    command = ["mypy", file_path]
    try:
        result = subprocess.run(command, capture_output=True, text=True, encoding='utf-8')
        output = result.stdout + result.stderr
        if "Success: no issues found" in output:
            print("✅ MyPy found no issues.")
            return True, "Passed"
        else:
            error_summary = "\n".join(line for line in output.splitlines() if "error:" in line)
            print(f"❌ MyPy found issues.")
            return False, error_summary
    except Exception as e:
        print(f"🚨 An error occurred while running MyPy: {e}")
        return False, str(e)

def run_bandit(target_path: str) -> tuple[bool, str]:
    """指定されたパスに対してBanditを実行し、(成功フラグ, 結果メッセージ)を返す"""
    print(f"🔬 Running Bandit security scan on {target_path}...")
    command = ["bandit", "-r", target_path, "-f", "json"]
    try:
        result = subprocess.run(command, capture_output=True, text=True, encoding='utf-8')
        report = json.loads(result.stdout)
        high_medium_issues = [
            f"- {res['issue_text']} (Severity: {res['issue_severity']}, File: {res['filename']}:{res['line_number']})"
            for res in report["results"]
            if res["issue_severity"] in ["HIGH", "MEDIUM"]
        ]
        if not high_medium_issues:
            print("✅ Bandit: No high or medium severity issues found.")
            return True, "Passed"
        else:
            issue_summary = "\n".join(high_medium_issues)
            print("❌ Bandit found security issues.")
            return False, issue_summary
    except json.JSONDecodeError:
        print("✅ Bandit: No security issues reported.")
        return True, "Passed"
    except Exception as e:
        print(f"🚨 An error occurred while running Bandit: {e}")
        return False, str(e)

def run_pytest_cov(project_path: str) -> float:
    """
    指定されたプロジェクトパスを基準にテストとカバレッジ計測を実行する。
    設定はpyproject.tomlから読み込まれる。
    """
    print(f"🔬 Running pytest-cov on {project_path}...")
    # 設定ファイルがあるので、コマンドはシンプルに 'pytest' だけで良い
    command = ["pytest"]
    try:
        # cwdを指定して、対象プロジェクトのルートでコマンドを実行する
        result = subprocess.run(
            command,
            cwd=project_path,  # これが重要！
            capture_output=True,
            text=True,
            encoding='utf-8'
        )
        output = result.stdout
        match = re.search(r"TOTAL\s+\d+\s+\d+\s+(\d+)%", output)
        if match:
            coverage = float(match.group(1))
            print(f"✅ Pytest-cov coverage: {coverage}%")
            return coverage
        print(f"⚠️ Pytest-cov coverage not found. Output:\n{output}")
        return 0.0
    except Exception as e:
        print(f"🚨 An error occurred while running pytest-cov: {e}")
        return 0.0

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\tools\exports\export_20250803_114325\source_code\NexusCore\src\utils\code_analyzer.py ===
# src/utils/code_analyzer.py

import subprocess
import re
import json

def run_pylint(file_path: str) -> float:
    """指定されたファイルに対してPylintを実行し、スコアを返す"""
    print(f"🔬 Running Pylint on {file_path}...")
    command = ["pylint", file_path]
    try:
        result = subprocess.run(command, capture_output=True, text=True, encoding='utf-8')
        output = result.stdout
        match = re.search(r"Your code has been rated at (\d+\.\d+)/10", output)
        if match:
            score = float(match.group(1))
            print(f"✅ Pylint score: {score}/10")
            return score
        print(f"⚠️ Pylint score not found in output.")
        return 0.0
    except Exception as e:
        print(f"🚨 An error occurred while running Pylint: {e}")
        return 0.0

def run_mypy(file_path: str) -> tuple[bool, str]:
    """指定されたファイルに対してMyPyを実行し、(成功フラグ, 結果メッセージ)を返す"""
    print(f"🔬 Running MyPy on {file_path}...")
    command = ["mypy", file_path]
    try:
        result = subprocess.run(command, capture_output=True, text=True, encoding='utf-8')
        output = result.stdout + result.stderr
        if "Success: no issues found" in output:
            print("✅ MyPy found no issues.")
            return True, "Passed"
        else:
            error_summary = "\n".join(line for line in output.splitlines() if "error:" in line)
            print(f"❌ MyPy found issues.")
            return False, error_summary
    except Exception as e:
        print(f"🚨 An error occurred while running MyPy: {e}")
        return False, str(e)

def run_bandit(target_path: str) -> tuple[bool, str]:
    """指定されたパスに対してBanditを実行し、(成功フラグ, 結果メッセージ)を返す"""
    print(f"🔬 Running Bandit security scan on {target_path}...")
    command = ["bandit", "-r", target_path, "-f", "json"]
    try:
        result = subprocess.run(command, capture_output=True, text=True, encoding='utf-8')
        report = json.loads(result.stdout)
        high_medium_issues = [
            f"- {res['issue_text']} (Severity: {res['issue_severity']}, File: {res['filename']}:{res['line_number']})"
            for res in report["results"]
            if res["issue_severity"] in ["HIGH", "MEDIUM"]
        ]
        if not high_medium_issues:
            print("✅ Bandit: No high or medium severity issues found.")
            return True, "Passed"
        else:
            issue_summary = "\n".join(high_medium_issues)
            print("❌ Bandit found security issues.")
            return False, issue_summary
    except json.JSONDecodeError:
        print("✅ Bandit: No security issues reported.")
        return True, "Passed"
    except Exception as e:
        print(f"🚨 An error occurred while running Bandit: {e}")
        return False, str(e)

def run_pytest_cov(project_path: str) -> float:
    """
    指定されたプロジェクトパスを基準にテストとカバレッジ計測を実行する。
    設定はpyproject.tomlから読み込まれる。
    """
    print(f"🔬 Running pytest-cov on {project_path}...")
    # 設定ファイルがあるので、コマンドはシンプルに 'pytest' だけで良い
    command = ["pytest"]
    try:
        # cwdを指定して、対象プロジェクトのルートでコマンドを実行する
        result = subprocess.run(
            command,
            cwd=project_path,  # これが重要！
            capture_output=True,
            text=True,
            encoding='utf-8'
        )
        output = result.stdout
        match = re.search(r"TOTAL\s+\d+\s+\d+\s+(\d+)%", output)
        if match:
            coverage = float(match.group(1))
            print(f"✅ Pytest-cov coverage: {coverage}%")
            return coverage
        print(f"⚠️ Pytest-cov coverage not found. Output:\n{output}")
        return 0.0
    except Exception as e:
        print(f"🚨 An error occurred while running pytest-cov: {e}")
        return 0.0

# === NexusCore/src\nexuscore\npe\engine.py ===
# npe/engine.py

# あなたの優れたルーティングロジックをNPEに統合する
from .llms import get_llm_client, get_model_cost # llms.pyを改修
from .policies import context_scanner, secure_context_builder
from .logger import log_transaction
from .budget import budget_manager

class NexusProtocolEngine:
    def __init__(self):
        print("Nexus Protocol Engine (v2) with Economic Governance is running.")

    def process_task(self, prompt: str, metadata: dict, project_id="proj-001"):
        log_data = {"project_id": project_id, "task_metadata": metadata}

        # --- ガバナンス・フェーズ ---
        # 1. セキュリティスキャン (既存のNPE機能)
        context_type = context_scanner(prompt)
        log_data["context_type"] = context_type
        if context_type == "sensitive":
            print("[NPE Security] Sensitive data detected. Applying security protocols.")
            prompt = secure_context_builder(prompt) # マスキング
            log_data["is_masked"] = True

        # 2. ルーティング判断 (あなたのLLMRouterのロジックをここに統合)
        route_decision = self._analyze_task_for_npe(prompt, metadata, context_type)
        log_data["initial_route_decision"] = route_decision
        
        # 3. 経済性チェック (新機能)
        estimated_cost = get_model_cost(route_decision, prompt)
        log_data["estimated_cost"] = estimated_cost

        if not budget_manager.check_budget(project_id, estimated_cost):
            # 予算オーバーの場合、より安価なモデルにフォールバックする
            print(f"[NPE Economic] Budget insufficient. Attempting to reroute to a cheaper model.")
            original_decision = route_decision
            route_decision = self._fallback_to_cheaper_model(original_decision)
            log_data["rerouted_to"] = route_decision
            # 再度コストをチェック
            estimated_cost = get_model_cost(route_decision, prompt)
            if not budget_manager.check_budget(project_id, estimated_cost):
                print("[NPE Economic] ERROR: No cheaper model available within budget. Task aborted.")
                log_transaction({**log_data, "status": "aborted_budget_exceeded"})
                return "Error: Task aborted due to budget limits."
        
        log_data["final_route_decision"] = route_decision

        # --- 実行フェーズ ---
        print(f"[NPE Executor] Executing task with '{route_decision}'.")
        client = get_llm_client(route_decision)
        # result, actual_cost = client.generate(...) # 応答と実際のコストを取得
        
        # --- ここではダミーの結果とコストを返す ---
        result = f"Response from {route_decision}."
        actual_cost = estimated_cost * 1.05 # 若干の誤差をシミュレート
        
        # --- 記録フェーズ ---
        budget_manager.record_cost(project_id, actual_cost)
        log_data["status"] = "success"
        log_data["actual_cost"] = actual_cost
        log_transaction(log_data)
        
        return result

    def _analyze_task_for_npe(self, prompt: str, metadata: dict, context_type: str) -> str:
        """あなたのルーターロジックをNPE用に拡張・統合"""
        # セキュリティポリシーを最優先
        if context_type == "sensitive":
            # 機密情報が含まれている場合は、たとえどんなタスクでもローカルLLM（を想定した安価なモデル）に強制ルーティング
            return "anthropic_haiku" # 最も安価なモデルをローカルLLMの代理とする

        if metadata and metadata.get("task_type") == "code_generation":
            return "openai_gpt4o"
        
        if "要約してください" in prompt or "summarize" in prompt.lower():
            return "anthropic_sonnet"

        if len(prompt) > 10000:
            return "anthropic_claude3_opus"

        return "openai_gpt4o" # デフォルト

    def _fallback_to_cheaper_model(self, current_model: str) -> str:
        """より安価なモデルへのフォールバックロジック"""
        fallback_map = {
            "openai_gpt4o": "anthropic_sonnet",
            "anthropic_claude3_opus": "anthropic_sonnet",
            "anthropic_sonnet": "anthropic_haiku",
            "anthropic_haiku": "anthropic_haiku" # これ以上安いものはない
        }
        fallback_model = fallback_map.get(current_model, "anthropic_haiku")
        print(f"[NPE Economic] Fallback from '{current_model}' to '{fallback_model}'.")
        return fallback_model

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\src\utils\config.py ===
# フォルダ: src/utils
# ファイル名: config.py
# メモ: プロジェクト全体の設定値（APIキー、秘密鍵、データベース接続情報など）を
#      一元管理するためのファイルです。すべての設定はここから読み込みます。

import os
from dotenv import load_dotenv

# プロジェクトのルートにある.envファイルを読み込む
# このファイルの場所から2階層上のディレクトリをルートと仮定
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
dotenv_path = os.path.join(project_root, '.env')
load_dotenv(dotenv_path=dotenv_path)

class Config:
    """
    環境変数から設定を読み込むための設定クラス。
    アプリケーション全体でこのクラスのインスタンスをインポートして使用します。
    """
    # --- OpenAI API ---
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")# フォルダ: src/utils
# ファイル名: config.py
# メモ: プロジェクト全体の設定値（APIキー、秘密鍵、データベース接続情報など）を
#      一元管理するためのファイルです。すべての設定はここから読み込みます。

import os
from dotenv import load_dotenv

# プロジェクトのルートにある.envファイルを読み込む
# このファイルの場所から2階層上のディレクトリをルートと仮定
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
dotenv_path = os.path.join(project_root, '.env')
load_dotenv(dotenv_path=dotenv_path)

class Config:
    """
    環境変数から設定を読み込むための設定クラス。
    アプリケーション全体でこのクラスのインスタンスをインポートして使用します。
    """
    # --- OpenAI API ---
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

    # --- Gemini API (Multi-Agent System) ---
    # ◀️ マルチエージェントシステム用のAPIキーを追加
    # エージェントA（生成役）用のキー
    GEMINI_API_KEY_AGENT_A = os.getenv("GEMINI_API_KEY_AGENT_A")
    # エージェントB（批評・改善役）用のキー
    GEMINI_API_KEY_AGENT_B = os.getenv("GEMINI_API_KEY_AGENT_B")


    # --- Flask Application ---
    FLASK_SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "a-very-secret-key-for-development-only")
    
    # --- Database ---
    DATABASE_URI = os.getenv("DATABASE_URI", "sqlite:///db.sqlite3")
    
    # --- Celery (for background tasks) ---
    CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
    CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")

# アプリケーション全体で共有するためのConfigクラスのインスタンス
config = Config()

# APIキーが設定されていない場合に警告を表示
if not config.OPENAI_API_KEY:
    print("⚠️ 警告: OPENAI_API_KEYが.envファイルに設定されていません。")

# ◀️ Gemini APIキーの警告を追加
if not config.GEMINI_API_KEY_AGENT_A or not config.GEMINI_API_KEY_AGENT_B:
    print("⚠️ 警告: マルチエージェント用のGEMINI_API_KEYが設定されていません。")



    # --- Flask Application ---
    FLASK_SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "a-very-secret-key-for-development-only")
    
    # --- Database ---
    DATABASE_URI = os.getenv("DATABASE_URI", "sqlite:///db.sqlite3")
    
    # --- Celery (for background tasks) ---
    CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
    CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")

# アプリケーション全体で共有するためのConfigクラスのインスタンス
config = Config()

# APIキーが設定されていない場合に警告を表示
if not config.OPENAI_API_KEY:
    print("⚠️ 警告: OPENAI_API_KEYが.envファイルに設定されていません。")


# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\src\utils\config.py ===
# フォルダ: src/utils
# ファイル名: config.py
# メモ: プロジェクト全体の設定値（APIキー、秘密鍵、データベース接続情報など）を
#      一元管理するためのファイルです。すべての設定はここから読み込みます。

import os
from dotenv import load_dotenv

# プロジェクトのルートにある.envファイルを読み込む
# このファイルの場所から2階層上のディレクトリをルートと仮定
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
dotenv_path = os.path.join(project_root, '.env')
load_dotenv(dotenv_path=dotenv_path)

class Config:
    """
    環境変数から設定を読み込むための設定クラス。
    アプリケーション全体でこのクラスのインスタンスをインポートして使用します。
    """
    # --- OpenAI API ---
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")# フォルダ: src/utils
# ファイル名: config.py
# メモ: プロジェクト全体の設定値（APIキー、秘密鍵、データベース接続情報など）を
#      一元管理するためのファイルです。すべての設定はここから読み込みます。

import os
from dotenv import load_dotenv

# プロジェクトのルートにある.envファイルを読み込む
# このファイルの場所から2階層上のディレクトリをルートと仮定
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
dotenv_path = os.path.join(project_root, '.env')
load_dotenv(dotenv_path=dotenv_path)

class Config:
    """
    環境変数から設定を読み込むための設定クラス。
    アプリケーション全体でこのクラスのインスタンスをインポートして使用します。
    """
    # --- OpenAI API ---
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

    # --- Gemini API (Multi-Agent System) ---
    # ◀️ マルチエージェントシステム用のAPIキーを追加
    # エージェントA（生成役）用のキー
    GEMINI_API_KEY_AGENT_A = os.getenv("GEMINI_API_KEY_AGENT_A")
    # エージェントB（批評・改善役）用のキー
    GEMINI_API_KEY_AGENT_B = os.getenv("GEMINI_API_KEY_AGENT_B")


    # --- Flask Application ---
    FLASK_SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "a-very-secret-key-for-development-only")
    
    # --- Database ---
    DATABASE_URI = os.getenv("DATABASE_URI", "sqlite:///db.sqlite3")
    
    # --- Celery (for background tasks) ---
    CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
    CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")

# アプリケーション全体で共有するためのConfigクラスのインスタンス
config = Config()

# APIキーが設定されていない場合に警告を表示
if not config.OPENAI_API_KEY:
    print("⚠️ 警告: OPENAI_API_KEYが.envファイルに設定されていません。")

# ◀️ Gemini APIキーの警告を追加
if not config.GEMINI_API_KEY_AGENT_A or not config.GEMINI_API_KEY_AGENT_B:
    print("⚠️ 警告: マルチエージェント用のGEMINI_API_KEYが設定されていません。")



    # --- Flask Application ---
    FLASK_SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "a-very-secret-key-for-development-only")
    
    # --- Database ---
    DATABASE_URI = os.getenv("DATABASE_URI", "sqlite:///db.sqlite3")
    
    # --- Celery (for background tasks) ---
    CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
    CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")

# アプリケーション全体で共有するためのConfigクラスのインスタンス
config = Config()

# APIキーが設定されていない場合に警告を表示
if not config.OPENAI_API_KEY:
    print("⚠️ 警告: OPENAI_API_KEYが.envファイルに設定されていません。")


# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\tools\exports\export_20250803_114325\source_code\NexusCore\src\utils\config.py ===
# フォルダ: src/utils
# ファイル名: config.py
# メモ: プロジェクト全体の設定値（APIキー、秘密鍵、データベース接続情報など）を
#      一元管理するためのファイルです。すべての設定はここから読み込みます。

import os
from dotenv import load_dotenv

# プロジェクトのルートにある.envファイルを読み込む
# このファイルの場所から2階層上のディレクトリをルートと仮定
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
dotenv_path = os.path.join(project_root, '.env')
load_dotenv(dotenv_path=dotenv_path)

class Config:
    """
    環境変数から設定を読み込むための設定クラス。
    アプリケーション全体でこのクラスのインスタンスをインポートして使用します。
    """
    # --- OpenAI API ---
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")# フォルダ: src/utils
# ファイル名: config.py
# メモ: プロジェクト全体の設定値（APIキー、秘密鍵、データベース接続情報など）を
#      一元管理するためのファイルです。すべての設定はここから読み込みます。

import os
from dotenv import load_dotenv

# プロジェクトのルートにある.envファイルを読み込む
# このファイルの場所から2階層上のディレクトリをルートと仮定
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
dotenv_path = os.path.join(project_root, '.env')
load_dotenv(dotenv_path=dotenv_path)

class Config:
    """
    環境変数から設定を読み込むための設定クラス。
    アプリケーション全体でこのクラスのインスタンスをインポートして使用します。
    """
    # --- OpenAI API ---
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

    # --- Gemini API (Multi-Agent System) ---
    # ◀️ マルチエージェントシステム用のAPIキーを追加
    # エージェントA（生成役）用のキー
    GEMINI_API_KEY_AGENT_A = os.getenv("GEMINI_API_KEY_AGENT_A")
    # エージェントB（批評・改善役）用のキー
    GEMINI_API_KEY_AGENT_B = os.getenv("GEMINI_API_KEY_AGENT_B")


    # --- Flask Application ---
    FLASK_SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "a-very-secret-key-for-development-only")
    
    # --- Database ---
    DATABASE_URI = os.getenv("DATABASE_URI", "sqlite:///db.sqlite3")
    
    # --- Celery (for background tasks) ---
    CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
    CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")

# アプリケーション全体で共有するためのConfigクラスのインスタンス
config = Config()

# APIキーが設定されていない場合に警告を表示
if not config.OPENAI_API_KEY:
    print("⚠️ 警告: OPENAI_API_KEYが.envファイルに設定されていません。")

# ◀️ Gemini APIキーの警告を追加
if not config.GEMINI_API_KEY_AGENT_A or not config.GEMINI_API_KEY_AGENT_B:
    print("⚠️ 警告: マルチエージェント用のGEMINI_API_KEYが設定されていません。")



    # --- Flask Application ---
    FLASK_SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "a-very-secret-key-for-development-only")
    
    # --- Database ---
    DATABASE_URI = os.getenv("DATABASE_URI", "sqlite:///db.sqlite3")
    
    # --- Celery (for background tasks) ---
    CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
    CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")

# アプリケーション全体で共有するためのConfigクラスのインスタンス
config = Config()

# APIキーが設定されていない場合に警告を表示
if not config.OPENAI_API_KEY:
    print("⚠️ 警告: OPENAI_API_KEYが.envファイルに設定されていません。")


# === NexusCore/healing_sandbox\src\agents\base_agent.py ===
# ==============================================================================
# フォルダ: src/agents
# ファイル名: base_agent.py
# メモ: すべてのエージェントが自身のクラス名を冠した専用ロガーを持つように
#      アーキテクチャをアップグレード。
# ==============================================================================
import json
import logging # ロギングをインポート
from openai import OpenAI
import google.generativeai as genai

class BaseAgent:
    def __init__(self, api_key: str, model: str):
        # --- ★★★★★ ここからが最重要修正点 ★★★★★ ---
        # 自分自身のクラス名をロガー名として、専用のロガーインスタンスを取得
        self.logger = logging.getLogger(self.__class__.__name__)
        # --- ★★★★★ ここまで ★★★★★ ---

        self.model = model
        self.client = None
        self.provider = None

        if "gpt" in model.lower():
            if not api_key or api_key == "dummy_key":
                raise ValueError("GPTモデルを使用するには、有効なOpenAI APIキーが必要です。")
            self.client = OpenAI(api_key=api_key)
            self.provider = "openai"
            self.logger.info(f"OpenAI client initialized for model: {self.model}")

        elif "gemini" in model.lower():
            if not api_key or api_key == "dummy_key":
                raise ValueError("Geminiモデルを使用するには、有効なGoogle APIキーが必要です。")
            genai.configure(api_key=api_key)
            self.client = genai.GenerativeModel(model)
            self.provider = "google"
            self.logger.info(f"Google Gemini client initialized for model: {self.model}")

        elif "dummy" in model.lower():
            self.provider = "dummy"
            self.logger.info("BaseAgent initialized in DUMMY mode for testing. No API client will be used.")
        
        else:
            raise ValueError(f"Unsupported or unknown model specified: {self.model}. Must contain 'gpt', 'gemini', or 'dummy'.")

    def _call_llm(self, prompt: str, system_prompt: str, temperature: float = 0.1, as_json: bool = False) -> str:
        """
        プロバイダーに応じて適切なLLM呼び出しメソッドを振り分ける。
        """
        self.logger.debug(f"Calling LLM. Provider: {self.provider}, JSON mode: {as_json}")
        if self.provider == "openai":
            return self._call_openai(prompt, system_prompt, temperature, as_json)
        elif self.provider == "google":
            return self._call_gemini(prompt, system_prompt, temperature, as_json)
        elif self.provider == "dummy":
            self.logger.warning("LLM call attempted in DUMMY mode. Returning empty string.")
            return json.dumps({"response": "dummy response"}) if as_json else "dummy response"
        else:
            self.logger.error(f"LLM provider '{self.provider}' is not implemented.")
            raise NotImplementedError(f"LLM provider '{self.provider}' is not implemented.")

    def _call_openai(self, prompt: str, system_prompt: str, temperature: float, as_json: bool) -> str:
        # (実装は変更なし)
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]
        response_format = {"type": "json_object"} if as_json else {"type": "text"}
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            response_format=response_format
        )
        return response.choices[0].message.content.strip()

    def _call_gemini(self, prompt: str, system_prompt: str, temperature: float, as_json: bool) -> str:
        # (実装は変更なし)
        generation_config = genai.types.GenerationConfig(
            temperature=temperature,
            response_mime_type="application/json" if as_json else "text/plain"
        )
        full_prompt = f"{system_prompt}\\n\\n---\\n\\n{prompt}"
        
        response = self.client.generate_content(
            full_prompt,
            generation_config=generation_config
        )
        return response.text.strip()

# === NexusCore/src\streamlit_legacy.py ===
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

# === NexusCore/src\nexuscore\agents\policy_agent.py ===
# ==============================================================================
# フォルダ: src/agents
# ファイル名: policy_agent.py
# メモ: テスト成功後、Guardianのレビュー前に介入する品質ゲート。
#      BaseAgentを継承し、既存アーキテクチャに準拠。
# ==============================================================================

import json
import re
from .base_agent import BaseAgent

class PolicyAgent(BaseAgent):
    """
    コードが事前に定義されたポリシー（規約）に準拠しているかを監査するエージェント。
    LLMを呼び出さず、設定ファイルに基づいて機械的にチェックを行う。
    """
    def __init__(self, api_key: str, model: str, policy_rules_path: str = "config/policy_rules.json"):
        """
        PolicyAgentを初期化する。
        LLMは使用しないが、BaseAgentのインターフェースに合わせるため引数を受け取る。
        """
        # BaseAgentの初期化を呼び出し、主にロガーをセットアップ
        super().__init__(api_key, model)
        
        try:
            with open(policy_rules_path, 'r', encoding='utf-8') as f:
                self.policies = json.load(f)
            self.logger.info(f"Loaded {len(self.policies)} policies from {policy_rules_path}")
        except FileNotFoundError:
            self.logger.error(f"Policy rules file not found at: {policy_rules_path}. No policies will be enforced.")
            self.policies = []
        except json.JSONDecodeError:
            self.logger.error(f"Failed to parse JSON from {policy_rules_path}. Check for syntax errors.")
            self.policies = []


    def audit(self, files_to_check: list) -> dict:
        """
        与えられたファイル群を監査し、監査結果を返す。

        Args:
            files_to_check (list): ファイルパスとコンテンツを含む辞書のリスト。
                                  例: [{"path": "app/main.py", "content": "..."}]

        Returns:
            dict: 監査結果。'result'キーに'APPROVED'または'REJECTED'、
                  'violations'キーに違反リストが含まれる。
        """
        all_violations = []
        self.logger.info(f"Starting policy audit for {len(files_to_check)} file(s)...")

        if not self.policies:
            self.logger.warning("No policies loaded. Skipping audit and approving by default.")
            return {"result": "APPROVED", "violations": []}

        for file_info in files_to_check:
            file_path = file_info.get("path")
            content = file_info.get("content")
            if not file_path or content is None:
                continue

            for policy in self.policies:
                # ポリシーに必要なキーが存在するかチェック
                if not all(k in policy for k in ["policy_id", "detection_pattern", "severity", "description"]):
                    self.logger.warning(f"Skipping malformed policy: {policy.get('policy_id', 'N/A')}")
                    continue

                # ターゲットファイルパターンに一致するかチェック
                if re.search(policy.get("target_file_pattern", ".*"), file_path):
                    for i, line in enumerate(content.splitlines()):
                        if re.search(policy["detection_pattern"], line):
                            violation = {
                                "file_path": file_path,
                                "line_number": i + 1,
                                "policy_id": policy["policy_id"],
                                "severity": policy["severity"],
                                "description": policy["description"],
                                "suggestion": policy.get("suggestion", "No specific suggestion.")
                            }
                            all_violations.append(violation)
                            self.logger.warning(f"Policy violation found: {violation}")

        result = "APPROVED" if not all_violations else "REJECTED"
        self.logger.info(f"Policy audit finished. Result: {result}, Violations: {len(all_violations)}")
        
        return {
            "result": result,
            "violations": all_violations
        }

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\healing_sandbox\src\agents\base_agent.py ===
# ==============================================================================
# フォルダ: src/agents
# ファイル名: base_agent.py
# メモ: すべてのエージェントが自身のクラス名を冠した専用ロガーを持つように
#      アーキテクチャをアップグレード。
# ==============================================================================
import json
import logging # ロギングをインポート
from openai import OpenAI
import google.generativeai as genai

class BaseAgent:
    def __init__(self, api_key: str, model: str):
        # --- ★★★★★ ここからが最重要修正点 ★★★★★ ---
        # 自分自身のクラス名をロガー名として、専用のロガーインスタンスを取得
        self.logger = logging.getLogger(self.__class__.__name__)
        # --- ★★★★★ ここまで ★★★★★ ---

        self.model = model
        self.client = None
        self.provider = None

        if "gpt" in model.lower():
            if not api_key or api_key == "dummy_key":
                raise ValueError("GPTモデルを使用するには、有効なOpenAI APIキーが必要です。")
            self.client = OpenAI(api_key=api_key)
            self.provider = "openai"
            self.logger.info(f"OpenAI client initialized for model: {self.model}")

        elif "gemini" in model.lower():
            if not api_key or api_key == "dummy_key":
                raise ValueError("Geminiモデルを使用するには、有効なGoogle APIキーが必要です。")
            genai.configure(api_key=api_key)
            self.client = genai.GenerativeModel(model)
            self.provider = "google"
            self.logger.info(f"Google Gemini client initialized for model: {self.model}")

        elif "dummy" in model.lower():
            self.provider = "dummy"
            self.logger.info("BaseAgent initialized in DUMMY mode for testing. No API client will be used.")
        
        else:
            raise ValueError(f"Unsupported or unknown model specified: {self.model}. Must contain 'gpt', 'gemini', or 'dummy'.")

    def _call_llm(self, prompt: str, system_prompt: str, temperature: float = 0.1, as_json: bool = False) -> str:
        """
        プロバイダーに応じて適切なLLM呼び出しメソッドを振り分ける。
        """
        self.logger.debug(f"Calling LLM. Provider: {self.provider}, JSON mode: {as_json}")
        if self.provider == "openai":
            return self._call_openai(prompt, system_prompt, temperature, as_json)
        elif self.provider == "google":
            return self._call_gemini(prompt, system_prompt, temperature, as_json)
        elif self.provider == "dummy":
            self.logger.warning("LLM call attempted in DUMMY mode. Returning empty string.")
            return json.dumps({"response": "dummy response"}) if as_json else "dummy response"
        else:
            self.logger.error(f"LLM provider '{self.provider}' is not implemented.")
            raise NotImplementedError(f"LLM provider '{self.provider}' is not implemented.")

    def _call_openai(self, prompt: str, system_prompt: str, temperature: float, as_json: bool) -> str:
        # (実装は変更なし)
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]
        response_format = {"type": "json_object"} if as_json else {"type": "text"}
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            response_format=response_format
        )
        return response.choices[0].message.content.strip()

    def _call_gemini(self, prompt: str, system_prompt: str, temperature: float, as_json: bool) -> str:
        # (実装は変更なし)
        generation_config = genai.types.GenerationConfig(
            temperature=temperature,
            response_mime_type="application/json" if as_json else "text/plain"
        )
        full_prompt = f"{system_prompt}\\n\\n---\\n\\n{prompt}"
        
        response = self.client.generate_content(
            full_prompt,
            generation_config=generation_config
        )
        return response.text.strip()

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\src\streamlit_legacy.py ===
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

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\src\agents\base_agent.py ===
# ==============================================================================
# フォルダ: src/agents
# ファイル名: base_agent.py
# メモ: すべてのエージェントが自身のクラス名を冠した専用ロガーを持つように
#      アーキテクチャをアップグレード。
# ==============================================================================
import json
import logging # ロギングをインポート
from openai import OpenAI
import google.generativeai as genai

class BaseAgent:
    def __init__(self, api_key: str, model: str):
        # --- ★★★★★ ここからが最重要修正点 ★★★★★ ---
        # 自分自身のクラス名をロガー名として、専用のロガーインスタンスを取得
        self.logger = logging.getLogger(self.__class__.__name__)
        # --- ★★★★★ ここまで ★★★★★ ---

        self.model = model
        self.client = None
        self.provider = None

        if "gpt" in model.lower():
            if not api_key or api_key == "dummy_key":
                raise ValueError("GPTモデルを使用するには、有効なOpenAI APIキーが必要です。")
            self.client = OpenAI(api_key=api_key)
            self.provider = "openai"
            self.logger.info(f"OpenAI client initialized for model: {self.model}")

        elif "gemini" in model.lower():
            if not api_key or api_key == "dummy_key":
                raise ValueError("Geminiモデルを使用するには、有効なGoogle APIキーが必要です。")
            genai.configure(api_key=api_key)
            self.client = genai.GenerativeModel(model)
            self.provider = "google"
            self.logger.info(f"Google Gemini client initialized for model: {self.model}")

        elif "dummy" in model.lower():
            self.provider = "dummy"
            self.logger.info("BaseAgent initialized in DUMMY mode for testing. No API client will be used.")
        
        else:
            raise ValueError(f"Unsupported or unknown model specified: {self.model}. Must contain 'gpt', 'gemini', or 'dummy'.")

    def _call_llm(self, prompt: str, system_prompt: str, temperature: float = 0.1, as_json: bool = False) -> str:
        """
        プロバイダーに応じて適切なLLM呼び出しメソッドを振り分ける。
        """
        self.logger.debug(f"Calling LLM. Provider: {self.provider}, JSON mode: {as_json}")
        if self.provider == "openai":
            return self._call_openai(prompt, system_prompt, temperature, as_json)
        elif self.provider == "google":
            return self._call_gemini(prompt, system_prompt, temperature, as_json)
        elif self.provider == "dummy":
            self.logger.warning("LLM call attempted in DUMMY mode. Returning empty string.")
            return json.dumps({"response": "dummy response"}) if as_json else "dummy response"
        else:
            self.logger.error(f"LLM provider '{self.provider}' is not implemented.")
            raise NotImplementedError(f"LLM provider '{self.provider}' is not implemented.")

    def _call_openai(self, prompt: str, system_prompt: str, temperature: float, as_json: bool) -> str:
        # (実装は変更なし)
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]
        response_format = {"type": "json_object"} if as_json else {"type": "text"}
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            response_format=response_format
        )
        return response.choices[0].message.content.strip()

    def _call_gemini(self, prompt: str, system_prompt: str, temperature: float, as_json: bool) -> str:
        # (実装は変更なし)
        generation_config = genai.types.GenerationConfig(
            temperature=temperature,
            response_mime_type="application/json" if as_json else "text/plain"
        )
        full_prompt = f"{system_prompt}\\n\\n---\\n\\n{prompt}"
        
        response = self.client.generate_content(
            full_prompt,
            generation_config=generation_config
        )
        return response.text.strip()

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\src\agents\policy_agent.py ===
# ==============================================================================
# フォルダ: src/agents
# ファイル名: policy_agent.py
# メモ: テスト成功後、Guardianのレビュー前に介入する品質ゲート。
#      BaseAgentを継承し、既存アーキテクチャに準拠。
# ==============================================================================

import json
import re
from .base_agent import BaseAgent

class PolicyAgent(BaseAgent):
    """
    コードが事前に定義されたポリシー（規約）に準拠しているかを監査するエージェント。
    LLMを呼び出さず、設定ファイルに基づいて機械的にチェックを行う。
    """
    def __init__(self, api_key: str, model: str, policy_rules_path: str = "config/policy_rules.json"):
        """
        PolicyAgentを初期化する。
        LLMは使用しないが、BaseAgentのインターフェースに合わせるため引数を受け取る。
        """
        # BaseAgentの初期化を呼び出し、主にロガーをセットアップ
        super().__init__(api_key, model)
        
        try:
            with open(policy_rules_path, 'r', encoding='utf-8') as f:
                self.policies = json.load(f)
            self.logger.info(f"Loaded {len(self.policies)} policies from {policy_rules_path}")
        except FileNotFoundError:
            self.logger.error(f"Policy rules file not found at: {policy_rules_path}. No policies will be enforced.")
            self.policies = []
        except json.JSONDecodeError:
            self.logger.error(f"Failed to parse JSON from {policy_rules_path}. Check for syntax errors.")
            self.policies = []


    def audit(self, files_to_check: list) -> dict:
        """
        与えられたファイル群を監査し、監査結果を返す。

        Args:
            files_to_check (list): ファイルパスとコンテンツを含む辞書のリスト。
                                  例: [{"path": "app/main.py", "content": "..."}]

        Returns:
            dict: 監査結果。'result'キーに'APPROVED'または'REJECTED'、
                  'violations'キーに違反リストが含まれる。
        """
        all_violations = []
        self.logger.info(f"Starting policy audit for {len(files_to_check)} file(s)...")

        if not self.policies:
            self.logger.warning("No policies loaded. Skipping audit and approving by default.")
            return {"result": "APPROVED", "violations": []}

        for file_info in files_to_check:
            file_path = file_info.get("path")
            content = file_info.get("content")
            if not file_path or content is None:
                continue

            for policy in self.policies:
                # ポリシーに必要なキーが存在するかチェック
                if not all(k in policy for k in ["policy_id", "detection_pattern", "severity", "description"]):
                    self.logger.warning(f"Skipping malformed policy: {policy.get('policy_id', 'N/A')}")
                    continue

                # ターゲットファイルパターンに一致するかチェック
                if re.search(policy.get("target_file_pattern", ".*"), file_path):
                    for i, line in enumerate(content.splitlines()):
                        if re.search(policy["detection_pattern"], line):
                            violation = {
                                "file_path": file_path,
                                "line_number": i + 1,
                                "policy_id": policy["policy_id"],
                                "severity": policy["severity"],
                                "description": policy["description"],
                                "suggestion": policy.get("suggestion", "No specific suggestion.")
                            }
                            all_violations.append(violation)
                            self.logger.warning(f"Policy violation found: {violation}")

        result = "APPROVED" if not all_violations else "REJECTED"
        self.logger.info(f"Policy audit finished. Result: {result}, Violations: {len(all_violations)}")
        
        return {
            "result": result,
            "violations": all_violations
        }

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\healing_sandbox\src\agents\base_agent.py ===
# ==============================================================================
# フォルダ: src/agents
# ファイル名: base_agent.py
# メモ: すべてのエージェントが自身のクラス名を冠した専用ロガーを持つように
#      アーキテクチャをアップグレード。
# ==============================================================================
import json
import logging # ロギングをインポート
from openai import OpenAI
import google.generativeai as genai

class BaseAgent:
    def __init__(self, api_key: str, model: str):
        # --- ★★★★★ ここからが最重要修正点 ★★★★★ ---
        # 自分自身のクラス名をロガー名として、専用のロガーインスタンスを取得
        self.logger = logging.getLogger(self.__class__.__name__)
        # --- ★★★★★ ここまで ★★★★★ ---

        self.model = model
        self.client = None
        self.provider = None

        if "gpt" in model.lower():
            if not api_key or api_key == "dummy_key":
                raise ValueError("GPTモデルを使用するには、有効なOpenAI APIキーが必要です。")
            self.client = OpenAI(api_key=api_key)
            self.provider = "openai"
            self.logger.info(f"OpenAI client initialized for model: {self.model}")

        elif "gemini" in model.lower():
            if not api_key or api_key == "dummy_key":
                raise ValueError("Geminiモデルを使用するには、有効なGoogle APIキーが必要です。")
            genai.configure(api_key=api_key)
            self.client = genai.GenerativeModel(model)
            self.provider = "google"
            self.logger.info(f"Google Gemini client initialized for model: {self.model}")

        elif "dummy" in model.lower():
            self.provider = "dummy"
            self.logger.info("BaseAgent initialized in DUMMY mode for testing. No API client will be used.")
        
        else:
            raise ValueError(f"Unsupported or unknown model specified: {self.model}. Must contain 'gpt', 'gemini', or 'dummy'.")

    def _call_llm(self, prompt: str, system_prompt: str, temperature: float = 0.1, as_json: bool = False) -> str:
        """
        プロバイダーに応じて適切なLLM呼び出しメソッドを振り分ける。
        """
        self.logger.debug(f"Calling LLM. Provider: {self.provider}, JSON mode: {as_json}")
        if self.provider == "openai":
            return self._call_openai(prompt, system_prompt, temperature, as_json)
        elif self.provider == "google":
            return self._call_gemini(prompt, system_prompt, temperature, as_json)
        elif self.provider == "dummy":
            self.logger.warning("LLM call attempted in DUMMY mode. Returning empty string.")
            return json.dumps({"response": "dummy response"}) if as_json else "dummy response"
        else:
            self.logger.error(f"LLM provider '{self.provider}' is not implemented.")
            raise NotImplementedError(f"LLM provider '{self.provider}' is not implemented.")

    def _call_openai(self, prompt: str, system_prompt: str, temperature: float, as_json: bool) -> str:
        # (実装は変更なし)
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]
        response_format = {"type": "json_object"} if as_json else {"type": "text"}
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            response_format=response_format
        )
        return response.choices[0].message.content.strip()

    def _call_gemini(self, prompt: str, system_prompt: str, temperature: float, as_json: bool) -> str:
        # (実装は変更なし)
        generation_config = genai.types.GenerationConfig(
            temperature=temperature,
            response_mime_type="application/json" if as_json else "text/plain"
        )
        full_prompt = f"{system_prompt}\\n\\n---\\n\\n{prompt}"
        
        response = self.client.generate_content(
            full_prompt,
            generation_config=generation_config
        )
        return response.text.strip()

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\src\streamlit_legacy.py ===
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

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\src\agents\base_agent.py ===
# ==============================================================================
# フォルダ: src/agents
# ファイル名: base_agent.py
# メモ: すべてのエージェントが自身のクラス名を冠した専用ロガーを持つように
#      アーキテクチャをアップグレード。
# ==============================================================================
import json
import logging # ロギングをインポート
from openai import OpenAI
import google.generativeai as genai

class BaseAgent:
    def __init__(self, api_key: str, model: str):
        # --- ★★★★★ ここからが最重要修正点 ★★★★★ ---
        # 自分自身のクラス名をロガー名として、専用のロガーインスタンスを取得
        self.logger = logging.getLogger(self.__class__.__name__)
        # --- ★★★★★ ここまで ★★★★★ ---

        self.model = model
        self.client = None
        self.provider = None

        if "gpt" in model.lower():
            if not api_key or api_key == "dummy_key":
                raise ValueError("GPTモデルを使用するには、有効なOpenAI APIキーが必要です。")
            self.client = OpenAI(api_key=api_key)
            self.provider = "openai"
            self.logger.info(f"OpenAI client initialized for model: {self.model}")

        elif "gemini" in model.lower():
            if not api_key or api_key == "dummy_key":
                raise ValueError("Geminiモデルを使用するには、有効なGoogle APIキーが必要です。")
            genai.configure(api_key=api_key)
            self.client = genai.GenerativeModel(model)
            self.provider = "google"
            self.logger.info(f"Google Gemini client initialized for model: {self.model}")

        elif "dummy" in model.lower():
            self.provider = "dummy"
            self.logger.info("BaseAgent initialized in DUMMY mode for testing. No API client will be used.")
        
        else:
            raise ValueError(f"Unsupported or unknown model specified: {self.model}. Must contain 'gpt', 'gemini', or 'dummy'.")

    def _call_llm(self, prompt: str, system_prompt: str, temperature: float = 0.1, as_json: bool = False) -> str:
        """
        プロバイダーに応じて適切なLLM呼び出しメソッドを振り分ける。
        """
        self.logger.debug(f"Calling LLM. Provider: {self.provider}, JSON mode: {as_json}")
        if self.provider == "openai":
            return self._call_openai(prompt, system_prompt, temperature, as_json)
        elif self.provider == "google":
            return self._call_gemini(prompt, system_prompt, temperature, as_json)
        elif self.provider == "dummy":
            self.logger.warning("LLM call attempted in DUMMY mode. Returning empty string.")
            return json.dumps({"response": "dummy response"}) if as_json else "dummy response"
        else:
            self.logger.error(f"LLM provider '{self.provider}' is not implemented.")
            raise NotImplementedError(f"LLM provider '{self.provider}' is not implemented.")

    def _call_openai(self, prompt: str, system_prompt: str, temperature: float, as_json: bool) -> str:
        # (実装は変更なし)
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]
        response_format = {"type": "json_object"} if as_json else {"type": "text"}
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            response_format=response_format
        )
        return response.choices[0].message.content.strip()

    def _call_gemini(self, prompt: str, system_prompt: str, temperature: float, as_json: bool) -> str:
        # (実装は変更なし)
        generation_config = genai.types.GenerationConfig(
            temperature=temperature,
            response_mime_type="application/json" if as_json else "text/plain"
        )
        full_prompt = f"{system_prompt}\\n\\n---\\n\\n{prompt}"
        
        response = self.client.generate_content(
            full_prompt,
            generation_config=generation_config
        )
        return response.text.strip()

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\src\agents\policy_agent.py ===
# ==============================================================================
# フォルダ: src/agents
# ファイル名: policy_agent.py
# メモ: テスト成功後、Guardianのレビュー前に介入する品質ゲート。
#      BaseAgentを継承し、既存アーキテクチャに準拠。
# ==============================================================================

import json
import re
from .base_agent import BaseAgent

class PolicyAgent(BaseAgent):
    """
    コードが事前に定義されたポリシー（規約）に準拠しているかを監査するエージェント。
    LLMを呼び出さず、設定ファイルに基づいて機械的にチェックを行う。
    """
    def __init__(self, api_key: str, model: str, policy_rules_path: str = "config/policy_rules.json"):
        """
        PolicyAgentを初期化する。
        LLMは使用しないが、BaseAgentのインターフェースに合わせるため引数を受け取る。
        """
        # BaseAgentの初期化を呼び出し、主にロガーをセットアップ
        super().__init__(api_key, model)
        
        try:
            with open(policy_rules_path, 'r', encoding='utf-8') as f:
                self.policies = json.load(f)
            self.logger.info(f"Loaded {len(self.policies)} policies from {policy_rules_path}")
        except FileNotFoundError:
            self.logger.error(f"Policy rules file not found at: {policy_rules_path}. No policies will be enforced.")
            self.policies = []
        except json.JSONDecodeError:
            self.logger.error(f"Failed to parse JSON from {policy_rules_path}. Check for syntax errors.")
            self.policies = []


    def audit(self, files_to_check: list) -> dict:
        """
        与えられたファイル群を監査し、監査結果を返す。

        Args:
            files_to_check (list): ファイルパスとコンテンツを含む辞書のリスト。
                                  例: [{"path": "app/main.py", "content": "..."}]

        Returns:
            dict: 監査結果。'result'キーに'APPROVED'または'REJECTED'、
                  'violations'キーに違反リストが含まれる。
        """
        all_violations = []
        self.logger.info(f"Starting policy audit for {len(files_to_check)} file(s)...")

        if not self.policies:
            self.logger.warning("No policies loaded. Skipping audit and approving by default.")
            return {"result": "APPROVED", "violations": []}

        for file_info in files_to_check:
            file_path = file_info.get("path")
            content = file_info.get("content")
            if not file_path or content is None:
                continue

            for policy in self.policies:
                # ポリシーに必要なキーが存在するかチェック
                if not all(k in policy for k in ["policy_id", "detection_pattern", "severity", "description"]):
                    self.logger.warning(f"Skipping malformed policy: {policy.get('policy_id', 'N/A')}")
                    continue

                # ターゲットファイルパターンに一致するかチェック
                if re.search(policy.get("target_file_pattern", ".*"), file_path):
                    for i, line in enumerate(content.splitlines()):
                        if re.search(policy["detection_pattern"], line):
                            violation = {
                                "file_path": file_path,
                                "line_number": i + 1,
                                "policy_id": policy["policy_id"],
                                "severity": policy["severity"],
                                "description": policy["description"],
                                "suggestion": policy.get("suggestion", "No specific suggestion.")
                            }
                            all_violations.append(violation)
                            self.logger.warning(f"Policy violation found: {violation}")

        result = "APPROVED" if not all_violations else "REJECTED"
        self.logger.info(f"Policy audit finished. Result: {result}, Violations: {len(all_violations)}")
        
        return {
            "result": result,
            "violations": all_violations
        }

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\tools\exports\export_20250803_114325\source_code\NexusCore\src\streamlit_legacy.py ===
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

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\tools\exports\export_20250803_114325\source_code\NexusCore\src\agents\base_agent.py ===
# ==============================================================================
# フォルダ: src/agents
# ファイル名: base_agent.py
# メモ: すべてのエージェントが自身のクラス名を冠した専用ロガーを持つように
#      アーキテクチャをアップグレード。
# ==============================================================================
import json
import logging # ロギングをインポート
from openai import OpenAI
import google.generativeai as genai

class BaseAgent:
    def __init__(self, api_key: str, model: str):
        # --- ★★★★★ ここからが最重要修正点 ★★★★★ ---
        # 自分自身のクラス名をロガー名として、専用のロガーインスタンスを取得
        self.logger = logging.getLogger(self.__class__.__name__)
        # --- ★★★★★ ここまで ★★★★★ ---

        self.model = model
        self.client = None
        self.provider = None

        if "gpt" in model.lower():
            if not api_key or api_key == "dummy_key":
                raise ValueError("GPTモデルを使用するには、有効なOpenAI APIキーが必要です。")
            self.client = OpenAI(api_key=api_key)
            self.provider = "openai"
            self.logger.info(f"OpenAI client initialized for model: {self.model}")

        elif "gemini" in model.lower():
            if not api_key or api_key == "dummy_key":
                raise ValueError("Geminiモデルを使用するには、有効なGoogle APIキーが必要です。")
            genai.configure(api_key=api_key)
            self.client = genai.GenerativeModel(model)
            self.provider = "google"
            self.logger.info(f"Google Gemini client initialized for model: {self.model}")

        elif "dummy" in model.lower():
            self.provider = "dummy"
            self.logger.info("BaseAgent initialized in DUMMY mode for testing. No API client will be used.")
        
        else:
            raise ValueError(f"Unsupported or unknown model specified: {self.model}. Must contain 'gpt', 'gemini', or 'dummy'.")

    def _call_llm(self, prompt: str, system_prompt: str, temperature: float = 0.1, as_json: bool = False) -> str:
        """
        プロバイダーに応じて適切なLLM呼び出しメソッドを振り分ける。
        """
        self.logger.debug(f"Calling LLM. Provider: {self.provider}, JSON mode: {as_json}")
        if self.provider == "openai":
            return self._call_openai(prompt, system_prompt, temperature, as_json)
        elif self.provider == "google":
            return self._call_gemini(prompt, system_prompt, temperature, as_json)
        elif self.provider == "dummy":
            self.logger.warning("LLM call attempted in DUMMY mode. Returning empty string.")
            return json.dumps({"response": "dummy response"}) if as_json else "dummy response"
        else:
            self.logger.error(f"LLM provider '{self.provider}' is not implemented.")
            raise NotImplementedError(f"LLM provider '{self.provider}' is not implemented.")

    def _call_openai(self, prompt: str, system_prompt: str, temperature: float, as_json: bool) -> str:
        # (実装は変更なし)
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]
        response_format = {"type": "json_object"} if as_json else {"type": "text"}
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            response_format=response_format
        )
        return response.choices[0].message.content.strip()

    def _call_gemini(self, prompt: str, system_prompt: str, temperature: float, as_json: bool) -> str:
        # (実装は変更なし)
        generation_config = genai.types.GenerationConfig(
            temperature=temperature,
            response_mime_type="application/json" if as_json else "text/plain"
        )
        full_prompt = f"{system_prompt}\\n\\n---\\n\\n{prompt}"
        
        response = self.client.generate_content(
            full_prompt,
            generation_config=generation_config
        )
        return response.text.strip()

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\tools\exports\export_20250803_114325\source_code\NexusCore\src\agents\policy_agent.py ===
# ==============================================================================
# フォルダ: src/agents
# ファイル名: policy_agent.py
# メモ: テスト成功後、Guardianのレビュー前に介入する品質ゲート。
#      BaseAgentを継承し、既存アーキテクチャに準拠。
# ==============================================================================

import json
import re
from .base_agent import BaseAgent

class PolicyAgent(BaseAgent):
    """
    コードが事前に定義されたポリシー（規約）に準拠しているかを監査するエージェント。
    LLMを呼び出さず、設定ファイルに基づいて機械的にチェックを行う。
    """
    def __init__(self, api_key: str, model: str, policy_rules_path: str = "config/policy_rules.json"):
        """
        PolicyAgentを初期化する。
        LLMは使用しないが、BaseAgentのインターフェースに合わせるため引数を受け取る。
        """
        # BaseAgentの初期化を呼び出し、主にロガーをセットアップ
        super().__init__(api_key, model)
        
        try:
            with open(policy_rules_path, 'r', encoding='utf-8') as f:
                self.policies = json.load(f)
            self.logger.info(f"Loaded {len(self.policies)} policies from {policy_rules_path}")
        except FileNotFoundError:
            self.logger.error(f"Policy rules file not found at: {policy_rules_path}. No policies will be enforced.")
            self.policies = []
        except json.JSONDecodeError:
            self.logger.error(f"Failed to parse JSON from {policy_rules_path}. Check for syntax errors.")
            self.policies = []


    def audit(self, files_to_check: list) -> dict:
        """
        与えられたファイル群を監査し、監査結果を返す。

        Args:
            files_to_check (list): ファイルパスとコンテンツを含む辞書のリスト。
                                  例: [{"path": "app/main.py", "content": "..."}]

        Returns:
            dict: 監査結果。'result'キーに'APPROVED'または'REJECTED'、
                  'violations'キーに違反リストが含まれる。
        """
        all_violations = []
        self.logger.info(f"Starting policy audit for {len(files_to_check)} file(s)...")

        if not self.policies:
            self.logger.warning("No policies loaded. Skipping audit and approving by default.")
            return {"result": "APPROVED", "violations": []}

        for file_info in files_to_check:
            file_path = file_info.get("path")
            content = file_info.get("content")
            if not file_path or content is None:
                continue

            for policy in self.policies:
                # ポリシーに必要なキーが存在するかチェック
                if not all(k in policy for k in ["policy_id", "detection_pattern", "severity", "description"]):
                    self.logger.warning(f"Skipping malformed policy: {policy.get('policy_id', 'N/A')}")
                    continue

                # ターゲットファイルパターンに一致するかチェック
                if re.search(policy.get("target_file_pattern", ".*"), file_path):
                    for i, line in enumerate(content.splitlines()):
                        if re.search(policy["detection_pattern"], line):
                            violation = {
                                "file_path": file_path,
                                "line_number": i + 1,
                                "policy_id": policy["policy_id"],
                                "severity": policy["severity"],
                                "description": policy["description"],
                                "suggestion": policy.get("suggestion", "No specific suggestion.")
                            }
                            all_violations.append(violation)
                            self.logger.warning(f"Policy violation found: {violation}")

        result = "APPROVED" if not all_violations else "REJECTED"
        self.logger.info(f"Policy audit finished. Result: {result}, Violations: {len(all_violations)}")
        
        return {
            "result": result,
            "violations": all_violations
        }

# === NexusCore/src\nexuscore\utils\const.py ===
TOOLS_CODE = """
import numpy as np
import pandas as pd 
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
import os,sys
import re
from datetime import datetime
from sympy import symbols, Eq, solve
import torch 
import requests
from bs4 import BeautifulSoup
import json
import math
import yfinance
import time
"""

write_denial_function = 'lambda *args, **kwargs: (_ for _ in ()).throw(PermissionError("Writing to disk operation is not permitted due to safety reasons. Please do not try again!"))'
read_denial_function = 'lambda *args, **kwargs: (_ for _ in ()).throw(PermissionError("Reading from disk operation is not permitted due to safety reasons. Please do not try again!"))'
class_denial = """Class Denial:
    def __getattr__(self, name):
        def method(*args, **kwargs):
            return "Using this class is not permitted due to safety reasons. Please do not try again!"
        return method
"""

GUARD_CODE = f"""
import os

os.kill = {write_denial_function}
os.system = {write_denial_function}
os.putenv = {write_denial_function}
os.remove = {write_denial_function}
os.removedirs = {write_denial_function}
os.rmdir = {write_denial_function}
os.fchdir = {write_denial_function}
os.setuid = {write_denial_function}
os.fork = {write_denial_function}
os.forkpty = {write_denial_function}
os.killpg = {write_denial_function}
os.rename = {write_denial_function}
os.renames = {write_denial_function}
os.truncate = {write_denial_function}
os.replace = {write_denial_function}
os.unlink = {write_denial_function}
os.fchmod = {write_denial_function}
os.fchown = {write_denial_function}
os.chmod = {write_denial_function}
os.chown = {write_denial_function}
os.chroot = {write_denial_function}
os.fchdir = {write_denial_function}
os.lchflags = {write_denial_function}
os.lchmod = {write_denial_function}
os.lchown = {write_denial_function}
os.getcwd = {write_denial_function}
os.chdir = {write_denial_function}
os.popen = {write_denial_function}

import shutil

shutil.rmtree = {write_denial_function}
shutil.move = {write_denial_function}
shutil.chown = {write_denial_function}

import subprocess

subprocess.Popen = {write_denial_function}  # type: ignore

import sys

sys.modules["ipdb"] = {write_denial_function}
sys.modules["joblib"] = {write_denial_function}
sys.modules["resource"] = {write_denial_function}
sys.modules["psutil"] = {write_denial_function}
sys.modules["tkinter"] = {write_denial_function}
"""

CODE_INTERPRETER_SYSTEM_PROMPT = """You are an AI code interpreter.
Your goal is to help users do a variety of jobs by executing Python code.

You should:
1. Comprehend the user's requirements carefully & to the letter.
2. Give a brief description for what you plan to do & call the provided function to run code.
3. Provide results analysis based on the execution output.
4. If error occurred, try to fix it.
5. Response in the same language as the user."""

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\src\utils\const.py ===
TOOLS_CODE = """
import numpy as np
import pandas as pd 
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
import os,sys
import re
from datetime import datetime
from sympy import symbols, Eq, solve
import torch 
import requests
from bs4 import BeautifulSoup
import json
import math
import yfinance
import time
"""

write_denial_function = 'lambda *args, **kwargs: (_ for _ in ()).throw(PermissionError("Writing to disk operation is not permitted due to safety reasons. Please do not try again!"))'
read_denial_function = 'lambda *args, **kwargs: (_ for _ in ()).throw(PermissionError("Reading from disk operation is not permitted due to safety reasons. Please do not try again!"))'
class_denial = """Class Denial:
    def __getattr__(self, name):
        def method(*args, **kwargs):
            return "Using this class is not permitted due to safety reasons. Please do not try again!"
        return method
"""

GUARD_CODE = f"""
import os

os.kill = {write_denial_function}
os.system = {write_denial_function}
os.putenv = {write_denial_function}
os.remove = {write_denial_function}
os.removedirs = {write_denial_function}
os.rmdir = {write_denial_function}
os.fchdir = {write_denial_function}
os.setuid = {write_denial_function}
os.fork = {write_denial_function}
os.forkpty = {write_denial_function}
os.killpg = {write_denial_function}
os.rename = {write_denial_function}
os.renames = {write_denial_function}
os.truncate = {write_denial_function}
os.replace = {write_denial_function}
os.unlink = {write_denial_function}
os.fchmod = {write_denial_function}
os.fchown = {write_denial_function}
os.chmod = {write_denial_function}
os.chown = {write_denial_function}
os.chroot = {write_denial_function}
os.fchdir = {write_denial_function}
os.lchflags = {write_denial_function}
os.lchmod = {write_denial_function}
os.lchown = {write_denial_function}
os.getcwd = {write_denial_function}
os.chdir = {write_denial_function}
os.popen = {write_denial_function}

import shutil

shutil.rmtree = {write_denial_function}
shutil.move = {write_denial_function}
shutil.chown = {write_denial_function}

import subprocess

subprocess.Popen = {write_denial_function}  # type: ignore

import sys

sys.modules["ipdb"] = {write_denial_function}
sys.modules["joblib"] = {write_denial_function}
sys.modules["resource"] = {write_denial_function}
sys.modules["psutil"] = {write_denial_function}
sys.modules["tkinter"] = {write_denial_function}
"""

CODE_INTERPRETER_SYSTEM_PROMPT = """You are an AI code interpreter.
Your goal is to help users do a variety of jobs by executing Python code.

You should:
1. Comprehend the user's requirements carefully & to the letter.
2. Give a brief description for what you plan to do & call the provided function to run code.
3. Provide results analysis based on the execution output.
4. If error occurred, try to fix it.
5. Response in the same language as the user."""

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\src\utils\const.py ===
TOOLS_CODE = """
import numpy as np
import pandas as pd 
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
import os,sys
import re
from datetime import datetime
from sympy import symbols, Eq, solve
import torch 
import requests
from bs4 import BeautifulSoup
import json
import math
import yfinance
import time
"""

write_denial_function = 'lambda *args, **kwargs: (_ for _ in ()).throw(PermissionError("Writing to disk operation is not permitted due to safety reasons. Please do not try again!"))'
read_denial_function = 'lambda *args, **kwargs: (_ for _ in ()).throw(PermissionError("Reading from disk operation is not permitted due to safety reasons. Please do not try again!"))'
class_denial = """Class Denial:
    def __getattr__(self, name):
        def method(*args, **kwargs):
            return "Using this class is not permitted due to safety reasons. Please do not try again!"
        return method
"""

GUARD_CODE = f"""
import os

os.kill = {write_denial_function}
os.system = {write_denial_function}
os.putenv = {write_denial_function}
os.remove = {write_denial_function}
os.removedirs = {write_denial_function}
os.rmdir = {write_denial_function}
os.fchdir = {write_denial_function}
os.setuid = {write_denial_function}
os.fork = {write_denial_function}
os.forkpty = {write_denial_function}
os.killpg = {write_denial_function}
os.rename = {write_denial_function}
os.renames = {write_denial_function}
os.truncate = {write_denial_function}
os.replace = {write_denial_function}
os.unlink = {write_denial_function}
os.fchmod = {write_denial_function}
os.fchown = {write_denial_function}
os.chmod = {write_denial_function}
os.chown = {write_denial_function}
os.chroot = {write_denial_function}
os.fchdir = {write_denial_function}
os.lchflags = {write_denial_function}
os.lchmod = {write_denial_function}
os.lchown = {write_denial_function}
os.getcwd = {write_denial_function}
os.chdir = {write_denial_function}
os.popen = {write_denial_function}

import shutil

shutil.rmtree = {write_denial_function}
shutil.move = {write_denial_function}
shutil.chown = {write_denial_function}

import subprocess

subprocess.Popen = {write_denial_function}  # type: ignore

import sys

sys.modules["ipdb"] = {write_denial_function}
sys.modules["joblib"] = {write_denial_function}
sys.modules["resource"] = {write_denial_function}
sys.modules["psutil"] = {write_denial_function}
sys.modules["tkinter"] = {write_denial_function}
"""

CODE_INTERPRETER_SYSTEM_PROMPT = """You are an AI code interpreter.
Your goal is to help users do a variety of jobs by executing Python code.

You should:
1. Comprehend the user's requirements carefully & to the letter.
2. Give a brief description for what you plan to do & call the provided function to run code.
3. Provide results analysis based on the execution output.
4. If error occurred, try to fix it.
5. Response in the same language as the user."""

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\tools\exports\export_20250803_114325\source_code\NexusCore\src\utils\const.py ===
TOOLS_CODE = """
import numpy as np
import pandas as pd 
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
import os,sys
import re
from datetime import datetime
from sympy import symbols, Eq, solve
import torch 
import requests
from bs4 import BeautifulSoup
import json
import math
import yfinance
import time
"""

write_denial_function = 'lambda *args, **kwargs: (_ for _ in ()).throw(PermissionError("Writing to disk operation is not permitted due to safety reasons. Please do not try again!"))'
read_denial_function = 'lambda *args, **kwargs: (_ for _ in ()).throw(PermissionError("Reading from disk operation is not permitted due to safety reasons. Please do not try again!"))'
class_denial = """Class Denial:
    def __getattr__(self, name):
        def method(*args, **kwargs):
            return "Using this class is not permitted due to safety reasons. Please do not try again!"
        return method
"""

GUARD_CODE = f"""
import os

os.kill = {write_denial_function}
os.system = {write_denial_function}
os.putenv = {write_denial_function}
os.remove = {write_denial_function}
os.removedirs = {write_denial_function}
os.rmdir = {write_denial_function}
os.fchdir = {write_denial_function}
os.setuid = {write_denial_function}
os.fork = {write_denial_function}
os.forkpty = {write_denial_function}
os.killpg = {write_denial_function}
os.rename = {write_denial_function}
os.renames = {write_denial_function}
os.truncate = {write_denial_function}
os.replace = {write_denial_function}
os.unlink = {write_denial_function}
os.fchmod = {write_denial_function}
os.fchown = {write_denial_function}
os.chmod = {write_denial_function}
os.chown = {write_denial_function}
os.chroot = {write_denial_function}
os.fchdir = {write_denial_function}
os.lchflags = {write_denial_function}
os.lchmod = {write_denial_function}
os.lchown = {write_denial_function}
os.getcwd = {write_denial_function}
os.chdir = {write_denial_function}
os.popen = {write_denial_function}

import shutil

shutil.rmtree = {write_denial_function}
shutil.move = {write_denial_function}
shutil.chown = {write_denial_function}

import subprocess

subprocess.Popen = {write_denial_function}  # type: ignore

import sys

sys.modules["ipdb"] = {write_denial_function}
sys.modules["joblib"] = {write_denial_function}
sys.modules["resource"] = {write_denial_function}
sys.modules["psutil"] = {write_denial_function}
sys.modules["tkinter"] = {write_denial_function}
"""

CODE_INTERPRETER_SYSTEM_PROMPT = """You are an AI code interpreter.
Your goal is to help users do a variety of jobs by executing Python code.

You should:
1. Comprehend the user's requirements carefully & to the letter.
2. Give a brief description for what you plan to do & call the provided function to run code.
3. Provide results analysis based on the execution output.
4. If error occurred, try to fix it.
5. Response in the same language as the user."""

# === NexusCore/openenv\Lib\site-packages\numpy\lib\tests\test_io.py ===
import gc
import gzip
import locale
import os
import re
import sys
import threading
import time
import warnings
from ctypes import c_bool
from datetime import datetime
from io import BytesIO, StringIO
from multiprocessing import Value, get_context
from pathlib import Path
from tempfile import NamedTemporaryFile

import pytest

import numpy as np
import numpy.ma as ma
from numpy._utils import asbytes
from numpy.exceptions import VisibleDeprecationWarning
from numpy.lib import _npyio_impl
from numpy.lib._iotools import ConversionWarning, ConverterError
from numpy.lib._npyio_impl import recfromcsv, recfromtxt
from numpy.ma.testutils import assert_equal
from numpy.testing import (
    HAS_REFCOUNT,
    IS_PYPY,
    IS_WASM,
    assert_,
    assert_allclose,
    assert_array_equal,
    assert_no_gc_cycles,
    assert_no_warnings,
    assert_raises,
    assert_raises_regex,
    assert_warns,
    break_cycles,
    suppress_warnings,
    tempdir,
    temppath,
)
from numpy.testing._private.utils import requires_memory


class TextIO(BytesIO):
    """Helper IO class.

    Writes encode strings to bytes if needed, reads return bytes.
    This makes it easier to emulate files opened in binary mode
    without needing to explicitly convert strings to bytes in
    setting up the test data.

    """
    def __init__(self, s=""):
        BytesIO.__init__(self, asbytes(s))

    def write(self, s):
        BytesIO.write(self, asbytes(s))

    def writelines(self, lines):
        BytesIO.writelines(self, [asbytes(s) for s in lines])


IS_64BIT = sys.maxsize > 2**32
try:
    import bz2
    HAS_BZ2 = True
except ImportError:
    HAS_BZ2 = False
try:
    import lzma
    HAS_LZMA = True
except ImportError:
    HAS_LZMA = False


def strptime(s, fmt=None):
    """
    This function is available in the datetime module only from Python >=
    2.5.

    """
    if isinstance(s, bytes):
        s = s.decode("latin1")
    return datetime(*time.strptime(s, fmt)[:3])


class RoundtripTest:
    def roundtrip(self, save_func, *args, **kwargs):
        """
        save_func : callable
            Function used to save arrays to file.
        file_on_disk : bool
            If true, store the file on disk, instead of in a
            string buffer.
        save_kwds : dict
            Parameters passed to `save_func`.
        load_kwds : dict
            Parameters passed to `numpy.load`.
        args : tuple of arrays
            Arrays stored to file.

        """
        save_kwds = kwargs.get('save_kwds', {})
        load_kwds = kwargs.get('load_kwds', {"allow_pickle": True})
        file_on_disk = kwargs.get('file_on_disk', False)

        if file_on_disk:
            target_file = NamedTemporaryFile(delete=False)
            load_file = target_file.name
        else:
            target_file = BytesIO()
            load_file = target_file

        try:
            arr = args

            save_func(target_file, *arr, **save_kwds)
            target_file.flush()
            target_file.seek(0)

            if sys.platform == 'win32' and not isinstance(target_file, BytesIO):
                target_file.close()

            arr_reloaded = np.load(load_file, **load_kwds)

            self.arr = arr
            self.arr_reloaded = arr_reloaded
        finally:
            if not isinstance(target_file, BytesIO):
                target_file.close()
                # holds an open file descriptor so it can't be deleted on win
                if 'arr_reloaded' in locals():
                    if not isinstance(arr_reloaded, np.lib.npyio.NpzFile):
                        os.remove(target_file.name)

    def check_roundtrips(self, a):
        self.roundtrip(a)
        self.roundtrip(a, file_on_disk=True)
        self.roundtrip(np.asfortranarray(a))
        self.roundtrip(np.asfortranarray(a), file_on_disk=True)
        if a.shape[0] > 1:
            # neither C nor Fortran contiguous for 2D arrays or more
            self.roundtrip(np.asfortranarray(a)[1:])
            self.roundtrip(np.asfortranarray(a)[1:], file_on_disk=True)

    def test_array(self):
        a = np.array([], float)
        self.check_roundtrips(a)

        a = np.array([[1, 2], [3, 4]], float)
        self.check_roundtrips(a)

        a = np.array([[1, 2], [3, 4]], int)
        self.check_roundtrips(a)

        a = np.array([[1 + 5j, 2 + 6j], [3 + 7j, 4 + 8j]], dtype=np.csingle)
        self.check_roundtrips(a)

        a = np.array([[1 + 5j, 2 + 6j], [3 + 7j, 4 + 8j]], dtype=np.cdouble)
        self.check_roundtrips(a)

    def test_array_object(self):
        a = np.array([], object)
        self.check_roundtrips(a)

        a = np.array([[1, 2], [3, 4]], object)
        self.check_roundtrips(a)

    def test_1D(self):
        a = np.array([1, 2, 3, 4], int)
        self.roundtrip(a)

    @pytest.mark.skipif(sys.platform == 'win32', reason="Fails on Win32")
    def test_mmap(self):
        a = np.array([[1, 2.5], [4, 7.3]])
        self.roundtrip(a, file_on_disk=True, load_kwds={'mmap_mode': 'r'})

        a = np.asfortranarray([[1, 2.5], [4, 7.3]])
        self.roundtrip(a, file_on_disk=True, load_kwds={'mmap_mode': 'r'})

    def test_record(self):
        a = np.array([(1, 2), (3, 4)], dtype=[('x', 'i4'), ('y', 'i4')])
        self.check_roundtrips(a)

    @pytest.mark.slow
    def test_format_2_0(self):
        dt = [(("%d" % i) * 100, float) for i in range(500)]
        a = np.ones(1000, dtype=dt)
        with warnings.catch_warnings(record=True):
            warnings.filterwarnings('always', '', UserWarning)
            self.check_roundtrips(a)


class TestSaveLoad(RoundtripTest):
    def roundtrip(self, *args, **kwargs):
        RoundtripTest.roundtrip(self, np.save, *args, **kwargs)
        assert_equal(self.arr[0], self.arr_reloaded)
        assert_equal(self.arr[0].dtype, self.arr_reloaded.dtype)
        assert_equal(self.arr[0].flags.fnc, self.arr_reloaded.flags.fnc)


class TestSavezLoad(RoundtripTest):
    def roundtrip(self, *args, **kwargs):
        RoundtripTest.roundtrip(self, np.savez, *args, **kwargs)
        try:
            for n, arr in enumerate(self.arr):
                reloaded = self.arr_reloaded['arr_%d' % n]
                assert_equal(arr, reloaded)
                assert_equal(arr.dtype, reloaded.dtype)
                assert_equal(arr.flags.fnc, reloaded.flags.fnc)
        finally:
            # delete tempfile, must be done here on windows
            if self.arr_reloaded.fid:
                self.arr_reloaded.fid.close()
                os.remove(self.arr_reloaded.fid.name)

    @pytest.mark.skipif(IS_PYPY, reason="Hangs on PyPy")
    @pytest.mark.skipif(not IS_64BIT, reason="Needs 64bit platform")
    @pytest.mark.slow
    def test_big_arrays(self):
        L = (1 << 31) + 100000
        a = np.empty(L, dtype=np.uint8)
        with temppath(prefix="numpy_test_big_arrays_", suffix=".npz") as tmp:
            np.savez(tmp, a=a)
            del a
            npfile = np.load(tmp)
            a = npfile['a']  # Should succeed
            npfile.close()

    def test_multiple_arrays(self):
        a = np.array([[1, 2], [3, 4]], float)
        b = np.array([[1 + 2j, 2 + 7j], [3 - 6j, 4 + 12j]], complex)
        self.roundtrip(a, b)

    def test_named_arrays(self):
        a = np.array([[1, 2], [3, 4]], float)
        b = np.array([[1 + 2j, 2 + 7j], [3 - 6j, 4 + 12j]], complex)
        c = BytesIO()
        np.savez(c, file_a=a, file_b=b)
        c.seek(0)
        l = np.load(c)
        assert_equal(a, l['file_a'])
        assert_equal(b, l['file_b'])

    def test_tuple_getitem_raises(self):
        # gh-23748
        a = np.array([1, 2, 3])
        f = BytesIO()
        np.savez(f, a=a)
        f.seek(0)
        l = np.load(f)
        with pytest.raises(KeyError, match="(1, 2)"):
            l[1, 2]

    def test_BagObj(self):
        a = np.array([[1, 2], [3, 4]], float)
        b = np.array([[1 + 2j, 2 + 7j], [3 - 6j, 4 + 12j]], complex)
        c = BytesIO()
        np.savez(c, file_a=a, file_b=b)
        c.seek(0)
        l = np.load(c)
        assert_equal(sorted(dir(l.f)), ['file_a', 'file_b'])
        assert_equal(a, l.f.file_a)
        assert_equal(b, l.f.file_b)

    @pytest.mark.skipif(IS_WASM, reason="Cannot start thread")
    def test_savez_filename_clashes(self):
        # Test that issue #852 is fixed
        # and savez functions in multithreaded environment

        def writer(error_list):
            with temppath(suffix='.npz') as tmp:
                arr = np.random.randn(500, 500)
                try:
                    np.savez(tmp, arr=arr)
                except OSError as err:
                    error_list.append(err)

        errors = []
        threads = [threading.Thread(target=writer, args=(errors,))
                   for j in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        if errors:
            raise AssertionError(errors)

    def test_not_closing_opened_fid(self):
        # Test that issue #2178 is fixed:
        # verify could seek on 'loaded' file
        with temppath(suffix='.npz') as tmp:
            with open(tmp, 'wb') as fp:
                np.savez(fp, data='LOVELY LOAD')
            with open(tmp, 'rb', 10000) as fp:
                fp.seek(0)
                assert_(not fp.closed)
                np.load(fp)['data']
                # fp must not get closed by .load
                assert_(not fp.closed)
                fp.seek(0)
                assert_(not fp.closed)

    @pytest.mark.slow_pypy
    def test_closing_fid(self):
        # Test that issue #1517 (too many opened files) remains closed
        # It might be a "weak" test since failed to get triggered on
        # e.g. Debian sid of 2012 Jul 05 but was reported to
        # trigger the failure on Ubuntu 10.04:
        # http://projects.scipy.org/numpy/ticket/1517#comment:2
        with temppath(suffix='.npz') as tmp:
            np.savez(tmp, data='LOVELY LOAD')
            # We need to check if the garbage collector can properly close
            # numpy npz file returned by np.load when their reference count
            # goes to zero.  Python running in debug mode raises a
            # ResourceWarning when file closing is left to the garbage
            # collector, so we catch the warnings.
            with suppress_warnings() as sup:
                sup.filter(ResourceWarning)  # TODO: specify exact message
                for i in range(1, 1025):
                    try:
                        np.load(tmp)["data"]
                    except Exception as e:
                        msg = f"Failed to load data from a file: {e}"
                        raise AssertionError(msg)
                    finally:
                        if IS_PYPY:
                            gc.collect()

    def test_closing_zipfile_after_load(self):
        # Check that zipfile owns file and can close it.  This needs to
        # pass a file name to load for the test. On windows failure will
        # cause a second error will be raised when the attempt to remove
        # the open file is made.
        prefix = 'numpy_test_closing_zipfile_after_load_'
        with temppath(suffix='.npz', prefix=prefix) as tmp:
            np.savez(tmp, lab='place holder')
            data = np.load(tmp)
            fp = data.zip.fp
            data.close()
            assert_(fp.closed)

    @pytest.mark.parametrize("count, expected_repr", [
        (1, "NpzFile {fname!r} with keys: arr_0"),
        (5, "NpzFile {fname!r} with keys: arr_0, arr_1, arr_2, arr_3, arr_4"),
        # _MAX_REPR_ARRAY_COUNT is 5, so files with more than 5 keys are
        # expected to end in '...'
        (6, "NpzFile {fname!r} with keys: arr_0, arr_1, arr_2, arr_3, arr_4..."),
    ])
    def test_repr_lists_keys(self, count, expected_repr):
        a = np.array([[1, 2], [3, 4]], float)
        with temppath(suffix='.npz') as tmp:
            np.savez(tmp, *[a] * count)
            l = np.load(tmp)
            assert repr(l) == expected_repr.format(fname=tmp)
            l.close()


class TestSaveTxt:
    def test_array(self):
        a = np.array([[1, 2], [3, 4]], float)
        fmt = "%.18e"
        c = BytesIO()
        np.savetxt(c, a, fmt=fmt)
        c.seek(0)
        assert_equal(c.readlines(),
                     [asbytes((fmt + ' ' + fmt + '\n') % (1, 2)),
                      asbytes((fmt + ' ' + fmt + '\n') % (3, 4))])

        a = np.array([[1, 2], [3, 4]], int)
        c = BytesIO()
        np.savetxt(c, a, fmt='%d')
        c.seek(0)
        assert_equal(c.readlines(), [b'1 2\n', b'3 4\n'])

    def test_1D(self):
        a = np.array([1, 2, 3, 4], int)
        c = BytesIO()
        np.savetxt(c, a, fmt='%d')
        c.seek(0)
        lines = c.readlines()
        assert_equal(lines, [b'1\n', b'2\n', b'3\n', b'4\n'])

    def test_0D_3D(self):
        c = BytesIO()
        assert_raises(ValueError, np.savetxt, c, np.array(1))
        assert_raises(ValueError, np.savetxt, c, np.array([[[1], [2]]]))

    def test_structured(self):
        a = np.array([(1, 2), (3, 4)], dtype=[('x', 'i4'), ('y', 'i4')])
        c = BytesIO()
        np.savetxt(c, a, fmt='%d')
        c.seek(0)
        assert_equal(c.readlines(), [b'1 2\n', b'3 4\n'])

    def test_structured_padded(self):
        # gh-13297
        a = np.array([(1, 2, 3), (4, 5, 6)], dtype=[
            ('foo', 'i4'), ('bar', 'i4'), ('baz', 'i4')
        ])
        c = BytesIO()
        np.savetxt(c, a[['foo', 'baz']], fmt='%d')
        c.seek(0)
        assert_equal(c.readlines(), [b'1 3\n', b'4 6\n'])

    def test_multifield_view(self):
        a = np.ones(1, dtype=[('x', 'i4'), ('y', 'i4'), ('z', 'f4')])
        v = a[['x', 'z']]
        with temppath(suffix='.npy') as path:
            path = Path(path)
            np.save(path, v)
            data = np.load(path)
            assert_array_equal(data, v)

    def test_delimiter(self):
        a = np.array([[1., 2.], [3., 4.]])
        c = BytesIO()
        np.savetxt(c, a, delimiter=',', fmt='%d')
        c.seek(0)
        assert_equal(c.readlines(), [b'1,2\n', b'3,4\n'])

    def test_format(self):
        a = np.array([(1, 2), (3, 4)])
        c = BytesIO()
        # Sequence of formats
        np.savetxt(c, a, fmt=['%02d', '%3.1f'])
        c.seek(0)
        assert_equal(c.readlines(), [b'01 2.0\n', b'03 4.0\n'])

        # A single multiformat string
        c = BytesIO()
        np.savetxt(c, a, fmt='%02d : %3.1f')
        c.seek(0)
        lines = c.readlines()
        assert_equal(lines, [b'01 : 2.0\n', b'03 : 4.0\n'])

        # Specify delimiter, should be overridden
        c = BytesIO()
        np.savetxt(c, a, fmt='%02d : %3.1f', delimiter=',')
        c.seek(0)
        lines = c.readlines()
        assert_equal(lines, [b'01 : 2.0\n', b'03 : 4.0\n'])

        # Bad fmt, should raise a ValueError
        c = BytesIO()
        assert_raises(ValueError, np.savetxt, c, a, fmt=99)

    def test_header_footer(self):
        # Test the functionality of the header and footer keyword argument.

        c = BytesIO()
        a = np.array([(1, 2), (3, 4)], dtype=int)
        test_header_footer = 'Test header / footer'
        # Test the header keyword argument
        np.savetxt(c, a, fmt='%1d', header=test_header_footer)
        c.seek(0)
        assert_equal(c.read(),
                     asbytes('# ' + test_header_footer + '\n1 2\n3 4\n'))
        # Test the footer keyword argument
        c = BytesIO()
        np.savetxt(c, a, fmt='%1d', footer=test_header_footer)
        c.seek(0)
        assert_equal(c.read(),
                     asbytes('1 2\n3 4\n# ' + test_header_footer + '\n'))
        # Test the commentstr keyword argument used on the header
        c = BytesIO()
        commentstr = '% '
        np.savetxt(c, a, fmt='%1d',
                   header=test_header_footer, comments=commentstr)
        c.seek(0)
        assert_equal(c.read(),
                     asbytes(commentstr + test_header_footer + '\n' + '1 2\n3 4\n'))
        # Test the commentstr keyword argument used on the footer
        c = BytesIO()
        commentstr = '% '
        np.savetxt(c, a, fmt='%1d',
                   footer=test_header_footer, comments=commentstr)
        c.seek(0)
        assert_equal(c.read(),
                     asbytes('1 2\n3 4\n' + commentstr + test_header_footer + '\n'))

    @pytest.mark.parametrize("filename_type", [Path, str])
    def test_file_roundtrip(self, filename_type):
        with temppath() as name:
            a = np.array([(1, 2), (3, 4)])
            np.savetxt(filename_type(name), a)
            b = np.loadtxt(filename_type(name))
            assert_array_equal(a, b)

    def test_complex_arrays(self):
        ncols = 2
        nrows = 2
        a = np.zeros((ncols, nrows), dtype=np.complex128)
        re = np.pi
        im = np.e
        a[:] = re + 1.0j * im

        # One format only
        c = BytesIO()
        np.savetxt(c, a, fmt=' %+.3e')
        c.seek(0)
        lines = c.readlines()
        assert_equal(
            lines,
            [b' ( +3.142e+00+ +2.718e+00j)  ( +3.142e+00+ +2.718e+00j)\n',
             b' ( +3.142e+00+ +2.718e+00j)  ( +3.142e+00+ +2.718e+00j)\n'])

        # One format for each real and imaginary part
        c = BytesIO()
        np.savetxt(c, a, fmt='  %+.3e' * 2 * ncols)
        c.seek(0)
        lines = c.readlines()
        assert_equal(
            lines,
            [b'  +3.142e+00  +2.718e+00  +3.142e+00  +2.718e+00\n',
             b'  +3.142e+00  +2.718e+00  +3.142e+00  +2.718e+00\n'])

        # One format for each complex number
        c = BytesIO()
        np.savetxt(c, a, fmt=['(%.3e%+.3ej)'] * ncols)
        c.seek(0)
        lines = c.readlines()
        assert_equal(
            lines,
            [b'(3.142e+00+2.718e+00j) (3.142e+00+2.718e+00j)\n',
             b'(3.142e+00+2.718e+00j) (3.142e+00+2.718e+00j)\n'])

    def test_complex_negative_exponent(self):
        # Previous to 1.15, some formats generated x+-yj, gh 7895
        ncols = 2
        nrows = 2
        a = np.zeros((ncols, nrows), dtype=np.complex128)
        re = np.pi
        im = np.e
        a[:] = re - 1.0j * im
        c = BytesIO()
        np.savetxt(c, a, fmt='%.3e')
        c.seek(0)
        lines = c.readlines()
        assert_equal(
            lines,
            [b' (3.142e+00-2.718e+00j)  (3.142e+00-2.718e+00j)\n',
             b' (3.142e+00-2.718e+00j)  (3.142e+00-2.718e+00j)\n'])

    def test_custom_writer(self):

        class CustomWriter(list):
            def write(self, text):
                self.extend(text.split(b'\n'))

        w = CustomWriter()
        a = np.array([(1, 2), (3, 4)])
        np.savetxt(w, a)
        b = np.loadtxt(w)
        assert_array_equal(a, b)

    def test_unicode(self):
        utf8 = b'\xcf\x96'.decode('UTF-8')
        a = np.array([utf8], dtype=np.str_)
        with tempdir() as tmpdir:
            # set encoding as on windows it may not be unicode even on py3
            np.savetxt(os.path.join(tmpdir, 'test.csv'), a, fmt=['%s'],
                       encoding='UTF-8')

    def test_unicode_roundtrip(self):
        utf8 = b'\xcf\x96'.decode('UTF-8')
        a = np.array([utf8], dtype=np.str_)
        # our gz wrapper support encoding
        suffixes = ['', '.gz']
        if HAS_BZ2:
            suffixes.append('.bz2')
        if HAS_LZMA:
            suffixes.extend(['.xz', '.lzma'])
        with tempdir() as tmpdir:
            for suffix in suffixes:
                np.savetxt(os.path.join(tmpdir, 'test.csv' + suffix), a,
                           fmt=['%s'], encoding='UTF-16-LE')
                b = np.loadtxt(os.path.join(tmpdir, 'test.csv' + suffix),
                               encoding='UTF-16-LE', dtype=np.str_)
                assert_array_equal(a, b)

    def test_unicode_bytestream(self):
        utf8 = b'\xcf\x96'.decode('UTF-8')
        a = np.array([utf8], dtype=np.str_)
        s = BytesIO()
        np.savetxt(s, a, fmt=['%s'], encoding='UTF-8')
        s.seek(0)
        assert_equal(s.read().decode('UTF-8'), utf8 + '\n')

    def test_unicode_stringstream(self):
        utf8 = b'\xcf\x96'.decode('UTF-8')
        a = np.array([utf8], dtype=np.str_)
        s = StringIO()
        np.savetxt(s, a, fmt=['%s'], encoding='UTF-8')
        s.seek(0)
        assert_equal(s.read(), utf8 + '\n')

    @pytest.mark.parametrize("iotype", [StringIO, BytesIO])
    def test_unicode_and_bytes_fmt(self, iotype):
        # string type of fmt should not matter, see also gh-4053
        a = np.array([1.])
        s = iotype()
        np.savetxt(s, a, fmt="%f")
        s.seek(0)
        if iotype is StringIO:
            assert_equal(s.read(), "%f\n" % 1.)
        else:
            assert_equal(s.read(), b"%f\n" % 1.)

    @pytest.mark.skipif(sys.platform == 'win32', reason="files>4GB may not work")
    @pytest.mark.slow
    @requires_memory(free_bytes=7e9)
    def test_large_zip(self):
        def check_large_zip(memoryerror_raised):
            memoryerror_raised.value = False
            try:
                # The test takes at least 6GB of memory, writes a file larger
                # than 4GB. This tests the ``allowZip64`` kwarg to ``zipfile``
                test_data = np.asarray([np.random.rand(
                                        np.random.randint(50, 100), 4)
                                        for i in range(800000)], dtype=object)
                with tempdir() as tmpdir:
                    np.savez(os.path.join(tmpdir, 'test.npz'),
                             test_data=test_data)
            except MemoryError:
                memoryerror_raised.value = True
                raise
        # run in a subprocess to ensure memory is released on PyPy, see gh-15775
        # Use an object in shared memory to re-raise the MemoryError exception
        # in our process if needed, see gh-16889
        memoryerror_raised = Value(c_bool)

        # Since Python 3.8, the default start method for multiprocessing has
        # been changed from 'fork' to 'spawn' on macOS, causing inconsistency
        # on memory sharing model, leading to failed test for check_large_zip
        ctx = get_context('fork')
        p = ctx.Process(target=check_large_zip, args=(memoryerror_raised,))
        p.start()
        p.join()
        if memoryerror_raised.value:
            raise MemoryError("Child process raised a MemoryError exception")
        # -9 indicates a SIGKILL, probably an OOM.
        if p.exitcode == -9:
            pytest.xfail("subprocess got a SIGKILL, apparently free memory was not sufficient")
        assert p.exitcode == 0

class LoadTxtBase:
    def check_compressed(self, fopen, suffixes):
        # Test that we can load data from a compressed file
        wanted = np.arange(6).reshape((2, 3))
        linesep = ('\n', '\r\n', '\r')
        for sep in linesep:
            data = '0 1 2' + sep + '3 4 5'
            for suffix in suffixes:
                with temppath(suffix=suffix) as name:
                    with fopen(name, mode='wt', encoding='UTF-32-LE') as f:
                        f.write(data)
                    res = self.loadfunc(name, encoding='UTF-32-LE')
                    assert_array_equal(res, wanted)
                    with fopen(name, "rt",  encoding='UTF-32-LE') as f:
                        res = self.loadfunc(f)
                    assert_array_equal(res, wanted)

    def test_compressed_gzip(self):
        self.check_compressed(gzip.open, ('.gz',))

    @pytest.mark.skipif(not HAS_BZ2, reason="Needs bz2")
    def test_compressed_bz2(self):
        self.check_compressed(bz2.open, ('.bz2',))

    @pytest.mark.skipif(not HAS_LZMA, reason="Needs lzma")
    def test_compressed_lzma(self):
        self.check_compressed(lzma.open, ('.xz', '.lzma'))

    def test_encoding(self):
        with temppath() as path:
            with open(path, "wb") as f:
                f.write('0.\n1.\n2.'.encode("UTF-16"))
            x = self.loadfunc(path, encoding="UTF-16")
            assert_array_equal(x, [0., 1., 2.])

    def test_stringload(self):
        # umlaute
        nonascii = b'\xc3\xb6\xc3\xbc\xc3\xb6'.decode("UTF-8")
        with temppath() as path:
            with open(path, "wb") as f:
                f.write(nonascii.encode("UTF-16"))
            x = self.loadfunc(path, encoding="UTF-16", dtype=np.str_)
            assert_array_equal(x, nonascii)

    def test_binary_decode(self):
        utf16 = b'\xff\xfeh\x04 \x00i\x04 \x00j\x04'
        v = self.loadfunc(BytesIO(utf16), dtype=np.str_, encoding='UTF-16')
        assert_array_equal(v, np.array(utf16.decode('UTF-16').split()))

    def test_converters_decode(self):
        # test converters that decode strings
        c = TextIO()
        c.write(b'\xcf\x96')
        c.seek(0)
        x = self.loadfunc(c, dtype=np.str_, encoding="bytes",
                          converters={0: lambda x: x.decode('UTF-8')})
        a = np.array([b'\xcf\x96'.decode('UTF-8')])
        assert_array_equal(x, a)

    def test_converters_nodecode(self):
        # test native string converters enabled by setting an encoding
        utf8 = b'\xcf\x96'.decode('UTF-8')
        with temppath() as path:
            with open(path, 'wt', encoding='UTF-8') as f:
                f.write(utf8)
            x = self.loadfunc(path, dtype=np.str_,
                              converters={0: lambda x: x + 't'},
                              encoding='UTF-8')
            a = np.array([utf8 + 't'])
            assert_array_equal(x, a)


class TestLoadTxt(LoadTxtBase):
    loadfunc = staticmethod(np.loadtxt)

    def setup_method(self):
        # lower chunksize for testing
        self.orig_chunk = _npyio_impl._loadtxt_chunksize
        _npyio_impl._loadtxt_chunksize = 1

    def teardown_method(self):
        _npyio_impl._loadtxt_chunksize = self.orig_chunk

    def test_record(self):
        c = TextIO()
        c.write('1 2\n3 4')
        c.seek(0)
        x = np.loadtxt(c, dtype=[('x', np.int32), ('y', np.int32)])
        a = np.array([(1, 2), (3, 4)], dtype=[('x', 'i4'), ('y', 'i4')])
        assert_array_equal(x, a)

        d = TextIO()
        d.write('M 64 75.0\nF 25 60.0')
        d.seek(0)
        mydescriptor = {'names': ('gender', 'age', 'weight'),
                        'formats': ('S1', 'i4', 'f4')}
        b = np.array([('M', 64.0, 75.0),
                      ('F', 25.0, 60.0)], dtype=mydescriptor)
        y = np.loadtxt(d, dtype=mydescriptor)
        assert_array_equal(y, b)

    def test_array(self):
        c = TextIO()
        c.write('1 2\n3 4')

        c.seek(0)
        x = np.loadtxt(c, dtype=int)
        a = np.array([[1, 2], [3, 4]], int)
        assert_array_equal(x, a)

        c.seek(0)
        x = np.loadtxt(c, dtype=float)
        a = np.array([[1, 2], [3, 4]], float)
        assert_array_equal(x, a)

    def test_1D(self):
        c = TextIO()
        c.write('1\n2\n3\n4\n')
        c.seek(0)
        x = np.loadtxt(c, dtype=int)
        a = np.array([1, 2, 3, 4], int)
        assert_array_equal(x, a)

        c = TextIO()
        c.write('1,2,3,4\n')
        c.seek(0)
        x = np.loadtxt(c, dtype=int, delimiter=',')
        a = np.array([1, 2, 3, 4], int)
        assert_array_equal(x, a)

    def test_missing(self):
        c = TextIO()
        c.write('1,2,3,,5\n')
        c.seek(0)
        x = np.loadtxt(c, dtype=int, delimiter=',',
                       converters={3: lambda s: int(s or - 999)})
        a = np.array([1, 2, 3, -999, 5], int)
        assert_array_equal(x, a)

    def test_converters_with_usecols(self):
        c = TextIO()
        c.write('1,2,3,,5\n6,7,8,9,10\n')
        c.seek(0)
        x = np.loadtxt(c, dtype=int, delimiter=',',
                       converters={3: lambda s: int(s or - 999)},
                       usecols=(1, 3,))
        a = np.array([[2, -999], [7, 9]], int)
        assert_array_equal(x, a)

    def test_comments_unicode(self):
        c = TextIO()
        c.write('# comment\n1,2,3,5\n')
        c.seek(0)
        x = np.loadtxt(c, dtype=int, delimiter=',',
                       comments='#')
        a = np.array([1, 2, 3, 5], int)
        assert_array_equal(x, a)

    def test_comments_byte(self):
        c = TextIO()
        c.write('# comment\n1,2,3,5\n')
        c.seek(0)
        x = np.loadtxt(c, dtype=int, delimiter=',',
                       comments=b'#')
        a = np.array([1, 2, 3, 5], int)
        assert_array_equal(x, a)

    def test_comments_multiple(self):
        c = TextIO()
        c.write('# comment\n1,2,3\n@ comment2\n4,5,6 // comment3')
        c.seek(0)
        x = np.loadtxt(c, dtype=int, delimiter=',',
                       comments=['#', '@', '//'])
        a = np.array([[1, 2, 3], [4, 5, 6]], int)
        assert_array_equal(x, a)

    @pytest.mark.skipif(IS_PYPY and sys.implementation.version <= (7, 3, 8),
                        reason="PyPy bug in error formatting")
    def test_comments_multi_chars(self):
        c = TextIO()
        c.write('/* comment\n1,2,3,5\n')
        c.seek(0)
        x = np.loadtxt(c, dtype=int, delimiter=',',
                       comments='/*')
        a = np.array([1, 2, 3, 5], int)
        assert_array_equal(x, a)

        # Check that '/*' is not transformed to ['/', '*']
        c = TextIO()
        c.write('*/ comment\n1,2,3,5\n')
        c.seek(0)
        assert_raises(ValueError, np.loadtxt, c, dtype=int, delimiter=',',
                      comments='/*')

    def test_skiprows(self):
        c = TextIO()
        c.write('comment\n1,2,3,5\n')
        c.seek(0)
        x = np.loadtxt(c, dtype=int, delimiter=',',
                       skiprows=1)
        a = np.array([1, 2, 3, 5], int)
        assert_array_equal(x, a)

        c = TextIO()
        c.write('# comment\n1,2,3,5\n')
        c.seek(0)
        x = np.loadtxt(c, dtype=int, delimiter=',',
                       skiprows=1)
        a = np.array([1, 2, 3, 5], int)
        assert_array_equal(x, a)

    def test_usecols(self):
        a = np.array([[1, 2], [3, 4]], float)
        c = BytesIO()
        np.savetxt(c, a)
        c.seek(0)
        x = np.loadtxt(c, dtype=float, usecols=(1,))
        assert_array_equal(x, a[:, 1])

        a = np.array([[1, 2, 3], [3, 4, 5]], float)
        c = BytesIO()
        np.savetxt(c, a)
        c.seek(0)
        x = np.loadtxt(c, dtype=float, usecols=(1, 2))
        assert_array_equal(x, a[:, 1:])

        # Testing with arrays instead of tuples.
        c.seek(0)
        x = np.loadtxt(c, dtype=float, usecols=np.array([1, 2]))
        assert_array_equal(x, a[:, 1:])

        # Testing with an integer instead of a sequence
        for int_type in [int, np.int8, np.int16,
                         np.int32, np.int64, np.uint8, np.uint16,
                         np.uint32, np.uint64]:
            to_read = int_type(1)
            c.seek(0)
            x = np.loadtxt(c, dtype=float, usecols=to_read)
            assert_array_equal(x, a[:, 1])

        # Testing with some crazy custom integer type
        class CrazyInt:
            def __index__(self):
                return 1

        crazy_int = CrazyInt()
        c.seek(0)
        x = np.loadtxt(c, dtype=float, usecols=crazy_int)
        assert_array_equal(x, a[:, 1])

        c.seek(0)
        x = np.loadtxt(c, dtype=float, usecols=(crazy_int,))
        assert_array_equal(x, a[:, 1])

        # Checking with dtypes defined converters.
        data = '''JOE 70.1 25.3
                BOB 60.5 27.9
                '''
        c = TextIO(data)
        names = ['stid', 'temp']
        dtypes = ['S4', 'f8']
        arr = np.loadtxt(c, usecols=(0, 2), dtype=list(zip(names, dtypes)))
        assert_equal(arr['stid'], [b"JOE", b"BOB"])
        assert_equal(arr['temp'], [25.3, 27.9])

        # Testing non-ints in usecols
        c.seek(0)
        bogus_idx = 1.5
        assert_raises_regex(
            TypeError,
            f'^usecols must be.*{type(bogus_idx).__name__}',
            np.loadtxt, c, usecols=bogus_idx
            )

        assert_raises_regex(
            TypeError,
            f'^usecols must be.*{type(bogus_idx).__name__}',
            np.loadtxt, c, usecols=[0, bogus_idx, 0]
            )

    def test_bad_usecols(self):
        with pytest.raises(OverflowError):
            np.loadtxt(["1\n"], usecols=[2**64], delimiter=",")
        with pytest.raises((ValueError, OverflowError)):
            # Overflow error on 32bit platforms
            np.loadtxt(["1\n"], usecols=[2**62], delimiter=",")
        with pytest.raises(TypeError,
                match="If a structured dtype .*. But 1 usecols were given and "
                      "the number of fields is 3."):
            np.loadtxt(["1,1\n"], dtype="i,2i", usecols=[0], delimiter=",")

    def test_fancy_dtype(self):
        c = TextIO()
        c.write('1,2,3.0\n4,5,6.0\n')
        c.seek(0)
        dt = np.dtype([('x', int), ('y', [('t', int), ('s', float)])])
        x = np.loadtxt(c, dtype=dt, delimiter=',')
        a = np.array([(1, (2, 3.0)), (4, (5, 6.0))], dt)
        assert_array_equal(x, a)

    def test_shaped_dtype(self):
        c = TextIO("aaaa  1.0  8.0  1 2 3 4 5 6")
        dt = np.dtype([('name', 'S4'), ('x', float), ('y', float),
                       ('block', int, (2, 3))])
        x = np.loadtxt(c, dtype=dt)
        a = np.array([('aaaa', 1.0, 8.0, [[1, 2, 3], [4, 5, 6]])],
                     dtype=dt)
        assert_array_equal(x, a)

    def test_3d_shaped_dtype(self):
        c = TextIO("aaaa  1.0  8.0  1 2 3 4 5 6 7 8 9 10 11 12")
        dt = np.dtype([('name', 'S4'), ('x', float), ('y', float),
                       ('block', int, (2, 2, 3))])
        x = np.loadtxt(c, dtype=dt)
        a = np.array([('aaaa', 1.0, 8.0,
                       [[[1, 2, 3], [4, 5, 6]], [[7, 8, 9], [10, 11, 12]]])],
                     dtype=dt)
        assert_array_equal(x, a)

    def test_str_dtype(self):
        # see gh-8033
        c = ["str1", "str2"]

        for dt in (str, np.bytes_):
            a = np.array(["str1", "str2"], dtype=dt)
            x = np.loadtxt(c, dtype=dt)
            assert_array_equal(x, a)

    def test_empty_file(self):
        with pytest.warns(UserWarning, match="input contained no data"):
            c = TextIO()
            x = np.loadtxt(c)
            assert_equal(x.shape, (0,))
            x = np.loadtxt(c, dtype=np.int64)
            assert_equal(x.shape, (0,))
            assert_(x.dtype == np.int64)

    def test_unused_converter(self):
        c = TextIO()
        c.writelines(['1 21\n', '3 42\n'])
        c.seek(0)
        data = np.loadtxt(c, usecols=(1,),
                          converters={0: lambda s: int(s, 16)})
        assert_array_equal(data, [21, 42])

        c.seek(0)
        data = np.loadtxt(c, usecols=(1,),
                          converters={1: lambda s: int(s, 16)})
        assert_array_equal(data, [33, 66])

    def test_dtype_with_object(self):
        # Test using an explicit dtype with an object
        data = """ 1; 2001-01-01
                   2; 2002-01-31 """
        ndtype = [('idx', int), ('code', object)]
        func = lambda s: strptime(s.strip(), "%Y-%m-%d")
        converters = {1: func}
        test = np.loadtxt(TextIO(data), delimiter=";", dtype=ndtype,
                          converters=converters)
        control = np.array(
            [(1, datetime(2001, 1, 1)), (2, datetime(2002, 1, 31))],
            dtype=ndtype)
        assert_equal(test, control)

    def test_uint64_type(self):
        tgt = (9223372043271415339, 9223372043271415853)
        c = TextIO()
        c.write("%s %s" % tgt)
        c.seek(0)
        res = np.loadtxt(c, dtype=np.uint64)
        assert_equal(res, tgt)

    def test_int64_type(self):
        tgt = (-9223372036854775807, 9223372036854775807)
        c = TextIO()
        c.write("%s %s" % tgt)
        c.seek(0)
        res = np.loadtxt(c, dtype=np.int64)
        assert_equal(res, tgt)

    def test_from_float_hex(self):
        # IEEE doubles and floats only, otherwise the float32
        # conversion may fail.
        tgt = np.logspace(-10, 10, 5).astype(np.float32)
        tgt = np.hstack((tgt, -tgt)).astype(float)
        inp = '\n'.join(map(float.hex, tgt))
        c = TextIO()
        c.write(inp)
        for dt in [float, np.float32]:
            c.seek(0)
            res = np.loadtxt(
                c, dtype=dt, converters=float.fromhex, encoding="latin1")
            assert_equal(res, tgt, err_msg=f"{dt}")

    @pytest.mark.skipif(IS_PYPY and sys.implementation.version <= (7, 3, 8),
                        reason="PyPy bug in error formatting")
    def test_default_float_converter_no_default_hex_conversion(self):
        """
        Ensure that fromhex is only used for values with the correct prefix and
        is not called by default. Regression test related to gh-19598.
        """
        c = TextIO("a b c")
        with pytest.raises(ValueError,
                match=".*convert string 'a' to float64 at row 0, column 1"):
            np.loadtxt(c)

    @pytest.mark.skipif(IS_PYPY and sys.implementation.version <= (7, 3, 8),
                        reason="PyPy bug in error formatting")
    def test_default_float_converter_exception(self):
        """
        Ensure that the exception message raised during failed floating point
        conversion is correct. Regression test related to gh-19598.
        """
        c = TextIO("qrs tuv")  # Invalid values for default float converter
        with pytest.raises(ValueError,
                match="could not convert string 'qrs' to float64"):
            np.loadtxt(c)

    def test_from_complex(self):
        tgt = (complex(1, 1), complex(1, -1))
        c = TextIO()
        c.write("%s %s" % tgt)
        c.seek(0)
        res = np.loadtxt(c, dtype=complex)
        assert_equal(res, tgt)

    def test_complex_misformatted(self):
        # test for backward compatibility
        # some complex formats used to generate x+-yj
        a = np.zeros((2, 2), dtype=np.complex128)
        re = np.pi
        im = np.e
        a[:] = re - 1.0j * im
        c = BytesIO()
        np.savetxt(c, a, fmt='%.16e')
        c.seek(0)
        txt = c.read()
        c.seek(0)
        # misformat the sign on the imaginary part, gh 7895
        txt_bad = txt.replace(b'e+00-', b'e00+-')
        assert_(txt_bad != txt)
        c.write(txt_bad)
        c.seek(0)
        res = np.loadtxt(c, dtype=complex)
        assert_equal(res, a)

    def test_universal_newline(self):
        with temppath() as name:
            with open(name, 'w') as f:
                f.write('1 21\r3 42\r')
            data = np.loadtxt(name)
        assert_array_equal(data, [[1, 21], [3, 42]])

    def test_empty_field_after_tab(self):
        c = TextIO()
        c.write('1 \t2 \t3\tstart \n4\t5\t6\t  \n7\t8\t9.5\t')
        c.seek(0)
        dt = {'names': ('x', 'y', 'z', 'comment'),
              'formats': ('<i4', '<i4', '<f4', '|S8')}
        x = np.loadtxt(c, dtype=dt, delimiter='\t')
        a = np.array([b'start ', b'  ', b''])
        assert_array_equal(x['comment'], a)

    def test_unpack_structured(self):
        txt = TextIO("M 21 72\nF 35 58")
        dt = {'names': ('a', 'b', 'c'), 'formats': ('|S1', '<i4', '<f4')}
        a, b, c = np.loadtxt(txt, dtype=dt, unpack=True)
        assert_(a.dtype.str == '|S1')
        assert_(b.dtype.str == '<i4')
        assert_(c.dtype.str == '<f4')
        assert_array_equal(a, np.array([b'M', b'F']))
        assert_array_equal(b, np.array([21, 35]))
        assert_array_equal(c, np.array([72.,  58.]))

    def test_ndmin_keyword(self):
        c = TextIO()
        c.write('1,2,3\n4,5,6')
        c.seek(0)
        assert_raises(ValueError, np.loadtxt, c, ndmin=3)
        c.seek(0)
        assert_raises(ValueError, np.loadtxt, c, ndmin=1.5)
        c.seek(0)
        x = np.loadtxt(c, dtype=int, delimiter=',', ndmin=1)
        a = np.array([[1, 2, 3], [4, 5, 6]])
        assert_array_equal(x, a)

        d = TextIO()
        d.write('0,1,2')
        d.seek(0)
        x = np.loadtxt(d, dtype=int, delimiter=',', ndmin=2)
        assert_(x.shape == (1, 3))
        d.seek(0)
        x = np.loadtxt(d, dtype=int, delimiter=',', ndmin=1)
        assert_(x.shape == (3,))
        d.seek(0)
        x = np.loadtxt(d, dtype=int, delimiter=',', ndmin=0)
        assert_(x.shape == (3,))

        e = TextIO()
        e.write('0\n1\n2')
        e.seek(0)
        x = np.loadtxt(e, dtype=int, delimiter=',', ndmin=2)
        assert_(x.shape == (3, 1))
        e.seek(0)
        x = np.loadtxt(e, dtype=int, delimiter=',', ndmin=1)
        assert_(x.shape == (3,))
        e.seek(0)
        x = np.loadtxt(e, dtype=int, delimiter=',', ndmin=0)
        assert_(x.shape == (3,))

        # Test ndmin kw with empty file.
        with pytest.warns(UserWarning, match="input contained no data"):
            f = TextIO()
            assert_(np.loadtxt(f, ndmin=2).shape == (0, 1,))
            assert_(np.loadtxt(f, ndmin=1).shape == (0,))

    def test_generator_source(self):
        def count():
            for i in range(10):
                yield "%d" % i

        res = np.loadtxt(count())
        assert_array_equal(res, np.arange(10))

    def test_bad_line(self):
        c = TextIO()
        c.write('1 2 3\n4 5 6\n2 3')
        c.seek(0)

        # Check for exception and that exception contains line number
        assert_raises_regex(ValueError, "3", np.loadtxt, c)

    def test_none_as_string(self):
        # gh-5155, None should work as string when format demands it
        c = TextIO()
        c.write('100,foo,200\n300,None,400')
        c.seek(0)
        dt = np.dtype([('x', int), ('a', 'S10'), ('y', int)])
        np.loadtxt(c, delimiter=',', dtype=dt, comments=None)  # Should succeed

    @pytest.mark.skipif(locale.getpreferredencoding() == 'ANSI_X3.4-1968',
                        reason="Wrong preferred encoding")
    def test_binary_load(self):
        butf8 = b"5,6,7,\xc3\x95scarscar\r\n15,2,3,hello\r\n"\
                b"20,2,3,\xc3\x95scar\r\n"
        sutf8 = butf8.decode("UTF-8").replace("\r", "").splitlines()
        with temppath() as path:
            with open(path, "wb") as f:
                f.write(butf8)
            with open(path, "rb") as f:
                x = np.loadtxt(f, encoding="UTF-8", dtype=np.str_)
            assert_array_equal(x, sutf8)
            # test broken latin1 conversion people now rely on
            with open(path, "rb") as f:
                x = np.loadtxt(f, encoding="UTF-8", dtype="S")
            x = [b'5,6,7,\xc3\x95scarscar', b'15,2,3,hello', b'20,2,3,\xc3\x95scar']
            assert_array_equal(x, np.array(x, dtype="S"))

    def test_max_rows(self):
        c = TextIO()
        c.write('1,2,3,5\n4,5,7,8\n2,1,4,5')
        c.seek(0)
        x = np.loadtxt(c, dtype=int, delimiter=',',
                       max_rows=1)
        a = np.array([1, 2, 3, 5], int)
        assert_array_equal(x, a)

    def test_max_rows_with_skiprows(self):
        c = TextIO()
        c.write('comments\n1,2,3,5\n4,5,7,8\n2,1,4,5')
        c.seek(0)
        x = np.loadtxt(c, dtype=int, delimiter=',',
                       skiprows=1, max_rows=1)
        a = np.array([1, 2, 3, 5], int)
        assert_array_equal(x, a)

        c = TextIO()
        c.write('comment\n1,2,3,5\n4,5,7,8\n2,1,4,5')
        c.seek(0)
        x = np.loadtxt(c, dtype=int, delimiter=',',
                       skiprows=1, max_rows=2)
        a = np.array([[1, 2, 3, 5], [4, 5, 7, 8]], int)
        assert_array_equal(x, a)

    def test_max_rows_with_read_continuation(self):
        c = TextIO()
        c.write('1,2,3,5\n4,5,7,8\n2,1,4,5')
        c.seek(0)
        x = np.loadtxt(c, dtype=int, delimiter=',',
                       max_rows=2)
        a = np.array([[1, 2, 3, 5], [4, 5, 7, 8]], int)
        assert_array_equal(x, a)
        # test continuation
        x = np.loadtxt(c, dtype=int, delimiter=',')
        a = np.array([2, 1, 4, 5], int)
        assert_array_equal(x, a)

    def test_max_rows_larger(self):
        #test max_rows > num rows
        c = TextIO()
        c.write('comment\n1,2,3,5\n4,5,7,8\n2,1,4,5')
        c.seek(0)
        x = np.loadtxt(c, dtype=int, delimiter=',',
                       skiprows=1, max_rows=6)
        a = np.array([[1, 2, 3, 5], [4, 5, 7, 8], [2, 1, 4, 5]], int)
        assert_array_equal(x, a)

    @pytest.mark.parametrize(["skip", "data"], [
            (1, ["ignored\n", "1,2\n", "\n", "3,4\n"]),
            # "Bad" lines that do not end in newlines:
            (1, ["ignored", "1,2", "", "3,4"]),
            (1, StringIO("ignored\n1,2\n\n3,4")),
            # Same as above, but do not skip any lines:
            (0, ["-1,0\n", "1,2\n", "\n", "3,4\n"]),
            (0, ["-1,0", "1,2", "", "3,4"]),
            (0, StringIO("-1,0\n1,2\n\n3,4"))])
    def test_max_rows_empty_lines(self, skip, data):
        with pytest.warns(UserWarning,
                    match=f"Input line 3.*max_rows={3 - skip}"):
            res = np.loadtxt(data, dtype=int, skiprows=skip, delimiter=",",
                             max_rows=3 - skip)
            assert_array_equal(res, [[-1, 0], [1, 2], [3, 4]][skip:])

        if isinstance(data, StringIO):
            data.seek(0)

        with warnings.catch_warnings():
            warnings.simplefilter("error", UserWarning)
            with pytest.raises(UserWarning):
                np.loadtxt(data, dtype=int, skiprows=skip, delimiter=",",
                           max_rows=3 - skip)

class Testfromregex:
    def test_record(self):
        c = TextIO()
        c.write('1.312 foo\n1.534 bar\n4.444 qux')
        c.seek(0)

        dt = [('num', np.float64), ('val', 'S3')]
        x = np.fromregex(c, r"([0-9.]+)\s+(...)", dt)
        a = np.array([(1.312, 'foo'), (1.534, 'bar'), (4.444, 'qux')],
                     dtype=dt)
        assert_array_equal(x, a)

    def test_record_2(self):
        c = TextIO()
        c.write('1312 foo\n1534 bar\n4444 qux')
        c.seek(0)

        dt = [('num', np.int32), ('val', 'S3')]
        x = np.fromregex(c, r"(\d+)\s+(...)", dt)
        a = np.array([(1312, 'foo'), (1534, 'bar'), (4444, 'qux')],
                     dtype=dt)
        assert_array_equal(x, a)

    def test_record_3(self):
        c = TextIO()
        c.write('1312 foo\n1534 bar\n4444 qux')
        c.seek(0)

        dt = [('num', np.float64)]
        x = np.fromregex(c, r"(\d+)\s+...", dt)
        a = np.array([(1312,), (1534,), (4444,)], dtype=dt)
        assert_array_equal(x, a)

    @pytest.mark.parametrize("path_type", [str, Path])
    def test_record_unicode(self, path_type):
        utf8 = b'\xcf\x96'
        with temppath() as str_path:
            path = path_type(str_path)
            with open(path, 'wb') as f:
                f.write(b'1.312 foo' + utf8 + b' \n1.534 bar\n4.444 qux')

            dt = [('num', np.float64), ('val', 'U4')]
            x = np.fromregex(path, r"(?u)([0-9.]+)\s+(\w+)", dt, encoding='UTF-8')
            a = np.array([(1.312, 'foo' + utf8.decode('UTF-8')), (1.534, 'bar'),
                           (4.444, 'qux')], dtype=dt)
            assert_array_equal(x, a)

            regexp = re.compile(r"([0-9.]+)\s+(\w+)", re.UNICODE)
            x = np.fromregex(path, regexp, dt, encoding='UTF-8')
            assert_array_equal(x, a)

    def test_compiled_bytes(self):
        regexp = re.compile(br'(\d)')
        c = BytesIO(b'123')
        dt = [('num', np.float64)]
        a = np.array([1, 2, 3], dtype=dt)
        x = np.fromregex(c, regexp, dt)
        assert_array_equal(x, a)

    def test_bad_dtype_not_structured(self):
        regexp = re.compile(br'(\d)')
        c = BytesIO(b'123')
        with pytest.raises(TypeError, match='structured datatype'):
            np.fromregex(c, regexp, dtype=np.float64)


#####--------------------------------------------------------------------------


class TestFromTxt(LoadTxtBase):
    loadfunc = staticmethod(np.genfromtxt)

    def test_record(self):
        # Test w/ explicit dtype
        data = TextIO('1 2\n3 4')
        test = np.genfromtxt(data, dtype=[('x', np.int32), ('y', np.int32)])
        control = np.array([(1, 2), (3, 4)], dtype=[('x', 'i4'), ('y', 'i4')])
        assert_equal(test, control)
        #
        data = TextIO('M 64.0 75.0\nF 25.0 60.0')
        descriptor = {'names': ('gender', 'age', 'weight'),
                      'formats': ('S1', 'i4', 'f4')}
        control = np.array([('M', 64.0, 75.0), ('F', 25.0, 60.0)],
                           dtype=descriptor)
        test = np.genfromtxt(data, dtype=descriptor)
        assert_equal(test, control)

    def test_array(self):
        # Test outputting a standard ndarray
        data = TextIO('1 2\n3 4')
        control = np.array([[1, 2], [3, 4]], dtype=int)
        test = np.genfromtxt(data, dtype=int)
        assert_array_equal(test, control)
        #
        data.seek(0)
        control = np.array([[1, 2], [3, 4]], dtype=float)
        test = np.loadtxt(data, dtype=float)
        assert_array_equal(test, control)

    def test_1D(self):
        # Test squeezing to 1D
        control = np.array([1, 2, 3, 4], int)
        #
        data = TextIO('1\n2\n3\n4\n')
        test = np.genfromtxt(data, dtype=int)
        assert_array_equal(test, control)
        #
        data = TextIO('1,2,3,4\n')
        test = np.genfromtxt(data, dtype=int, delimiter=',')
        assert_array_equal(test, control)

    def test_comments(self):
        # Test the stripping of comments
        control = np.array([1, 2, 3, 5], int)
        # Comment on its own line
        data = TextIO('# comment\n1,2,3,5\n')
        test = np.genfromtxt(data, dtype=int, delimiter=',', comments='#')
        assert_equal(test, control)
        # Comment at the end of a line
        data = TextIO('1,2,3,5# comment\n')
        test = np.genfromtxt(data, dtype=int, delimiter=',', comments='#')
        assert_equal(test, control)

    def test_skiprows(self):
        # Test row skipping
        control = np.array([1, 2, 3, 5], int)
        kwargs = {"dtype": int, "delimiter": ','}
        #
        data = TextIO('comment\n1,2,3,5\n')
        test = np.genfromtxt(data, skip_header=1, **kwargs)
        assert_equal(test, control)
        #
        data = TextIO('# comment\n1,2,3,5\n')
        test = np.loadtxt(data, skiprows=1, **kwargs)
        assert_equal(test, control)

    def test_skip_footer(self):
        data = [f"# {i}" for i in range(1, 6)]
        data.append("A, B, C")
        data.extend([f"{i},{i:3.1f},{i:03d}" for i in range(51)])
        data[-1] = "99,99"
        kwargs = {"delimiter": ",", "names": True, "skip_header": 5, "skip_footer": 10}
        test = np.genfromtxt(TextIO("\n".join(data)), **kwargs)
        ctrl = np.array([(f"{i:f}", f"{i:f}", f"{i:f}") for i in range(41)],
                        dtype=[(_, float) for _ in "ABC"])
        assert_equal(test, ctrl)

    def test_skip_footer_with_invalid(self):
        with suppress_warnings() as sup:
            sup.filter(ConversionWarning)
            basestr = '1 1\n2 2\n3 3\n4 4\n5  \n6  \n7  \n'
            # Footer too small to get rid of all invalid values
            assert_raises(ValueError, np.genfromtxt,
                          TextIO(basestr), skip_footer=1)
    #        except ValueError:
    #            pass
            a = np.genfromtxt(
                TextIO(basestr), skip_footer=1, invalid_raise=False)
            assert_equal(a, np.array([[1., 1.], [2., 2.], [3., 3.], [4., 4.]]))
            #
            a = np.genfromtxt(TextIO(basestr), skip_footer=3)
            assert_equal(a, np.array([[1., 1.], [2., 2.], [3., 3.], [4., 4.]]))
            #
            basestr = '1 1\n2  \n3 3\n4 4\n5  \n6 6\n7 7\n'
            a = np.genfromtxt(
                TextIO(basestr), skip_footer=1, invalid_raise=False)
            assert_equal(a, np.array([[1., 1.], [3., 3.], [4., 4.], [6., 6.]]))
            a = np.genfromtxt(
                TextIO(basestr), skip_footer=3, invalid_raise=False)
            assert_equal(a, np.array([[1., 1.], [3., 3.], [4., 4.]]))

    def test_header(self):
        # Test retrieving a header
        data = TextIO('gender age weight\nM 64.0 75.0\nF 25.0 60.0')
        with warnings.catch_warnings(record=True) as w:
            warnings.filterwarnings('always', '', VisibleDeprecationWarning)
            test = np.genfromtxt(data, dtype=None, names=True,
                                 encoding='bytes')
            assert_(w[0].category is VisibleDeprecationWarning)
        control = {'gender': np.array([b'M', b'F']),
                   'age': np.array([64.0, 25.0]),
                   'weight': np.array([75.0, 60.0])}
        assert_equal(test['gender'], control['gender'])
        assert_equal(test['age'], control['age'])
        assert_equal(test['weight'], control['weight'])

    def test_auto_dtype(self):
        # Test the automatic definition of the output dtype
        data = TextIO('A 64 75.0 3+4j True\nBCD 25 60.0 5+6j False')
        with warnings.catch_warnings(record=True) as w:
            warnings.filterwarnings('always', '', VisibleDeprecationWarning)
            test = np.genfromtxt(data, dtype=None, encoding='bytes')
            assert_(w[0].category is VisibleDeprecationWarning)
        control = [np.array([b'A', b'BCD']),
                   np.array([64, 25]),
                   np.array([75.0, 60.0]),
                   np.array([3 + 4j, 5 + 6j]),
                   np.array([True, False]), ]
        assert_equal(test.dtype.names, ['f0', 'f1', 'f2', 'f3', 'f4'])
        for (i, ctrl) in enumerate(control):
            assert_equal(test[f'f{i}'], ctrl)

    def test_auto_dtype_uniform(self):
        # Tests whether the output dtype can be uniformized
        data = TextIO('1 2 3 4\n5 6 7 8\n')
        test = np.genfromtxt(data, dtype=None)
        control = np.array([[1, 2, 3, 4], [5, 6, 7, 8]])
        assert_equal(test, control)

    def test_fancy_dtype(self):
        # Check that a nested dtype isn't MIA
        data = TextIO('1,2,3.0\n4,5,6.0\n')
        fancydtype = np.dtype([('x', int), ('y', [('t', int), ('s', float)])])
        test = np.genfromtxt(data, dtype=fancydtype, delimiter=',')
        control = np.array([(1, (2, 3.0)), (4, (5, 6.0))], dtype=fancydtype)
        assert_equal(test, control)

    def test_names_overwrite(self):
        # Test overwriting the names of the dtype
        descriptor = {'names': ('g', 'a', 'w'),
                      'formats': ('S1', 'i4', 'f4')}
        data = TextIO(b'M 64.0 75.0\nF 25.0 60.0')
        names = ('gender', 'age', 'weight')
        test = np.genfromtxt(data, dtype=descriptor, names=names)
        descriptor['names'] = names
        control = np.array([('M', 64.0, 75.0),
                            ('F', 25.0, 60.0)], dtype=descriptor)
        assert_equal(test, control)

    def test_bad_fname(self):
        with pytest.raises(TypeError, match='fname must be a string,'):
            np.genfromtxt(123)

    def test_commented_header(self):
        # Check that names can be retrieved even if the line is commented out.
        data = TextIO("""
#gender age weight
M   21  72.100000
F   35  58.330000
M   33  21.99
        """)
        # The # is part of the first name and should be deleted automatically.
        with warnings.catch_warnings(record=True) as w:
            warnings.filterwarnings('always', '', VisibleDeprecationWarning)
            test = np.genfromtxt(data, names=True, dtype=None,
                                 encoding="bytes")
            assert_(w[0].category is VisibleDeprecationWarning)
        ctrl = np.array([('M', 21, 72.1), ('F', 35, 58.33), ('M', 33, 21.99)],
                        dtype=[('gender', '|S1'), ('age', int), ('weight', float)])
        assert_equal(test, ctrl)
        # Ditto, but we should get rid of the first element
        data = TextIO(b"""
# gender age weight
M   21  72.100000
F   35  58.330000
M   33  21.99
        """)
        with warnings.catch_warnings(record=True) as w:
            warnings.filterwarnings('always', '', VisibleDeprecationWarning)
            test = np.genfromtxt(data, names=True, dtype=None,
                                 encoding="bytes")
            assert_(w[0].category is VisibleDeprecationWarning)
        assert_equal(test, ctrl)

    def test_names_and_comments_none(self):
        # Tests case when names is true but comments is None (gh-10780)
        data = TextIO('col1 col2\n 1 2\n 3 4')
        test = np.genfromtxt(data, dtype=(int, int), comments=None, names=True)
        control = np.array([(1, 2), (3, 4)], dtype=[('col1', int), ('col2', int)])
        assert_equal(test, control)

    def test_file_is_closed_on_error(self):
        # gh-13200
        with tempdir() as tmpdir:
            fpath = os.path.join(tmpdir, "test.csv")
            with open(fpath, "wb") as f:
                f.write('\N{GREEK PI SYMBOL}'.encode())

            # ResourceWarnings are emitted from a destructor, so won't be
            # detected by regular propagation to errors.
            with assert_no_warnings():
                with pytest.raises(UnicodeDecodeError):
                    np.genfromtxt(fpath, encoding="ascii")

    def test_autonames_and_usecols(self):
        # Tests names and usecols
        data = TextIO('A B C D\n aaaa 121 45 9.1')
        with warnings.catch_warnings(record=True) as w:
            warnings.filterwarnings('always', '', VisibleDeprecationWarning)
            test = np.genfromtxt(data, usecols=('A', 'C', 'D'),
                                names=True, dtype=None, encoding="bytes")
            assert_(w[0].category is VisibleDeprecationWarning)
        control = np.array(('aaaa', 45, 9.1),
                           dtype=[('A', '|S4'), ('C', int), ('D', float)])
        assert_equal(test, control)

    def test_converters_with_usecols(self):
        # Test the combination user-defined converters and usecol
        data = TextIO('1,2,3,,5\n6,7,8,9,10\n')
        test = np.genfromtxt(data, dtype=int, delimiter=',',
                            converters={3: lambda s: int(s or - 999)},
                            usecols=(1, 3,))
        control = np.array([[2, -999], [7, 9]], int)
        assert_equal(test, control)

    def test_converters_with_usecols_and_names(self):
        # Tests names and usecols
        data = TextIO('A B C D\n aaaa 121 45 9.1')
        with warnings.catch_warnings(record=True) as w:
            warnings.filterwarnings('always', '', VisibleDeprecationWarning)
            test = np.genfromtxt(data, usecols=('A', 'C', 'D'), names=True,
                                dtype=None, encoding="bytes",
                                converters={'C': lambda s: 2 * int(s)})
            assert_(w[0].category is VisibleDeprecationWarning)
        control = np.array(('aaaa', 90, 9.1),
                           dtype=[('A', '|S4'), ('C', int), ('D', float)])
        assert_equal(test, control)

    def test_converters_cornercases(self):
        # Test the conversion to datetime.
        converter = {
            'date': lambda s: strptime(s, '%Y-%m-%d %H:%M:%SZ')}
        data = TextIO('2009-02-03 12:00:00Z, 72214.0')
        test = np.genfromtxt(data, delimiter=',', dtype=None,
                            names=['date', 'stid'], converters=converter)
        control = np.array((datetime(2009, 2, 3), 72214.),
                           dtype=[('date', np.object_), ('stid', float)])
        assert_equal(test, control)

    def test_converters_cornercases2(self):
        # Test the conversion to datetime64.
        converter = {
            'date': lambda s: np.datetime64(strptime(s, '%Y-%m-%d %H:%M:%SZ'))}
        data = TextIO('2009-02-03 12:00:00Z, 72214.0')
        test = np.genfromtxt(data, delimiter=',', dtype=None,
                            names=['date', 'stid'], converters=converter)
        control = np.array((datetime(2009, 2, 3), 72214.),
                           dtype=[('date', 'datetime64[us]'), ('stid', float)])
        assert_equal(test, control)

    def test_unused_converter(self):
        # Test whether unused converters are forgotten
        data = TextIO("1 21\n  3 42\n")
        test = np.genfromtxt(data, usecols=(1,),
                            converters={0: lambda s: int(s, 16)})
        assert_equal(test, [21, 42])
        #
        data.seek(0)
        test = np.genfromtxt(data, usecols=(1,),
                            converters={1: lambda s: int(s, 16)})
        assert_equal(test, [33, 66])

    def test_invalid_converter(self):
        strip_rand = lambda x: float((b'r' in x.lower() and x.split()[-1]) or
                                     ((b'r' not in x.lower() and x.strip()) or 0.0))
        strip_per = lambda x: float((b'%' in x.lower() and x.split()[0]) or
                                    ((b'%' not in x.lower() and x.strip()) or 0.0))
        s = TextIO("D01N01,10/1/2003 ,1 %,R 75,400,600\r\n"
                   "L24U05,12/5/2003, 2 %,1,300, 150.5\r\n"
                   "D02N03,10/10/2004,R 1,,7,145.55")
        kwargs = {
            "converters": {2: strip_per, 3: strip_rand}, "delimiter": ",",
            "dtype": None, "encoding": "bytes"}
        assert_raises(ConverterError, np.genfromtxt, s, **kwargs)

    def test_tricky_converter_bug1666(self):
        # Test some corner cases
        s = TextIO('q1,2\nq3,4')
        cnv = lambda s: float(s[1:])
        test = np.genfromtxt(s, delimiter=',', converters={0: cnv})
        control = np.array([[1., 2.], [3., 4.]])
        assert_equal(test, control)

    def test_dtype_with_converters(self):
        dstr = "2009; 23; 46"
        test = np.genfromtxt(TextIO(dstr,),
                            delimiter=";", dtype=float, converters={0: bytes})
        control = np.array([('2009', 23., 46)],
                           dtype=[('f0', '|S4'), ('f1', float), ('f2', float)])
        assert_equal(test, control)
        test = np.genfromtxt(TextIO(dstr,),
                            delimiter=";", dtype=float, converters={0: float})
        control = np.array([2009., 23., 46],)
        assert_equal(test, control)

    @pytest.mark.filterwarnings("ignore:.*recfromcsv.*:DeprecationWarning")
    def test_dtype_with_converters_and_usecols(self):
        dstr = "1,5,-1,1:1\n2,8,-1,1:n\n3,3,-2,m:n\n"
        dmap = {'1:1': 0, '1:n': 1, 'm:1': 2, 'm:n': 3}
        dtyp = [('e1', 'i4'), ('e2', 'i4'), ('e3', 'i2'), ('n', 'i1')]
        conv = {0: int, 1: int, 2: int, 3: lambda r: dmap[r.decode()]}
        test = recfromcsv(TextIO(dstr,), dtype=dtyp, delimiter=',',
                          names=None, converters=conv, encoding="bytes")
        control = np.rec.array([(1, 5, -1, 0), (2, 8, -1, 1), (3, 3, -2, 3)], dtype=dtyp)
        assert_equal(test, control)
        dtyp = [('e1', 'i4'), ('e2', 'i4'), ('n', 'i1')]
        test = recfromcsv(TextIO(dstr,), dtype=dtyp, delimiter=',',
                          usecols=(0, 1, 3), names=None, converters=conv,
                          encoding="bytes")
        control = np.rec.array([(1, 5, 0), (2, 8, 1), (3, 3, 3)], dtype=dtyp)
        assert_equal(test, control)

    def test_dtype_with_object(self):
        # Test using an explicit dtype with an object
        data = """ 1; 2001-01-01
                   2; 2002-01-31 """
        ndtype = [('idx', int), ('code', object)]
        func = lambda s: strptime(s.strip(), "%Y-%m-%d")
        converters = {1: func}
        test = np.genfromtxt(TextIO(data), delimiter=";", dtype=ndtype,
                             converters=converters)
        control = np.array(
            [(1, datetime(2001, 1, 1)), (2, datetime(2002, 1, 31))],
            dtype=ndtype)
        assert_equal(test, control)

        ndtype = [('nest', [('idx', int), ('code', object)])]
        with assert_raises_regex(NotImplementedError,
                                 'Nested fields.* not supported.*'):
            test = np.genfromtxt(TextIO(data), delimiter=";",
                                 dtype=ndtype, converters=converters)

        # nested but empty fields also aren't supported
        ndtype = [('idx', int), ('code', object), ('nest', [])]
        with assert_raises_regex(NotImplementedError,
                                 'Nested fields.* not supported.*'):
            test = np.genfromtxt(TextIO(data), delimiter=";",
                                 dtype=ndtype, converters=converters)

    def test_dtype_with_object_no_converter(self):
        # Object without a converter uses bytes:
        parsed = np.genfromtxt(TextIO("1"), dtype=object)
        assert parsed[()] == b"1"
        parsed = np.genfromtxt(TextIO("string"), dtype=object)
        assert parsed[()] == b"string"

    def test_userconverters_with_explicit_dtype(self):
        # Test user_converters w/ explicit (standard) dtype
        data = TextIO('skip,skip,2001-01-01,1.0,skip')
        test = np.genfromtxt(data, delimiter=",", names=None, dtype=float,
                             usecols=(2, 3), converters={2: bytes})
        control = np.array([('2001-01-01', 1.)],
                           dtype=[('', '|S10'), ('', float)])
        assert_equal(test, control)

    def test_utf8_userconverters_with_explicit_dtype(self):
        utf8 = b'\xcf\x96'
        with temppath() as path:
            with open(path, 'wb') as f:
                f.write(b'skip,skip,2001-01-01' + utf8 + b',1.0,skip')
            test = np.genfromtxt(path, delimiter=",", names=None, dtype=float,
                                 usecols=(2, 3), converters={2: str},
                                 encoding='UTF-8')
        control = np.array([('2001-01-01' + utf8.decode('UTF-8'), 1.)],
                           dtype=[('', '|U11'), ('', float)])
        assert_equal(test, control)

    def test_spacedelimiter(self):
        # Test space delimiter
        data = TextIO("1  2  3  4   5\n6  7  8  9  10")
        test = np.genfromtxt(data)
        control = np.array([[1., 2., 3., 4., 5.],
                            [6., 7., 8., 9., 10.]])
        assert_equal(test, control)

    def test_integer_delimiter(self):
        # Test using an integer for delimiter
        data = "  1  2  3\n  4  5 67\n890123  4"
        test = np.genfromtxt(TextIO(data), delimiter=3)
        control = np.array([[1, 2, 3], [4, 5, 67], [890, 123, 4]])
        assert_equal(test, control)

    def test_missing(self):
        data = TextIO('1,2,3,,5\n')
        test = np.genfromtxt(data, dtype=int, delimiter=',',
                            converters={3: lambda s: int(s or - 999)})
        control = np.array([1, 2, 3, -999, 5], int)
        assert_equal(test, control)

    def test_missing_with_tabs(self):
        # Test w/ a delimiter tab
        txt = "1\t2\t3\n\t2\t\n1\t\t3"
        test = np.genfromtxt(TextIO(txt), delimiter="\t",
                             usemask=True,)
        ctrl_d = np.array([(1, 2, 3), (np.nan, 2, np.nan), (1, np.nan, 3)],)
        ctrl_m = np.array([(0, 0, 0), (1, 0, 1), (0, 1, 0)], dtype=bool)
        assert_equal(test.data, ctrl_d)
        assert_equal(test.mask, ctrl_m)

    def test_usecols(self):
        # Test the selection of columns
        # Select 1 column
        control = np.array([[1, 2], [3, 4]], float)
        data = TextIO()
        np.savetxt(data, control)
        data.seek(0)
        test = np.genfromtxt(data, dtype=float, usecols=(1,))
        assert_equal(test, control[:, 1])
        #
        control = np.array([[1, 2, 3], [3, 4, 5]], float)
        data = TextIO()
        np.savetxt(data, control)
        data.seek(0)
        test = np.genfromtxt(data, dtype=float, usecols=(1, 2))
        assert_equal(test, control[:, 1:])
        # Testing with arrays instead of tuples.
        data.seek(0)
        test = np.genfromtxt(data, dtype=float, usecols=np.array([1, 2]))
        assert_equal(test, control[:, 1:])

    def test_usecols_as_css(self):
        # Test giving usecols with a comma-separated string
        data = "1 2 3\n4 5 6"
        test = np.genfromtxt(TextIO(data),
                             names="a, b, c", usecols="a, c")
        ctrl = np.array([(1, 3), (4, 6)], dtype=[(_, float) for _ in "ac"])
        assert_equal(test, ctrl)

    def test_usecols_with_structured_dtype(self):
        # Test usecols with an explicit structured dtype
        data = TextIO("JOE 70.1 25.3\nBOB 60.5 27.9")
        names = ['stid', 'temp']
        dtypes = ['S4', 'f8']
        test = np.genfromtxt(
            data, usecols=(0, 2), dtype=list(zip(names, dtypes)))
        assert_equal(test['stid'], [b"JOE", b"BOB"])
        assert_equal(test['temp'], [25.3, 27.9])

    def test_usecols_with_integer(self):
        # Test usecols with an integer
        test = np.genfromtxt(TextIO(b"1 2 3\n4 5 6"), usecols=0)
        assert_equal(test, np.array([1., 4.]))

    def test_usecols_with_named_columns(self):
        # Test usecols with named columns
        ctrl = np.array([(1, 3), (4, 6)], dtype=[('a', float), ('c', float)])
        data = "1 2 3\n4 5 6"
        kwargs = {"names": "a, b, c"}
        test = np.genfromtxt(TextIO(data), usecols=(0, -1), **kwargs)
        assert_equal(test, ctrl)
        test = np.genfromtxt(TextIO(data),
                             usecols=('a', 'c'), **kwargs)
        assert_equal(test, ctrl)

    def test_empty_file(self):
        # Test that an empty file raises the proper warning.
        with suppress_warnings() as sup:
            sup.filter(message="genfromtxt: Empty input file:")
            data = TextIO()
            test = np.genfromtxt(data)
            assert_equal(test, np.array([]))

            # when skip_header > 0
            test = np.genfromtxt(data, skip_header=1)
            assert_equal(test, np.array([]))

    def test_fancy_dtype_alt(self):
        # Check that a nested dtype isn't MIA
        data = TextIO('1,2,3.0\n4,5,6.0\n')
        fancydtype = np.dtype([('x', int), ('y', [('t', int), ('s', float)])])
        test = np.genfromtxt(data, dtype=fancydtype, delimiter=',', usemask=True)
        control = ma.array([(1, (2, 3.0)), (4, (5, 6.0))], dtype=fancydtype)
        assert_equal(test, control)

    def test_shaped_dtype(self):
        c = TextIO("aaaa  1.0  8.0  1 2 3 4 5 6")
        dt = np.dtype([('name', 'S4'), ('x', float), ('y', float),
                       ('block', int, (2, 3))])
        x = np.genfromtxt(c, dtype=dt)
        a = np.array([('aaaa', 1.0, 8.0, [[1, 2, 3], [4, 5, 6]])],
                     dtype=dt)
        assert_array_equal(x, a)

    def test_withmissing(self):
        data = TextIO('A,B\n0,1\n2,N/A')
        kwargs = {"delimiter": ",", "missing_values": "N/A", "names": True}
        test = np.genfromtxt(data, dtype=None, usemask=True, **kwargs)
        control = ma.array([(0, 1), (2, -1)],
                           mask=[(False, False), (False, True)],
                           dtype=[('A', int), ('B', int)])
        assert_equal(test, control)
        assert_equal(test.mask, control.mask)
        #
        data.seek(0)
        test = np.genfromtxt(data, usemask=True, **kwargs)
        control = ma.array([(0, 1), (2, -1)],
                           mask=[(False, False), (False, True)],
                           dtype=[('A', float), ('B', float)])
        assert_equal(test, control)
        assert_equal(test.mask, control.mask)

    def test_user_missing_values(self):
        data = "A, B, C\n0, 0., 0j\n1, N/A, 1j\n-9, 2.2, N/A\n3, -99, 3j"
        basekwargs = {"dtype": None, "delimiter": ",", "names": True}
        mdtype = [('A', int), ('B', float), ('C', complex)]
        #
        test = np.genfromtxt(TextIO(data), missing_values="N/A",
                            **basekwargs)
        control = ma.array([(0, 0.0, 0j), (1, -999, 1j),
                            (-9, 2.2, -999j), (3, -99, 3j)],
                           mask=[(0, 0, 0), (0, 1, 0), (0, 0, 1), (0, 0, 0)],
                           dtype=mdtype)
        assert_equal(test, control)
        #
        basekwargs['dtype'] = mdtype
        test = np.genfromtxt(TextIO(data),
                            missing_values={0: -9, 1: -99, 2: -999j}, usemask=True, **basekwargs)
        control = ma.array([(0, 0.0, 0j), (1, -999, 1j),
                            (-9, 2.2, -999j), (3, -99, 3j)],
                           mask=[(0, 0, 0), (0, 1, 0), (1, 0, 1), (0, 1, 0)],
                           dtype=mdtype)
        assert_equal(test, control)
        #
        test = np.genfromtxt(TextIO(data),
                            missing_values={0: -9, 'B': -99, 'C': -999j},
                            usemask=True,
                            **basekwargs)
        control = ma.array([(0, 0.0, 0j), (1, -999, 1j),
                            (-9, 2.2, -999j), (3, -99, 3j)],
                           mask=[(0, 0, 0), (0, 1, 0), (1, 0, 1), (0, 1, 0)],
                           dtype=mdtype)
        assert_equal(test, control)

    def test_user_filling_values(self):
        # Test with missing and filling values
        ctrl = np.array([(0, 3), (4, -999)], dtype=[('a', int), ('b', int)])
        data = "N/A, 2, 3\n4, ,???"
        kwargs = {"delimiter": ",",
                      "dtype": int,
                      "names": "a,b,c",
                      "missing_values": {0: "N/A", 'b': " ", 2: "???"},
                      "filling_values": {0: 0, 'b': 0, 2: -999}}
        test = np.genfromtxt(TextIO(data), **kwargs)
        ctrl = np.array([(0, 2, 3), (4, 0, -999)],
                        dtype=[(_, int) for _ in "abc"])
        assert_equal(test, ctrl)
        #
        test = np.genfromtxt(TextIO(data), usecols=(0, -1), **kwargs)
        ctrl = np.array([(0, 3), (4, -999)], dtype=[(_, int) for _ in "ac"])
        assert_equal(test, ctrl)

        data2 = "1,2,*,4\n5,*,7,8\n"
        test = np.genfromtxt(TextIO(data2), delimiter=',', dtype=int,
                             missing_values="*", filling_values=0)
        ctrl = np.array([[1, 2, 0, 4], [5, 0, 7, 8]])
        assert_equal(test, ctrl)
        test = np.genfromtxt(TextIO(data2), delimiter=',', dtype=int,
                             missing_values="*", filling_values=-1)
        ctrl = np.array([[1, 2, -1, 4], [5, -1, 7, 8]])
        assert_equal(test, ctrl)

    def test_withmissing_float(self):
        data = TextIO('A,B\n0,1.5\n2,-999.00')
        test = np.genfromtxt(data, dtype=None, delimiter=',',
                            missing_values='-999.0', names=True, usemask=True)
        control = ma.array([(0, 1.5), (2, -1.)],
                           mask=[(False, False), (False, True)],
                           dtype=[('A', int), ('B', float)])
        assert_equal(test, control)
        assert_equal(test.mask, control.mask)

    def test_with_masked_column_uniform(self):
        # Test masked column
        data = TextIO('1 2 3\n4 5 6\n')
        test = np.genfromtxt(data, dtype=None,
                             missing_values='2,5', usemask=True)
        control = ma.array([[1, 2, 3], [4, 5, 6]], mask=[[0, 1, 0], [0, 1, 0]])
        assert_equal(test, control)

    def test_with_masked_column_various(self):
        # Test masked column
        data = TextIO('True 2 3\nFalse 5 6\n')
        test = np.genfromtxt(data, dtype=None,
                             missing_values='2,5', usemask=True)
        control = ma.array([(1, 2, 3), (0, 5, 6)],
                           mask=[(0, 1, 0), (0, 1, 0)],
                           dtype=[('f0', bool), ('f1', bool), ('f2', int)])
        assert_equal(test, control)

    def test_invalid_raise(self):
        # Test invalid raise
        data = ["1, 1, 1, 1, 1"] * 50
        for i in range(5):
            data[10 * i] = "2, 2, 2, 2 2"
        data.insert(0, "a, b, c, d, e")
        mdata = TextIO("\n".join(data))

        kwargs = {"delimiter": ",", "dtype": None, "names": True}

        def f():
            return np.genfromtxt(mdata, invalid_raise=False, **kwargs)
        mtest = assert_warns(ConversionWarning, f)
        assert_equal(len(mtest), 45)
        assert_equal(mtest, np.ones(45, dtype=[(_, int) for _ in 'abcde']))
        #
        mdata.seek(0)
        assert_raises(ValueError, np.genfromtxt, mdata,
                      delimiter=",", names=True)

    def test_invalid_raise_with_usecols(self):
        # Test invalid_raise with usecols
        data = ["1, 1, 1, 1, 1"] * 50
        for i in range(5):
            data[10 * i] = "2, 2, 2, 2 2"
        data.insert(0, "a, b, c, d, e")
        mdata = TextIO("\n".join(data))

        kwargs = {"delimiter": ",", "dtype": None, "names": True,
                      "invalid_raise": False}

        def f():
            return np.genfromtxt(mdata, usecols=(0, 4), **kwargs)
        mtest = assert_warns(ConversionWarning, f)
        assert_equal(len(mtest), 45)
        assert_equal(mtest, np.ones(45, dtype=[(_, int) for _ in 'ae']))
        #
        mdata.seek(0)
        mtest = np.genfromtxt(mdata, usecols=(0, 1), **kwargs)
        assert_equal(len(mtest), 50)
        control = np.ones(50, dtype=[(_, int) for _ in 'ab'])
        control[[10 * _ for _ in range(5)]] = (2, 2)
        assert_equal(mtest, control)

    def test_inconsistent_dtype(self):
        # Test inconsistent dtype
        data = ["1, 1, 1, 1, -1.1"] * 50
        mdata = TextIO("\n".join(data))

        converters = {4: lambda x: f"({x.decode()})"}
        kwargs = {"delimiter": ",", "converters": converters,
                      "dtype": [(_, int) for _ in 'abcde'], "encoding": "bytes"}
        assert_raises(ValueError, np.genfromtxt, mdata, **kwargs)

    def test_default_field_format(self):
        # Test default format
        data = "0, 1, 2.3\n4, 5, 6.7"
        mtest = np.genfromtxt(TextIO(data),
                             delimiter=",", dtype=None, defaultfmt="f%02i")
        ctrl = np.array([(0, 1, 2.3), (4, 5, 6.7)],
                        dtype=[("f00", int), ("f01", int), ("f02", float)])
        assert_equal(mtest, ctrl)

    def test_single_dtype_wo_names(self):
        # Test single dtype w/o names
        data = "0, 1, 2.3\n4, 5, 6.7"
        mtest = np.genfromtxt(TextIO(data),
                             delimiter=",", dtype=float, defaultfmt="f%02i")
        ctrl = np.array([[0., 1., 2.3], [4., 5., 6.7]], dtype=float)
        assert_equal(mtest, ctrl)

    def test_single_dtype_w_explicit_names(self):
        # Test single dtype w explicit names
        data = "0, 1, 2.3\n4, 5, 6.7"
        mtest = np.genfromtxt(TextIO(data),
                             delimiter=",", dtype=float, names="a, b, c")
        ctrl = np.array([(0., 1., 2.3), (4., 5., 6.7)],
                        dtype=[(_, float) for _ in "abc"])
        assert_equal(mtest, ctrl)

    def test_single_dtype_w_implicit_names(self):
        # Test single dtype w implicit names
        data = "a, b, c\n0, 1, 2.3\n4, 5, 6.7"
        mtest = np.genfromtxt(TextIO(data),
                             delimiter=",", dtype=float, names=True)
        ctrl = np.array([(0., 1., 2.3), (4., 5., 6.7)],
                        dtype=[(_, float) for _ in "abc"])
        assert_equal(mtest, ctrl)

    def test_easy_structured_dtype(self):
        # Test easy structured dtype
        data = "0, 1, 2.3\n4, 5, 6.7"
        mtest = np.genfromtxt(TextIO(data), delimiter=",",
                             dtype=(int, float, float), defaultfmt="f_%02i")
        ctrl = np.array([(0, 1., 2.3), (4, 5., 6.7)],
                        dtype=[("f_00", int), ("f_01", float), ("f_02", float)])
        assert_equal(mtest, ctrl)

    def test_autostrip(self):
        # Test autostrip
        data = "01/01/2003  , 1.3,   abcde"
        kwargs = {"delimiter": ",", "dtype": None, "encoding": "bytes"}
        with warnings.catch_warnings(record=True) as w:
            warnings.filterwarnings('always', '', VisibleDeprecationWarning)
            mtest = np.genfromtxt(TextIO(data), **kwargs)
            assert_(w[0].category is VisibleDeprecationWarning)
        ctrl = np.array([('01/01/2003  ', 1.3, '   abcde')],
                        dtype=[('f0', '|S12'), ('f1', float), ('f2', '|S8')])
        assert_equal(mtest, ctrl)
        with warnings.catch_warnings(record=True) as w:
            warnings.filterwarnings('always', '', VisibleDeprecationWarning)
            mtest = np.genfromtxt(TextIO(data), autostrip=True, **kwargs)
            assert_(w[0].category is VisibleDeprecationWarning)
        ctrl = np.array([('01/01/2003', 1.3, 'abcde')],
                        dtype=[('f0', '|S10'), ('f1', float), ('f2', '|S5')])
        assert_equal(mtest, ctrl)

    def test_replace_space(self):
        # Test the 'replace_space' option
        txt = "A.A, B (B), C:C\n1, 2, 3.14"
        # Test default: replace ' ' by '_' and delete non-alphanum chars
        test = np.genfromtxt(TextIO(txt),
                             delimiter=",", names=True, dtype=None)
        ctrl_dtype = [("AA", int), ("B_B", int), ("CC", float)]
        ctrl = np.array((1, 2, 3.14), dtype=ctrl_dtype)
        assert_equal(test, ctrl)
        # Test: no replace, no delete
        test = np.genfromtxt(TextIO(txt),
                             delimiter=",", names=True, dtype=None,
                             replace_space='', deletechars='')
        ctrl_dtype = [("A.A", int), ("B (B)", int), ("C:C", float)]
        ctrl = np.array((1, 2, 3.14), dtype=ctrl_dtype)
        assert_equal(test, ctrl)
        # Test: no delete (spaces are replaced by _)
        test = np.genfromtxt(TextIO(txt),
                             delimiter=",", names=True, dtype=None,
                             deletechars='')
        ctrl_dtype = [("A.A", int), ("B_(B)", int), ("C:C", float)]
        ctrl = np.array((1, 2, 3.14), dtype=ctrl_dtype)
        assert_equal(test, ctrl)

    def test_replace_space_known_dtype(self):
        # Test the 'replace_space' (and related) options when dtype != None
        txt = "A.A, B (B), C:C\n1, 2, 3"
        # Test default: replace ' ' by '_' and delete non-alphanum chars
        test = np.genfromtxt(TextIO(txt),
                             delimiter=",", names=True, dtype=int)
        ctrl_dtype = [("AA", int), ("B_B", int), ("CC", int)]
        ctrl = np.array((1, 2, 3), dtype=ctrl_dtype)
        assert_equal(test, ctrl)
        # Test: no replace, no delete
        test = np.genfromtxt(TextIO(txt),
                             delimiter=",", names=True, dtype=int,
                             replace_space='', deletechars='')
        ctrl_dtype = [("A.A", int), ("B (B)", int), ("C:C", int)]
        ctrl = np.array((1, 2, 3), dtype=ctrl_dtype)
        assert_equal(test, ctrl)
        # Test: no delete (spaces are replaced by _)
        test = np.genfromtxt(TextIO(txt),
                             delimiter=",", names=True, dtype=int,
                             deletechars='')
        ctrl_dtype = [("A.A", int), ("B_(B)", int), ("C:C", int)]
        ctrl = np.array((1, 2, 3), dtype=ctrl_dtype)
        assert_equal(test, ctrl)

    def test_incomplete_names(self):
        # Test w/ incomplete names
        data = "A,,C\n0,1,2\n3,4,5"
        kwargs = {"delimiter": ",", "names": True}
        # w/ dtype=None
        ctrl = np.array([(0, 1, 2), (3, 4, 5)],
                        dtype=[(_, int) for _ in ('A', 'f0', 'C')])
        test = np.genfromtxt(TextIO(data), dtype=None, **kwargs)
        assert_equal(test, ctrl)
        # w/ default dtype
        ctrl = np.array([(0, 1, 2), (3, 4, 5)],
                        dtype=[(_, float) for _ in ('A', 'f0', 'C')])
        test = np.genfromtxt(TextIO(data), **kwargs)

    def test_names_auto_completion(self):
        # Make sure that names are properly completed
        data = "1 2 3\n 4 5 6"
        test = np.genfromtxt(TextIO(data),
                             dtype=(int, float, int), names="a")
        ctrl = np.array([(1, 2, 3), (4, 5, 6)],
                        dtype=[('a', int), ('f0', float), ('f1', int)])
        assert_equal(test, ctrl)

    def test_names_with_usecols_bug1636(self):
        # Make sure we pick up the right names w/ usecols
        data = "A,B,C,D,E\n0,1,2,3,4\n0,1,2,3,4\n0,1,2,3,4"
        ctrl_names = ("A", "C", "E")
        test = np.genfromtxt(TextIO(data),
                             dtype=(int, int, int), delimiter=",",
                             usecols=(0, 2, 4), names=True)
        assert_equal(test.dtype.names, ctrl_names)
        #
        test = np.genfromtxt(TextIO(data),
                             dtype=(int, int, int), delimiter=",",
                             usecols=("A", "C", "E"), names=True)
        assert_equal(test.dtype.names, ctrl_names)
        #
        test = np.genfromtxt(TextIO(data),
                             dtype=int, delimiter=",",
                             usecols=("A", "C", "E"), names=True)
        assert_equal(test.dtype.names, ctrl_names)

    def test_fixed_width_names(self):
        # Test fix-width w/ names
        data = "    A    B   C\n    0    1 2.3\n   45   67   9."
        kwargs = {"delimiter": (5, 5, 4), "names": True, "dtype": None}
        ctrl = np.array([(0, 1, 2.3), (45, 67, 9.)],
                        dtype=[('A', int), ('B', int), ('C', float)])
        test = np.genfromtxt(TextIO(data), **kwargs)
        assert_equal(test, ctrl)
        #
        kwargs = {"delimiter": 5, "names": True, "dtype": None}
        ctrl = np.array([(0, 1, 2.3), (45, 67, 9.)],
                        dtype=[('A', int), ('B', int), ('C', float)])
        test = np.genfromtxt(TextIO(data), **kwargs)
        assert_equal(test, ctrl)

    def test_filling_values(self):
        # Test missing values
        data = b"1, 2, 3\n1, , 5\n0, 6, \n"
        kwargs = {"delimiter": ",", "dtype": None, "filling_values": -999}
        ctrl = np.array([[1, 2, 3], [1, -999, 5], [0, 6, -999]], dtype=int)
        test = np.genfromtxt(TextIO(data), **kwargs)
        assert_equal(test, ctrl)

    def test_comments_is_none(self):
        # Github issue 329 (None was previously being converted to 'None').
        with warnings.catch_warnings(record=True) as w:
            warnings.filterwarnings('always', '', VisibleDeprecationWarning)
            test = np.genfromtxt(TextIO("test1,testNonetherestofthedata"),
                                 dtype=None, comments=None, delimiter=',',
                                 encoding="bytes")
            assert_(w[0].category is VisibleDeprecationWarning)
        assert_equal(test[1], b'testNonetherestofthedata')
        with warnings.catch_warnings(record=True) as w:
            warnings.filterwarnings('always', '', VisibleDeprecationWarning)
            test = np.genfromtxt(TextIO("test1, testNonetherestofthedata"),
                                 dtype=None, comments=None, delimiter=',',
                                 encoding="bytes")
            assert_(w[0].category is VisibleDeprecationWarning)
        assert_equal(test[1], b' testNonetherestofthedata')

    def test_latin1(self):
        latin1 = b'\xf6\xfc\xf6'
        norm = b"norm1,norm2,norm3\n"
        enc = b"test1,testNonethe" + latin1 + b",test3\n"
        s = norm + enc + norm
        with warnings.catch_warnings(record=True) as w:
            warnings.filterwarnings('always', '', VisibleDeprecationWarning)
            test = np.genfromtxt(TextIO(s),
                                 dtype=None, comments=None, delimiter=',',
                                 encoding="bytes")
            assert_(w[0].category is VisibleDeprecationWarning)
        assert_equal(test[1, 0], b"test1")
        assert_equal(test[1, 1], b"testNonethe" + latin1)
        assert_equal(test[1, 2], b"test3")
        test = np.genfromtxt(TextIO(s),
                             dtype=None, comments=None, delimiter=',',
                             encoding='latin1')
        assert_equal(test[1, 0], "test1")
        assert_equal(test[1, 1], "testNonethe" + latin1.decode('latin1'))
        assert_equal(test[1, 2], "test3")

        with warnings.catch_warnings(record=True) as w:
            warnings.filterwarnings('always', '', VisibleDeprecationWarning)
            test = np.genfromtxt(TextIO(b"0,testNonethe" + latin1),
                                 dtype=None, comments=None, delimiter=',',
                                 encoding="bytes")
            assert_(w[0].category is VisibleDeprecationWarning)
        assert_equal(test['f0'], 0)
        assert_equal(test['f1'], b"testNonethe" + latin1)

    def test_binary_decode_autodtype(self):
        utf16 = b'\xff\xfeh\x04 \x00i\x04 \x00j\x04'
        v = self.loadfunc(BytesIO(utf16), dtype=None, encoding='UTF-16')
        assert_array_equal(v, np.array(utf16.decode('UTF-16').split()))

    def test_utf8_byte_encoding(self):
        utf8 = b"\xcf\x96"
        norm = b"norm1,norm2,norm3\n"
        enc = b"test1,testNonethe" + utf8 + b",test3\n"
        s = norm + enc + norm
        with warnings.catch_warnings(record=True) as w:
            warnings.filterwarnings('always', '', VisibleDeprecationWarning)
            test = np.genfromtxt(TextIO(s),
                                 dtype=None, comments=None, delimiter=',',
                                 encoding="bytes")
            assert_(w[0].category is VisibleDeprecationWarning)
        ctl = np.array([
                 [b'norm1', b'norm2', b'norm3'],
                 [b'test1', b'testNonethe' + utf8, b'test3'],
                 [b'norm1', b'norm2', b'norm3']])
        assert_array_equal(test, ctl)

    def test_utf8_file(self):
        utf8 = b"\xcf\x96"
        with temppath() as path:
            with open(path, "wb") as f:
                f.write((b"test1,testNonethe" + utf8 + b",test3\n") * 2)
            test = np.genfromtxt(path, dtype=None, comments=None,
                                 delimiter=',', encoding="UTF-8")
            ctl = np.array([
                     ["test1", "testNonethe" + utf8.decode("UTF-8"), "test3"],
                     ["test1", "testNonethe" + utf8.decode("UTF-8"), "test3"]],
                     dtype=np.str_)
            assert_array_equal(test, ctl)

            # test a mixed dtype
            with open(path, "wb") as f:
                f.write(b"0,testNonethe" + utf8)
            test = np.genfromtxt(path, dtype=None, comments=None,
                                 delimiter=',', encoding="UTF-8")
            assert_equal(test['f0'], 0)
            assert_equal(test['f1'], "testNonethe" + utf8.decode("UTF-8"))

    def test_utf8_file_nodtype_unicode(self):
        # bytes encoding with non-latin1 -> unicode upcast
        utf8 = '\u03d6'
        latin1 = '\xf6\xfc\xf6'

        # skip test if cannot encode utf8 test string with preferred
        # encoding. The preferred encoding is assumed to be the default
        # encoding of open. Will need to change this for PyTest, maybe
        # using pytest.mark.xfail(raises=***).
        try:
            encoding = locale.getpreferredencoding()
            utf8.encode(encoding)
        except (UnicodeError, ImportError):
            pytest.skip('Skipping test_utf8_file_nodtype_unicode, '
                        'unable to encode utf8 in preferred encoding')

        with temppath() as path:
            with open(path, "wt") as f:
                f.write("norm1,norm2,norm3\n")
                f.write("norm1," + latin1 + ",norm3\n")
                f.write("test1,testNonethe" + utf8 + ",test3\n")
            with warnings.catch_warnings(record=True) as w:
                warnings.filterwarnings('always', '',
                                        VisibleDeprecationWarning)
                test = np.genfromtxt(path, dtype=None, comments=None,
                                     delimiter=',', encoding="bytes")
                # Check for warning when encoding not specified.
                assert_(w[0].category is VisibleDeprecationWarning)
            ctl = np.array([
                     ["norm1", "norm2", "norm3"],
                     ["norm1", latin1, "norm3"],
                     ["test1", "testNonethe" + utf8, "test3"]],
                     dtype=np.str_)
            assert_array_equal(test, ctl)

    @pytest.mark.filterwarnings("ignore:.*recfromtxt.*:DeprecationWarning")
    def test_recfromtxt(self):
        #
        data = TextIO('A,B\n0,1\n2,3')
        kwargs = {"delimiter": ",", "missing_values": "N/A", "names": True}
        test = recfromtxt(data, **kwargs)
        control = np.array([(0, 1), (2, 3)],
                           dtype=[('A', int), ('B', int)])
        assert_(isinstance(test, np.recarray))
        assert_equal(test, control)
        #
        data = TextIO('A,B\n0,1\n2,N/A')
        test = recfromtxt(data, dtype=None, usemask=True, **kwargs)
        control = ma.array([(0, 1), (2, -1)],
                           mask=[(False, False), (False, True)],
                           dtype=[('A', int), ('B', int)])
        assert_equal(test, control)
        assert_equal(test.mask, control.mask)
        assert_equal(test.A, [0, 2])

    @pytest.mark.filterwarnings("ignore:.*recfromcsv.*:DeprecationWarning")
    def test_recfromcsv(self):
        #
        data = TextIO('A,B\n0,1\n2,3')
        kwargs = {"missing_values": "N/A", "names": True, "case_sensitive": True,
                      "encoding": "bytes"}
        test = recfromcsv(data, dtype=None, **kwargs)
        control = np.array([(0, 1), (2, 3)],
                           dtype=[('A', int), ('B', int)])
        assert_(isinstance(test, np.recarray))
        assert_equal(test, control)
        #
        data = TextIO('A,B\n0,1\n2,N/A')
        test = recfromcsv(data, dtype=None, usemask=True, **kwargs)
        control = ma.array([(0, 1), (2, -1)],
                           mask=[(False, False), (False, True)],
                           dtype=[('A', int), ('B', int)])
        assert_equal(test, control)
        assert_equal(test.mask, control.mask)
        assert_equal(test.A, [0, 2])
        #
        data = TextIO('A,B\n0,1\n2,3')
        test = recfromcsv(data, missing_values='N/A',)
        control = np.array([(0, 1), (2, 3)],
                           dtype=[('a', int), ('b', int)])
        assert_(isinstance(test, np.recarray))
        assert_equal(test, control)
        #
        data = TextIO('A,B\n0,1\n2,3')
        dtype = [('a', int), ('b', float)]
        test = recfromcsv(data, missing_values='N/A', dtype=dtype)
        control = np.array([(0, 1), (2, 3)],
                           dtype=dtype)
        assert_(isinstance(test, np.recarray))
        assert_equal(test, control)

        # gh-10394
        data = TextIO('color\n"red"\n"blue"')
        test = recfromcsv(data, converters={0: lambda x: x.strip('\"')})
        control = np.array([('red',), ('blue',)], dtype=[('color', (str, 4))])
        assert_equal(test.dtype, control.dtype)
        assert_equal(test, control)

    def test_max_rows(self):
        # Test the `max_rows` keyword argument.
        data = '1 2\n3 4\n5 6\n7 8\n9 10\n'
        txt = TextIO(data)
        a1 = np.genfromtxt(txt, max_rows=3)
        a2 = np.genfromtxt(txt)
        assert_equal(a1, [[1, 2], [3, 4], [5, 6]])
        assert_equal(a2, [[7, 8], [9, 10]])

        # max_rows must be at least 1.
        assert_raises(ValueError, np.genfromtxt, TextIO(data), max_rows=0)

        # An input with several invalid rows.
        data = '1 1\n2 2\n0 \n3 3\n4 4\n5  \n6  \n7  \n'

        test = np.genfromtxt(TextIO(data), max_rows=2)
        control = np.array([[1., 1.], [2., 2.]])
        assert_equal(test, control)

        # Test keywords conflict
        assert_raises(ValueError, np.genfromtxt, TextIO(data), skip_footer=1,
                      max_rows=4)

        # Test with invalid value
        assert_raises(ValueError, np.genfromtxt, TextIO(data), max_rows=4)

        # Test with invalid not raise
        with suppress_warnings() as sup:
            sup.filter(ConversionWarning)

            test = np.genfromtxt(TextIO(data), max_rows=4, invalid_raise=False)
            control = np.array([[1., 1.], [2., 2.], [3., 3.], [4., 4.]])
            assert_equal(test, control)

            test = np.genfromtxt(TextIO(data), max_rows=5, invalid_raise=False)
            control = np.array([[1., 1.], [2., 2.], [3., 3.], [4., 4.]])
            assert_equal(test, control)

        # Structured array with field names.
        data = 'a b\n#c d\n1 1\n2 2\n#0 \n3 3\n4 4\n5  5\n'

        # Test with header, names and comments
        txt = TextIO(data)
        test = np.genfromtxt(txt, skip_header=1, max_rows=3, names=True)
        control = np.array([(1.0, 1.0), (2.0, 2.0), (3.0, 3.0)],
                      dtype=[('c', '<f8'), ('d', '<f8')])
        assert_equal(test, control)
        # To continue reading the same "file", don't use skip_header or
        # names, and use the previously determined dtype.
        test = np.genfromtxt(txt, max_rows=None, dtype=test.dtype)
        control = np.array([(4.0, 4.0), (5.0, 5.0)],
                      dtype=[('c', '<f8'), ('d', '<f8')])
        assert_equal(test, control)

    def test_gft_using_filename(self):
        # Test that we can load data from a filename as well as a file
        # object
        tgt = np.arange(6).reshape((2, 3))
        linesep = ('\n', '\r\n', '\r')

        for sep in linesep:
            data = '0 1 2' + sep + '3 4 5'
            with temppath() as name:
                with open(name, 'w') as f:
                    f.write(data)
                res = np.genfromtxt(name)
            assert_array_equal(res, tgt)

    def test_gft_from_gzip(self):
        # Test that we can load data from a gzipped file
        wanted = np.arange(6).reshape((2, 3))
        linesep = ('\n', '\r\n', '\r')

        for sep in linesep:
            data = '0 1 2' + sep + '3 4 5'
            s = BytesIO()
            with gzip.GzipFile(fileobj=s, mode='w') as g:
                g.write(asbytes(data))

            with temppath(suffix='.gz2') as name:
                with open(name, 'w') as f:
                    f.write(data)
                assert_array_equal(np.genfromtxt(name), wanted)

    def test_gft_using_generator(self):
        # gft doesn't work with unicode.
        def count():
            for i in range(10):
                yield asbytes("%d" % i)

        res = np.genfromtxt(count())
        assert_array_equal(res, np.arange(10))

    def test_auto_dtype_largeint(self):
        # Regression test for numpy/numpy#5635 whereby large integers could
        # cause OverflowErrors.

        # Test the automatic definition of the output dtype
        #
        # 2**66 = 73786976294838206464 => should convert to float
        # 2**34 = 17179869184 => should convert to int64
        # 2**10 = 1024 => should convert to int (int32 on 32-bit systems,
        #                 int64 on 64-bit systems)

        data = TextIO('73786976294838206464 17179869184 1024')

        test = np.genfromtxt(data, dtype=None)

        assert_equal(test.dtype.names, ['f0', 'f1', 'f2'])

        assert_(test.dtype['f0'] == float)
        assert_(test.dtype['f1'] == np.int64)
        assert_(test.dtype['f2'] == np.int_)

        assert_allclose(test['f0'], 73786976294838206464.)
        assert_equal(test['f1'], 17179869184)
        assert_equal(test['f2'], 1024)

    def test_unpack_float_data(self):
        txt = TextIO("1,2,3\n4,5,6\n7,8,9\n0.0,1.0,2.0")
        a, b, c = np.loadtxt(txt, delimiter=",", unpack=True)
        assert_array_equal(a, np.array([1.0, 4.0, 7.0, 0.0]))
        assert_array_equal(b, np.array([2.0, 5.0, 8.0, 1.0]))
        assert_array_equal(c, np.array([3.0, 6.0, 9.0, 2.0]))

    def test_unpack_structured(self):
        # Regression test for gh-4341
        # Unpacking should work on structured arrays
        txt = TextIO("M 21 72\nF 35 58")
        dt = {'names': ('a', 'b', 'c'), 'formats': ('S1', 'i4', 'f4')}
        a, b, c = np.genfromtxt(txt, dtype=dt, unpack=True)
        assert_equal(a.dtype, np.dtype('S1'))
        assert_equal(b.dtype, np.dtype('i4'))
        assert_equal(c.dtype, np.dtype('f4'))
        assert_array_equal(a, np.array([b'M', b'F']))
        assert_array_equal(b, np.array([21, 35]))
        assert_array_equal(c, np.array([72.,  58.]))

    def test_unpack_auto_dtype(self):
        # Regression test for gh-4341
        # Unpacking should work when dtype=None
        txt = TextIO("M 21 72.\nF 35 58.")
        expected = (np.array(["M", "F"]), np.array([21, 35]), np.array([72., 58.]))
        test = np.genfromtxt(txt, dtype=None, unpack=True, encoding="utf-8")
        for arr, result in zip(expected, test):
            assert_array_equal(arr, result)
            assert_equal(arr.dtype, result.dtype)

    def test_unpack_single_name(self):
        # Regression test for gh-4341
        # Unpacking should work when structured dtype has only one field
        txt = TextIO("21\n35")
        dt = {'names': ('a',), 'formats': ('i4',)}
        expected = np.array([21, 35], dtype=np.int32)
        test = np.genfromtxt(txt, dtype=dt, unpack=True)
        assert_array_equal(expected, test)
        assert_equal(expected.dtype, test.dtype)

    def test_squeeze_scalar(self):
        # Regression test for gh-4341
        # Unpacking a scalar should give zero-dim output,
        # even if dtype is structured
        txt = TextIO("1")
        dt = {'names': ('a',), 'formats': ('i4',)}
        expected = np.array((1,), dtype=np.int32)
        test = np.genfromtxt(txt, dtype=dt, unpack=True)
        assert_array_equal(expected, test)
        assert_equal((), test.shape)
        assert_equal(expected.dtype, test.dtype)

    @pytest.mark.parametrize("ndim", [0, 1, 2])
    def test_ndmin_keyword(self, ndim: int):
        # lets have the same behaviour of ndmin as loadtxt
        # as they should be the same for non-missing values
        txt = "42"

        a = np.loadtxt(StringIO(txt), ndmin=ndim)
        b = np.genfromtxt(StringIO(txt), ndmin=ndim)

        assert_array_equal(a, b)


class TestPathUsage:
    # Test that pathlib.Path can be used
    def test_loadtxt(self):
        with temppath(suffix='.txt') as path:
            path = Path(path)
            a = np.array([[1.1, 2], [3, 4]])
            np.savetxt(path, a)
            x = np.loadtxt(path)
            assert_array_equal(x, a)

    def test_save_load(self):
        # Test that pathlib.Path instances can be used with save.
        with temppath(suffix='.npy') as path:
            path = Path(path)
            a = np.array([[1, 2], [3, 4]], int)
            np.save(path, a)
            data = np.load(path)
            assert_array_equal(data, a)

    def test_save_load_memmap(self):
        # Test that pathlib.Path instances can be loaded mem-mapped.
        with temppath(suffix='.npy') as path:
            path = Path(path)
            a = np.array([[1, 2], [3, 4]], int)
            np.save(path, a)
            data = np.load(path, mmap_mode='r')
            assert_array_equal(data, a)
            # close the mem-mapped file
            del data
            if IS_PYPY:
                break_cycles()
                break_cycles()

    @pytest.mark.xfail(IS_WASM, reason="memmap doesn't work correctly")
    @pytest.mark.parametrize("filename_type", [Path, str])
    def test_save_load_memmap_readwrite(self, filename_type):
        with temppath(suffix='.npy') as path:
            path = filename_type(path)
            a = np.array([[1, 2], [3, 4]], int)
            np.save(path, a)
            b = np.load(path, mmap_mode='r+')
            a[0][0] = 5
            b[0][0] = 5
            del b  # closes the file
            if IS_PYPY:
                break_cycles()
                break_cycles()
            data = np.load(path)
            assert_array_equal(data, a)

    @pytest.mark.parametrize("filename_type", [Path, str])
    def test_savez_load(self, filename_type):
        with temppath(suffix='.npz') as path:
            path = filename_type(path)
            np.savez(path, lab='place holder')
            with np.load(path) as data:
                assert_array_equal(data['lab'], 'place holder')

    @pytest.mark.parametrize("filename_type", [Path, str])
    def test_savez_compressed_load(self, filename_type):
        with temppath(suffix='.npz') as path:
            path = filename_type(path)
            np.savez_compressed(path, lab='place holder')
            data = np.load(path)
            assert_array_equal(data['lab'], 'place holder')
            data.close()

    @pytest.mark.parametrize("filename_type", [Path, str])
    def test_genfromtxt(self, filename_type):
        with temppath(suffix='.txt') as path:
            path = filename_type(path)
            a = np.array([(1, 2), (3, 4)])
            np.savetxt(path, a)
            data = np.genfromtxt(path)
            assert_array_equal(a, data)

    @pytest.mark.parametrize("filename_type", [Path, str])
    @pytest.mark.filterwarnings("ignore:.*recfromtxt.*:DeprecationWarning")
    def test_recfromtxt(self, filename_type):
        with temppath(suffix='.txt') as path:
            path = filename_type(path)
            with open(path, 'w') as f:
                f.write('A,B\n0,1\n2,3')

            kwargs = {"delimiter": ",", "missing_values": "N/A", "names": True}
            test = recfromtxt(path, **kwargs)
            control = np.array([(0, 1), (2, 3)],
                               dtype=[('A', int), ('B', int)])
            assert_(isinstance(test, np.recarray))
            assert_equal(test, control)

    @pytest.mark.parametrize("filename_type", [Path, str])
    @pytest.mark.filterwarnings("ignore:.*recfromcsv.*:DeprecationWarning")
    def test_recfromcsv(self, filename_type):
        with temppath(suffix='.txt') as path:
            path = filename_type(path)
            with open(path, 'w') as f:
                f.write('A,B\n0,1\n2,3')

            kwargs = {
                "missing_values": "N/A", "names": True, "case_sensitive": True
            }
            test = recfromcsv(path, dtype=None, **kwargs)
            control = np.array([(0, 1), (2, 3)],
                               dtype=[('A', int), ('B', int)])
            assert_(isinstance(test, np.recarray))
            assert_equal(test, control)


def test_gzip_load():
    a = np.random.random((5, 5))

    s = BytesIO()
    f = gzip.GzipFile(fileobj=s, mode="w")

    np.save(f, a)
    f.close()
    s.seek(0)

    f = gzip.GzipFile(fileobj=s, mode="r")
    assert_array_equal(np.load(f), a)


# These next two classes encode the minimal API needed to save()/load() arrays.
# The `test_ducktyping` ensures they work correctly
class JustWriter:
    def __init__(self, base):
        self.base = base

    def write(self, s):
        return self.base.write(s)

    def flush(self):
        return self.base.flush()

class JustReader:
    def __init__(self, base):
        self.base = base

    def read(self, n):
        return self.base.read(n)

    def seek(self, off, whence=0):
        return self.base.seek(off, whence)


def test_ducktyping():
    a = np.random.random((5, 5))

    s = BytesIO()
    f = JustWriter(s)

    np.save(f, a)
    f.flush()
    s.seek(0)

    f = JustReader(s)
    assert_array_equal(np.load(f), a)


def test_gzip_loadtxt():
    # Thanks to another windows brokenness, we can't use
    # NamedTemporaryFile: a file created from this function cannot be
    # reopened by another open call. So we first put the gzipped string
    # of the test reference array, write it to a securely opened file,
    # which is then read from by the loadtxt function
    s = BytesIO()
    g = gzip.GzipFile(fileobj=s, mode='w')
    g.write(b'1 2 3\n')
    g.close()

    s.seek(0)
    with temppath(suffix='.gz') as name:
        with open(name, 'wb') as f:
            f.write(s.read())
        res = np.loadtxt(name)
    s.close()

    assert_array_equal(res, [1, 2, 3])


def test_gzip_loadtxt_from_string():
    s = BytesIO()
    f = gzip.GzipFile(fileobj=s, mode="w")
    f.write(b'1 2 3\n')
    f.close()
    s.seek(0)

    f = gzip.GzipFile(fileobj=s, mode="r")
    assert_array_equal(np.loadtxt(f), [1, 2, 3])


def test_npzfile_dict():
    s = BytesIO()
    x = np.zeros((3, 3))
    y = np.zeros((3, 3))

    np.savez(s, x=x, y=y)
    s.seek(0)

    z = np.load(s)

    assert_('x' in z)
    assert_('y' in z)
    assert_('x' in z.keys())
    assert_('y' in z.keys())

    for f, a in z.items():
        assert_(f in ['x', 'y'])
        assert_equal(a.shape, (3, 3))

    for a in z.values():
        assert_equal(a.shape, (3, 3))

    assert_(len(z.items()) == 2)

    for f in z:
        assert_(f in ['x', 'y'])

    assert_('x' in z.keys())
    assert (z.get('x') == z['x']).all()


@pytest.mark.skipif(not HAS_REFCOUNT, reason="Python lacks refcounts")
def test_load_refcount():
    # Check that objects returned by np.load are directly freed based on
    # their refcount, rather than needing the gc to collect them.

    f = BytesIO()
    np.savez(f, [1, 2, 3])
    f.seek(0)

    with assert_no_gc_cycles():
        np.load(f)

    f.seek(0)
    dt = [("a", 'u1', 2), ("b", 'u1', 2)]
    with assert_no_gc_cycles():
        x = np.loadtxt(TextIO("0 1 2 3"), dtype=dt)
        assert_equal(x, np.array([((0, 1), (2, 3))], dtype=dt))


def test_load_multiple_arrays_until_eof():
    f = BytesIO()
    np.save(f, 1)
    np.save(f, 2)
    f.seek(0)
    out1 = np.load(f)
    assert out1 == 1
    out2 = np.load(f)
    assert out2 == 2
    with pytest.raises(EOFError):
        np.load(f)


def test_savez_nopickle():
    obj_array = np.array([1, 'hello'], dtype=object)
    with temppath(suffix='.npz') as tmp:
        np.savez(tmp, obj_array)

    with temppath(suffix='.npz') as tmp:
        with pytest.raises(ValueError, match="Object arrays cannot be saved when.*"):
            np.savez(tmp, obj_array, allow_pickle=False)

    with temppath(suffix='.npz') as tmp:
        np.savez_compressed(tmp, obj_array)

    with temppath(suffix='.npz') as tmp:
        with pytest.raises(ValueError, match="Object arrays cannot be saved when.*"):
            np.savez_compressed(tmp, obj_array, allow_pickle=False)

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\numpy\lib\tests\test_io.py ===
import gc
import gzip
import locale
import os
import re
import sys
import threading
import time
import warnings
from ctypes import c_bool
from datetime import datetime
from io import BytesIO, StringIO
from multiprocessing import Value, get_context
from pathlib import Path
from tempfile import NamedTemporaryFile

import pytest

import numpy as np
import numpy.ma as ma
from numpy._utils import asbytes
from numpy.exceptions import VisibleDeprecationWarning
from numpy.lib import _npyio_impl
from numpy.lib._iotools import ConversionWarning, ConverterError
from numpy.lib._npyio_impl import recfromcsv, recfromtxt
from numpy.ma.testutils import assert_equal
from numpy.testing import (
    HAS_REFCOUNT,
    IS_PYPY,
    IS_WASM,
    assert_,
    assert_allclose,
    assert_array_equal,
    assert_no_gc_cycles,
    assert_no_warnings,
    assert_raises,
    assert_raises_regex,
    assert_warns,
    break_cycles,
    suppress_warnings,
    tempdir,
    temppath,
)
from numpy.testing._private.utils import requires_memory


class TextIO(BytesIO):
    """Helper IO class.

    Writes encode strings to bytes if needed, reads return bytes.
    This makes it easier to emulate files opened in binary mode
    without needing to explicitly convert strings to bytes in
    setting up the test data.

    """
    def __init__(self, s=""):
        BytesIO.__init__(self, asbytes(s))

    def write(self, s):
        BytesIO.write(self, asbytes(s))

    def writelines(self, lines):
        BytesIO.writelines(self, [asbytes(s) for s in lines])


IS_64BIT = sys.maxsize > 2**32
try:
    import bz2
    HAS_BZ2 = True
except ImportError:
    HAS_BZ2 = False
try:
    import lzma
    HAS_LZMA = True
except ImportError:
    HAS_LZMA = False


def strptime(s, fmt=None):
    """
    This function is available in the datetime module only from Python >=
    2.5.

    """
    if isinstance(s, bytes):
        s = s.decode("latin1")
    return datetime(*time.strptime(s, fmt)[:3])


class RoundtripTest:
    def roundtrip(self, save_func, *args, **kwargs):
        """
        save_func : callable
            Function used to save arrays to file.
        file_on_disk : bool
            If true, store the file on disk, instead of in a
            string buffer.
        save_kwds : dict
            Parameters passed to `save_func`.
        load_kwds : dict
            Parameters passed to `numpy.load`.
        args : tuple of arrays
            Arrays stored to file.

        """
        save_kwds = kwargs.get('save_kwds', {})
        load_kwds = kwargs.get('load_kwds', {"allow_pickle": True})
        file_on_disk = kwargs.get('file_on_disk', False)

        if file_on_disk:
            target_file = NamedTemporaryFile(delete=False)
            load_file = target_file.name
        else:
            target_file = BytesIO()
            load_file = target_file

        try:
            arr = args

            save_func(target_file, *arr, **save_kwds)
            target_file.flush()
            target_file.seek(0)

            if sys.platform == 'win32' and not isinstance(target_file, BytesIO):
                target_file.close()

            arr_reloaded = np.load(load_file, **load_kwds)

            self.arr = arr
            self.arr_reloaded = arr_reloaded
        finally:
            if not isinstance(target_file, BytesIO):
                target_file.close()
                # holds an open file descriptor so it can't be deleted on win
                if 'arr_reloaded' in locals():
                    if not isinstance(arr_reloaded, np.lib.npyio.NpzFile):
                        os.remove(target_file.name)

    def check_roundtrips(self, a):
        self.roundtrip(a)
        self.roundtrip(a, file_on_disk=True)
        self.roundtrip(np.asfortranarray(a))
        self.roundtrip(np.asfortranarray(a), file_on_disk=True)
        if a.shape[0] > 1:
            # neither C nor Fortran contiguous for 2D arrays or more
            self.roundtrip(np.asfortranarray(a)[1:])
            self.roundtrip(np.asfortranarray(a)[1:], file_on_disk=True)

    def test_array(self):
        a = np.array([], float)
        self.check_roundtrips(a)

        a = np.array([[1, 2], [3, 4]], float)
        self.check_roundtrips(a)

        a = np.array([[1, 2], [3, 4]], int)
        self.check_roundtrips(a)

        a = np.array([[1 + 5j, 2 + 6j], [3 + 7j, 4 + 8j]], dtype=np.csingle)
        self.check_roundtrips(a)

        a = np.array([[1 + 5j, 2 + 6j], [3 + 7j, 4 + 8j]], dtype=np.cdouble)
        self.check_roundtrips(a)

    def test_array_object(self):
        a = np.array([], object)
        self.check_roundtrips(a)

        a = np.array([[1, 2], [3, 4]], object)
        self.check_roundtrips(a)

    def test_1D(self):
        a = np.array([1, 2, 3, 4], int)
        self.roundtrip(a)

    @pytest.mark.skipif(sys.platform == 'win32', reason="Fails on Win32")
    def test_mmap(self):
        a = np.array([[1, 2.5], [4, 7.3]])
        self.roundtrip(a, file_on_disk=True, load_kwds={'mmap_mode': 'r'})

        a = np.asfortranarray([[1, 2.5], [4, 7.3]])
        self.roundtrip(a, file_on_disk=True, load_kwds={'mmap_mode': 'r'})

    def test_record(self):
        a = np.array([(1, 2), (3, 4)], dtype=[('x', 'i4'), ('y', 'i4')])
        self.check_roundtrips(a)

    @pytest.mark.slow
    def test_format_2_0(self):
        dt = [(("%d" % i) * 100, float) for i in range(500)]
        a = np.ones(1000, dtype=dt)
        with warnings.catch_warnings(record=True):
            warnings.filterwarnings('always', '', UserWarning)
            self.check_roundtrips(a)


class TestSaveLoad(RoundtripTest):
    def roundtrip(self, *args, **kwargs):
        RoundtripTest.roundtrip(self, np.save, *args, **kwargs)
        assert_equal(self.arr[0], self.arr_reloaded)
        assert_equal(self.arr[0].dtype, self.arr_reloaded.dtype)
        assert_equal(self.arr[0].flags.fnc, self.arr_reloaded.flags.fnc)


class TestSavezLoad(RoundtripTest):
    def roundtrip(self, *args, **kwargs):
        RoundtripTest.roundtrip(self, np.savez, *args, **kwargs)
        try:
            for n, arr in enumerate(self.arr):
                reloaded = self.arr_reloaded['arr_%d' % n]
                assert_equal(arr, reloaded)
                assert_equal(arr.dtype, reloaded.dtype)
                assert_equal(arr.flags.fnc, reloaded.flags.fnc)
        finally:
            # delete tempfile, must be done here on windows
            if self.arr_reloaded.fid:
                self.arr_reloaded.fid.close()
                os.remove(self.arr_reloaded.fid.name)

    @pytest.mark.skipif(IS_PYPY, reason="Hangs on PyPy")
    @pytest.mark.skipif(not IS_64BIT, reason="Needs 64bit platform")
    @pytest.mark.slow
    def test_big_arrays(self):
        L = (1 << 31) + 100000
        a = np.empty(L, dtype=np.uint8)
        with temppath(prefix="numpy_test_big_arrays_", suffix=".npz") as tmp:
            np.savez(tmp, a=a)
            del a
            npfile = np.load(tmp)
            a = npfile['a']  # Should succeed
            npfile.close()

    def test_multiple_arrays(self):
        a = np.array([[1, 2], [3, 4]], float)
        b = np.array([[1 + 2j, 2 + 7j], [3 - 6j, 4 + 12j]], complex)
        self.roundtrip(a, b)

    def test_named_arrays(self):
        a = np.array([[1, 2], [3, 4]], float)
        b = np.array([[1 + 2j, 2 + 7j], [3 - 6j, 4 + 12j]], complex)
        c = BytesIO()
        np.savez(c, file_a=a, file_b=b)
        c.seek(0)
        l = np.load(c)
        assert_equal(a, l['file_a'])
        assert_equal(b, l['file_b'])

    def test_tuple_getitem_raises(self):
        # gh-23748
        a = np.array([1, 2, 3])
        f = BytesIO()
        np.savez(f, a=a)
        f.seek(0)
        l = np.load(f)
        with pytest.raises(KeyError, match="(1, 2)"):
            l[1, 2]

    def test_BagObj(self):
        a = np.array([[1, 2], [3, 4]], float)
        b = np.array([[1 + 2j, 2 + 7j], [3 - 6j, 4 + 12j]], complex)
        c = BytesIO()
        np.savez(c, file_a=a, file_b=b)
        c.seek(0)
        l = np.load(c)
        assert_equal(sorted(dir(l.f)), ['file_a', 'file_b'])
        assert_equal(a, l.f.file_a)
        assert_equal(b, l.f.file_b)

    @pytest.mark.skipif(IS_WASM, reason="Cannot start thread")
    def test_savez_filename_clashes(self):
        # Test that issue #852 is fixed
        # and savez functions in multithreaded environment

        def writer(error_list):
            with temppath(suffix='.npz') as tmp:
                arr = np.random.randn(500, 500)
                try:
                    np.savez(tmp, arr=arr)
                except OSError as err:
                    error_list.append(err)

        errors = []
        threads = [threading.Thread(target=writer, args=(errors,))
                   for j in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        if errors:
            raise AssertionError(errors)

    def test_not_closing_opened_fid(self):
        # Test that issue #2178 is fixed:
        # verify could seek on 'loaded' file
        with temppath(suffix='.npz') as tmp:
            with open(tmp, 'wb') as fp:
                np.savez(fp, data='LOVELY LOAD')
            with open(tmp, 'rb', 10000) as fp:
                fp.seek(0)
                assert_(not fp.closed)
                np.load(fp)['data']
                # fp must not get closed by .load
                assert_(not fp.closed)
                fp.seek(0)
                assert_(not fp.closed)

    @pytest.mark.slow_pypy
    def test_closing_fid(self):
        # Test that issue #1517 (too many opened files) remains closed
        # It might be a "weak" test since failed to get triggered on
        # e.g. Debian sid of 2012 Jul 05 but was reported to
        # trigger the failure on Ubuntu 10.04:
        # http://projects.scipy.org/numpy/ticket/1517#comment:2
        with temppath(suffix='.npz') as tmp:
            np.savez(tmp, data='LOVELY LOAD')
            # We need to check if the garbage collector can properly close
            # numpy npz file returned by np.load when their reference count
            # goes to zero.  Python running in debug mode raises a
            # ResourceWarning when file closing is left to the garbage
            # collector, so we catch the warnings.
            with suppress_warnings() as sup:
                sup.filter(ResourceWarning)  # TODO: specify exact message
                for i in range(1, 1025):
                    try:
                        np.load(tmp)["data"]
                    except Exception as e:
                        msg = f"Failed to load data from a file: {e}"
                        raise AssertionError(msg)
                    finally:
                        if IS_PYPY:
                            gc.collect()

    def test_closing_zipfile_after_load(self):
        # Check that zipfile owns file and can close it.  This needs to
        # pass a file name to load for the test. On windows failure will
        # cause a second error will be raised when the attempt to remove
        # the open file is made.
        prefix = 'numpy_test_closing_zipfile_after_load_'
        with temppath(suffix='.npz', prefix=prefix) as tmp:
            np.savez(tmp, lab='place holder')
            data = np.load(tmp)
            fp = data.zip.fp
            data.close()
            assert_(fp.closed)

    @pytest.mark.parametrize("count, expected_repr", [
        (1, "NpzFile {fname!r} with keys: arr_0"),
        (5, "NpzFile {fname!r} with keys: arr_0, arr_1, arr_2, arr_3, arr_4"),
        # _MAX_REPR_ARRAY_COUNT is 5, so files with more than 5 keys are
        # expected to end in '...'
        (6, "NpzFile {fname!r} with keys: arr_0, arr_1, arr_2, arr_3, arr_4..."),
    ])
    def test_repr_lists_keys(self, count, expected_repr):
        a = np.array([[1, 2], [3, 4]], float)
        with temppath(suffix='.npz') as tmp:
            np.savez(tmp, *[a] * count)
            l = np.load(tmp)
            assert repr(l) == expected_repr.format(fname=tmp)
            l.close()


class TestSaveTxt:
    def test_array(self):
        a = np.array([[1, 2], [3, 4]], float)
        fmt = "%.18e"
        c = BytesIO()
        np.savetxt(c, a, fmt=fmt)
        c.seek(0)
        assert_equal(c.readlines(),
                     [asbytes((fmt + ' ' + fmt + '\n') % (1, 2)),
                      asbytes((fmt + ' ' + fmt + '\n') % (3, 4))])

        a = np.array([[1, 2], [3, 4]], int)
        c = BytesIO()
        np.savetxt(c, a, fmt='%d')
        c.seek(0)
        assert_equal(c.readlines(), [b'1 2\n', b'3 4\n'])

    def test_1D(self):
        a = np.array([1, 2, 3, 4], int)
        c = BytesIO()
        np.savetxt(c, a, fmt='%d')
        c.seek(0)
        lines = c.readlines()
        assert_equal(lines, [b'1\n', b'2\n', b'3\n', b'4\n'])

    def test_0D_3D(self):
        c = BytesIO()
        assert_raises(ValueError, np.savetxt, c, np.array(1))
        assert_raises(ValueError, np.savetxt, c, np.array([[[1], [2]]]))

    def test_structured(self):
        a = np.array([(1, 2), (3, 4)], dtype=[('x', 'i4'), ('y', 'i4')])
        c = BytesIO()
        np.savetxt(c, a, fmt='%d')
        c.seek(0)
        assert_equal(c.readlines(), [b'1 2\n', b'3 4\n'])

    def test_structured_padded(self):
        # gh-13297
        a = np.array([(1, 2, 3), (4, 5, 6)], dtype=[
            ('foo', 'i4'), ('bar', 'i4'), ('baz', 'i4')
        ])
        c = BytesIO()
        np.savetxt(c, a[['foo', 'baz']], fmt='%d')
        c.seek(0)
        assert_equal(c.readlines(), [b'1 3\n', b'4 6\n'])

    def test_multifield_view(self):
        a = np.ones(1, dtype=[('x', 'i4'), ('y', 'i4'), ('z', 'f4')])
        v = a[['x', 'z']]
        with temppath(suffix='.npy') as path:
            path = Path(path)
            np.save(path, v)
            data = np.load(path)
            assert_array_equal(data, v)

    def test_delimiter(self):
        a = np.array([[1., 2.], [3., 4.]])
        c = BytesIO()
        np.savetxt(c, a, delimiter=',', fmt='%d')
        c.seek(0)
        assert_equal(c.readlines(), [b'1,2\n', b'3,4\n'])

    def test_format(self):
        a = np.array([(1, 2), (3, 4)])
        c = BytesIO()
        # Sequence of formats
        np.savetxt(c, a, fmt=['%02d', '%3.1f'])
        c.seek(0)
        assert_equal(c.readlines(), [b'01 2.0\n', b'03 4.0\n'])

        # A single multiformat string
        c = BytesIO()
        np.savetxt(c, a, fmt='%02d : %3.1f')
        c.seek(0)
        lines = c.readlines()
        assert_equal(lines, [b'01 : 2.0\n', b'03 : 4.0\n'])

        # Specify delimiter, should be overridden
        c = BytesIO()
        np.savetxt(c, a, fmt='%02d : %3.1f', delimiter=',')
        c.seek(0)
        lines = c.readlines()
        assert_equal(lines, [b'01 : 2.0\n', b'03 : 4.0\n'])

        # Bad fmt, should raise a ValueError
        c = BytesIO()
        assert_raises(ValueError, np.savetxt, c, a, fmt=99)

    def test_header_footer(self):
        # Test the functionality of the header and footer keyword argument.

        c = BytesIO()
        a = np.array([(1, 2), (3, 4)], dtype=int)
        test_header_footer = 'Test header / footer'
        # Test the header keyword argument
        np.savetxt(c, a, fmt='%1d', header=test_header_footer)
        c.seek(0)
        assert_equal(c.read(),
                     asbytes('# ' + test_header_footer + '\n1 2\n3 4\n'))
        # Test the footer keyword argument
        c = BytesIO()
        np.savetxt(c, a, fmt='%1d', footer=test_header_footer)
        c.seek(0)
        assert_equal(c.read(),
                     asbytes('1 2\n3 4\n# ' + test_header_footer + '\n'))
        # Test the commentstr keyword argument used on the header
        c = BytesIO()
        commentstr = '% '
        np.savetxt(c, a, fmt='%1d',
                   header=test_header_footer, comments=commentstr)
        c.seek(0)
        assert_equal(c.read(),
                     asbytes(commentstr + test_header_footer + '\n' + '1 2\n3 4\n'))
        # Test the commentstr keyword argument used on the footer
        c = BytesIO()
        commentstr = '% '
        np.savetxt(c, a, fmt='%1d',
                   footer=test_header_footer, comments=commentstr)
        c.seek(0)
        assert_equal(c.read(),
                     asbytes('1 2\n3 4\n' + commentstr + test_header_footer + '\n'))

    @pytest.mark.parametrize("filename_type", [Path, str])
    def test_file_roundtrip(self, filename_type):
        with temppath() as name:
            a = np.array([(1, 2), (3, 4)])
            np.savetxt(filename_type(name), a)
            b = np.loadtxt(filename_type(name))
            assert_array_equal(a, b)

    def test_complex_arrays(self):
        ncols = 2
        nrows = 2
        a = np.zeros((ncols, nrows), dtype=np.complex128)
        re = np.pi
        im = np.e
        a[:] = re + 1.0j * im

        # One format only
        c = BytesIO()
        np.savetxt(c, a, fmt=' %+.3e')
        c.seek(0)
        lines = c.readlines()
        assert_equal(
            lines,
            [b' ( +3.142e+00+ +2.718e+00j)  ( +3.142e+00+ +2.718e+00j)\n',
             b' ( +3.142e+00+ +2.718e+00j)  ( +3.142e+00+ +2.718e+00j)\n'])

        # One format for each real and imaginary part
        c = BytesIO()
        np.savetxt(c, a, fmt='  %+.3e' * 2 * ncols)
        c.seek(0)
        lines = c.readlines()
        assert_equal(
            lines,
            [b'  +3.142e+00  +2.718e+00  +3.142e+00  +2.718e+00\n',
             b'  +3.142e+00  +2.718e+00  +3.142e+00  +2.718e+00\n'])

        # One format for each complex number
        c = BytesIO()
        np.savetxt(c, a, fmt=['(%.3e%+.3ej)'] * ncols)
        c.seek(0)
        lines = c.readlines()
        assert_equal(
            lines,
            [b'(3.142e+00+2.718e+00j) (3.142e+00+2.718e+00j)\n',
             b'(3.142e+00+2.718e+00j) (3.142e+00+2.718e+00j)\n'])

    def test_complex_negative_exponent(self):
        # Previous to 1.15, some formats generated x+-yj, gh 7895
        ncols = 2
        nrows = 2
        a = np.zeros((ncols, nrows), dtype=np.complex128)
        re = np.pi
        im = np.e
        a[:] = re - 1.0j * im
        c = BytesIO()
        np.savetxt(c, a, fmt='%.3e')
        c.seek(0)
        lines = c.readlines()
        assert_equal(
            lines,
            [b' (3.142e+00-2.718e+00j)  (3.142e+00-2.718e+00j)\n',
             b' (3.142e+00-2.718e+00j)  (3.142e+00-2.718e+00j)\n'])

    def test_custom_writer(self):

        class CustomWriter(list):
            def write(self, text):
                self.extend(text.split(b'\n'))

        w = CustomWriter()
        a = np.array([(1, 2), (3, 4)])
        np.savetxt(w, a)
        b = np.loadtxt(w)
        assert_array_equal(a, b)

    def test_unicode(self):
        utf8 = b'\xcf\x96'.decode('UTF-8')
        a = np.array([utf8], dtype=np.str_)
        with tempdir() as tmpdir:
            # set encoding as on windows it may not be unicode even on py3
            np.savetxt(os.path.join(tmpdir, 'test.csv'), a, fmt=['%s'],
                       encoding='UTF-8')

    def test_unicode_roundtrip(self):
        utf8 = b'\xcf\x96'.decode('UTF-8')
        a = np.array([utf8], dtype=np.str_)
        # our gz wrapper support encoding
        suffixes = ['', '.gz']
        if HAS_BZ2:
            suffixes.append('.bz2')
        if HAS_LZMA:
            suffixes.extend(['.xz', '.lzma'])
        with tempdir() as tmpdir:
            for suffix in suffixes:
                np.savetxt(os.path.join(tmpdir, 'test.csv' + suffix), a,
                           fmt=['%s'], encoding='UTF-16-LE')
                b = np.loadtxt(os.path.join(tmpdir, 'test.csv' + suffix),
                               encoding='UTF-16-LE', dtype=np.str_)
                assert_array_equal(a, b)

    def test_unicode_bytestream(self):
        utf8 = b'\xcf\x96'.decode('UTF-8')
        a = np.array([utf8], dtype=np.str_)
        s = BytesIO()
        np.savetxt(s, a, fmt=['%s'], encoding='UTF-8')
        s.seek(0)
        assert_equal(s.read().decode('UTF-8'), utf8 + '\n')

    def test_unicode_stringstream(self):
        utf8 = b'\xcf\x96'.decode('UTF-8')
        a = np.array([utf8], dtype=np.str_)
        s = StringIO()
        np.savetxt(s, a, fmt=['%s'], encoding='UTF-8')
        s.seek(0)
        assert_equal(s.read(), utf8 + '\n')

    @pytest.mark.parametrize("iotype", [StringIO, BytesIO])
    def test_unicode_and_bytes_fmt(self, iotype):
        # string type of fmt should not matter, see also gh-4053
        a = np.array([1.])
        s = iotype()
        np.savetxt(s, a, fmt="%f")
        s.seek(0)
        if iotype is StringIO:
            assert_equal(s.read(), "%f\n" % 1.)
        else:
            assert_equal(s.read(), b"%f\n" % 1.)

    @pytest.mark.skipif(sys.platform == 'win32', reason="files>4GB may not work")
    @pytest.mark.slow
    @requires_memory(free_bytes=7e9)
    def test_large_zip(self):
        def check_large_zip(memoryerror_raised):
            memoryerror_raised.value = False
            try:
                # The test takes at least 6GB of memory, writes a file larger
                # than 4GB. This tests the ``allowZip64`` kwarg to ``zipfile``
                test_data = np.asarray([np.random.rand(
                                        np.random.randint(50, 100), 4)
                                        for i in range(800000)], dtype=object)
                with tempdir() as tmpdir:
                    np.savez(os.path.join(tmpdir, 'test.npz'),
                             test_data=test_data)
            except MemoryError:
                memoryerror_raised.value = True
                raise
        # run in a subprocess to ensure memory is released on PyPy, see gh-15775
        # Use an object in shared memory to re-raise the MemoryError exception
        # in our process if needed, see gh-16889
        memoryerror_raised = Value(c_bool)

        # Since Python 3.8, the default start method for multiprocessing has
        # been changed from 'fork' to 'spawn' on macOS, causing inconsistency
        # on memory sharing model, leading to failed test for check_large_zip
        ctx = get_context('fork')
        p = ctx.Process(target=check_large_zip, args=(memoryerror_raised,))
        p.start()
        p.join()
        if memoryerror_raised.value:
            raise MemoryError("Child process raised a MemoryError exception")
        # -9 indicates a SIGKILL, probably an OOM.
        if p.exitcode == -9:
            pytest.xfail("subprocess got a SIGKILL, apparently free memory was not sufficient")
        assert p.exitcode == 0

class LoadTxtBase:
    def check_compressed(self, fopen, suffixes):
        # Test that we can load data from a compressed file
        wanted = np.arange(6).reshape((2, 3))
        linesep = ('\n', '\r\n', '\r')
        for sep in linesep:
            data = '0 1 2' + sep + '3 4 5'
            for suffix in suffixes:
                with temppath(suffix=suffix) as name:
                    with fopen(name, mode='wt', encoding='UTF-32-LE') as f:
                        f.write(data)
                    res = self.loadfunc(name, encoding='UTF-32-LE')
                    assert_array_equal(res, wanted)
                    with fopen(name, "rt",  encoding='UTF-32-LE') as f:
                        res = self.loadfunc(f)
                    assert_array_equal(res, wanted)

    def test_compressed_gzip(self):
        self.check_compressed(gzip.open, ('.gz',))

    @pytest.mark.skipif(not HAS_BZ2, reason="Needs bz2")
    def test_compressed_bz2(self):
        self.check_compressed(bz2.open, ('.bz2',))

    @pytest.mark.skipif(not HAS_LZMA, reason="Needs lzma")
    def test_compressed_lzma(self):
        self.check_compressed(lzma.open, ('.xz', '.lzma'))

    def test_encoding(self):
        with temppath() as path:
            with open(path, "wb") as f:
                f.write('0.\n1.\n2.'.encode("UTF-16"))
            x = self.loadfunc(path, encoding="UTF-16")
            assert_array_equal(x, [0., 1., 2.])

    def test_stringload(self):
        # umlaute
        nonascii = b'\xc3\xb6\xc3\xbc\xc3\xb6'.decode("UTF-8")
        with temppath() as path:
            with open(path, "wb") as f:
                f.write(nonascii.encode("UTF-16"))
            x = self.loadfunc(path, encoding="UTF-16", dtype=np.str_)
            assert_array_equal(x, nonascii)

    def test_binary_decode(self):
        utf16 = b'\xff\xfeh\x04 \x00i\x04 \x00j\x04'
        v = self.loadfunc(BytesIO(utf16), dtype=np.str_, encoding='UTF-16')
        assert_array_equal(v, np.array(utf16.decode('UTF-16').split()))

    def test_converters_decode(self):
        # test converters that decode strings
        c = TextIO()
        c.write(b'\xcf\x96')
        c.seek(0)
        x = self.loadfunc(c, dtype=np.str_, encoding="bytes",
                          converters={0: lambda x: x.decode('UTF-8')})
        a = np.array([b'\xcf\x96'.decode('UTF-8')])
        assert_array_equal(x, a)

    def test_converters_nodecode(self):
        # test native string converters enabled by setting an encoding
        utf8 = b'\xcf\x96'.decode('UTF-8')
        with temppath() as path:
            with open(path, 'wt', encoding='UTF-8') as f:
                f.write(utf8)
            x = self.loadfunc(path, dtype=np.str_,
                              converters={0: lambda x: x + 't'},
                              encoding='UTF-8')
            a = np.array([utf8 + 't'])
            assert_array_equal(x, a)


class TestLoadTxt(LoadTxtBase):
    loadfunc = staticmethod(np.loadtxt)

    def setup_method(self):
        # lower chunksize for testing
        self.orig_chunk = _npyio_impl._loadtxt_chunksize
        _npyio_impl._loadtxt_chunksize = 1

    def teardown_method(self):
        _npyio_impl._loadtxt_chunksize = self.orig_chunk

    def test_record(self):
        c = TextIO()
        c.write('1 2\n3 4')
        c.seek(0)
        x = np.loadtxt(c, dtype=[('x', np.int32), ('y', np.int32)])
        a = np.array([(1, 2), (3, 4)], dtype=[('x', 'i4'), ('y', 'i4')])
        assert_array_equal(x, a)

        d = TextIO()
        d.write('M 64 75.0\nF 25 60.0')
        d.seek(0)
        mydescriptor = {'names': ('gender', 'age', 'weight'),
                        'formats': ('S1', 'i4', 'f4')}
        b = np.array([('M', 64.0, 75.0),
                      ('F', 25.0, 60.0)], dtype=mydescriptor)
        y = np.loadtxt(d, dtype=mydescriptor)
        assert_array_equal(y, b)

    def test_array(self):
        c = TextIO()
        c.write('1 2\n3 4')

        c.seek(0)
        x = np.loadtxt(c, dtype=int)
        a = np.array([[1, 2], [3, 4]], int)
        assert_array_equal(x, a)

        c.seek(0)
        x = np.loadtxt(c, dtype=float)
        a = np.array([[1, 2], [3, 4]], float)
        assert_array_equal(x, a)

    def test_1D(self):
        c = TextIO()
        c.write('1\n2\n3\n4\n')
        c.seek(0)
        x = np.loadtxt(c, dtype=int)
        a = np.array([1, 2, 3, 4], int)
        assert_array_equal(x, a)

        c = TextIO()
        c.write('1,2,3,4\n')
        c.seek(0)
        x = np.loadtxt(c, dtype=int, delimiter=',')
        a = np.array([1, 2, 3, 4], int)
        assert_array_equal(x, a)

    def test_missing(self):
        c = TextIO()
        c.write('1,2,3,,5\n')
        c.seek(0)
        x = np.loadtxt(c, dtype=int, delimiter=',',
                       converters={3: lambda s: int(s or - 999)})
        a = np.array([1, 2, 3, -999, 5], int)
        assert_array_equal(x, a)

    def test_converters_with_usecols(self):
        c = TextIO()
        c.write('1,2,3,,5\n6,7,8,9,10\n')
        c.seek(0)
        x = np.loadtxt(c, dtype=int, delimiter=',',
                       converters={3: lambda s: int(s or - 999)},
                       usecols=(1, 3,))
        a = np.array([[2, -999], [7, 9]], int)
        assert_array_equal(x, a)

    def test_comments_unicode(self):
        c = TextIO()
        c.write('# comment\n1,2,3,5\n')
        c.seek(0)
        x = np.loadtxt(c, dtype=int, delimiter=',',
                       comments='#')
        a = np.array([1, 2, 3, 5], int)
        assert_array_equal(x, a)

    def test_comments_byte(self):
        c = TextIO()
        c.write('# comment\n1,2,3,5\n')
        c.seek(0)
        x = np.loadtxt(c, dtype=int, delimiter=',',
                       comments=b'#')
        a = np.array([1, 2, 3, 5], int)
        assert_array_equal(x, a)

    def test_comments_multiple(self):
        c = TextIO()
        c.write('# comment\n1,2,3\n@ comment2\n4,5,6 // comment3')
        c.seek(0)
        x = np.loadtxt(c, dtype=int, delimiter=',',
                       comments=['#', '@', '//'])
        a = np.array([[1, 2, 3], [4, 5, 6]], int)
        assert_array_equal(x, a)

    @pytest.mark.skipif(IS_PYPY and sys.implementation.version <= (7, 3, 8),
                        reason="PyPy bug in error formatting")
    def test_comments_multi_chars(self):
        c = TextIO()
        c.write('/* comment\n1,2,3,5\n')
        c.seek(0)
        x = np.loadtxt(c, dtype=int, delimiter=',',
                       comments='/*')
        a = np.array([1, 2, 3, 5], int)
        assert_array_equal(x, a)

        # Check that '/*' is not transformed to ['/', '*']
        c = TextIO()
        c.write('*/ comment\n1,2,3,5\n')
        c.seek(0)
        assert_raises(ValueError, np.loadtxt, c, dtype=int, delimiter=',',
                      comments='/*')

    def test_skiprows(self):
        c = TextIO()
        c.write('comment\n1,2,3,5\n')
        c.seek(0)
        x = np.loadtxt(c, dtype=int, delimiter=',',
                       skiprows=1)
        a = np.array([1, 2, 3, 5], int)
        assert_array_equal(x, a)

        c = TextIO()
        c.write('# comment\n1,2,3,5\n')
        c.seek(0)
        x = np.loadtxt(c, dtype=int, delimiter=',',
                       skiprows=1)
        a = np.array([1, 2, 3, 5], int)
        assert_array_equal(x, a)

    def test_usecols(self):
        a = np.array([[1, 2], [3, 4]], float)
        c = BytesIO()
        np.savetxt(c, a)
        c.seek(0)
        x = np.loadtxt(c, dtype=float, usecols=(1,))
        assert_array_equal(x, a[:, 1])

        a = np.array([[1, 2, 3], [3, 4, 5]], float)
        c = BytesIO()
        np.savetxt(c, a)
        c.seek(0)
        x = np.loadtxt(c, dtype=float, usecols=(1, 2))
        assert_array_equal(x, a[:, 1:])

        # Testing with arrays instead of tuples.
        c.seek(0)
        x = np.loadtxt(c, dtype=float, usecols=np.array([1, 2]))
        assert_array_equal(x, a[:, 1:])

        # Testing with an integer instead of a sequence
        for int_type in [int, np.int8, np.int16,
                         np.int32, np.int64, np.uint8, np.uint16,
                         np.uint32, np.uint64]:
            to_read = int_type(1)
            c.seek(0)
            x = np.loadtxt(c, dtype=float, usecols=to_read)
            assert_array_equal(x, a[:, 1])

        # Testing with some crazy custom integer type
        class CrazyInt:
            def __index__(self):
                return 1

        crazy_int = CrazyInt()
        c.seek(0)
        x = np.loadtxt(c, dtype=float, usecols=crazy_int)
        assert_array_equal(x, a[:, 1])

        c.seek(0)
        x = np.loadtxt(c, dtype=float, usecols=(crazy_int,))
        assert_array_equal(x, a[:, 1])

        # Checking with dtypes defined converters.
        data = '''JOE 70.1 25.3
                BOB 60.5 27.9
                '''
        c = TextIO(data)
        names = ['stid', 'temp']
        dtypes = ['S4', 'f8']
        arr = np.loadtxt(c, usecols=(0, 2), dtype=list(zip(names, dtypes)))
        assert_equal(arr['stid'], [b"JOE", b"BOB"])
        assert_equal(arr['temp'], [25.3, 27.9])

        # Testing non-ints in usecols
        c.seek(0)
        bogus_idx = 1.5
        assert_raises_regex(
            TypeError,
            f'^usecols must be.*{type(bogus_idx).__name__}',
            np.loadtxt, c, usecols=bogus_idx
            )

        assert_raises_regex(
            TypeError,
            f'^usecols must be.*{type(bogus_idx).__name__}',
            np.loadtxt, c, usecols=[0, bogus_idx, 0]
            )

    def test_bad_usecols(self):
        with pytest.raises(OverflowError):
            np.loadtxt(["1\n"], usecols=[2**64], delimiter=",")
        with pytest.raises((ValueError, OverflowError)):
            # Overflow error on 32bit platforms
            np.loadtxt(["1\n"], usecols=[2**62], delimiter=",")
        with pytest.raises(TypeError,
                match="If a structured dtype .*. But 1 usecols were given and "
                      "the number of fields is 3."):
            np.loadtxt(["1,1\n"], dtype="i,2i", usecols=[0], delimiter=",")

    def test_fancy_dtype(self):
        c = TextIO()
        c.write('1,2,3.0\n4,5,6.0\n')
        c.seek(0)
        dt = np.dtype([('x', int), ('y', [('t', int), ('s', float)])])
        x = np.loadtxt(c, dtype=dt, delimiter=',')
        a = np.array([(1, (2, 3.0)), (4, (5, 6.0))], dt)
        assert_array_equal(x, a)

    def test_shaped_dtype(self):
        c = TextIO("aaaa  1.0  8.0  1 2 3 4 5 6")
        dt = np.dtype([('name', 'S4'), ('x', float), ('y', float),
                       ('block', int, (2, 3))])
        x = np.loadtxt(c, dtype=dt)
        a = np.array([('aaaa', 1.0, 8.0, [[1, 2, 3], [4, 5, 6]])],
                     dtype=dt)
        assert_array_equal(x, a)

    def test_3d_shaped_dtype(self):
        c = TextIO("aaaa  1.0  8.0  1 2 3 4 5 6 7 8 9 10 11 12")
        dt = np.dtype([('name', 'S4'), ('x', float), ('y', float),
                       ('block', int, (2, 2, 3))])
        x = np.loadtxt(c, dtype=dt)
        a = np.array([('aaaa', 1.0, 8.0,
                       [[[1, 2, 3], [4, 5, 6]], [[7, 8, 9], [10, 11, 12]]])],
                     dtype=dt)
        assert_array_equal(x, a)

    def test_str_dtype(self):
        # see gh-8033
        c = ["str1", "str2"]

        for dt in (str, np.bytes_):
            a = np.array(["str1", "str2"], dtype=dt)
            x = np.loadtxt(c, dtype=dt)
            assert_array_equal(x, a)

    def test_empty_file(self):
        with pytest.warns(UserWarning, match="input contained no data"):
            c = TextIO()
            x = np.loadtxt(c)
            assert_equal(x.shape, (0,))
            x = np.loadtxt(c, dtype=np.int64)
            assert_equal(x.shape, (0,))
            assert_(x.dtype == np.int64)

    def test_unused_converter(self):
        c = TextIO()
        c.writelines(['1 21\n', '3 42\n'])
        c.seek(0)
        data = np.loadtxt(c, usecols=(1,),
                          converters={0: lambda s: int(s, 16)})
        assert_array_equal(data, [21, 42])

        c.seek(0)
        data = np.loadtxt(c, usecols=(1,),
                          converters={1: lambda s: int(s, 16)})
        assert_array_equal(data, [33, 66])

    def test_dtype_with_object(self):
        # Test using an explicit dtype with an object
        data = """ 1; 2001-01-01
                   2; 2002-01-31 """
        ndtype = [('idx', int), ('code', object)]
        func = lambda s: strptime(s.strip(), "%Y-%m-%d")
        converters = {1: func}
        test = np.loadtxt(TextIO(data), delimiter=";", dtype=ndtype,
                          converters=converters)
        control = np.array(
            [(1, datetime(2001, 1, 1)), (2, datetime(2002, 1, 31))],
            dtype=ndtype)
        assert_equal(test, control)

    def test_uint64_type(self):
        tgt = (9223372043271415339, 9223372043271415853)
        c = TextIO()
        c.write("%s %s" % tgt)
        c.seek(0)
        res = np.loadtxt(c, dtype=np.uint64)
        assert_equal(res, tgt)

    def test_int64_type(self):
        tgt = (-9223372036854775807, 9223372036854775807)
        c = TextIO()
        c.write("%s %s" % tgt)
        c.seek(0)
        res = np.loadtxt(c, dtype=np.int64)
        assert_equal(res, tgt)

    def test_from_float_hex(self):
        # IEEE doubles and floats only, otherwise the float32
        # conversion may fail.
        tgt = np.logspace(-10, 10, 5).astype(np.float32)
        tgt = np.hstack((tgt, -tgt)).astype(float)
        inp = '\n'.join(map(float.hex, tgt))
        c = TextIO()
        c.write(inp)
        for dt in [float, np.float32]:
            c.seek(0)
            res = np.loadtxt(
                c, dtype=dt, converters=float.fromhex, encoding="latin1")
            assert_equal(res, tgt, err_msg=f"{dt}")

    @pytest.mark.skipif(IS_PYPY and sys.implementation.version <= (7, 3, 8),
                        reason="PyPy bug in error formatting")
    def test_default_float_converter_no_default_hex_conversion(self):
        """
        Ensure that fromhex is only used for values with the correct prefix and
        is not called by default. Regression test related to gh-19598.
        """
        c = TextIO("a b c")
        with pytest.raises(ValueError,
                match=".*convert string 'a' to float64 at row 0, column 1"):
            np.loadtxt(c)

    @pytest.mark.skipif(IS_PYPY and sys.implementation.version <= (7, 3, 8),
                        reason="PyPy bug in error formatting")
    def test_default_float_converter_exception(self):
        """
        Ensure that the exception message raised during failed floating point
        conversion is correct. Regression test related to gh-19598.
        """
        c = TextIO("qrs tuv")  # Invalid values for default float converter
        with pytest.raises(ValueError,
                match="could not convert string 'qrs' to float64"):
            np.loadtxt(c)

    def test_from_complex(self):
        tgt = (complex(1, 1), complex(1, -1))
        c = TextIO()
        c.write("%s %s" % tgt)
        c.seek(0)
        res = np.loadtxt(c, dtype=complex)
        assert_equal(res, tgt)

    def test_complex_misformatted(self):
        # test for backward compatibility
        # some complex formats used to generate x+-yj
        a = np.zeros((2, 2), dtype=np.complex128)
        re = np.pi
        im = np.e
        a[:] = re - 1.0j * im
        c = BytesIO()
        np.savetxt(c, a, fmt='%.16e')
        c.seek(0)
        txt = c.read()
        c.seek(0)
        # misformat the sign on the imaginary part, gh 7895
        txt_bad = txt.replace(b'e+00-', b'e00+-')
        assert_(txt_bad != txt)
        c.write(txt_bad)
        c.seek(0)
        res = np.loadtxt(c, dtype=complex)
        assert_equal(res, a)

    def test_universal_newline(self):
        with temppath() as name:
            with open(name, 'w') as f:
                f.write('1 21\r3 42\r')
            data = np.loadtxt(name)
        assert_array_equal(data, [[1, 21], [3, 42]])

    def test_empty_field_after_tab(self):
        c = TextIO()
        c.write('1 \t2 \t3\tstart \n4\t5\t6\t  \n7\t8\t9.5\t')
        c.seek(0)
        dt = {'names': ('x', 'y', 'z', 'comment'),
              'formats': ('<i4', '<i4', '<f4', '|S8')}
        x = np.loadtxt(c, dtype=dt, delimiter='\t')
        a = np.array([b'start ', b'  ', b''])
        assert_array_equal(x['comment'], a)

    def test_unpack_structured(self):
        txt = TextIO("M 21 72\nF 35 58")
        dt = {'names': ('a', 'b', 'c'), 'formats': ('|S1', '<i4', '<f4')}
        a, b, c = np.loadtxt(txt, dtype=dt, unpack=True)
        assert_(a.dtype.str == '|S1')
        assert_(b.dtype.str == '<i4')
        assert_(c.dtype.str == '<f4')
        assert_array_equal(a, np.array([b'M', b'F']))
        assert_array_equal(b, np.array([21, 35]))
        assert_array_equal(c, np.array([72.,  58.]))

    def test_ndmin_keyword(self):
        c = TextIO()
        c.write('1,2,3\n4,5,6')
        c.seek(0)
        assert_raises(ValueError, np.loadtxt, c, ndmin=3)
        c.seek(0)
        assert_raises(ValueError, np.loadtxt, c, ndmin=1.5)
        c.seek(0)
        x = np.loadtxt(c, dtype=int, delimiter=',', ndmin=1)
        a = np.array([[1, 2, 3], [4, 5, 6]])
        assert_array_equal(x, a)

        d = TextIO()
        d.write('0,1,2')
        d.seek(0)
        x = np.loadtxt(d, dtype=int, delimiter=',', ndmin=2)
        assert_(x.shape == (1, 3))
        d.seek(0)
        x = np.loadtxt(d, dtype=int, delimiter=',', ndmin=1)
        assert_(x.shape == (3,))
        d.seek(0)
        x = np.loadtxt(d, dtype=int, delimiter=',', ndmin=0)
        assert_(x.shape == (3,))

        e = TextIO()
        e.write('0\n1\n2')
        e.seek(0)
        x = np.loadtxt(e, dtype=int, delimiter=',', ndmin=2)
        assert_(x.shape == (3, 1))
        e.seek(0)
        x = np.loadtxt(e, dtype=int, delimiter=',', ndmin=1)
        assert_(x.shape == (3,))
        e.seek(0)
        x = np.loadtxt(e, dtype=int, delimiter=',', ndmin=0)
        assert_(x.shape == (3,))

        # Test ndmin kw with empty file.
        with pytest.warns(UserWarning, match="input contained no data"):
            f = TextIO()
            assert_(np.loadtxt(f, ndmin=2).shape == (0, 1,))
            assert_(np.loadtxt(f, ndmin=1).shape == (0,))

    def test_generator_source(self):
        def count():
            for i in range(10):
                yield "%d" % i

        res = np.loadtxt(count())
        assert_array_equal(res, np.arange(10))

    def test_bad_line(self):
        c = TextIO()
        c.write('1 2 3\n4 5 6\n2 3')
        c.seek(0)

        # Check for exception and that exception contains line number
        assert_raises_regex(ValueError, "3", np.loadtxt, c)

    def test_none_as_string(self):
        # gh-5155, None should work as string when format demands it
        c = TextIO()
        c.write('100,foo,200\n300,None,400')
        c.seek(0)
        dt = np.dtype([('x', int), ('a', 'S10'), ('y', int)])
        np.loadtxt(c, delimiter=',', dtype=dt, comments=None)  # Should succeed

    @pytest.mark.skipif(locale.getpreferredencoding() == 'ANSI_X3.4-1968',
                        reason="Wrong preferred encoding")
    def test_binary_load(self):
        butf8 = b"5,6,7,\xc3\x95scarscar\r\n15,2,3,hello\r\n"\
                b"20,2,3,\xc3\x95scar\r\n"
        sutf8 = butf8.decode("UTF-8").replace("\r", "").splitlines()
        with temppath() as path:
            with open(path, "wb") as f:
                f.write(butf8)
            with open(path, "rb") as f:
                x = np.loadtxt(f, encoding="UTF-8", dtype=np.str_)
            assert_array_equal(x, sutf8)
            # test broken latin1 conversion people now rely on
            with open(path, "rb") as f:
                x = np.loadtxt(f, encoding="UTF-8", dtype="S")
            x = [b'5,6,7,\xc3\x95scarscar', b'15,2,3,hello', b'20,2,3,\xc3\x95scar']
            assert_array_equal(x, np.array(x, dtype="S"))

    def test_max_rows(self):
        c = TextIO()
        c.write('1,2,3,5\n4,5,7,8\n2,1,4,5')
        c.seek(0)
        x = np.loadtxt(c, dtype=int, delimiter=',',
                       max_rows=1)
        a = np.array([1, 2, 3, 5], int)
        assert_array_equal(x, a)

    def test_max_rows_with_skiprows(self):
        c = TextIO()
        c.write('comments\n1,2,3,5\n4,5,7,8\n2,1,4,5')
        c.seek(0)
        x = np.loadtxt(c, dtype=int, delimiter=',',
                       skiprows=1, max_rows=1)
        a = np.array([1, 2, 3, 5], int)
        assert_array_equal(x, a)

        c = TextIO()
        c.write('comment\n1,2,3,5\n4,5,7,8\n2,1,4,5')
        c.seek(0)
        x = np.loadtxt(c, dtype=int, delimiter=',',
                       skiprows=1, max_rows=2)
        a = np.array([[1, 2, 3, 5], [4, 5, 7, 8]], int)
        assert_array_equal(x, a)

    def test_max_rows_with_read_continuation(self):
        c = TextIO()
        c.write('1,2,3,5\n4,5,7,8\n2,1,4,5')
        c.seek(0)
        x = np.loadtxt(c, dtype=int, delimiter=',',
                       max_rows=2)
        a = np.array([[1, 2, 3, 5], [4, 5, 7, 8]], int)
        assert_array_equal(x, a)
        # test continuation
        x = np.loadtxt(c, dtype=int, delimiter=',')
        a = np.array([2, 1, 4, 5], int)
        assert_array_equal(x, a)

    def test_max_rows_larger(self):
        #test max_rows > num rows
        c = TextIO()
        c.write('comment\n1,2,3,5\n4,5,7,8\n2,1,4,5')
        c.seek(0)
        x = np.loadtxt(c, dtype=int, delimiter=',',
                       skiprows=1, max_rows=6)
        a = np.array([[1, 2, 3, 5], [4, 5, 7, 8], [2, 1, 4, 5]], int)
        assert_array_equal(x, a)

    @pytest.mark.parametrize(["skip", "data"], [
            (1, ["ignored\n", "1,2\n", "\n", "3,4\n"]),
            # "Bad" lines that do not end in newlines:
            (1, ["ignored", "1,2", "", "3,4"]),
            (1, StringIO("ignored\n1,2\n\n3,4")),
            # Same as above, but do not skip any lines:
            (0, ["-1,0\n", "1,2\n", "\n", "3,4\n"]),
            (0, ["-1,0", "1,2", "", "3,4"]),
            (0, StringIO("-1,0\n1,2\n\n3,4"))])
    def test_max_rows_empty_lines(self, skip, data):
        with pytest.warns(UserWarning,
                    match=f"Input line 3.*max_rows={3 - skip}"):
            res = np.loadtxt(data, dtype=int, skiprows=skip, delimiter=",",
                             max_rows=3 - skip)
            assert_array_equal(res, [[-1, 0], [1, 2], [3, 4]][skip:])

        if isinstance(data, StringIO):
            data.seek(0)

        with warnings.catch_warnings():
            warnings.simplefilter("error", UserWarning)
            with pytest.raises(UserWarning):
                np.loadtxt(data, dtype=int, skiprows=skip, delimiter=",",
                           max_rows=3 - skip)

class Testfromregex:
    def test_record(self):
        c = TextIO()
        c.write('1.312 foo\n1.534 bar\n4.444 qux')
        c.seek(0)

        dt = [('num', np.float64), ('val', 'S3')]
        x = np.fromregex(c, r"([0-9.]+)\s+(...)", dt)
        a = np.array([(1.312, 'foo'), (1.534, 'bar'), (4.444, 'qux')],
                     dtype=dt)
        assert_array_equal(x, a)

    def test_record_2(self):
        c = TextIO()
        c.write('1312 foo\n1534 bar\n4444 qux')
        c.seek(0)

        dt = [('num', np.int32), ('val', 'S3')]
        x = np.fromregex(c, r"(\d+)\s+(...)", dt)
        a = np.array([(1312, 'foo'), (1534, 'bar'), (4444, 'qux')],
                     dtype=dt)
        assert_array_equal(x, a)

    def test_record_3(self):
        c = TextIO()
        c.write('1312 foo\n1534 bar\n4444 qux')
        c.seek(0)

        dt = [('num', np.float64)]
        x = np.fromregex(c, r"(\d+)\s+...", dt)
        a = np.array([(1312,), (1534,), (4444,)], dtype=dt)
        assert_array_equal(x, a)

    @pytest.mark.parametrize("path_type", [str, Path])
    def test_record_unicode(self, path_type):
        utf8 = b'\xcf\x96'
        with temppath() as str_path:
            path = path_type(str_path)
            with open(path, 'wb') as f:
                f.write(b'1.312 foo' + utf8 + b' \n1.534 bar\n4.444 qux')

            dt = [('num', np.float64), ('val', 'U4')]
            x = np.fromregex(path, r"(?u)([0-9.]+)\s+(\w+)", dt, encoding='UTF-8')
            a = np.array([(1.312, 'foo' + utf8.decode('UTF-8')), (1.534, 'bar'),
                           (4.444, 'qux')], dtype=dt)
            assert_array_equal(x, a)

            regexp = re.compile(r"([0-9.]+)\s+(\w+)", re.UNICODE)
            x = np.fromregex(path, regexp, dt, encoding='UTF-8')
            assert_array_equal(x, a)

    def test_compiled_bytes(self):
        regexp = re.compile(br'(\d)')
        c = BytesIO(b'123')
        dt = [('num', np.float64)]
        a = np.array([1, 2, 3], dtype=dt)
        x = np.fromregex(c, regexp, dt)
        assert_array_equal(x, a)

    def test_bad_dtype_not_structured(self):
        regexp = re.compile(br'(\d)')
        c = BytesIO(b'123')
        with pytest.raises(TypeError, match='structured datatype'):
            np.fromregex(c, regexp, dtype=np.float64)


#####--------------------------------------------------------------------------


class TestFromTxt(LoadTxtBase):
    loadfunc = staticmethod(np.genfromtxt)

    def test_record(self):
        # Test w/ explicit dtype
        data = TextIO('1 2\n3 4')
        test = np.genfromtxt(data, dtype=[('x', np.int32), ('y', np.int32)])
        control = np.array([(1, 2), (3, 4)], dtype=[('x', 'i4'), ('y', 'i4')])
        assert_equal(test, control)
        #
        data = TextIO('M 64.0 75.0\nF 25.0 60.0')
        descriptor = {'names': ('gender', 'age', 'weight'),
                      'formats': ('S1', 'i4', 'f4')}
        control = np.array([('M', 64.0, 75.0), ('F', 25.0, 60.0)],
                           dtype=descriptor)
        test = np.genfromtxt(data, dtype=descriptor)
        assert_equal(test, control)

    def test_array(self):
        # Test outputting a standard ndarray
        data = TextIO('1 2\n3 4')
        control = np.array([[1, 2], [3, 4]], dtype=int)
        test = np.genfromtxt(data, dtype=int)
        assert_array_equal(test, control)
        #
        data.seek(0)
        control = np.array([[1, 2], [3, 4]], dtype=float)
        test = np.loadtxt(data, dtype=float)
        assert_array_equal(test, control)

    def test_1D(self):
        # Test squeezing to 1D
        control = np.array([1, 2, 3, 4], int)
        #
        data = TextIO('1\n2\n3\n4\n')
        test = np.genfromtxt(data, dtype=int)
        assert_array_equal(test, control)
        #
        data = TextIO('1,2,3,4\n')
        test = np.genfromtxt(data, dtype=int, delimiter=',')
        assert_array_equal(test, control)

    def test_comments(self):
        # Test the stripping of comments
        control = np.array([1, 2, 3, 5], int)
        # Comment on its own line
        data = TextIO('# comment\n1,2,3,5\n')
        test = np.genfromtxt(data, dtype=int, delimiter=',', comments='#')
        assert_equal(test, control)
        # Comment at the end of a line
        data = TextIO('1,2,3,5# comment\n')
        test = np.genfromtxt(data, dtype=int, delimiter=',', comments='#')
        assert_equal(test, control)

    def test_skiprows(self):
        # Test row skipping
        control = np.array([1, 2, 3, 5], int)
        kwargs = {"dtype": int, "delimiter": ','}
        #
        data = TextIO('comment\n1,2,3,5\n')
        test = np.genfromtxt(data, skip_header=1, **kwargs)
        assert_equal(test, control)
        #
        data = TextIO('# comment\n1,2,3,5\n')
        test = np.loadtxt(data, skiprows=1, **kwargs)
        assert_equal(test, control)

    def test_skip_footer(self):
        data = [f"# {i}" for i in range(1, 6)]
        data.append("A, B, C")
        data.extend([f"{i},{i:3.1f},{i:03d}" for i in range(51)])
        data[-1] = "99,99"
        kwargs = {"delimiter": ",", "names": True, "skip_header": 5, "skip_footer": 10}
        test = np.genfromtxt(TextIO("\n".join(data)), **kwargs)
        ctrl = np.array([(f"{i:f}", f"{i:f}", f"{i:f}") for i in range(41)],
                        dtype=[(_, float) for _ in "ABC"])
        assert_equal(test, ctrl)

    def test_skip_footer_with_invalid(self):
        with suppress_warnings() as sup:
            sup.filter(ConversionWarning)
            basestr = '1 1\n2 2\n3 3\n4 4\n5  \n6  \n7  \n'
            # Footer too small to get rid of all invalid values
            assert_raises(ValueError, np.genfromtxt,
                          TextIO(basestr), skip_footer=1)
    #        except ValueError:
    #            pass
            a = np.genfromtxt(
                TextIO(basestr), skip_footer=1, invalid_raise=False)
            assert_equal(a, np.array([[1., 1.], [2., 2.], [3., 3.], [4., 4.]]))
            #
            a = np.genfromtxt(TextIO(basestr), skip_footer=3)
            assert_equal(a, np.array([[1., 1.], [2., 2.], [3., 3.], [4., 4.]]))
            #
            basestr = '1 1\n2  \n3 3\n4 4\n5  \n6 6\n7 7\n'
            a = np.genfromtxt(
                TextIO(basestr), skip_footer=1, invalid_raise=False)
            assert_equal(a, np.array([[1., 1.], [3., 3.], [4., 4.], [6., 6.]]))
            a = np.genfromtxt(
                TextIO(basestr), skip_footer=3, invalid_raise=False)
            assert_equal(a, np.array([[1., 1.], [3., 3.], [4., 4.]]))

    def test_header(self):
        # Test retrieving a header
        data = TextIO('gender age weight\nM 64.0 75.0\nF 25.0 60.0')
        with warnings.catch_warnings(record=True) as w:
            warnings.filterwarnings('always', '', VisibleDeprecationWarning)
            test = np.genfromtxt(data, dtype=None, names=True,
                                 encoding='bytes')
            assert_(w[0].category is VisibleDeprecationWarning)
        control = {'gender': np.array([b'M', b'F']),
                   'age': np.array([64.0, 25.0]),
                   'weight': np.array([75.0, 60.0])}
        assert_equal(test['gender'], control['gender'])
        assert_equal(test['age'], control['age'])
        assert_equal(test['weight'], control['weight'])

    def test_auto_dtype(self):
        # Test the automatic definition of the output dtype
        data = TextIO('A 64 75.0 3+4j True\nBCD 25 60.0 5+6j False')
        with warnings.catch_warnings(record=True) as w:
            warnings.filterwarnings('always', '', VisibleDeprecationWarning)
            test = np.genfromtxt(data, dtype=None, encoding='bytes')
            assert_(w[0].category is VisibleDeprecationWarning)
        control = [np.array([b'A', b'BCD']),
                   np.array([64, 25]),
                   np.array([75.0, 60.0]),
                   np.array([3 + 4j, 5 + 6j]),
                   np.array([True, False]), ]
        assert_equal(test.dtype.names, ['f0', 'f1', 'f2', 'f3', 'f4'])
        for (i, ctrl) in enumerate(control):
            assert_equal(test[f'f{i}'], ctrl)

    def test_auto_dtype_uniform(self):
        # Tests whether the output dtype can be uniformized
        data = TextIO('1 2 3 4\n5 6 7 8\n')
        test = np.genfromtxt(data, dtype=None)
        control = np.array([[1, 2, 3, 4], [5, 6, 7, 8]])
        assert_equal(test, control)

    def test_fancy_dtype(self):
        # Check that a nested dtype isn't MIA
        data = TextIO('1,2,3.0\n4,5,6.0\n')
        fancydtype = np.dtype([('x', int), ('y', [('t', int), ('s', float)])])
        test = np.genfromtxt(data, dtype=fancydtype, delimiter=',')
        control = np.array([(1, (2, 3.0)), (4, (5, 6.0))], dtype=fancydtype)
        assert_equal(test, control)

    def test_names_overwrite(self):
        # Test overwriting the names of the dtype
        descriptor = {'names': ('g', 'a', 'w'),
                      'formats': ('S1', 'i4', 'f4')}
        data = TextIO(b'M 64.0 75.0\nF 25.0 60.0')
        names = ('gender', 'age', 'weight')
        test = np.genfromtxt(data, dtype=descriptor, names=names)
        descriptor['names'] = names
        control = np.array([('M', 64.0, 75.0),
                            ('F', 25.0, 60.0)], dtype=descriptor)
        assert_equal(test, control)

    def test_bad_fname(self):
        with pytest.raises(TypeError, match='fname must be a string,'):
            np.genfromtxt(123)

    def test_commented_header(self):
        # Check that names can be retrieved even if the line is commented out.
        data = TextIO("""
#gender age weight
M   21  72.100000
F   35  58.330000
M   33  21.99
        """)
        # The # is part of the first name and should be deleted automatically.
        with warnings.catch_warnings(record=True) as w:
            warnings.filterwarnings('always', '', VisibleDeprecationWarning)
            test = np.genfromtxt(data, names=True, dtype=None,
                                 encoding="bytes")
            assert_(w[0].category is VisibleDeprecationWarning)
        ctrl = np.array([('M', 21, 72.1), ('F', 35, 58.33), ('M', 33, 21.99)],
                        dtype=[('gender', '|S1'), ('age', int), ('weight', float)])
        assert_equal(test, ctrl)
        # Ditto, but we should get rid of the first element
        data = TextIO(b"""
# gender age weight
M   21  72.100000
F   35  58.330000
M   33  21.99
        """)
        with warnings.catch_warnings(record=True) as w:
            warnings.filterwarnings('always', '', VisibleDeprecationWarning)
            test = np.genfromtxt(data, names=True, dtype=None,
                                 encoding="bytes")
            assert_(w[0].category is VisibleDeprecationWarning)
        assert_equal(test, ctrl)

    def test_names_and_comments_none(self):
        # Tests case when names is true but comments is None (gh-10780)
        data = TextIO('col1 col2\n 1 2\n 3 4')
        test = np.genfromtxt(data, dtype=(int, int), comments=None, names=True)
        control = np.array([(1, 2), (3, 4)], dtype=[('col1', int), ('col2', int)])
        assert_equal(test, control)

    def test_file_is_closed_on_error(self):
        # gh-13200
        with tempdir() as tmpdir:
            fpath = os.path.join(tmpdir, "test.csv")
            with open(fpath, "wb") as f:
                f.write('\N{GREEK PI SYMBOL}'.encode())

            # ResourceWarnings are emitted from a destructor, so won't be
            # detected by regular propagation to errors.
            with assert_no_warnings():
                with pytest.raises(UnicodeDecodeError):
                    np.genfromtxt(fpath, encoding="ascii")

    def test_autonames_and_usecols(self):
        # Tests names and usecols
        data = TextIO('A B C D\n aaaa 121 45 9.1')
        with warnings.catch_warnings(record=True) as w:
            warnings.filterwarnings('always', '', VisibleDeprecationWarning)
            test = np.genfromtxt(data, usecols=('A', 'C', 'D'),
                                names=True, dtype=None, encoding="bytes")
            assert_(w[0].category is VisibleDeprecationWarning)
        control = np.array(('aaaa', 45, 9.1),
                           dtype=[('A', '|S4'), ('C', int), ('D', float)])
        assert_equal(test, control)

    def test_converters_with_usecols(self):
        # Test the combination user-defined converters and usecol
        data = TextIO('1,2,3,,5\n6,7,8,9,10\n')
        test = np.genfromtxt(data, dtype=int, delimiter=',',
                            converters={3: lambda s: int(s or - 999)},
                            usecols=(1, 3,))
        control = np.array([[2, -999], [7, 9]], int)
        assert_equal(test, control)

    def test_converters_with_usecols_and_names(self):
        # Tests names and usecols
        data = TextIO('A B C D\n aaaa 121 45 9.1')
        with warnings.catch_warnings(record=True) as w:
            warnings.filterwarnings('always', '', VisibleDeprecationWarning)
            test = np.genfromtxt(data, usecols=('A', 'C', 'D'), names=True,
                                dtype=None, encoding="bytes",
                                converters={'C': lambda s: 2 * int(s)})
            assert_(w[0].category is VisibleDeprecationWarning)
        control = np.array(('aaaa', 90, 9.1),
                           dtype=[('A', '|S4'), ('C', int), ('D', float)])
        assert_equal(test, control)

    def test_converters_cornercases(self):
        # Test the conversion to datetime.
        converter = {
            'date': lambda s: strptime(s, '%Y-%m-%d %H:%M:%SZ')}
        data = TextIO('2009-02-03 12:00:00Z, 72214.0')
        test = np.genfromtxt(data, delimiter=',', dtype=None,
                            names=['date', 'stid'], converters=converter)
        control = np.array((datetime(2009, 2, 3), 72214.),
                           dtype=[('date', np.object_), ('stid', float)])
        assert_equal(test, control)

    def test_converters_cornercases2(self):
        # Test the conversion to datetime64.
        converter = {
            'date': lambda s: np.datetime64(strptime(s, '%Y-%m-%d %H:%M:%SZ'))}
        data = TextIO('2009-02-03 12:00:00Z, 72214.0')
        test = np.genfromtxt(data, delimiter=',', dtype=None,
                            names=['date', 'stid'], converters=converter)
        control = np.array((datetime(2009, 2, 3), 72214.),
                           dtype=[('date', 'datetime64[us]'), ('stid', float)])
        assert_equal(test, control)

    def test_unused_converter(self):
        # Test whether unused converters are forgotten
        data = TextIO("1 21\n  3 42\n")
        test = np.genfromtxt(data, usecols=(1,),
                            converters={0: lambda s: int(s, 16)})
        assert_equal(test, [21, 42])
        #
        data.seek(0)
        test = np.genfromtxt(data, usecols=(1,),
                            converters={1: lambda s: int(s, 16)})
        assert_equal(test, [33, 66])

    def test_invalid_converter(self):
        strip_rand = lambda x: float((b'r' in x.lower() and x.split()[-1]) or
                                     ((b'r' not in x.lower() and x.strip()) or 0.0))
        strip_per = lambda x: float((b'%' in x.lower() and x.split()[0]) or
                                    ((b'%' not in x.lower() and x.strip()) or 0.0))
        s = TextIO("D01N01,10/1/2003 ,1 %,R 75,400,600\r\n"
                   "L24U05,12/5/2003, 2 %,1,300, 150.5\r\n"
                   "D02N03,10/10/2004,R 1,,7,145.55")
        kwargs = {
            "converters": {2: strip_per, 3: strip_rand}, "delimiter": ",",
            "dtype": None, "encoding": "bytes"}
        assert_raises(ConverterError, np.genfromtxt, s, **kwargs)

    def test_tricky_converter_bug1666(self):
        # Test some corner cases
        s = TextIO('q1,2\nq3,4')
        cnv = lambda s: float(s[1:])
        test = np.genfromtxt(s, delimiter=',', converters={0: cnv})
        control = np.array([[1., 2.], [3., 4.]])
        assert_equal(test, control)

    def test_dtype_with_converters(self):
        dstr = "2009; 23; 46"
        test = np.genfromtxt(TextIO(dstr,),
                            delimiter=";", dtype=float, converters={0: bytes})
        control = np.array([('2009', 23., 46)],
                           dtype=[('f0', '|S4'), ('f1', float), ('f2', float)])
        assert_equal(test, control)
        test = np.genfromtxt(TextIO(dstr,),
                            delimiter=";", dtype=float, converters={0: float})
        control = np.array([2009., 23., 46],)
        assert_equal(test, control)

    @pytest.mark.filterwarnings("ignore:.*recfromcsv.*:DeprecationWarning")
    def test_dtype_with_converters_and_usecols(self):
        dstr = "1,5,-1,1:1\n2,8,-1,1:n\n3,3,-2,m:n\n"
        dmap = {'1:1': 0, '1:n': 1, 'm:1': 2, 'm:n': 3}
        dtyp = [('e1', 'i4'), ('e2', 'i4'), ('e3', 'i2'), ('n', 'i1')]
        conv = {0: int, 1: int, 2: int, 3: lambda r: dmap[r.decode()]}
        test = recfromcsv(TextIO(dstr,), dtype=dtyp, delimiter=',',
                          names=None, converters=conv, encoding="bytes")
        control = np.rec.array([(1, 5, -1, 0), (2, 8, -1, 1), (3, 3, -2, 3)], dtype=dtyp)
        assert_equal(test, control)
        dtyp = [('e1', 'i4'), ('e2', 'i4'), ('n', 'i1')]
        test = recfromcsv(TextIO(dstr,), dtype=dtyp, delimiter=',',
                          usecols=(0, 1, 3), names=None, converters=conv,
                          encoding="bytes")
        control = np.rec.array([(1, 5, 0), (2, 8, 1), (3, 3, 3)], dtype=dtyp)
        assert_equal(test, control)

    def test_dtype_with_object(self):
        # Test using an explicit dtype with an object
        data = """ 1; 2001-01-01
                   2; 2002-01-31 """
        ndtype = [('idx', int), ('code', object)]
        func = lambda s: strptime(s.strip(), "%Y-%m-%d")
        converters = {1: func}
        test = np.genfromtxt(TextIO(data), delimiter=";", dtype=ndtype,
                             converters=converters)
        control = np.array(
            [(1, datetime(2001, 1, 1)), (2, datetime(2002, 1, 31))],
            dtype=ndtype)
        assert_equal(test, control)

        ndtype = [('nest', [('idx', int), ('code', object)])]
        with assert_raises_regex(NotImplementedError,
                                 'Nested fields.* not supported.*'):
            test = np.genfromtxt(TextIO(data), delimiter=";",
                                 dtype=ndtype, converters=converters)

        # nested but empty fields also aren't supported
        ndtype = [('idx', int), ('code', object), ('nest', [])]
        with assert_raises_regex(NotImplementedError,
                                 'Nested fields.* not supported.*'):
            test = np.genfromtxt(TextIO(data), delimiter=";",
                                 dtype=ndtype, converters=converters)

    def test_dtype_with_object_no_converter(self):
        # Object without a converter uses bytes:
        parsed = np.genfromtxt(TextIO("1"), dtype=object)
        assert parsed[()] == b"1"
        parsed = np.genfromtxt(TextIO("string"), dtype=object)
        assert parsed[()] == b"string"

    def test_userconverters_with_explicit_dtype(self):
        # Test user_converters w/ explicit (standard) dtype
        data = TextIO('skip,skip,2001-01-01,1.0,skip')
        test = np.genfromtxt(data, delimiter=",", names=None, dtype=float,
                             usecols=(2, 3), converters={2: bytes})
        control = np.array([('2001-01-01', 1.)],
                           dtype=[('', '|S10'), ('', float)])
        assert_equal(test, control)

    def test_utf8_userconverters_with_explicit_dtype(self):
        utf8 = b'\xcf\x96'
        with temppath() as path:
            with open(path, 'wb') as f:
                f.write(b'skip,skip,2001-01-01' + utf8 + b',1.0,skip')
            test = np.genfromtxt(path, delimiter=",", names=None, dtype=float,
                                 usecols=(2, 3), converters={2: str},
                                 encoding='UTF-8')
        control = np.array([('2001-01-01' + utf8.decode('UTF-8'), 1.)],
                           dtype=[('', '|U11'), ('', float)])
        assert_equal(test, control)

    def test_spacedelimiter(self):
        # Test space delimiter
        data = TextIO("1  2  3  4   5\n6  7  8  9  10")
        test = np.genfromtxt(data)
        control = np.array([[1., 2., 3., 4., 5.],
                            [6., 7., 8., 9., 10.]])
        assert_equal(test, control)

    def test_integer_delimiter(self):
        # Test using an integer for delimiter
        data = "  1  2  3\n  4  5 67\n890123  4"
        test = np.genfromtxt(TextIO(data), delimiter=3)
        control = np.array([[1, 2, 3], [4, 5, 67], [890, 123, 4]])
        assert_equal(test, control)

    def test_missing(self):
        data = TextIO('1,2,3,,5\n')
        test = np.genfromtxt(data, dtype=int, delimiter=',',
                            converters={3: lambda s: int(s or - 999)})
        control = np.array([1, 2, 3, -999, 5], int)
        assert_equal(test, control)

    def test_missing_with_tabs(self):
        # Test w/ a delimiter tab
        txt = "1\t2\t3\n\t2\t\n1\t\t3"
        test = np.genfromtxt(TextIO(txt), delimiter="\t",
                             usemask=True,)
        ctrl_d = np.array([(1, 2, 3), (np.nan, 2, np.nan), (1, np.nan, 3)],)
        ctrl_m = np.array([(0, 0, 0), (1, 0, 1), (0, 1, 0)], dtype=bool)
        assert_equal(test.data, ctrl_d)
        assert_equal(test.mask, ctrl_m)

    def test_usecols(self):
        # Test the selection of columns
        # Select 1 column
        control = np.array([[1, 2], [3, 4]], float)
        data = TextIO()
        np.savetxt(data, control)
        data.seek(0)
        test = np.genfromtxt(data, dtype=float, usecols=(1,))
        assert_equal(test, control[:, 1])
        #
        control = np.array([[1, 2, 3], [3, 4, 5]], float)
        data = TextIO()
        np.savetxt(data, control)
        data.seek(0)
        test = np.genfromtxt(data, dtype=float, usecols=(1, 2))
        assert_equal(test, control[:, 1:])
        # Testing with arrays instead of tuples.
        data.seek(0)
        test = np.genfromtxt(data, dtype=float, usecols=np.array([1, 2]))
        assert_equal(test, control[:, 1:])

    def test_usecols_as_css(self):
        # Test giving usecols with a comma-separated string
        data = "1 2 3\n4 5 6"
        test = np.genfromtxt(TextIO(data),
                             names="a, b, c", usecols="a, c")
        ctrl = np.array([(1, 3), (4, 6)], dtype=[(_, float) for _ in "ac"])
        assert_equal(test, ctrl)

    def test_usecols_with_structured_dtype(self):
        # Test usecols with an explicit structured dtype
        data = TextIO("JOE 70.1 25.3\nBOB 60.5 27.9")
        names = ['stid', 'temp']
        dtypes = ['S4', 'f8']
        test = np.genfromtxt(
            data, usecols=(0, 2), dtype=list(zip(names, dtypes)))
        assert_equal(test['stid'], [b"JOE", b"BOB"])
        assert_equal(test['temp'], [25.3, 27.9])

    def test_usecols_with_integer(self):
        # Test usecols with an integer
        test = np.genfromtxt(TextIO(b"1 2 3\n4 5 6"), usecols=0)
        assert_equal(test, np.array([1., 4.]))

    def test_usecols_with_named_columns(self):
        # Test usecols with named columns
        ctrl = np.array([(1, 3), (4, 6)], dtype=[('a', float), ('c', float)])
        data = "1 2 3\n4 5 6"
        kwargs = {"names": "a, b, c"}
        test = np.genfromtxt(TextIO(data), usecols=(0, -1), **kwargs)
        assert_equal(test, ctrl)
        test = np.genfromtxt(TextIO(data),
                             usecols=('a', 'c'), **kwargs)
        assert_equal(test, ctrl)

    def test_empty_file(self):
        # Test that an empty file raises the proper warning.
        with suppress_warnings() as sup:
            sup.filter(message="genfromtxt: Empty input file:")
            data = TextIO()
            test = np.genfromtxt(data)
            assert_equal(test, np.array([]))

            # when skip_header > 0
            test = np.genfromtxt(data, skip_header=1)
            assert_equal(test, np.array([]))

    def test_fancy_dtype_alt(self):
        # Check that a nested dtype isn't MIA
        data = TextIO('1,2,3.0\n4,5,6.0\n')
        fancydtype = np.dtype([('x', int), ('y', [('t', int), ('s', float)])])
        test = np.genfromtxt(data, dtype=fancydtype, delimiter=',', usemask=True)
        control = ma.array([(1, (2, 3.0)), (4, (5, 6.0))], dtype=fancydtype)
        assert_equal(test, control)

    def test_shaped_dtype(self):
        c = TextIO("aaaa  1.0  8.0  1 2 3 4 5 6")
        dt = np.dtype([('name', 'S4'), ('x', float), ('y', float),
                       ('block', int, (2, 3))])
        x = np.genfromtxt(c, dtype=dt)
        a = np.array([('aaaa', 1.0, 8.0, [[1, 2, 3], [4, 5, 6]])],
                     dtype=dt)
        assert_array_equal(x, a)

    def test_withmissing(self):
        data = TextIO('A,B\n0,1\n2,N/A')
        kwargs = {"delimiter": ",", "missing_values": "N/A", "names": True}
        test = np.genfromtxt(data, dtype=None, usemask=True, **kwargs)
        control = ma.array([(0, 1), (2, -1)],
                           mask=[(False, False), (False, True)],
                           dtype=[('A', int), ('B', int)])
        assert_equal(test, control)
        assert_equal(test.mask, control.mask)
        #
        data.seek(0)
        test = np.genfromtxt(data, usemask=True, **kwargs)
        control = ma.array([(0, 1), (2, -1)],
                           mask=[(False, False), (False, True)],
                           dtype=[('A', float), ('B', float)])
        assert_equal(test, control)
        assert_equal(test.mask, control.mask)

    def test_user_missing_values(self):
        data = "A, B, C\n0, 0., 0j\n1, N/A, 1j\n-9, 2.2, N/A\n3, -99, 3j"
        basekwargs = {"dtype": None, "delimiter": ",", "names": True}
        mdtype = [('A', int), ('B', float), ('C', complex)]
        #
        test = np.genfromtxt(TextIO(data), missing_values="N/A",
                            **basekwargs)
        control = ma.array([(0, 0.0, 0j), (1, -999, 1j),
                            (-9, 2.2, -999j), (3, -99, 3j)],
                           mask=[(0, 0, 0), (0, 1, 0), (0, 0, 1), (0, 0, 0)],
                           dtype=mdtype)
        assert_equal(test, control)
        #
        basekwargs['dtype'] = mdtype
        test = np.genfromtxt(TextIO(data),
                            missing_values={0: -9, 1: -99, 2: -999j}, usemask=True, **basekwargs)
        control = ma.array([(0, 0.0, 0j), (1, -999, 1j),
                            (-9, 2.2, -999j), (3, -99, 3j)],
                           mask=[(0, 0, 0), (0, 1, 0), (1, 0, 1), (0, 1, 0)],
                           dtype=mdtype)
        assert_equal(test, control)
        #
        test = np.genfromtxt(TextIO(data),
                            missing_values={0: -9, 'B': -99, 'C': -999j},
                            usemask=True,
                            **basekwargs)
        control = ma.array([(0, 0.0, 0j), (1, -999, 1j),
                            (-9, 2.2, -999j), (3, -99, 3j)],
                           mask=[(0, 0, 0), (0, 1, 0), (1, 0, 1), (0, 1, 0)],
                           dtype=mdtype)
        assert_equal(test, control)

    def test_user_filling_values(self):
        # Test with missing and filling values
        ctrl = np.array([(0, 3), (4, -999)], dtype=[('a', int), ('b', int)])
        data = "N/A, 2, 3\n4, ,???"
        kwargs = {"delimiter": ",",
                      "dtype": int,
                      "names": "a,b,c",
                      "missing_values": {0: "N/A", 'b': " ", 2: "???"},
                      "filling_values": {0: 0, 'b': 0, 2: -999}}
        test = np.genfromtxt(TextIO(data), **kwargs)
        ctrl = np.array([(0, 2, 3), (4, 0, -999)],
                        dtype=[(_, int) for _ in "abc"])
        assert_equal(test, ctrl)
        #
        test = np.genfromtxt(TextIO(data), usecols=(0, -1), **kwargs)
        ctrl = np.array([(0, 3), (4, -999)], dtype=[(_, int) for _ in "ac"])
        assert_equal(test, ctrl)

        data2 = "1,2,*,4\n5,*,7,8\n"
        test = np.genfromtxt(TextIO(data2), delimiter=',', dtype=int,
                             missing_values="*", filling_values=0)
        ctrl = np.array([[1, 2, 0, 4], [5, 0, 7, 8]])
        assert_equal(test, ctrl)
        test = np.genfromtxt(TextIO(data2), delimiter=',', dtype=int,
                             missing_values="*", filling_values=-1)
        ctrl = np.array([[1, 2, -1, 4], [5, -1, 7, 8]])
        assert_equal(test, ctrl)

    def test_withmissing_float(self):
        data = TextIO('A,B\n0,1.5\n2,-999.00')
        test = np.genfromtxt(data, dtype=None, delimiter=',',
                            missing_values='-999.0', names=True, usemask=True)
        control = ma.array([(0, 1.5), (2, -1.)],
                           mask=[(False, False), (False, True)],
                           dtype=[('A', int), ('B', float)])
        assert_equal(test, control)
        assert_equal(test.mask, control.mask)

    def test_with_masked_column_uniform(self):
        # Test masked column
        data = TextIO('1 2 3\n4 5 6\n')
        test = np.genfromtxt(data, dtype=None,
                             missing_values='2,5', usemask=True)
        control = ma.array([[1, 2, 3], [4, 5, 6]], mask=[[0, 1, 0], [0, 1, 0]])
        assert_equal(test, control)

    def test_with_masked_column_various(self):
        # Test masked column
        data = TextIO('True 2 3\nFalse 5 6\n')
        test = np.genfromtxt(data, dtype=None,
                             missing_values='2,5', usemask=True)
        control = ma.array([(1, 2, 3), (0, 5, 6)],
                           mask=[(0, 1, 0), (0, 1, 0)],
                           dtype=[('f0', bool), ('f1', bool), ('f2', int)])
        assert_equal(test, control)

    def test_invalid_raise(self):
        # Test invalid raise
        data = ["1, 1, 1, 1, 1"] * 50
        for i in range(5):
            data[10 * i] = "2, 2, 2, 2 2"
        data.insert(0, "a, b, c, d, e")
        mdata = TextIO("\n".join(data))

        kwargs = {"delimiter": ",", "dtype": None, "names": True}

        def f():
            return np.genfromtxt(mdata, invalid_raise=False, **kwargs)
        mtest = assert_warns(ConversionWarning, f)
        assert_equal(len(mtest), 45)
        assert_equal(mtest, np.ones(45, dtype=[(_, int) for _ in 'abcde']))
        #
        mdata.seek(0)
        assert_raises(ValueError, np.genfromtxt, mdata,
                      delimiter=",", names=True)

    def test_invalid_raise_with_usecols(self):
        # Test invalid_raise with usecols
        data = ["1, 1, 1, 1, 1"] * 50
        for i in range(5):
            data[10 * i] = "2, 2, 2, 2 2"
        data.insert(0, "a, b, c, d, e")
        mdata = TextIO("\n".join(data))

        kwargs = {"delimiter": ",", "dtype": None, "names": True,
                      "invalid_raise": False}

        def f():
            return np.genfromtxt(mdata, usecols=(0, 4), **kwargs)
        mtest = assert_warns(ConversionWarning, f)
        assert_equal(len(mtest), 45)
        assert_equal(mtest, np.ones(45, dtype=[(_, int) for _ in 'ae']))
        #
        mdata.seek(0)
        mtest = np.genfromtxt(mdata, usecols=(0, 1), **kwargs)
        assert_equal(len(mtest), 50)
        control = np.ones(50, dtype=[(_, int) for _ in 'ab'])
        control[[10 * _ for _ in range(5)]] = (2, 2)
        assert_equal(mtest, control)

    def test_inconsistent_dtype(self):
        # Test inconsistent dtype
        data = ["1, 1, 1, 1, -1.1"] * 50
        mdata = TextIO("\n".join(data))

        converters = {4: lambda x: f"({x.decode()})"}
        kwargs = {"delimiter": ",", "converters": converters,
                      "dtype": [(_, int) for _ in 'abcde'], "encoding": "bytes"}
        assert_raises(ValueError, np.genfromtxt, mdata, **kwargs)

    def test_default_field_format(self):
        # Test default format
        data = "0, 1, 2.3\n4, 5, 6.7"
        mtest = np.genfromtxt(TextIO(data),
                             delimiter=",", dtype=None, defaultfmt="f%02i")
        ctrl = np.array([(0, 1, 2.3), (4, 5, 6.7)],
                        dtype=[("f00", int), ("f01", int), ("f02", float)])
        assert_equal(mtest, ctrl)

    def test_single_dtype_wo_names(self):
        # Test single dtype w/o names
        data = "0, 1, 2.3\n4, 5, 6.7"
        mtest = np.genfromtxt(TextIO(data),
                             delimiter=",", dtype=float, defaultfmt="f%02i")
        ctrl = np.array([[0., 1., 2.3], [4., 5., 6.7]], dtype=float)
        assert_equal(mtest, ctrl)

    def test_single_dtype_w_explicit_names(self):
        # Test single dtype w explicit names
        data = "0, 1, 2.3\n4, 5, 6.7"
        mtest = np.genfromtxt(TextIO(data),
                             delimiter=",", dtype=float, names="a, b, c")
        ctrl = np.array([(0., 1., 2.3), (4., 5., 6.7)],
                        dtype=[(_, float) for _ in "abc"])
        assert_equal(mtest, ctrl)

    def test_single_dtype_w_implicit_names(self):
        # Test single dtype w implicit names
        data = "a, b, c\n0, 1, 2.3\n4, 5, 6.7"
        mtest = np.genfromtxt(TextIO(data),
                             delimiter=",", dtype=float, names=True)
        ctrl = np.array([(0., 1., 2.3), (4., 5., 6.7)],
                        dtype=[(_, float) for _ in "abc"])
        assert_equal(mtest, ctrl)

    def test_easy_structured_dtype(self):
        # Test easy structured dtype
        data = "0, 1, 2.3\n4, 5, 6.7"
        mtest = np.genfromtxt(TextIO(data), delimiter=",",
                             dtype=(int, float, float), defaultfmt="f_%02i")
        ctrl = np.array([(0, 1., 2.3), (4, 5., 6.7)],
                        dtype=[("f_00", int), ("f_01", float), ("f_02", float)])
        assert_equal(mtest, ctrl)

    def test_autostrip(self):
        # Test autostrip
        data = "01/01/2003  , 1.3,   abcde"
        kwargs = {"delimiter": ",", "dtype": None, "encoding": "bytes"}
        with warnings.catch_warnings(record=True) as w:
            warnings.filterwarnings('always', '', VisibleDeprecationWarning)
            mtest = np.genfromtxt(TextIO(data), **kwargs)
            assert_(w[0].category is VisibleDeprecationWarning)
        ctrl = np.array([('01/01/2003  ', 1.3, '   abcde')],
                        dtype=[('f0', '|S12'), ('f1', float), ('f2', '|S8')])
        assert_equal(mtest, ctrl)
        with warnings.catch_warnings(record=True) as w:
            warnings.filterwarnings('always', '', VisibleDeprecationWarning)
            mtest = np.genfromtxt(TextIO(data), autostrip=True, **kwargs)
            assert_(w[0].category is VisibleDeprecationWarning)
        ctrl = np.array([('01/01/2003', 1.3, 'abcde')],
                        dtype=[('f0', '|S10'), ('f1', float), ('f2', '|S5')])
        assert_equal(mtest, ctrl)

    def test_replace_space(self):
        # Test the 'replace_space' option
        txt = "A.A, B (B), C:C\n1, 2, 3.14"
        # Test default: replace ' ' by '_' and delete non-alphanum chars
        test = np.genfromtxt(TextIO(txt),
                             delimiter=",", names=True, dtype=None)
        ctrl_dtype = [("AA", int), ("B_B", int), ("CC", float)]
        ctrl = np.array((1, 2, 3.14), dtype=ctrl_dtype)
        assert_equal(test, ctrl)
        # Test: no replace, no delete
        test = np.genfromtxt(TextIO(txt),
                             delimiter=",", names=True, dtype=None,
                             replace_space='', deletechars='')
        ctrl_dtype = [("A.A", int), ("B (B)", int), ("C:C", float)]
        ctrl = np.array((1, 2, 3.14), dtype=ctrl_dtype)
        assert_equal(test, ctrl)
        # Test: no delete (spaces are replaced by _)
        test = np.genfromtxt(TextIO(txt),
                             delimiter=",", names=True, dtype=None,
                             deletechars='')
        ctrl_dtype = [("A.A", int), ("B_(B)", int), ("C:C", float)]
        ctrl = np.array((1, 2, 3.14), dtype=ctrl_dtype)
        assert_equal(test, ctrl)

    def test_replace_space_known_dtype(self):
        # Test the 'replace_space' (and related) options when dtype != None
        txt = "A.A, B (B), C:C\n1, 2, 3"
        # Test default: replace ' ' by '_' and delete non-alphanum chars
        test = np.genfromtxt(TextIO(txt),
                             delimiter=",", names=True, dtype=int)
        ctrl_dtype = [("AA", int), ("B_B", int), ("CC", int)]
        ctrl = np.array((1, 2, 3), dtype=ctrl_dtype)
        assert_equal(test, ctrl)
        # Test: no replace, no delete
        test = np.genfromtxt(TextIO(txt),
                             delimiter=",", names=True, dtype=int,
                             replace_space='', deletechars='')
        ctrl_dtype = [("A.A", int), ("B (B)", int), ("C:C", int)]
        ctrl = np.array((1, 2, 3), dtype=ctrl_dtype)
        assert_equal(test, ctrl)
        # Test: no delete (spaces are replaced by _)
        test = np.genfromtxt(TextIO(txt),
                             delimiter=",", names=True, dtype=int,
                             deletechars='')
        ctrl_dtype = [("A.A", int), ("B_(B)", int), ("C:C", int)]
        ctrl = np.array((1, 2, 3), dtype=ctrl_dtype)
        assert_equal(test, ctrl)

    def test_incomplete_names(self):
        # Test w/ incomplete names
        data = "A,,C\n0,1,2\n3,4,5"
        kwargs = {"delimiter": ",", "names": True}
        # w/ dtype=None
        ctrl = np.array([(0, 1, 2), (3, 4, 5)],
                        dtype=[(_, int) for _ in ('A', 'f0', 'C')])
        test = np.genfromtxt(TextIO(data), dtype=None, **kwargs)
        assert_equal(test, ctrl)
        # w/ default dtype
        ctrl = np.array([(0, 1, 2), (3, 4, 5)],
                        dtype=[(_, float) for _ in ('A', 'f0', 'C')])
        test = np.genfromtxt(TextIO(data), **kwargs)

    def test_names_auto_completion(self):
        # Make sure that names are properly completed
        data = "1 2 3\n 4 5 6"
        test = np.genfromtxt(TextIO(data),
                             dtype=(int, float, int), names="a")
        ctrl = np.array([(1, 2, 3), (4, 5, 6)],
                        dtype=[('a', int), ('f0', float), ('f1', int)])
        assert_equal(test, ctrl)

    def test_names_with_usecols_bug1636(self):
        # Make sure we pick up the right names w/ usecols
        data = "A,B,C,D,E\n0,1,2,3,4\n0,1,2,3,4\n0,1,2,3,4"
        ctrl_names = ("A", "C", "E")
        test = np.genfromtxt(TextIO(data),
                             dtype=(int, int, int), delimiter=",",
                             usecols=(0, 2, 4), names=True)
        assert_equal(test.dtype.names, ctrl_names)
        #
        test = np.genfromtxt(TextIO(data),
                             dtype=(int, int, int), delimiter=",",
                             usecols=("A", "C", "E"), names=True)
        assert_equal(test.dtype.names, ctrl_names)
        #
        test = np.genfromtxt(TextIO(data),
                             dtype=int, delimiter=",",
                             usecols=("A", "C", "E"), names=True)
        assert_equal(test.dtype.names, ctrl_names)

    def test_fixed_width_names(self):
        # Test fix-width w/ names
        data = "    A    B   C\n    0    1 2.3\n   45   67   9."
        kwargs = {"delimiter": (5, 5, 4), "names": True, "dtype": None}
        ctrl = np.array([(0, 1, 2.3), (45, 67, 9.)],
                        dtype=[('A', int), ('B', int), ('C', float)])
        test = np.genfromtxt(TextIO(data), **kwargs)
        assert_equal(test, ctrl)
        #
        kwargs = {"delimiter": 5, "names": True, "dtype": None}
        ctrl = np.array([(0, 1, 2.3), (45, 67, 9.)],
                        dtype=[('A', int), ('B', int), ('C', float)])
        test = np.genfromtxt(TextIO(data), **kwargs)
        assert_equal(test, ctrl)

    def test_filling_values(self):
        # Test missing values
        data = b"1, 2, 3\n1, , 5\n0, 6, \n"
        kwargs = {"delimiter": ",", "dtype": None, "filling_values": -999}
        ctrl = np.array([[1, 2, 3], [1, -999, 5], [0, 6, -999]], dtype=int)
        test = np.genfromtxt(TextIO(data), **kwargs)
        assert_equal(test, ctrl)

    def test_comments_is_none(self):
        # Github issue 329 (None was previously being converted to 'None').
        with warnings.catch_warnings(record=True) as w:
            warnings.filterwarnings('always', '', VisibleDeprecationWarning)
            test = np.genfromtxt(TextIO("test1,testNonetherestofthedata"),
                                 dtype=None, comments=None, delimiter=',',
                                 encoding="bytes")
            assert_(w[0].category is VisibleDeprecationWarning)
        assert_equal(test[1], b'testNonetherestofthedata')
        with warnings.catch_warnings(record=True) as w:
            warnings.filterwarnings('always', '', VisibleDeprecationWarning)
            test = np.genfromtxt(TextIO("test1, testNonetherestofthedata"),
                                 dtype=None, comments=None, delimiter=',',
                                 encoding="bytes")
            assert_(w[0].category is VisibleDeprecationWarning)
        assert_equal(test[1], b' testNonetherestofthedata')

    def test_latin1(self):
        latin1 = b'\xf6\xfc\xf6'
        norm = b"norm1,norm2,norm3\n"
        enc = b"test1,testNonethe" + latin1 + b",test3\n"
        s = norm + enc + norm
        with warnings.catch_warnings(record=True) as w:
            warnings.filterwarnings('always', '', VisibleDeprecationWarning)
            test = np.genfromtxt(TextIO(s),
                                 dtype=None, comments=None, delimiter=',',
                                 encoding="bytes")
            assert_(w[0].category is VisibleDeprecationWarning)
        assert_equal(test[1, 0], b"test1")
        assert_equal(test[1, 1], b"testNonethe" + latin1)
        assert_equal(test[1, 2], b"test3")
        test = np.genfromtxt(TextIO(s),
                             dtype=None, comments=None, delimiter=',',
                             encoding='latin1')
        assert_equal(test[1, 0], "test1")
        assert_equal(test[1, 1], "testNonethe" + latin1.decode('latin1'))
        assert_equal(test[1, 2], "test3")

        with warnings.catch_warnings(record=True) as w:
            warnings.filterwarnings('always', '', VisibleDeprecationWarning)
            test = np.genfromtxt(TextIO(b"0,testNonethe" + latin1),
                                 dtype=None, comments=None, delimiter=',',
                                 encoding="bytes")
            assert_(w[0].category is VisibleDeprecationWarning)
        assert_equal(test['f0'], 0)
        assert_equal(test['f1'], b"testNonethe" + latin1)

    def test_binary_decode_autodtype(self):
        utf16 = b'\xff\xfeh\x04 \x00i\x04 \x00j\x04'
        v = self.loadfunc(BytesIO(utf16), dtype=None, encoding='UTF-16')
        assert_array_equal(v, np.array(utf16.decode('UTF-16').split()))

    def test_utf8_byte_encoding(self):
        utf8 = b"\xcf\x96"
        norm = b"norm1,norm2,norm3\n"
        enc = b"test1,testNonethe" + utf8 + b",test3\n"
        s = norm + enc + norm
        with warnings.catch_warnings(record=True) as w:
            warnings.filterwarnings('always', '', VisibleDeprecationWarning)
            test = np.genfromtxt(TextIO(s),
                                 dtype=None, comments=None, delimiter=',',
                                 encoding="bytes")
            assert_(w[0].category is VisibleDeprecationWarning)
        ctl = np.array([
                 [b'norm1', b'norm2', b'norm3'],
                 [b'test1', b'testNonethe' + utf8, b'test3'],
                 [b'norm1', b'norm2', b'norm3']])
        assert_array_equal(test, ctl)

    def test_utf8_file(self):
        utf8 = b"\xcf\x96"
        with temppath() as path:
            with open(path, "wb") as f:
                f.write((b"test1,testNonethe" + utf8 + b",test3\n") * 2)
            test = np.genfromtxt(path, dtype=None, comments=None,
                                 delimiter=',', encoding="UTF-8")
            ctl = np.array([
                     ["test1", "testNonethe" + utf8.decode("UTF-8"), "test3"],
                     ["test1", "testNonethe" + utf8.decode("UTF-8"), "test3"]],
                     dtype=np.str_)
            assert_array_equal(test, ctl)

            # test a mixed dtype
            with open(path, "wb") as f:
                f.write(b"0,testNonethe" + utf8)
            test = np.genfromtxt(path, dtype=None, comments=None,
                                 delimiter=',', encoding="UTF-8")
            assert_equal(test['f0'], 0)
            assert_equal(test['f1'], "testNonethe" + utf8.decode("UTF-8"))

    def test_utf8_file_nodtype_unicode(self):
        # bytes encoding with non-latin1 -> unicode upcast
        utf8 = '\u03d6'
        latin1 = '\xf6\xfc\xf6'

        # skip test if cannot encode utf8 test string with preferred
        # encoding. The preferred encoding is assumed to be the default
        # encoding of open. Will need to change this for PyTest, maybe
        # using pytest.mark.xfail(raises=***).
        try:
            encoding = locale.getpreferredencoding()
            utf8.encode(encoding)
        except (UnicodeError, ImportError):
            pytest.skip('Skipping test_utf8_file_nodtype_unicode, '
                        'unable to encode utf8 in preferred encoding')

        with temppath() as path:
            with open(path, "wt") as f:
                f.write("norm1,norm2,norm3\n")
                f.write("norm1," + latin1 + ",norm3\n")
                f.write("test1,testNonethe" + utf8 + ",test3\n")
            with warnings.catch_warnings(record=True) as w:
                warnings.filterwarnings('always', '',
                                        VisibleDeprecationWarning)
                test = np.genfromtxt(path, dtype=None, comments=None,
                                     delimiter=',', encoding="bytes")
                # Check for warning when encoding not specified.
                assert_(w[0].category is VisibleDeprecationWarning)
            ctl = np.array([
                     ["norm1", "norm2", "norm3"],
                     ["norm1", latin1, "norm3"],
                     ["test1", "testNonethe" + utf8, "test3"]],
                     dtype=np.str_)
            assert_array_equal(test, ctl)

    @pytest.mark.filterwarnings("ignore:.*recfromtxt.*:DeprecationWarning")
    def test_recfromtxt(self):
        #
        data = TextIO('A,B\n0,1\n2,3')
        kwargs = {"delimiter": ",", "missing_values": "N/A", "names": True}
        test = recfromtxt(data, **kwargs)
        control = np.array([(0, 1), (2, 3)],
                           dtype=[('A', int), ('B', int)])
        assert_(isinstance(test, np.recarray))
        assert_equal(test, control)
        #
        data = TextIO('A,B\n0,1\n2,N/A')
        test = recfromtxt(data, dtype=None, usemask=True, **kwargs)
        control = ma.array([(0, 1), (2, -1)],
                           mask=[(False, False), (False, True)],
                           dtype=[('A', int), ('B', int)])
        assert_equal(test, control)
        assert_equal(test.mask, control.mask)
        assert_equal(test.A, [0, 2])

    @pytest.mark.filterwarnings("ignore:.*recfromcsv.*:DeprecationWarning")
    def test_recfromcsv(self):
        #
        data = TextIO('A,B\n0,1\n2,3')
        kwargs = {"missing_values": "N/A", "names": True, "case_sensitive": True,
                      "encoding": "bytes"}
        test = recfromcsv(data, dtype=None, **kwargs)
        control = np.array([(0, 1), (2, 3)],
                           dtype=[('A', int), ('B', int)])
        assert_(isinstance(test, np.recarray))
        assert_equal(test, control)
        #
        data = TextIO('A,B\n0,1\n2,N/A')
        test = recfromcsv(data, dtype=None, usemask=True, **kwargs)
        control = ma.array([(0, 1), (2, -1)],
                           mask=[(False, False), (False, True)],
                           dtype=[('A', int), ('B', int)])
        assert_equal(test, control)
        assert_equal(test.mask, control.mask)
        assert_equal(test.A, [0, 2])
        #
        data = TextIO('A,B\n0,1\n2,3')
        test = recfromcsv(data, missing_values='N/A',)
        control = np.array([(0, 1), (2, 3)],
                           dtype=[('a', int), ('b', int)])
        assert_(isinstance(test, np.recarray))
        assert_equal(test, control)
        #
        data = TextIO('A,B\n0,1\n2,3')
        dtype = [('a', int), ('b', float)]
        test = recfromcsv(data, missing_values='N/A', dtype=dtype)
        control = np.array([(0, 1), (2, 3)],
                           dtype=dtype)
        assert_(isinstance(test, np.recarray))
        assert_equal(test, control)

        # gh-10394
        data = TextIO('color\n"red"\n"blue"')
        test = recfromcsv(data, converters={0: lambda x: x.strip('\"')})
        control = np.array([('red',), ('blue',)], dtype=[('color', (str, 4))])
        assert_equal(test.dtype, control.dtype)
        assert_equal(test, control)

    def test_max_rows(self):
        # Test the `max_rows` keyword argument.
        data = '1 2\n3 4\n5 6\n7 8\n9 10\n'
        txt = TextIO(data)
        a1 = np.genfromtxt(txt, max_rows=3)
        a2 = np.genfromtxt(txt)
        assert_equal(a1, [[1, 2], [3, 4], [5, 6]])
        assert_equal(a2, [[7, 8], [9, 10]])

        # max_rows must be at least 1.
        assert_raises(ValueError, np.genfromtxt, TextIO(data), max_rows=0)

        # An input with several invalid rows.
        data = '1 1\n2 2\n0 \n3 3\n4 4\n5  \n6  \n7  \n'

        test = np.genfromtxt(TextIO(data), max_rows=2)
        control = np.array([[1., 1.], [2., 2.]])
        assert_equal(test, control)

        # Test keywords conflict
        assert_raises(ValueError, np.genfromtxt, TextIO(data), skip_footer=1,
                      max_rows=4)

        # Test with invalid value
        assert_raises(ValueError, np.genfromtxt, TextIO(data), max_rows=4)

        # Test with invalid not raise
        with suppress_warnings() as sup:
            sup.filter(ConversionWarning)

            test = np.genfromtxt(TextIO(data), max_rows=4, invalid_raise=False)
            control = np.array([[1., 1.], [2., 2.], [3., 3.], [4., 4.]])
            assert_equal(test, control)

            test = np.genfromtxt(TextIO(data), max_rows=5, invalid_raise=False)
            control = np.array([[1., 1.], [2., 2.], [3., 3.], [4., 4.]])
            assert_equal(test, control)

        # Structured array with field names.
        data = 'a b\n#c d\n1 1\n2 2\n#0 \n3 3\n4 4\n5  5\n'

        # Test with header, names and comments
        txt = TextIO(data)
        test = np.genfromtxt(txt, skip_header=1, max_rows=3, names=True)
        control = np.array([(1.0, 1.0), (2.0, 2.0), (3.0, 3.0)],
                      dtype=[('c', '<f8'), ('d', '<f8')])
        assert_equal(test, control)
        # To continue reading the same "file", don't use skip_header or
        # names, and use the previously determined dtype.
        test = np.genfromtxt(txt, max_rows=None, dtype=test.dtype)
        control = np.array([(4.0, 4.0), (5.0, 5.0)],
                      dtype=[('c', '<f8'), ('d', '<f8')])
        assert_equal(test, control)

    def test_gft_using_filename(self):
        # Test that we can load data from a filename as well as a file
        # object
        tgt = np.arange(6).reshape((2, 3))
        linesep = ('\n', '\r\n', '\r')

        for sep in linesep:
            data = '0 1 2' + sep + '3 4 5'
            with temppath() as name:
                with open(name, 'w') as f:
                    f.write(data)
                res = np.genfromtxt(name)
            assert_array_equal(res, tgt)

    def test_gft_from_gzip(self):
        # Test that we can load data from a gzipped file
        wanted = np.arange(6).reshape((2, 3))
        linesep = ('\n', '\r\n', '\r')

        for sep in linesep:
            data = '0 1 2' + sep + '3 4 5'
            s = BytesIO()
            with gzip.GzipFile(fileobj=s, mode='w') as g:
                g.write(asbytes(data))

            with temppath(suffix='.gz2') as name:
                with open(name, 'w') as f:
                    f.write(data)
                assert_array_equal(np.genfromtxt(name), wanted)

    def test_gft_using_generator(self):
        # gft doesn't work with unicode.
        def count():
            for i in range(10):
                yield asbytes("%d" % i)

        res = np.genfromtxt(count())
        assert_array_equal(res, np.arange(10))

    def test_auto_dtype_largeint(self):
        # Regression test for numpy/numpy#5635 whereby large integers could
        # cause OverflowErrors.

        # Test the automatic definition of the output dtype
        #
        # 2**66 = 73786976294838206464 => should convert to float
        # 2**34 = 17179869184 => should convert to int64
        # 2**10 = 1024 => should convert to int (int32 on 32-bit systems,
        #                 int64 on 64-bit systems)

        data = TextIO('73786976294838206464 17179869184 1024')

        test = np.genfromtxt(data, dtype=None)

        assert_equal(test.dtype.names, ['f0', 'f1', 'f2'])

        assert_(test.dtype['f0'] == float)
        assert_(test.dtype['f1'] == np.int64)
        assert_(test.dtype['f2'] == np.int_)

        assert_allclose(test['f0'], 73786976294838206464.)
        assert_equal(test['f1'], 17179869184)
        assert_equal(test['f2'], 1024)

    def test_unpack_float_data(self):
        txt = TextIO("1,2,3\n4,5,6\n7,8,9\n0.0,1.0,2.0")
        a, b, c = np.loadtxt(txt, delimiter=",", unpack=True)
        assert_array_equal(a, np.array([1.0, 4.0, 7.0, 0.0]))
        assert_array_equal(b, np.array([2.0, 5.0, 8.0, 1.0]))
        assert_array_equal(c, np.array([3.0, 6.0, 9.0, 2.0]))

    def test_unpack_structured(self):
        # Regression test for gh-4341
        # Unpacking should work on structured arrays
        txt = TextIO("M 21 72\nF 35 58")
        dt = {'names': ('a', 'b', 'c'), 'formats': ('S1', 'i4', 'f4')}
        a, b, c = np.genfromtxt(txt, dtype=dt, unpack=True)
        assert_equal(a.dtype, np.dtype('S1'))
        assert_equal(b.dtype, np.dtype('i4'))
        assert_equal(c.dtype, np.dtype('f4'))
        assert_array_equal(a, np.array([b'M', b'F']))
        assert_array_equal(b, np.array([21, 35]))
        assert_array_equal(c, np.array([72.,  58.]))

    def test_unpack_auto_dtype(self):
        # Regression test for gh-4341
        # Unpacking should work when dtype=None
        txt = TextIO("M 21 72.\nF 35 58.")
        expected = (np.array(["M", "F"]), np.array([21, 35]), np.array([72., 58.]))
        test = np.genfromtxt(txt, dtype=None, unpack=True, encoding="utf-8")
        for arr, result in zip(expected, test):
            assert_array_equal(arr, result)
            assert_equal(arr.dtype, result.dtype)

    def test_unpack_single_name(self):
        # Regression test for gh-4341
        # Unpacking should work when structured dtype has only one field
        txt = TextIO("21\n35")
        dt = {'names': ('a',), 'formats': ('i4',)}
        expected = np.array([21, 35], dtype=np.int32)
        test = np.genfromtxt(txt, dtype=dt, unpack=True)
        assert_array_equal(expected, test)
        assert_equal(expected.dtype, test.dtype)

    def test_squeeze_scalar(self):
        # Regression test for gh-4341
        # Unpacking a scalar should give zero-dim output,
        # even if dtype is structured
        txt = TextIO("1")
        dt = {'names': ('a',), 'formats': ('i4',)}
        expected = np.array((1,), dtype=np.int32)
        test = np.genfromtxt(txt, dtype=dt, unpack=True)
        assert_array_equal(expected, test)
        assert_equal((), test.shape)
        assert_equal(expected.dtype, test.dtype)

    @pytest.mark.parametrize("ndim", [0, 1, 2])
    def test_ndmin_keyword(self, ndim: int):
        # lets have the same behaviour of ndmin as loadtxt
        # as they should be the same for non-missing values
        txt = "42"

        a = np.loadtxt(StringIO(txt), ndmin=ndim)
        b = np.genfromtxt(StringIO(txt), ndmin=ndim)

        assert_array_equal(a, b)


class TestPathUsage:
    # Test that pathlib.Path can be used
    def test_loadtxt(self):
        with temppath(suffix='.txt') as path:
            path = Path(path)
            a = np.array([[1.1, 2], [3, 4]])
            np.savetxt(path, a)
            x = np.loadtxt(path)
            assert_array_equal(x, a)

    def test_save_load(self):
        # Test that pathlib.Path instances can be used with save.
        with temppath(suffix='.npy') as path:
            path = Path(path)
            a = np.array([[1, 2], [3, 4]], int)
            np.save(path, a)
            data = np.load(path)
            assert_array_equal(data, a)

    def test_save_load_memmap(self):
        # Test that pathlib.Path instances can be loaded mem-mapped.
        with temppath(suffix='.npy') as path:
            path = Path(path)
            a = np.array([[1, 2], [3, 4]], int)
            np.save(path, a)
            data = np.load(path, mmap_mode='r')
            assert_array_equal(data, a)
            # close the mem-mapped file
            del data
            if IS_PYPY:
                break_cycles()
                break_cycles()

    @pytest.mark.xfail(IS_WASM, reason="memmap doesn't work correctly")
    @pytest.mark.parametrize("filename_type", [Path, str])
    def test_save_load_memmap_readwrite(self, filename_type):
        with temppath(suffix='.npy') as path:
            path = filename_type(path)
            a = np.array([[1, 2], [3, 4]], int)
            np.save(path, a)
            b = np.load(path, mmap_mode='r+')
            a[0][0] = 5
            b[0][0] = 5
            del b  # closes the file
            if IS_PYPY:
                break_cycles()
                break_cycles()
            data = np.load(path)
            assert_array_equal(data, a)

    @pytest.mark.parametrize("filename_type", [Path, str])
    def test_savez_load(self, filename_type):
        with temppath(suffix='.npz') as path:
            path = filename_type(path)
            np.savez(path, lab='place holder')
            with np.load(path) as data:
                assert_array_equal(data['lab'], 'place holder')

    @pytest.mark.parametrize("filename_type", [Path, str])
    def test_savez_compressed_load(self, filename_type):
        with temppath(suffix='.npz') as path:
            path = filename_type(path)
            np.savez_compressed(path, lab='place holder')
            data = np.load(path)
            assert_array_equal(data['lab'], 'place holder')
            data.close()

    @pytest.mark.parametrize("filename_type", [Path, str])
    def test_genfromtxt(self, filename_type):
        with temppath(suffix='.txt') as path:
            path = filename_type(path)
            a = np.array([(1, 2), (3, 4)])
            np.savetxt(path, a)
            data = np.genfromtxt(path)
            assert_array_equal(a, data)

    @pytest.mark.parametrize("filename_type", [Path, str])
    @pytest.mark.filterwarnings("ignore:.*recfromtxt.*:DeprecationWarning")
    def test_recfromtxt(self, filename_type):
        with temppath(suffix='.txt') as path:
            path = filename_type(path)
            with open(path, 'w') as f:
                f.write('A,B\n0,1\n2,3')

            kwargs = {"delimiter": ",", "missing_values": "N/A", "names": True}
            test = recfromtxt(path, **kwargs)
            control = np.array([(0, 1), (2, 3)],
                               dtype=[('A', int), ('B', int)])
            assert_(isinstance(test, np.recarray))
            assert_equal(test, control)

    @pytest.mark.parametrize("filename_type", [Path, str])
    @pytest.mark.filterwarnings("ignore:.*recfromcsv.*:DeprecationWarning")
    def test_recfromcsv(self, filename_type):
        with temppath(suffix='.txt') as path:
            path = filename_type(path)
            with open(path, 'w') as f:
                f.write('A,B\n0,1\n2,3')

            kwargs = {
                "missing_values": "N/A", "names": True, "case_sensitive": True
            }
            test = recfromcsv(path, dtype=None, **kwargs)
            control = np.array([(0, 1), (2, 3)],
                               dtype=[('A', int), ('B', int)])
            assert_(isinstance(test, np.recarray))
            assert_equal(test, control)


def test_gzip_load():
    a = np.random.random((5, 5))

    s = BytesIO()
    f = gzip.GzipFile(fileobj=s, mode="w")

    np.save(f, a)
    f.close()
    s.seek(0)

    f = gzip.GzipFile(fileobj=s, mode="r")
    assert_array_equal(np.load(f), a)


# These next two classes encode the minimal API needed to save()/load() arrays.
# The `test_ducktyping` ensures they work correctly
class JustWriter:
    def __init__(self, base):
        self.base = base

    def write(self, s):
        return self.base.write(s)

    def flush(self):
        return self.base.flush()

class JustReader:
    def __init__(self, base):
        self.base = base

    def read(self, n):
        return self.base.read(n)

    def seek(self, off, whence=0):
        return self.base.seek(off, whence)


def test_ducktyping():
    a = np.random.random((5, 5))

    s = BytesIO()
    f = JustWriter(s)

    np.save(f, a)
    f.flush()
    s.seek(0)

    f = JustReader(s)
    assert_array_equal(np.load(f), a)


def test_gzip_loadtxt():
    # Thanks to another windows brokenness, we can't use
    # NamedTemporaryFile: a file created from this function cannot be
    # reopened by another open call. So we first put the gzipped string
    # of the test reference array, write it to a securely opened file,
    # which is then read from by the loadtxt function
    s = BytesIO()
    g = gzip.GzipFile(fileobj=s, mode='w')
    g.write(b'1 2 3\n')
    g.close()

    s.seek(0)
    with temppath(suffix='.gz') as name:
        with open(name, 'wb') as f:
            f.write(s.read())
        res = np.loadtxt(name)
    s.close()

    assert_array_equal(res, [1, 2, 3])


def test_gzip_loadtxt_from_string():
    s = BytesIO()
    f = gzip.GzipFile(fileobj=s, mode="w")
    f.write(b'1 2 3\n')
    f.close()
    s.seek(0)

    f = gzip.GzipFile(fileobj=s, mode="r")
    assert_array_equal(np.loadtxt(f), [1, 2, 3])


def test_npzfile_dict():
    s = BytesIO()
    x = np.zeros((3, 3))
    y = np.zeros((3, 3))

    np.savez(s, x=x, y=y)
    s.seek(0)

    z = np.load(s)

    assert_('x' in z)
    assert_('y' in z)
    assert_('x' in z.keys())
    assert_('y' in z.keys())

    for f, a in z.items():
        assert_(f in ['x', 'y'])
        assert_equal(a.shape, (3, 3))

    for a in z.values():
        assert_equal(a.shape, (3, 3))

    assert_(len(z.items()) == 2)

    for f in z:
        assert_(f in ['x', 'y'])

    assert_('x' in z.keys())
    assert (z.get('x') == z['x']).all()


@pytest.mark.skipif(not HAS_REFCOUNT, reason="Python lacks refcounts")
def test_load_refcount():
    # Check that objects returned by np.load are directly freed based on
    # their refcount, rather than needing the gc to collect them.

    f = BytesIO()
    np.savez(f, [1, 2, 3])
    f.seek(0)

    with assert_no_gc_cycles():
        np.load(f)

    f.seek(0)
    dt = [("a", 'u1', 2), ("b", 'u1', 2)]
    with assert_no_gc_cycles():
        x = np.loadtxt(TextIO("0 1 2 3"), dtype=dt)
        assert_equal(x, np.array([((0, 1), (2, 3))], dtype=dt))


def test_load_multiple_arrays_until_eof():
    f = BytesIO()
    np.save(f, 1)
    np.save(f, 2)
    f.seek(0)
    out1 = np.load(f)
    assert out1 == 1
    out2 = np.load(f)
    assert out2 == 2
    with pytest.raises(EOFError):
        np.load(f)


def test_savez_nopickle():
    obj_array = np.array([1, 'hello'], dtype=object)
    with temppath(suffix='.npz') as tmp:
        np.savez(tmp, obj_array)

    with temppath(suffix='.npz') as tmp:
        with pytest.raises(ValueError, match="Object arrays cannot be saved when.*"):
            np.savez(tmp, obj_array, allow_pickle=False)

    with temppath(suffix='.npz') as tmp:
        np.savez_compressed(tmp, obj_array)

    with temppath(suffix='.npz') as tmp:
        with pytest.raises(ValueError, match="Object arrays cannot be saved when.*"):
            np.savez_compressed(tmp, obj_array, allow_pickle=False)

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\numpy\lib\tests\test_io.py ===
import gc
import gzip
import locale
import os
import re
import sys
import threading
import time
import warnings
from ctypes import c_bool
from datetime import datetime
from io import BytesIO, StringIO
from multiprocessing import Value, get_context
from pathlib import Path
from tempfile import NamedTemporaryFile

import pytest

import numpy as np
import numpy.ma as ma
from numpy._utils import asbytes
from numpy.exceptions import VisibleDeprecationWarning
from numpy.lib import _npyio_impl
from numpy.lib._iotools import ConversionWarning, ConverterError
from numpy.lib._npyio_impl import recfromcsv, recfromtxt
from numpy.ma.testutils import assert_equal
from numpy.testing import (
    HAS_REFCOUNT,
    IS_PYPY,
    IS_WASM,
    assert_,
    assert_allclose,
    assert_array_equal,
    assert_no_gc_cycles,
    assert_no_warnings,
    assert_raises,
    assert_raises_regex,
    assert_warns,
    break_cycles,
    suppress_warnings,
    tempdir,
    temppath,
)
from numpy.testing._private.utils import requires_memory


class TextIO(BytesIO):
    """Helper IO class.

    Writes encode strings to bytes if needed, reads return bytes.
    This makes it easier to emulate files opened in binary mode
    without needing to explicitly convert strings to bytes in
    setting up the test data.

    """
    def __init__(self, s=""):
        BytesIO.__init__(self, asbytes(s))

    def write(self, s):
        BytesIO.write(self, asbytes(s))

    def writelines(self, lines):
        BytesIO.writelines(self, [asbytes(s) for s in lines])


IS_64BIT = sys.maxsize > 2**32
try:
    import bz2
    HAS_BZ2 = True
except ImportError:
    HAS_BZ2 = False
try:
    import lzma
    HAS_LZMA = True
except ImportError:
    HAS_LZMA = False


def strptime(s, fmt=None):
    """
    This function is available in the datetime module only from Python >=
    2.5.

    """
    if isinstance(s, bytes):
        s = s.decode("latin1")
    return datetime(*time.strptime(s, fmt)[:3])


class RoundtripTest:
    def roundtrip(self, save_func, *args, **kwargs):
        """
        save_func : callable
            Function used to save arrays to file.
        file_on_disk : bool
            If true, store the file on disk, instead of in a
            string buffer.
        save_kwds : dict
            Parameters passed to `save_func`.
        load_kwds : dict
            Parameters passed to `numpy.load`.
        args : tuple of arrays
            Arrays stored to file.

        """
        save_kwds = kwargs.get('save_kwds', {})
        load_kwds = kwargs.get('load_kwds', {"allow_pickle": True})
        file_on_disk = kwargs.get('file_on_disk', False)

        if file_on_disk:
            target_file = NamedTemporaryFile(delete=False)
            load_file = target_file.name
        else:
            target_file = BytesIO()
            load_file = target_file

        try:
            arr = args

            save_func(target_file, *arr, **save_kwds)
            target_file.flush()
            target_file.seek(0)

            if sys.platform == 'win32' and not isinstance(target_file, BytesIO):
                target_file.close()

            arr_reloaded = np.load(load_file, **load_kwds)

            self.arr = arr
            self.arr_reloaded = arr_reloaded
        finally:
            if not isinstance(target_file, BytesIO):
                target_file.close()
                # holds an open file descriptor so it can't be deleted on win
                if 'arr_reloaded' in locals():
                    if not isinstance(arr_reloaded, np.lib.npyio.NpzFile):
                        os.remove(target_file.name)

    def check_roundtrips(self, a):
        self.roundtrip(a)
        self.roundtrip(a, file_on_disk=True)
        self.roundtrip(np.asfortranarray(a))
        self.roundtrip(np.asfortranarray(a), file_on_disk=True)
        if a.shape[0] > 1:
            # neither C nor Fortran contiguous for 2D arrays or more
            self.roundtrip(np.asfortranarray(a)[1:])
            self.roundtrip(np.asfortranarray(a)[1:], file_on_disk=True)

    def test_array(self):
        a = np.array([], float)
        self.check_roundtrips(a)

        a = np.array([[1, 2], [3, 4]], float)
        self.check_roundtrips(a)

        a = np.array([[1, 2], [3, 4]], int)
        self.check_roundtrips(a)

        a = np.array([[1 + 5j, 2 + 6j], [3 + 7j, 4 + 8j]], dtype=np.csingle)
        self.check_roundtrips(a)

        a = np.array([[1 + 5j, 2 + 6j], [3 + 7j, 4 + 8j]], dtype=np.cdouble)
        self.check_roundtrips(a)

    def test_array_object(self):
        a = np.array([], object)
        self.check_roundtrips(a)

        a = np.array([[1, 2], [3, 4]], object)
        self.check_roundtrips(a)

    def test_1D(self):
        a = np.array([1, 2, 3, 4], int)
        self.roundtrip(a)

    @pytest.mark.skipif(sys.platform == 'win32', reason="Fails on Win32")
    def test_mmap(self):
        a = np.array([[1, 2.5], [4, 7.3]])
        self.roundtrip(a, file_on_disk=True, load_kwds={'mmap_mode': 'r'})

        a = np.asfortranarray([[1, 2.5], [4, 7.3]])
        self.roundtrip(a, file_on_disk=True, load_kwds={'mmap_mode': 'r'})

    def test_record(self):
        a = np.array([(1, 2), (3, 4)], dtype=[('x', 'i4'), ('y', 'i4')])
        self.check_roundtrips(a)

    @pytest.mark.slow
    def test_format_2_0(self):
        dt = [(("%d" % i) * 100, float) for i in range(500)]
        a = np.ones(1000, dtype=dt)
        with warnings.catch_warnings(record=True):
            warnings.filterwarnings('always', '', UserWarning)
            self.check_roundtrips(a)


class TestSaveLoad(RoundtripTest):
    def roundtrip(self, *args, **kwargs):
        RoundtripTest.roundtrip(self, np.save, *args, **kwargs)
        assert_equal(self.arr[0], self.arr_reloaded)
        assert_equal(self.arr[0].dtype, self.arr_reloaded.dtype)
        assert_equal(self.arr[0].flags.fnc, self.arr_reloaded.flags.fnc)


class TestSavezLoad(RoundtripTest):
    def roundtrip(self, *args, **kwargs):
        RoundtripTest.roundtrip(self, np.savez, *args, **kwargs)
        try:
            for n, arr in enumerate(self.arr):
                reloaded = self.arr_reloaded['arr_%d' % n]
                assert_equal(arr, reloaded)
                assert_equal(arr.dtype, reloaded.dtype)
                assert_equal(arr.flags.fnc, reloaded.flags.fnc)
        finally:
            # delete tempfile, must be done here on windows
            if self.arr_reloaded.fid:
                self.arr_reloaded.fid.close()
                os.remove(self.arr_reloaded.fid.name)

    @pytest.mark.skipif(IS_PYPY, reason="Hangs on PyPy")
    @pytest.mark.skipif(not IS_64BIT, reason="Needs 64bit platform")
    @pytest.mark.slow
    def test_big_arrays(self):
        L = (1 << 31) + 100000
        a = np.empty(L, dtype=np.uint8)
        with temppath(prefix="numpy_test_big_arrays_", suffix=".npz") as tmp:
            np.savez(tmp, a=a)
            del a
            npfile = np.load(tmp)
            a = npfile['a']  # Should succeed
            npfile.close()

    def test_multiple_arrays(self):
        a = np.array([[1, 2], [3, 4]], float)
        b = np.array([[1 + 2j, 2 + 7j], [3 - 6j, 4 + 12j]], complex)
        self.roundtrip(a, b)

    def test_named_arrays(self):
        a = np.array([[1, 2], [3, 4]], float)
        b = np.array([[1 + 2j, 2 + 7j], [3 - 6j, 4 + 12j]], complex)
        c = BytesIO()
        np.savez(c, file_a=a, file_b=b)
        c.seek(0)
        l = np.load(c)
        assert_equal(a, l['file_a'])
        assert_equal(b, l['file_b'])

    def test_tuple_getitem_raises(self):
        # gh-23748
        a = np.array([1, 2, 3])
        f = BytesIO()
        np.savez(f, a=a)
        f.seek(0)
        l = np.load(f)
        with pytest.raises(KeyError, match="(1, 2)"):
            l[1, 2]

    def test_BagObj(self):
        a = np.array([[1, 2], [3, 4]], float)
        b = np.array([[1 + 2j, 2 + 7j], [3 - 6j, 4 + 12j]], complex)
        c = BytesIO()
        np.savez(c, file_a=a, file_b=b)
        c.seek(0)
        l = np.load(c)
        assert_equal(sorted(dir(l.f)), ['file_a', 'file_b'])
        assert_equal(a, l.f.file_a)
        assert_equal(b, l.f.file_b)

    @pytest.mark.skipif(IS_WASM, reason="Cannot start thread")
    def test_savez_filename_clashes(self):
        # Test that issue #852 is fixed
        # and savez functions in multithreaded environment

        def writer(error_list):
            with temppath(suffix='.npz') as tmp:
                arr = np.random.randn(500, 500)
                try:
                    np.savez(tmp, arr=arr)
                except OSError as err:
                    error_list.append(err)

        errors = []
        threads = [threading.Thread(target=writer, args=(errors,))
                   for j in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        if errors:
            raise AssertionError(errors)

    def test_not_closing_opened_fid(self):
        # Test that issue #2178 is fixed:
        # verify could seek on 'loaded' file
        with temppath(suffix='.npz') as tmp:
            with open(tmp, 'wb') as fp:
                np.savez(fp, data='LOVELY LOAD')
            with open(tmp, 'rb', 10000) as fp:
                fp.seek(0)
                assert_(not fp.closed)
                np.load(fp)['data']
                # fp must not get closed by .load
                assert_(not fp.closed)
                fp.seek(0)
                assert_(not fp.closed)

    @pytest.mark.slow_pypy
    def test_closing_fid(self):
        # Test that issue #1517 (too many opened files) remains closed
        # It might be a "weak" test since failed to get triggered on
        # e.g. Debian sid of 2012 Jul 05 but was reported to
        # trigger the failure on Ubuntu 10.04:
        # http://projects.scipy.org/numpy/ticket/1517#comment:2
        with temppath(suffix='.npz') as tmp:
            np.savez(tmp, data='LOVELY LOAD')
            # We need to check if the garbage collector can properly close
            # numpy npz file returned by np.load when their reference count
            # goes to zero.  Python running in debug mode raises a
            # ResourceWarning when file closing is left to the garbage
            # collector, so we catch the warnings.
            with suppress_warnings() as sup:
                sup.filter(ResourceWarning)  # TODO: specify exact message
                for i in range(1, 1025):
                    try:
                        np.load(tmp)["data"]
                    except Exception as e:
                        msg = f"Failed to load data from a file: {e}"
                        raise AssertionError(msg)
                    finally:
                        if IS_PYPY:
                            gc.collect()

    def test_closing_zipfile_after_load(self):
        # Check that zipfile owns file and can close it.  This needs to
        # pass a file name to load for the test. On windows failure will
        # cause a second error will be raised when the attempt to remove
        # the open file is made.
        prefix = 'numpy_test_closing_zipfile_after_load_'
        with temppath(suffix='.npz', prefix=prefix) as tmp:
            np.savez(tmp, lab='place holder')
            data = np.load(tmp)
            fp = data.zip.fp
            data.close()
            assert_(fp.closed)

    @pytest.mark.parametrize("count, expected_repr", [
        (1, "NpzFile {fname!r} with keys: arr_0"),
        (5, "NpzFile {fname!r} with keys: arr_0, arr_1, arr_2, arr_3, arr_4"),
        # _MAX_REPR_ARRAY_COUNT is 5, so files with more than 5 keys are
        # expected to end in '...'
        (6, "NpzFile {fname!r} with keys: arr_0, arr_1, arr_2, arr_3, arr_4..."),
    ])
    def test_repr_lists_keys(self, count, expected_repr):
        a = np.array([[1, 2], [3, 4]], float)
        with temppath(suffix='.npz') as tmp:
            np.savez(tmp, *[a] * count)
            l = np.load(tmp)
            assert repr(l) == expected_repr.format(fname=tmp)
            l.close()


class TestSaveTxt:
    def test_array(self):
        a = np.array([[1, 2], [3, 4]], float)
        fmt = "%.18e"
        c = BytesIO()
        np.savetxt(c, a, fmt=fmt)
        c.seek(0)
        assert_equal(c.readlines(),
                     [asbytes((fmt + ' ' + fmt + '\n') % (1, 2)),
                      asbytes((fmt + ' ' + fmt + '\n') % (3, 4))])

        a = np.array([[1, 2], [3, 4]], int)
        c = BytesIO()
        np.savetxt(c, a, fmt='%d')
        c.seek(0)
        assert_equal(c.readlines(), [b'1 2\n', b'3 4\n'])

    def test_1D(self):
        a = np.array([1, 2, 3, 4], int)
        c = BytesIO()
        np.savetxt(c, a, fmt='%d')
        c.seek(0)
        lines = c.readlines()
        assert_equal(lines, [b'1\n', b'2\n', b'3\n', b'4\n'])

    def test_0D_3D(self):
        c = BytesIO()
        assert_raises(ValueError, np.savetxt, c, np.array(1))
        assert_raises(ValueError, np.savetxt, c, np.array([[[1], [2]]]))

    def test_structured(self):
        a = np.array([(1, 2), (3, 4)], dtype=[('x', 'i4'), ('y', 'i4')])
        c = BytesIO()
        np.savetxt(c, a, fmt='%d')
        c.seek(0)
        assert_equal(c.readlines(), [b'1 2\n', b'3 4\n'])

    def test_structured_padded(self):
        # gh-13297
        a = np.array([(1, 2, 3), (4, 5, 6)], dtype=[
            ('foo', 'i4'), ('bar', 'i4'), ('baz', 'i4')
        ])
        c = BytesIO()
        np.savetxt(c, a[['foo', 'baz']], fmt='%d')
        c.seek(0)
        assert_equal(c.readlines(), [b'1 3\n', b'4 6\n'])

    def test_multifield_view(self):
        a = np.ones(1, dtype=[('x', 'i4'), ('y', 'i4'), ('z', 'f4')])
        v = a[['x', 'z']]
        with temppath(suffix='.npy') as path:
            path = Path(path)
            np.save(path, v)
            data = np.load(path)
            assert_array_equal(data, v)

    def test_delimiter(self):
        a = np.array([[1., 2.], [3., 4.]])
        c = BytesIO()
        np.savetxt(c, a, delimiter=',', fmt='%d')
        c.seek(0)
        assert_equal(c.readlines(), [b'1,2\n', b'3,4\n'])

    def test_format(self):
        a = np.array([(1, 2), (3, 4)])
        c = BytesIO()
        # Sequence of formats
        np.savetxt(c, a, fmt=['%02d', '%3.1f'])
        c.seek(0)
        assert_equal(c.readlines(), [b'01 2.0\n', b'03 4.0\n'])

        # A single multiformat string
        c = BytesIO()
        np.savetxt(c, a, fmt='%02d : %3.1f')
        c.seek(0)
        lines = c.readlines()
        assert_equal(lines, [b'01 : 2.0\n', b'03 : 4.0\n'])

        # Specify delimiter, should be overridden
        c = BytesIO()
        np.savetxt(c, a, fmt='%02d : %3.1f', delimiter=',')
        c.seek(0)
        lines = c.readlines()
        assert_equal(lines, [b'01 : 2.0\n', b'03 : 4.0\n'])

        # Bad fmt, should raise a ValueError
        c = BytesIO()
        assert_raises(ValueError, np.savetxt, c, a, fmt=99)

    def test_header_footer(self):
        # Test the functionality of the header and footer keyword argument.

        c = BytesIO()
        a = np.array([(1, 2), (3, 4)], dtype=int)
        test_header_footer = 'Test header / footer'
        # Test the header keyword argument
        np.savetxt(c, a, fmt='%1d', header=test_header_footer)
        c.seek(0)
        assert_equal(c.read(),
                     asbytes('# ' + test_header_footer + '\n1 2\n3 4\n'))
        # Test the footer keyword argument
        c = BytesIO()
        np.savetxt(c, a, fmt='%1d', footer=test_header_footer)
        c.seek(0)
        assert_equal(c.read(),
                     asbytes('1 2\n3 4\n# ' + test_header_footer + '\n'))
        # Test the commentstr keyword argument used on the header
        c = BytesIO()
        commentstr = '% '
        np.savetxt(c, a, fmt='%1d',
                   header=test_header_footer, comments=commentstr)
        c.seek(0)
        assert_equal(c.read(),
                     asbytes(commentstr + test_header_footer + '\n' + '1 2\n3 4\n'))
        # Test the commentstr keyword argument used on the footer
        c = BytesIO()
        commentstr = '% '
        np.savetxt(c, a, fmt='%1d',
                   footer=test_header_footer, comments=commentstr)
        c.seek(0)
        assert_equal(c.read(),
                     asbytes('1 2\n3 4\n' + commentstr + test_header_footer + '\n'))

    @pytest.mark.parametrize("filename_type", [Path, str])
    def test_file_roundtrip(self, filename_type):
        with temppath() as name:
            a = np.array([(1, 2), (3, 4)])
            np.savetxt(filename_type(name), a)
            b = np.loadtxt(filename_type(name))
            assert_array_equal(a, b)

    def test_complex_arrays(self):
        ncols = 2
        nrows = 2
        a = np.zeros((ncols, nrows), dtype=np.complex128)
        re = np.pi
        im = np.e
        a[:] = re + 1.0j * im

        # One format only
        c = BytesIO()
        np.savetxt(c, a, fmt=' %+.3e')
        c.seek(0)
        lines = c.readlines()
        assert_equal(
            lines,
            [b' ( +3.142e+00+ +2.718e+00j)  ( +3.142e+00+ +2.718e+00j)\n',
             b' ( +3.142e+00+ +2.718e+00j)  ( +3.142e+00+ +2.718e+00j)\n'])

        # One format for each real and imaginary part
        c = BytesIO()
        np.savetxt(c, a, fmt='  %+.3e' * 2 * ncols)
        c.seek(0)
        lines = c.readlines()
        assert_equal(
            lines,
            [b'  +3.142e+00  +2.718e+00  +3.142e+00  +2.718e+00\n',
             b'  +3.142e+00  +2.718e+00  +3.142e+00  +2.718e+00\n'])

        # One format for each complex number
        c = BytesIO()
        np.savetxt(c, a, fmt=['(%.3e%+.3ej)'] * ncols)
        c.seek(0)
        lines = c.readlines()
        assert_equal(
            lines,
            [b'(3.142e+00+2.718e+00j) (3.142e+00+2.718e+00j)\n',
             b'(3.142e+00+2.718e+00j) (3.142e+00+2.718e+00j)\n'])

    def test_complex_negative_exponent(self):
        # Previous to 1.15, some formats generated x+-yj, gh 7895
        ncols = 2
        nrows = 2
        a = np.zeros((ncols, nrows), dtype=np.complex128)
        re = np.pi
        im = np.e
        a[:] = re - 1.0j * im
        c = BytesIO()
        np.savetxt(c, a, fmt='%.3e')
        c.seek(0)
        lines = c.readlines()
        assert_equal(
            lines,
            [b' (3.142e+00-2.718e+00j)  (3.142e+00-2.718e+00j)\n',
             b' (3.142e+00-2.718e+00j)  (3.142e+00-2.718e+00j)\n'])

    def test_custom_writer(self):

        class CustomWriter(list):
            def write(self, text):
                self.extend(text.split(b'\n'))

        w = CustomWriter()
        a = np.array([(1, 2), (3, 4)])
        np.savetxt(w, a)
        b = np.loadtxt(w)
        assert_array_equal(a, b)

    def test_unicode(self):
        utf8 = b'\xcf\x96'.decode('UTF-8')
        a = np.array([utf8], dtype=np.str_)
        with tempdir() as tmpdir:
            # set encoding as on windows it may not be unicode even on py3
            np.savetxt(os.path.join(tmpdir, 'test.csv'), a, fmt=['%s'],
                       encoding='UTF-8')

    def test_unicode_roundtrip(self):
        utf8 = b'\xcf\x96'.decode('UTF-8')
        a = np.array([utf8], dtype=np.str_)
        # our gz wrapper support encoding
        suffixes = ['', '.gz']
        if HAS_BZ2:
            suffixes.append('.bz2')
        if HAS_LZMA:
            suffixes.extend(['.xz', '.lzma'])
        with tempdir() as tmpdir:
            for suffix in suffixes:
                np.savetxt(os.path.join(tmpdir, 'test.csv' + suffix), a,
                           fmt=['%s'], encoding='UTF-16-LE')
                b = np.loadtxt(os.path.join(tmpdir, 'test.csv' + suffix),
                               encoding='UTF-16-LE', dtype=np.str_)
                assert_array_equal(a, b)

    def test_unicode_bytestream(self):
        utf8 = b'\xcf\x96'.decode('UTF-8')
        a = np.array([utf8], dtype=np.str_)
        s = BytesIO()
        np.savetxt(s, a, fmt=['%s'], encoding='UTF-8')
        s.seek(0)
        assert_equal(s.read().decode('UTF-8'), utf8 + '\n')

    def test_unicode_stringstream(self):
        utf8 = b'\xcf\x96'.decode('UTF-8')
        a = np.array([utf8], dtype=np.str_)
        s = StringIO()
        np.savetxt(s, a, fmt=['%s'], encoding='UTF-8')
        s.seek(0)
        assert_equal(s.read(), utf8 + '\n')

    @pytest.mark.parametrize("iotype", [StringIO, BytesIO])
    def test_unicode_and_bytes_fmt(self, iotype):
        # string type of fmt should not matter, see also gh-4053
        a = np.array([1.])
        s = iotype()
        np.savetxt(s, a, fmt="%f")
        s.seek(0)
        if iotype is StringIO:
            assert_equal(s.read(), "%f\n" % 1.)
        else:
            assert_equal(s.read(), b"%f\n" % 1.)

    @pytest.mark.skipif(sys.platform == 'win32', reason="files>4GB may not work")
    @pytest.mark.slow
    @requires_memory(free_bytes=7e9)
    def test_large_zip(self):
        def check_large_zip(memoryerror_raised):
            memoryerror_raised.value = False
            try:
                # The test takes at least 6GB of memory, writes a file larger
                # than 4GB. This tests the ``allowZip64`` kwarg to ``zipfile``
                test_data = np.asarray([np.random.rand(
                                        np.random.randint(50, 100), 4)
                                        for i in range(800000)], dtype=object)
                with tempdir() as tmpdir:
                    np.savez(os.path.join(tmpdir, 'test.npz'),
                             test_data=test_data)
            except MemoryError:
                memoryerror_raised.value = True
                raise
        # run in a subprocess to ensure memory is released on PyPy, see gh-15775
        # Use an object in shared memory to re-raise the MemoryError exception
        # in our process if needed, see gh-16889
        memoryerror_raised = Value(c_bool)

        # Since Python 3.8, the default start method for multiprocessing has
        # been changed from 'fork' to 'spawn' on macOS, causing inconsistency
        # on memory sharing model, leading to failed test for check_large_zip
        ctx = get_context('fork')
        p = ctx.Process(target=check_large_zip, args=(memoryerror_raised,))
        p.start()
        p.join()
        if memoryerror_raised.value:
            raise MemoryError("Child process raised a MemoryError exception")
        # -9 indicates a SIGKILL, probably an OOM.
        if p.exitcode == -9:
            pytest.xfail("subprocess got a SIGKILL, apparently free memory was not sufficient")
        assert p.exitcode == 0

class LoadTxtBase:
    def check_compressed(self, fopen, suffixes):
        # Test that we can load data from a compressed file
        wanted = np.arange(6).reshape((2, 3))
        linesep = ('\n', '\r\n', '\r')
        for sep in linesep:
            data = '0 1 2' + sep + '3 4 5'
            for suffix in suffixes:
                with temppath(suffix=suffix) as name:
                    with fopen(name, mode='wt', encoding='UTF-32-LE') as f:
                        f.write(data)
                    res = self.loadfunc(name, encoding='UTF-32-LE')
                    assert_array_equal(res, wanted)
                    with fopen(name, "rt",  encoding='UTF-32-LE') as f:
                        res = self.loadfunc(f)
                    assert_array_equal(res, wanted)

    def test_compressed_gzip(self):
        self.check_compressed(gzip.open, ('.gz',))

    @pytest.mark.skipif(not HAS_BZ2, reason="Needs bz2")
    def test_compressed_bz2(self):
        self.check_compressed(bz2.open, ('.bz2',))

    @pytest.mark.skipif(not HAS_LZMA, reason="Needs lzma")
    def test_compressed_lzma(self):
        self.check_compressed(lzma.open, ('.xz', '.lzma'))

    def test_encoding(self):
        with temppath() as path:
            with open(path, "wb") as f:
                f.write('0.\n1.\n2.'.encode("UTF-16"))
            x = self.loadfunc(path, encoding="UTF-16")
            assert_array_equal(x, [0., 1., 2.])

    def test_stringload(self):
        # umlaute
        nonascii = b'\xc3\xb6\xc3\xbc\xc3\xb6'.decode("UTF-8")
        with temppath() as path:
            with open(path, "wb") as f:
                f.write(nonascii.encode("UTF-16"))
            x = self.loadfunc(path, encoding="UTF-16", dtype=np.str_)
            assert_array_equal(x, nonascii)

    def test_binary_decode(self):
        utf16 = b'\xff\xfeh\x04 \x00i\x04 \x00j\x04'
        v = self.loadfunc(BytesIO(utf16), dtype=np.str_, encoding='UTF-16')
        assert_array_equal(v, np.array(utf16.decode('UTF-16').split()))

    def test_converters_decode(self):
        # test converters that decode strings
        c = TextIO()
        c.write(b'\xcf\x96')
        c.seek(0)
        x = self.loadfunc(c, dtype=np.str_, encoding="bytes",
                          converters={0: lambda x: x.decode('UTF-8')})
        a = np.array([b'\xcf\x96'.decode('UTF-8')])
        assert_array_equal(x, a)

    def test_converters_nodecode(self):
        # test native string converters enabled by setting an encoding
        utf8 = b'\xcf\x96'.decode('UTF-8')
        with temppath() as path:
            with open(path, 'wt', encoding='UTF-8') as f:
                f.write(utf8)
            x = self.loadfunc(path, dtype=np.str_,
                              converters={0: lambda x: x + 't'},
                              encoding='UTF-8')
            a = np.array([utf8 + 't'])
            assert_array_equal(x, a)


class TestLoadTxt(LoadTxtBase):
    loadfunc = staticmethod(np.loadtxt)

    def setup_method(self):
        # lower chunksize for testing
        self.orig_chunk = _npyio_impl._loadtxt_chunksize
        _npyio_impl._loadtxt_chunksize = 1

    def teardown_method(self):
        _npyio_impl._loadtxt_chunksize = self.orig_chunk

    def test_record(self):
        c = TextIO()
        c.write('1 2\n3 4')
        c.seek(0)
        x = np.loadtxt(c, dtype=[('x', np.int32), ('y', np.int32)])
        a = np.array([(1, 2), (3, 4)], dtype=[('x', 'i4'), ('y', 'i4')])
        assert_array_equal(x, a)

        d = TextIO()
        d.write('M 64 75.0\nF 25 60.0')
        d.seek(0)
        mydescriptor = {'names': ('gender', 'age', 'weight'),
                        'formats': ('S1', 'i4', 'f4')}
        b = np.array([('M', 64.0, 75.0),
                      ('F', 25.0, 60.0)], dtype=mydescriptor)
        y = np.loadtxt(d, dtype=mydescriptor)
        assert_array_equal(y, b)

    def test_array(self):
        c = TextIO()
        c.write('1 2\n3 4')

        c.seek(0)
        x = np.loadtxt(c, dtype=int)
        a = np.array([[1, 2], [3, 4]], int)
        assert_array_equal(x, a)

        c.seek(0)
        x = np.loadtxt(c, dtype=float)
        a = np.array([[1, 2], [3, 4]], float)
        assert_array_equal(x, a)

    def test_1D(self):
        c = TextIO()
        c.write('1\n2\n3\n4\n')
        c.seek(0)
        x = np.loadtxt(c, dtype=int)
        a = np.array([1, 2, 3, 4], int)
        assert_array_equal(x, a)

        c = TextIO()
        c.write('1,2,3,4\n')
        c.seek(0)
        x = np.loadtxt(c, dtype=int, delimiter=',')
        a = np.array([1, 2, 3, 4], int)
        assert_array_equal(x, a)

    def test_missing(self):
        c = TextIO()
        c.write('1,2,3,,5\n')
        c.seek(0)
        x = np.loadtxt(c, dtype=int, delimiter=',',
                       converters={3: lambda s: int(s or - 999)})
        a = np.array([1, 2, 3, -999, 5], int)
        assert_array_equal(x, a)

    def test_converters_with_usecols(self):
        c = TextIO()
        c.write('1,2,3,,5\n6,7,8,9,10\n')
        c.seek(0)
        x = np.loadtxt(c, dtype=int, delimiter=',',
                       converters={3: lambda s: int(s or - 999)},
                       usecols=(1, 3,))
        a = np.array([[2, -999], [7, 9]], int)
        assert_array_equal(x, a)

    def test_comments_unicode(self):
        c = TextIO()
        c.write('# comment\n1,2,3,5\n')
        c.seek(0)
        x = np.loadtxt(c, dtype=int, delimiter=',',
                       comments='#')
        a = np.array([1, 2, 3, 5], int)
        assert_array_equal(x, a)

    def test_comments_byte(self):
        c = TextIO()
        c.write('# comment\n1,2,3,5\n')
        c.seek(0)
        x = np.loadtxt(c, dtype=int, delimiter=',',
                       comments=b'#')
        a = np.array([1, 2, 3, 5], int)
        assert_array_equal(x, a)

    def test_comments_multiple(self):
        c = TextIO()
        c.write('# comment\n1,2,3\n@ comment2\n4,5,6 // comment3')
        c.seek(0)
        x = np.loadtxt(c, dtype=int, delimiter=',',
                       comments=['#', '@', '//'])
        a = np.array([[1, 2, 3], [4, 5, 6]], int)
        assert_array_equal(x, a)

    @pytest.mark.skipif(IS_PYPY and sys.implementation.version <= (7, 3, 8),
                        reason="PyPy bug in error formatting")
    def test_comments_multi_chars(self):
        c = TextIO()
        c.write('/* comment\n1,2,3,5\n')
        c.seek(0)
        x = np.loadtxt(c, dtype=int, delimiter=',',
                       comments='/*')
        a = np.array([1, 2, 3, 5], int)
        assert_array_equal(x, a)

        # Check that '/*' is not transformed to ['/', '*']
        c = TextIO()
        c.write('*/ comment\n1,2,3,5\n')
        c.seek(0)
        assert_raises(ValueError, np.loadtxt, c, dtype=int, delimiter=',',
                      comments='/*')

    def test_skiprows(self):
        c = TextIO()
        c.write('comment\n1,2,3,5\n')
        c.seek(0)
        x = np.loadtxt(c, dtype=int, delimiter=',',
                       skiprows=1)
        a = np.array([1, 2, 3, 5], int)
        assert_array_equal(x, a)

        c = TextIO()
        c.write('# comment\n1,2,3,5\n')
        c.seek(0)
        x = np.loadtxt(c, dtype=int, delimiter=',',
                       skiprows=1)
        a = np.array([1, 2, 3, 5], int)
        assert_array_equal(x, a)

    def test_usecols(self):
        a = np.array([[1, 2], [3, 4]], float)
        c = BytesIO()
        np.savetxt(c, a)
        c.seek(0)
        x = np.loadtxt(c, dtype=float, usecols=(1,))
        assert_array_equal(x, a[:, 1])

        a = np.array([[1, 2, 3], [3, 4, 5]], float)
        c = BytesIO()
        np.savetxt(c, a)
        c.seek(0)
        x = np.loadtxt(c, dtype=float, usecols=(1, 2))
        assert_array_equal(x, a[:, 1:])

        # Testing with arrays instead of tuples.
        c.seek(0)
        x = np.loadtxt(c, dtype=float, usecols=np.array([1, 2]))
        assert_array_equal(x, a[:, 1:])

        # Testing with an integer instead of a sequence
        for int_type in [int, np.int8, np.int16,
                         np.int32, np.int64, np.uint8, np.uint16,
                         np.uint32, np.uint64]:
            to_read = int_type(1)
            c.seek(0)
            x = np.loadtxt(c, dtype=float, usecols=to_read)
            assert_array_equal(x, a[:, 1])

        # Testing with some crazy custom integer type
        class CrazyInt:
            def __index__(self):
                return 1

        crazy_int = CrazyInt()
        c.seek(0)
        x = np.loadtxt(c, dtype=float, usecols=crazy_int)
        assert_array_equal(x, a[:, 1])

        c.seek(0)
        x = np.loadtxt(c, dtype=float, usecols=(crazy_int,))
        assert_array_equal(x, a[:, 1])

        # Checking with dtypes defined converters.
        data = '''JOE 70.1 25.3
                BOB 60.5 27.9
                '''
        c = TextIO(data)
        names = ['stid', 'temp']
        dtypes = ['S4', 'f8']
        arr = np.loadtxt(c, usecols=(0, 2), dtype=list(zip(names, dtypes)))
        assert_equal(arr['stid'], [b"JOE", b"BOB"])
        assert_equal(arr['temp'], [25.3, 27.9])

        # Testing non-ints in usecols
        c.seek(0)
        bogus_idx = 1.5
        assert_raises_regex(
            TypeError,
            f'^usecols must be.*{type(bogus_idx).__name__}',
            np.loadtxt, c, usecols=bogus_idx
            )

        assert_raises_regex(
            TypeError,
            f'^usecols must be.*{type(bogus_idx).__name__}',
            np.loadtxt, c, usecols=[0, bogus_idx, 0]
            )

    def test_bad_usecols(self):
        with pytest.raises(OverflowError):
            np.loadtxt(["1\n"], usecols=[2**64], delimiter=",")
        with pytest.raises((ValueError, OverflowError)):
            # Overflow error on 32bit platforms
            np.loadtxt(["1\n"], usecols=[2**62], delimiter=",")
        with pytest.raises(TypeError,
                match="If a structured dtype .*. But 1 usecols were given and "
                      "the number of fields is 3."):
            np.loadtxt(["1,1\n"], dtype="i,2i", usecols=[0], delimiter=",")

    def test_fancy_dtype(self):
        c = TextIO()
        c.write('1,2,3.0\n4,5,6.0\n')
        c.seek(0)
        dt = np.dtype([('x', int), ('y', [('t', int), ('s', float)])])
        x = np.loadtxt(c, dtype=dt, delimiter=',')
        a = np.array([(1, (2, 3.0)), (4, (5, 6.0))], dt)
        assert_array_equal(x, a)

    def test_shaped_dtype(self):
        c = TextIO("aaaa  1.0  8.0  1 2 3 4 5 6")
        dt = np.dtype([('name', 'S4'), ('x', float), ('y', float),
                       ('block', int, (2, 3))])
        x = np.loadtxt(c, dtype=dt)
        a = np.array([('aaaa', 1.0, 8.0, [[1, 2, 3], [4, 5, 6]])],
                     dtype=dt)
        assert_array_equal(x, a)

    def test_3d_shaped_dtype(self):
        c = TextIO("aaaa  1.0  8.0  1 2 3 4 5 6 7 8 9 10 11 12")
        dt = np.dtype([('name', 'S4'), ('x', float), ('y', float),
                       ('block', int, (2, 2, 3))])
        x = np.loadtxt(c, dtype=dt)
        a = np.array([('aaaa', 1.0, 8.0,
                       [[[1, 2, 3], [4, 5, 6]], [[7, 8, 9], [10, 11, 12]]])],
                     dtype=dt)
        assert_array_equal(x, a)

    def test_str_dtype(self):
        # see gh-8033
        c = ["str1", "str2"]

        for dt in (str, np.bytes_):
            a = np.array(["str1", "str2"], dtype=dt)
            x = np.loadtxt(c, dtype=dt)
            assert_array_equal(x, a)

    def test_empty_file(self):
        with pytest.warns(UserWarning, match="input contained no data"):
            c = TextIO()
            x = np.loadtxt(c)
            assert_equal(x.shape, (0,))
            x = np.loadtxt(c, dtype=np.int64)
            assert_equal(x.shape, (0,))
            assert_(x.dtype == np.int64)

    def test_unused_converter(self):
        c = TextIO()
        c.writelines(['1 21\n', '3 42\n'])
        c.seek(0)
        data = np.loadtxt(c, usecols=(1,),
                          converters={0: lambda s: int(s, 16)})
        assert_array_equal(data, [21, 42])

        c.seek(0)
        data = np.loadtxt(c, usecols=(1,),
                          converters={1: lambda s: int(s, 16)})
        assert_array_equal(data, [33, 66])

    def test_dtype_with_object(self):
        # Test using an explicit dtype with an object
        data = """ 1; 2001-01-01
                   2; 2002-01-31 """
        ndtype = [('idx', int), ('code', object)]
        func = lambda s: strptime(s.strip(), "%Y-%m-%d")
        converters = {1: func}
        test = np.loadtxt(TextIO(data), delimiter=";", dtype=ndtype,
                          converters=converters)
        control = np.array(
            [(1, datetime(2001, 1, 1)), (2, datetime(2002, 1, 31))],
            dtype=ndtype)
        assert_equal(test, control)

    def test_uint64_type(self):
        tgt = (9223372043271415339, 9223372043271415853)
        c = TextIO()
        c.write("%s %s" % tgt)
        c.seek(0)
        res = np.loadtxt(c, dtype=np.uint64)
        assert_equal(res, tgt)

    def test_int64_type(self):
        tgt = (-9223372036854775807, 9223372036854775807)
        c = TextIO()
        c.write("%s %s" % tgt)
        c.seek(0)
        res = np.loadtxt(c, dtype=np.int64)
        assert_equal(res, tgt)

    def test_from_float_hex(self):
        # IEEE doubles and floats only, otherwise the float32
        # conversion may fail.
        tgt = np.logspace(-10, 10, 5).astype(np.float32)
        tgt = np.hstack((tgt, -tgt)).astype(float)
        inp = '\n'.join(map(float.hex, tgt))
        c = TextIO()
        c.write(inp)
        for dt in [float, np.float32]:
            c.seek(0)
            res = np.loadtxt(
                c, dtype=dt, converters=float.fromhex, encoding="latin1")
            assert_equal(res, tgt, err_msg=f"{dt}")

    @pytest.mark.skipif(IS_PYPY and sys.implementation.version <= (7, 3, 8),
                        reason="PyPy bug in error formatting")
    def test_default_float_converter_no_default_hex_conversion(self):
        """
        Ensure that fromhex is only used for values with the correct prefix and
        is not called by default. Regression test related to gh-19598.
        """
        c = TextIO("a b c")
        with pytest.raises(ValueError,
                match=".*convert string 'a' to float64 at row 0, column 1"):
            np.loadtxt(c)

    @pytest.mark.skipif(IS_PYPY and sys.implementation.version <= (7, 3, 8),
                        reason="PyPy bug in error formatting")
    def test_default_float_converter_exception(self):
        """
        Ensure that the exception message raised during failed floating point
        conversion is correct. Regression test related to gh-19598.
        """
        c = TextIO("qrs tuv")  # Invalid values for default float converter
        with pytest.raises(ValueError,
                match="could not convert string 'qrs' to float64"):
            np.loadtxt(c)

    def test_from_complex(self):
        tgt = (complex(1, 1), complex(1, -1))
        c = TextIO()
        c.write("%s %s" % tgt)
        c.seek(0)
        res = np.loadtxt(c, dtype=complex)
        assert_equal(res, tgt)

    def test_complex_misformatted(self):
        # test for backward compatibility
        # some complex formats used to generate x+-yj
        a = np.zeros((2, 2), dtype=np.complex128)
        re = np.pi
        im = np.e
        a[:] = re - 1.0j * im
        c = BytesIO()
        np.savetxt(c, a, fmt='%.16e')
        c.seek(0)
        txt = c.read()
        c.seek(0)
        # misformat the sign on the imaginary part, gh 7895
        txt_bad = txt.replace(b'e+00-', b'e00+-')
        assert_(txt_bad != txt)
        c.write(txt_bad)
        c.seek(0)
        res = np.loadtxt(c, dtype=complex)
        assert_equal(res, a)

    def test_universal_newline(self):
        with temppath() as name:
            with open(name, 'w') as f:
                f.write('1 21\r3 42\r')
            data = np.loadtxt(name)
        assert_array_equal(data, [[1, 21], [3, 42]])

    def test_empty_field_after_tab(self):
        c = TextIO()
        c.write('1 \t2 \t3\tstart \n4\t5\t6\t  \n7\t8\t9.5\t')
        c.seek(0)
        dt = {'names': ('x', 'y', 'z', 'comment'),
              'formats': ('<i4', '<i4', '<f4', '|S8')}
        x = np.loadtxt(c, dtype=dt, delimiter='\t')
        a = np.array([b'start ', b'  ', b''])
        assert_array_equal(x['comment'], a)

    def test_unpack_structured(self):
        txt = TextIO("M 21 72\nF 35 58")
        dt = {'names': ('a', 'b', 'c'), 'formats': ('|S1', '<i4', '<f4')}
        a, b, c = np.loadtxt(txt, dtype=dt, unpack=True)
        assert_(a.dtype.str == '|S1')
        assert_(b.dtype.str == '<i4')
        assert_(c.dtype.str == '<f4')
        assert_array_equal(a, np.array([b'M', b'F']))
        assert_array_equal(b, np.array([21, 35]))
        assert_array_equal(c, np.array([72.,  58.]))

    def test_ndmin_keyword(self):
        c = TextIO()
        c.write('1,2,3\n4,5,6')
        c.seek(0)
        assert_raises(ValueError, np.loadtxt, c, ndmin=3)
        c.seek(0)
        assert_raises(ValueError, np.loadtxt, c, ndmin=1.5)
        c.seek(0)
        x = np.loadtxt(c, dtype=int, delimiter=',', ndmin=1)
        a = np.array([[1, 2, 3], [4, 5, 6]])
        assert_array_equal(x, a)

        d = TextIO()
        d.write('0,1,2')
        d.seek(0)
        x = np.loadtxt(d, dtype=int, delimiter=',', ndmin=2)
        assert_(x.shape == (1, 3))
        d.seek(0)
        x = np.loadtxt(d, dtype=int, delimiter=',', ndmin=1)
        assert_(x.shape == (3,))
        d.seek(0)
        x = np.loadtxt(d, dtype=int, delimiter=',', ndmin=0)
        assert_(x.shape == (3,))

        e = TextIO()
        e.write('0\n1\n2')
        e.seek(0)
        x = np.loadtxt(e, dtype=int, delimiter=',', ndmin=2)
        assert_(x.shape == (3, 1))
        e.seek(0)
        x = np.loadtxt(e, dtype=int, delimiter=',', ndmin=1)
        assert_(x.shape == (3,))
        e.seek(0)
        x = np.loadtxt(e, dtype=int, delimiter=',', ndmin=0)
        assert_(x.shape == (3,))

        # Test ndmin kw with empty file.
        with pytest.warns(UserWarning, match="input contained no data"):
            f = TextIO()
            assert_(np.loadtxt(f, ndmin=2).shape == (0, 1,))
            assert_(np.loadtxt(f, ndmin=1).shape == (0,))

    def test_generator_source(self):
        def count():
            for i in range(10):
                yield "%d" % i

        res = np.loadtxt(count())
        assert_array_equal(res, np.arange(10))

    def test_bad_line(self):
        c = TextIO()
        c.write('1 2 3\n4 5 6\n2 3')
        c.seek(0)

        # Check for exception and that exception contains line number
        assert_raises_regex(ValueError, "3", np.loadtxt, c)

    def test_none_as_string(self):
        # gh-5155, None should work as string when format demands it
        c = TextIO()
        c.write('100,foo,200\n300,None,400')
        c.seek(0)
        dt = np.dtype([('x', int), ('a', 'S10'), ('y', int)])
        np.loadtxt(c, delimiter=',', dtype=dt, comments=None)  # Should succeed

    @pytest.mark.skipif(locale.getpreferredencoding() == 'ANSI_X3.4-1968',
                        reason="Wrong preferred encoding")
    def test_binary_load(self):
        butf8 = b"5,6,7,\xc3\x95scarscar\r\n15,2,3,hello\r\n"\
                b"20,2,3,\xc3\x95scar\r\n"
        sutf8 = butf8.decode("UTF-8").replace("\r", "").splitlines()
        with temppath() as path:
            with open(path, "wb") as f:
                f.write(butf8)
            with open(path, "rb") as f:
                x = np.loadtxt(f, encoding="UTF-8", dtype=np.str_)
            assert_array_equal(x, sutf8)
            # test broken latin1 conversion people now rely on
            with open(path, "rb") as f:
                x = np.loadtxt(f, encoding="UTF-8", dtype="S")
            x = [b'5,6,7,\xc3\x95scarscar', b'15,2,3,hello', b'20,2,3,\xc3\x95scar']
            assert_array_equal(x, np.array(x, dtype="S"))

    def test_max_rows(self):
        c = TextIO()
        c.write('1,2,3,5\n4,5,7,8\n2,1,4,5')
        c.seek(0)
        x = np.loadtxt(c, dtype=int, delimiter=',',
                       max_rows=1)
        a = np.array([1, 2, 3, 5], int)
        assert_array_equal(x, a)

    def test_max_rows_with_skiprows(self):
        c = TextIO()
        c.write('comments\n1,2,3,5\n4,5,7,8\n2,1,4,5')
        c.seek(0)
        x = np.loadtxt(c, dtype=int, delimiter=',',
                       skiprows=1, max_rows=1)
        a = np.array([1, 2, 3, 5], int)
        assert_array_equal(x, a)

        c = TextIO()
        c.write('comment\n1,2,3,5\n4,5,7,8\n2,1,4,5')
        c.seek(0)
        x = np.loadtxt(c, dtype=int, delimiter=',',
                       skiprows=1, max_rows=2)
        a = np.array([[1, 2, 3, 5], [4, 5, 7, 8]], int)
        assert_array_equal(x, a)

    def test_max_rows_with_read_continuation(self):
        c = TextIO()
        c.write('1,2,3,5\n4,5,7,8\n2,1,4,5')
        c.seek(0)
        x = np.loadtxt(c, dtype=int, delimiter=',',
                       max_rows=2)
        a = np.array([[1, 2, 3, 5], [4, 5, 7, 8]], int)
        assert_array_equal(x, a)
        # test continuation
        x = np.loadtxt(c, dtype=int, delimiter=',')
        a = np.array([2, 1, 4, 5], int)
        assert_array_equal(x, a)

    def test_max_rows_larger(self):
        #test max_rows > num rows
        c = TextIO()
        c.write('comment\n1,2,3,5\n4,5,7,8\n2,1,4,5')
        c.seek(0)
        x = np.loadtxt(c, dtype=int, delimiter=',',
                       skiprows=1, max_rows=6)
        a = np.array([[1, 2, 3, 5], [4, 5, 7, 8], [2, 1, 4, 5]], int)
        assert_array_equal(x, a)

    @pytest.mark.parametrize(["skip", "data"], [
            (1, ["ignored\n", "1,2\n", "\n", "3,4\n"]),
            # "Bad" lines that do not end in newlines:
            (1, ["ignored", "1,2", "", "3,4"]),
            (1, StringIO("ignored\n1,2\n\n3,4")),
            # Same as above, but do not skip any lines:
            (0, ["-1,0\n", "1,2\n", "\n", "3,4\n"]),
            (0, ["-1,0", "1,2", "", "3,4"]),
            (0, StringIO("-1,0\n1,2\n\n3,4"))])
    def test_max_rows_empty_lines(self, skip, data):
        with pytest.warns(UserWarning,
                    match=f"Input line 3.*max_rows={3 - skip}"):
            res = np.loadtxt(data, dtype=int, skiprows=skip, delimiter=",",
                             max_rows=3 - skip)
            assert_array_equal(res, [[-1, 0], [1, 2], [3, 4]][skip:])

        if isinstance(data, StringIO):
            data.seek(0)

        with warnings.catch_warnings():
            warnings.simplefilter("error", UserWarning)
            with pytest.raises(UserWarning):
                np.loadtxt(data, dtype=int, skiprows=skip, delimiter=",",
                           max_rows=3 - skip)

class Testfromregex:
    def test_record(self):
        c = TextIO()
        c.write('1.312 foo\n1.534 bar\n4.444 qux')
        c.seek(0)

        dt = [('num', np.float64), ('val', 'S3')]
        x = np.fromregex(c, r"([0-9.]+)\s+(...)", dt)
        a = np.array([(1.312, 'foo'), (1.534, 'bar'), (4.444, 'qux')],
                     dtype=dt)
        assert_array_equal(x, a)

    def test_record_2(self):
        c = TextIO()
        c.write('1312 foo\n1534 bar\n4444 qux')
        c.seek(0)

        dt = [('num', np.int32), ('val', 'S3')]
        x = np.fromregex(c, r"(\d+)\s+(...)", dt)
        a = np.array([(1312, 'foo'), (1534, 'bar'), (4444, 'qux')],
                     dtype=dt)
        assert_array_equal(x, a)

    def test_record_3(self):
        c = TextIO()
        c.write('1312 foo\n1534 bar\n4444 qux')
        c.seek(0)

        dt = [('num', np.float64)]
        x = np.fromregex(c, r"(\d+)\s+...", dt)
        a = np.array([(1312,), (1534,), (4444,)], dtype=dt)
        assert_array_equal(x, a)

    @pytest.mark.parametrize("path_type", [str, Path])
    def test_record_unicode(self, path_type):
        utf8 = b'\xcf\x96'
        with temppath() as str_path:
            path = path_type(str_path)
            with open(path, 'wb') as f:
                f.write(b'1.312 foo' + utf8 + b' \n1.534 bar\n4.444 qux')

            dt = [('num', np.float64), ('val', 'U4')]
            x = np.fromregex(path, r"(?u)([0-9.]+)\s+(\w+)", dt, encoding='UTF-8')
            a = np.array([(1.312, 'foo' + utf8.decode('UTF-8')), (1.534, 'bar'),
                           (4.444, 'qux')], dtype=dt)
            assert_array_equal(x, a)

            regexp = re.compile(r"([0-9.]+)\s+(\w+)", re.UNICODE)
            x = np.fromregex(path, regexp, dt, encoding='UTF-8')
            assert_array_equal(x, a)

    def test_compiled_bytes(self):
        regexp = re.compile(br'(\d)')
        c = BytesIO(b'123')
        dt = [('num', np.float64)]
        a = np.array([1, 2, 3], dtype=dt)
        x = np.fromregex(c, regexp, dt)
        assert_array_equal(x, a)

    def test_bad_dtype_not_structured(self):
        regexp = re.compile(br'(\d)')
        c = BytesIO(b'123')
        with pytest.raises(TypeError, match='structured datatype'):
            np.fromregex(c, regexp, dtype=np.float64)


#####--------------------------------------------------------------------------


class TestFromTxt(LoadTxtBase):
    loadfunc = staticmethod(np.genfromtxt)

    def test_record(self):
        # Test w/ explicit dtype
        data = TextIO('1 2\n3 4')
        test = np.genfromtxt(data, dtype=[('x', np.int32), ('y', np.int32)])
        control = np.array([(1, 2), (3, 4)], dtype=[('x', 'i4'), ('y', 'i4')])
        assert_equal(test, control)
        #
        data = TextIO('M 64.0 75.0\nF 25.0 60.0')
        descriptor = {'names': ('gender', 'age', 'weight'),
                      'formats': ('S1', 'i4', 'f4')}
        control = np.array([('M', 64.0, 75.0), ('F', 25.0, 60.0)],
                           dtype=descriptor)
        test = np.genfromtxt(data, dtype=descriptor)
        assert_equal(test, control)

    def test_array(self):
        # Test outputting a standard ndarray
        data = TextIO('1 2\n3 4')
        control = np.array([[1, 2], [3, 4]], dtype=int)
        test = np.genfromtxt(data, dtype=int)
        assert_array_equal(test, control)
        #
        data.seek(0)
        control = np.array([[1, 2], [3, 4]], dtype=float)
        test = np.loadtxt(data, dtype=float)
        assert_array_equal(test, control)

    def test_1D(self):
        # Test squeezing to 1D
        control = np.array([1, 2, 3, 4], int)
        #
        data = TextIO('1\n2\n3\n4\n')
        test = np.genfromtxt(data, dtype=int)
        assert_array_equal(test, control)
        #
        data = TextIO('1,2,3,4\n')
        test = np.genfromtxt(data, dtype=int, delimiter=',')
        assert_array_equal(test, control)

    def test_comments(self):
        # Test the stripping of comments
        control = np.array([1, 2, 3, 5], int)
        # Comment on its own line
        data = TextIO('# comment\n1,2,3,5\n')
        test = np.genfromtxt(data, dtype=int, delimiter=',', comments='#')
        assert_equal(test, control)
        # Comment at the end of a line
        data = TextIO('1,2,3,5# comment\n')
        test = np.genfromtxt(data, dtype=int, delimiter=',', comments='#')
        assert_equal(test, control)

    def test_skiprows(self):
        # Test row skipping
        control = np.array([1, 2, 3, 5], int)
        kwargs = {"dtype": int, "delimiter": ','}
        #
        data = TextIO('comment\n1,2,3,5\n')
        test = np.genfromtxt(data, skip_header=1, **kwargs)
        assert_equal(test, control)
        #
        data = TextIO('# comment\n1,2,3,5\n')
        test = np.loadtxt(data, skiprows=1, **kwargs)
        assert_equal(test, control)

    def test_skip_footer(self):
        data = [f"# {i}" for i in range(1, 6)]
        data.append("A, B, C")
        data.extend([f"{i},{i:3.1f},{i:03d}" for i in range(51)])
        data[-1] = "99,99"
        kwargs = {"delimiter": ",", "names": True, "skip_header": 5, "skip_footer": 10}
        test = np.genfromtxt(TextIO("\n".join(data)), **kwargs)
        ctrl = np.array([(f"{i:f}", f"{i:f}", f"{i:f}") for i in range(41)],
                        dtype=[(_, float) for _ in "ABC"])
        assert_equal(test, ctrl)

    def test_skip_footer_with_invalid(self):
        with suppress_warnings() as sup:
            sup.filter(ConversionWarning)
            basestr = '1 1\n2 2\n3 3\n4 4\n5  \n6  \n7  \n'
            # Footer too small to get rid of all invalid values
            assert_raises(ValueError, np.genfromtxt,
                          TextIO(basestr), skip_footer=1)
    #        except ValueError:
    #            pass
            a = np.genfromtxt(
                TextIO(basestr), skip_footer=1, invalid_raise=False)
            assert_equal(a, np.array([[1., 1.], [2., 2.], [3., 3.], [4., 4.]]))
            #
            a = np.genfromtxt(TextIO(basestr), skip_footer=3)
            assert_equal(a, np.array([[1., 1.], [2., 2.], [3., 3.], [4., 4.]]))
            #
            basestr = '1 1\n2  \n3 3\n4 4\n5  \n6 6\n7 7\n'
            a = np.genfromtxt(
                TextIO(basestr), skip_footer=1, invalid_raise=False)
            assert_equal(a, np.array([[1., 1.], [3., 3.], [4., 4.], [6., 6.]]))
            a = np.genfromtxt(
                TextIO(basestr), skip_footer=3, invalid_raise=False)
            assert_equal(a, np.array([[1., 1.], [3., 3.], [4., 4.]]))

    def test_header(self):
        # Test retrieving a header
        data = TextIO('gender age weight\nM 64.0 75.0\nF 25.0 60.0')
        with warnings.catch_warnings(record=True) as w:
            warnings.filterwarnings('always', '', VisibleDeprecationWarning)
            test = np.genfromtxt(data, dtype=None, names=True,
                                 encoding='bytes')
            assert_(w[0].category is VisibleDeprecationWarning)
        control = {'gender': np.array([b'M', b'F']),
                   'age': np.array([64.0, 25.0]),
                   'weight': np.array([75.0, 60.0])}
        assert_equal(test['gender'], control['gender'])
        assert_equal(test['age'], control['age'])
        assert_equal(test['weight'], control['weight'])

    def test_auto_dtype(self):
        # Test the automatic definition of the output dtype
        data = TextIO('A 64 75.0 3+4j True\nBCD 25 60.0 5+6j False')
        with warnings.catch_warnings(record=True) as w:
            warnings.filterwarnings('always', '', VisibleDeprecationWarning)
            test = np.genfromtxt(data, dtype=None, encoding='bytes')
            assert_(w[0].category is VisibleDeprecationWarning)
        control = [np.array([b'A', b'BCD']),
                   np.array([64, 25]),
                   np.array([75.0, 60.0]),
                   np.array([3 + 4j, 5 + 6j]),
                   np.array([True, False]), ]
        assert_equal(test.dtype.names, ['f0', 'f1', 'f2', 'f3', 'f4'])
        for (i, ctrl) in enumerate(control):
            assert_equal(test[f'f{i}'], ctrl)

    def test_auto_dtype_uniform(self):
        # Tests whether the output dtype can be uniformized
        data = TextIO('1 2 3 4\n5 6 7 8\n')
        test = np.genfromtxt(data, dtype=None)
        control = np.array([[1, 2, 3, 4], [5, 6, 7, 8]])
        assert_equal(test, control)

    def test_fancy_dtype(self):
        # Check that a nested dtype isn't MIA
        data = TextIO('1,2,3.0\n4,5,6.0\n')
        fancydtype = np.dtype([('x', int), ('y', [('t', int), ('s', float)])])
        test = np.genfromtxt(data, dtype=fancydtype, delimiter=',')
        control = np.array([(1, (2, 3.0)), (4, (5, 6.0))], dtype=fancydtype)
        assert_equal(test, control)

    def test_names_overwrite(self):
        # Test overwriting the names of the dtype
        descriptor = {'names': ('g', 'a', 'w'),
                      'formats': ('S1', 'i4', 'f4')}
        data = TextIO(b'M 64.0 75.0\nF 25.0 60.0')
        names = ('gender', 'age', 'weight')
        test = np.genfromtxt(data, dtype=descriptor, names=names)
        descriptor['names'] = names
        control = np.array([('M', 64.0, 75.0),
                            ('F', 25.0, 60.0)], dtype=descriptor)
        assert_equal(test, control)

    def test_bad_fname(self):
        with pytest.raises(TypeError, match='fname must be a string,'):
            np.genfromtxt(123)

    def test_commented_header(self):
        # Check that names can be retrieved even if the line is commented out.
        data = TextIO("""
#gender age weight
M   21  72.100000
F   35  58.330000
M   33  21.99
        """)
        # The # is part of the first name and should be deleted automatically.
        with warnings.catch_warnings(record=True) as w:
            warnings.filterwarnings('always', '', VisibleDeprecationWarning)
            test = np.genfromtxt(data, names=True, dtype=None,
                                 encoding="bytes")
            assert_(w[0].category is VisibleDeprecationWarning)
        ctrl = np.array([('M', 21, 72.1), ('F', 35, 58.33), ('M', 33, 21.99)],
                        dtype=[('gender', '|S1'), ('age', int), ('weight', float)])
        assert_equal(test, ctrl)
        # Ditto, but we should get rid of the first element
        data = TextIO(b"""
# gender age weight
M   21  72.100000
F   35  58.330000
M   33  21.99
        """)
        with warnings.catch_warnings(record=True) as w:
            warnings.filterwarnings('always', '', VisibleDeprecationWarning)
            test = np.genfromtxt(data, names=True, dtype=None,
                                 encoding="bytes")
            assert_(w[0].category is VisibleDeprecationWarning)
        assert_equal(test, ctrl)

    def test_names_and_comments_none(self):
        # Tests case when names is true but comments is None (gh-10780)
        data = TextIO('col1 col2\n 1 2\n 3 4')
        test = np.genfromtxt(data, dtype=(int, int), comments=None, names=True)
        control = np.array([(1, 2), (3, 4)], dtype=[('col1', int), ('col2', int)])
        assert_equal(test, control)

    def test_file_is_closed_on_error(self):
        # gh-13200
        with tempdir() as tmpdir:
            fpath = os.path.join(tmpdir, "test.csv")
            with open(fpath, "wb") as f:
                f.write('\N{GREEK PI SYMBOL}'.encode())

            # ResourceWarnings are emitted from a destructor, so won't be
            # detected by regular propagation to errors.
            with assert_no_warnings():
                with pytest.raises(UnicodeDecodeError):
                    np.genfromtxt(fpath, encoding="ascii")

    def test_autonames_and_usecols(self):
        # Tests names and usecols
        data = TextIO('A B C D\n aaaa 121 45 9.1')
        with warnings.catch_warnings(record=True) as w:
            warnings.filterwarnings('always', '', VisibleDeprecationWarning)
            test = np.genfromtxt(data, usecols=('A', 'C', 'D'),
                                names=True, dtype=None, encoding="bytes")
            assert_(w[0].category is VisibleDeprecationWarning)
        control = np.array(('aaaa', 45, 9.1),
                           dtype=[('A', '|S4'), ('C', int), ('D', float)])
        assert_equal(test, control)

    def test_converters_with_usecols(self):
        # Test the combination user-defined converters and usecol
        data = TextIO('1,2,3,,5\n6,7,8,9,10\n')
        test = np.genfromtxt(data, dtype=int, delimiter=',',
                            converters={3: lambda s: int(s or - 999)},
                            usecols=(1, 3,))
        control = np.array([[2, -999], [7, 9]], int)
        assert_equal(test, control)

    def test_converters_with_usecols_and_names(self):
        # Tests names and usecols
        data = TextIO('A B C D\n aaaa 121 45 9.1')
        with warnings.catch_warnings(record=True) as w:
            warnings.filterwarnings('always', '', VisibleDeprecationWarning)
            test = np.genfromtxt(data, usecols=('A', 'C', 'D'), names=True,
                                dtype=None, encoding="bytes",
                                converters={'C': lambda s: 2 * int(s)})
            assert_(w[0].category is VisibleDeprecationWarning)
        control = np.array(('aaaa', 90, 9.1),
                           dtype=[('A', '|S4'), ('C', int), ('D', float)])
        assert_equal(test, control)

    def test_converters_cornercases(self):
        # Test the conversion to datetime.
        converter = {
            'date': lambda s: strptime(s, '%Y-%m-%d %H:%M:%SZ')}
        data = TextIO('2009-02-03 12:00:00Z, 72214.0')
        test = np.genfromtxt(data, delimiter=',', dtype=None,
                            names=['date', 'stid'], converters=converter)
        control = np.array((datetime(2009, 2, 3), 72214.),
                           dtype=[('date', np.object_), ('stid', float)])
        assert_equal(test, control)

    def test_converters_cornercases2(self):
        # Test the conversion to datetime64.
        converter = {
            'date': lambda s: np.datetime64(strptime(s, '%Y-%m-%d %H:%M:%SZ'))}
        data = TextIO('2009-02-03 12:00:00Z, 72214.0')
        test = np.genfromtxt(data, delimiter=',', dtype=None,
                            names=['date', 'stid'], converters=converter)
        control = np.array((datetime(2009, 2, 3), 72214.),
                           dtype=[('date', 'datetime64[us]'), ('stid', float)])
        assert_equal(test, control)

    def test_unused_converter(self):
        # Test whether unused converters are forgotten
        data = TextIO("1 21\n  3 42\n")
        test = np.genfromtxt(data, usecols=(1,),
                            converters={0: lambda s: int(s, 16)})
        assert_equal(test, [21, 42])
        #
        data.seek(0)
        test = np.genfromtxt(data, usecols=(1,),
                            converters={1: lambda s: int(s, 16)})
        assert_equal(test, [33, 66])

    def test_invalid_converter(self):
        strip_rand = lambda x: float((b'r' in x.lower() and x.split()[-1]) or
                                     ((b'r' not in x.lower() and x.strip()) or 0.0))
        strip_per = lambda x: float((b'%' in x.lower() and x.split()[0]) or
                                    ((b'%' not in x.lower() and x.strip()) or 0.0))
        s = TextIO("D01N01,10/1/2003 ,1 %,R 75,400,600\r\n"
                   "L24U05,12/5/2003, 2 %,1,300, 150.5\r\n"
                   "D02N03,10/10/2004,R 1,,7,145.55")
        kwargs = {
            "converters": {2: strip_per, 3: strip_rand}, "delimiter": ",",
            "dtype": None, "encoding": "bytes"}
        assert_raises(ConverterError, np.genfromtxt, s, **kwargs)

    def test_tricky_converter_bug1666(self):
        # Test some corner cases
        s = TextIO('q1,2\nq3,4')
        cnv = lambda s: float(s[1:])
        test = np.genfromtxt(s, delimiter=',', converters={0: cnv})
        control = np.array([[1., 2.], [3., 4.]])
        assert_equal(test, control)

    def test_dtype_with_converters(self):
        dstr = "2009; 23; 46"
        test = np.genfromtxt(TextIO(dstr,),
                            delimiter=";", dtype=float, converters={0: bytes})
        control = np.array([('2009', 23., 46)],
                           dtype=[('f0', '|S4'), ('f1', float), ('f2', float)])
        assert_equal(test, control)
        test = np.genfromtxt(TextIO(dstr,),
                            delimiter=";", dtype=float, converters={0: float})
        control = np.array([2009., 23., 46],)
        assert_equal(test, control)

    @pytest.mark.filterwarnings("ignore:.*recfromcsv.*:DeprecationWarning")
    def test_dtype_with_converters_and_usecols(self):
        dstr = "1,5,-1,1:1\n2,8,-1,1:n\n3,3,-2,m:n\n"
        dmap = {'1:1': 0, '1:n': 1, 'm:1': 2, 'm:n': 3}
        dtyp = [('e1', 'i4'), ('e2', 'i4'), ('e3', 'i2'), ('n', 'i1')]
        conv = {0: int, 1: int, 2: int, 3: lambda r: dmap[r.decode()]}
        test = recfromcsv(TextIO(dstr,), dtype=dtyp, delimiter=',',
                          names=None, converters=conv, encoding="bytes")
        control = np.rec.array([(1, 5, -1, 0), (2, 8, -1, 1), (3, 3, -2, 3)], dtype=dtyp)
        assert_equal(test, control)
        dtyp = [('e1', 'i4'), ('e2', 'i4'), ('n', 'i1')]
        test = recfromcsv(TextIO(dstr,), dtype=dtyp, delimiter=',',
                          usecols=(0, 1, 3), names=None, converters=conv,
                          encoding="bytes")
        control = np.rec.array([(1, 5, 0), (2, 8, 1), (3, 3, 3)], dtype=dtyp)
        assert_equal(test, control)

    def test_dtype_with_object(self):
        # Test using an explicit dtype with an object
        data = """ 1; 2001-01-01
                   2; 2002-01-31 """
        ndtype = [('idx', int), ('code', object)]
        func = lambda s: strptime(s.strip(), "%Y-%m-%d")
        converters = {1: func}
        test = np.genfromtxt(TextIO(data), delimiter=";", dtype=ndtype,
                             converters=converters)
        control = np.array(
            [(1, datetime(2001, 1, 1)), (2, datetime(2002, 1, 31))],
            dtype=ndtype)
        assert_equal(test, control)

        ndtype = [('nest', [('idx', int), ('code', object)])]
        with assert_raises_regex(NotImplementedError,
                                 'Nested fields.* not supported.*'):
            test = np.genfromtxt(TextIO(data), delimiter=";",
                                 dtype=ndtype, converters=converters)

        # nested but empty fields also aren't supported
        ndtype = [('idx', int), ('code', object), ('nest', [])]
        with assert_raises_regex(NotImplementedError,
                                 'Nested fields.* not supported.*'):
            test = np.genfromtxt(TextIO(data), delimiter=";",
                                 dtype=ndtype, converters=converters)

    def test_dtype_with_object_no_converter(self):
        # Object without a converter uses bytes:
        parsed = np.genfromtxt(TextIO("1"), dtype=object)
        assert parsed[()] == b"1"
        parsed = np.genfromtxt(TextIO("string"), dtype=object)
        assert parsed[()] == b"string"

    def test_userconverters_with_explicit_dtype(self):
        # Test user_converters w/ explicit (standard) dtype
        data = TextIO('skip,skip,2001-01-01,1.0,skip')
        test = np.genfromtxt(data, delimiter=",", names=None, dtype=float,
                             usecols=(2, 3), converters={2: bytes})
        control = np.array([('2001-01-01', 1.)],
                           dtype=[('', '|S10'), ('', float)])
        assert_equal(test, control)

    def test_utf8_userconverters_with_explicit_dtype(self):
        utf8 = b'\xcf\x96'
        with temppath() as path:
            with open(path, 'wb') as f:
                f.write(b'skip,skip,2001-01-01' + utf8 + b',1.0,skip')
            test = np.genfromtxt(path, delimiter=",", names=None, dtype=float,
                                 usecols=(2, 3), converters={2: str},
                                 encoding='UTF-8')
        control = np.array([('2001-01-01' + utf8.decode('UTF-8'), 1.)],
                           dtype=[('', '|U11'), ('', float)])
        assert_equal(test, control)

    def test_spacedelimiter(self):
        # Test space delimiter
        data = TextIO("1  2  3  4   5\n6  7  8  9  10")
        test = np.genfromtxt(data)
        control = np.array([[1., 2., 3., 4., 5.],
                            [6., 7., 8., 9., 10.]])
        assert_equal(test, control)

    def test_integer_delimiter(self):
        # Test using an integer for delimiter
        data = "  1  2  3\n  4  5 67\n890123  4"
        test = np.genfromtxt(TextIO(data), delimiter=3)
        control = np.array([[1, 2, 3], [4, 5, 67], [890, 123, 4]])
        assert_equal(test, control)

    def test_missing(self):
        data = TextIO('1,2,3,,5\n')
        test = np.genfromtxt(data, dtype=int, delimiter=',',
                            converters={3: lambda s: int(s or - 999)})
        control = np.array([1, 2, 3, -999, 5], int)
        assert_equal(test, control)

    def test_missing_with_tabs(self):
        # Test w/ a delimiter tab
        txt = "1\t2\t3\n\t2\t\n1\t\t3"
        test = np.genfromtxt(TextIO(txt), delimiter="\t",
                             usemask=True,)
        ctrl_d = np.array([(1, 2, 3), (np.nan, 2, np.nan), (1, np.nan, 3)],)
        ctrl_m = np.array([(0, 0, 0), (1, 0, 1), (0, 1, 0)], dtype=bool)
        assert_equal(test.data, ctrl_d)
        assert_equal(test.mask, ctrl_m)

    def test_usecols(self):
        # Test the selection of columns
        # Select 1 column
        control = np.array([[1, 2], [3, 4]], float)
        data = TextIO()
        np.savetxt(data, control)
        data.seek(0)
        test = np.genfromtxt(data, dtype=float, usecols=(1,))
        assert_equal(test, control[:, 1])
        #
        control = np.array([[1, 2, 3], [3, 4, 5]], float)
        data = TextIO()
        np.savetxt(data, control)
        data.seek(0)
        test = np.genfromtxt(data, dtype=float, usecols=(1, 2))
        assert_equal(test, control[:, 1:])
        # Testing with arrays instead of tuples.
        data.seek(0)
        test = np.genfromtxt(data, dtype=float, usecols=np.array([1, 2]))
        assert_equal(test, control[:, 1:])

    def test_usecols_as_css(self):
        # Test giving usecols with a comma-separated string
        data = "1 2 3\n4 5 6"
        test = np.genfromtxt(TextIO(data),
                             names="a, b, c", usecols="a, c")
        ctrl = np.array([(1, 3), (4, 6)], dtype=[(_, float) for _ in "ac"])
        assert_equal(test, ctrl)

    def test_usecols_with_structured_dtype(self):
        # Test usecols with an explicit structured dtype
        data = TextIO("JOE 70.1 25.3\nBOB 60.5 27.9")
        names = ['stid', 'temp']
        dtypes = ['S4', 'f8']
        test = np.genfromtxt(
            data, usecols=(0, 2), dtype=list(zip(names, dtypes)))
        assert_equal(test['stid'], [b"JOE", b"BOB"])
        assert_equal(test['temp'], [25.3, 27.9])

    def test_usecols_with_integer(self):
        # Test usecols with an integer
        test = np.genfromtxt(TextIO(b"1 2 3\n4 5 6"), usecols=0)
        assert_equal(test, np.array([1., 4.]))

    def test_usecols_with_named_columns(self):
        # Test usecols with named columns
        ctrl = np.array([(1, 3), (4, 6)], dtype=[('a', float), ('c', float)])
        data = "1 2 3\n4 5 6"
        kwargs = {"names": "a, b, c"}
        test = np.genfromtxt(TextIO(data), usecols=(0, -1), **kwargs)
        assert_equal(test, ctrl)
        test = np.genfromtxt(TextIO(data),
                             usecols=('a', 'c'), **kwargs)
        assert_equal(test, ctrl)

    def test_empty_file(self):
        # Test that an empty file raises the proper warning.
        with suppress_warnings() as sup:
            sup.filter(message="genfromtxt: Empty input file:")
            data = TextIO()
            test = np.genfromtxt(data)
            assert_equal(test, np.array([]))

            # when skip_header > 0
            test = np.genfromtxt(data, skip_header=1)
            assert_equal(test, np.array([]))

    def test_fancy_dtype_alt(self):
        # Check that a nested dtype isn't MIA
        data = TextIO('1,2,3.0\n4,5,6.0\n')
        fancydtype = np.dtype([('x', int), ('y', [('t', int), ('s', float)])])
        test = np.genfromtxt(data, dtype=fancydtype, delimiter=',', usemask=True)
        control = ma.array([(1, (2, 3.0)), (4, (5, 6.0))], dtype=fancydtype)
        assert_equal(test, control)

    def test_shaped_dtype(self):
        c = TextIO("aaaa  1.0  8.0  1 2 3 4 5 6")
        dt = np.dtype([('name', 'S4'), ('x', float), ('y', float),
                       ('block', int, (2, 3))])
        x = np.genfromtxt(c, dtype=dt)
        a = np.array([('aaaa', 1.0, 8.0, [[1, 2, 3], [4, 5, 6]])],
                     dtype=dt)
        assert_array_equal(x, a)

    def test_withmissing(self):
        data = TextIO('A,B\n0,1\n2,N/A')
        kwargs = {"delimiter": ",", "missing_values": "N/A", "names": True}
        test = np.genfromtxt(data, dtype=None, usemask=True, **kwargs)
        control = ma.array([(0, 1), (2, -1)],
                           mask=[(False, False), (False, True)],
                           dtype=[('A', int), ('B', int)])
        assert_equal(test, control)
        assert_equal(test.mask, control.mask)
        #
        data.seek(0)
        test = np.genfromtxt(data, usemask=True, **kwargs)
        control = ma.array([(0, 1), (2, -1)],
                           mask=[(False, False), (False, True)],
                           dtype=[('A', float), ('B', float)])
        assert_equal(test, control)
        assert_equal(test.mask, control.mask)

    def test_user_missing_values(self):
        data = "A, B, C\n0, 0., 0j\n1, N/A, 1j\n-9, 2.2, N/A\n3, -99, 3j"
        basekwargs = {"dtype": None, "delimiter": ",", "names": True}
        mdtype = [('A', int), ('B', float), ('C', complex)]
        #
        test = np.genfromtxt(TextIO(data), missing_values="N/A",
                            **basekwargs)
        control = ma.array([(0, 0.0, 0j), (1, -999, 1j),
                            (-9, 2.2, -999j), (3, -99, 3j)],
                           mask=[(0, 0, 0), (0, 1, 0), (0, 0, 1), (0, 0, 0)],
                           dtype=mdtype)
        assert_equal(test, control)
        #
        basekwargs['dtype'] = mdtype
        test = np.genfromtxt(TextIO(data),
                            missing_values={0: -9, 1: -99, 2: -999j}, usemask=True, **basekwargs)
        control = ma.array([(0, 0.0, 0j), (1, -999, 1j),
                            (-9, 2.2, -999j), (3, -99, 3j)],
                           mask=[(0, 0, 0), (0, 1, 0), (1, 0, 1), (0, 1, 0)],
                           dtype=mdtype)
        assert_equal(test, control)
        #
        test = np.genfromtxt(TextIO(data),
                            missing_values={0: -9, 'B': -99, 'C': -999j},
                            usemask=True,
                            **basekwargs)
        control = ma.array([(0, 0.0, 0j), (1, -999, 1j),
                            (-9, 2.2, -999j), (3, -99, 3j)],
                           mask=[(0, 0, 0), (0, 1, 0), (1, 0, 1), (0, 1, 0)],
                           dtype=mdtype)
        assert_equal(test, control)

    def test_user_filling_values(self):
        # Test with missing and filling values
        ctrl = np.array([(0, 3), (4, -999)], dtype=[('a', int), ('b', int)])
        data = "N/A, 2, 3\n4, ,???"
        kwargs = {"delimiter": ",",
                      "dtype": int,
                      "names": "a,b,c",
                      "missing_values": {0: "N/A", 'b': " ", 2: "???"},
                      "filling_values": {0: 0, 'b': 0, 2: -999}}
        test = np.genfromtxt(TextIO(data), **kwargs)
        ctrl = np.array([(0, 2, 3), (4, 0, -999)],
                        dtype=[(_, int) for _ in "abc"])
        assert_equal(test, ctrl)
        #
        test = np.genfromtxt(TextIO(data), usecols=(0, -1), **kwargs)
        ctrl = np.array([(0, 3), (4, -999)], dtype=[(_, int) for _ in "ac"])
        assert_equal(test, ctrl)

        data2 = "1,2,*,4\n5,*,7,8\n"
        test = np.genfromtxt(TextIO(data2), delimiter=',', dtype=int,
                             missing_values="*", filling_values=0)
        ctrl = np.array([[1, 2, 0, 4], [5, 0, 7, 8]])
        assert_equal(test, ctrl)
        test = np.genfromtxt(TextIO(data2), delimiter=',', dtype=int,
                             missing_values="*", filling_values=-1)
        ctrl = np.array([[1, 2, -1, 4], [5, -1, 7, 8]])
        assert_equal(test, ctrl)

    def test_withmissing_float(self):
        data = TextIO('A,B\n0,1.5\n2,-999.00')
        test = np.genfromtxt(data, dtype=None, delimiter=',',
                            missing_values='-999.0', names=True, usemask=True)
        control = ma.array([(0, 1.5), (2, -1.)],
                           mask=[(False, False), (False, True)],
                           dtype=[('A', int), ('B', float)])
        assert_equal(test, control)
        assert_equal(test.mask, control.mask)

    def test_with_masked_column_uniform(self):
        # Test masked column
        data = TextIO('1 2 3\n4 5 6\n')
        test = np.genfromtxt(data, dtype=None,
                             missing_values='2,5', usemask=True)
        control = ma.array([[1, 2, 3], [4, 5, 6]], mask=[[0, 1, 0], [0, 1, 0]])
        assert_equal(test, control)

    def test_with_masked_column_various(self):
        # Test masked column
        data = TextIO('True 2 3\nFalse 5 6\n')
        test = np.genfromtxt(data, dtype=None,
                             missing_values='2,5', usemask=True)
        control = ma.array([(1, 2, 3), (0, 5, 6)],
                           mask=[(0, 1, 0), (0, 1, 0)],
                           dtype=[('f0', bool), ('f1', bool), ('f2', int)])
        assert_equal(test, control)

    def test_invalid_raise(self):
        # Test invalid raise
        data = ["1, 1, 1, 1, 1"] * 50
        for i in range(5):
            data[10 * i] = "2, 2, 2, 2 2"
        data.insert(0, "a, b, c, d, e")
        mdata = TextIO("\n".join(data))

        kwargs = {"delimiter": ",", "dtype": None, "names": True}

        def f():
            return np.genfromtxt(mdata, invalid_raise=False, **kwargs)
        mtest = assert_warns(ConversionWarning, f)
        assert_equal(len(mtest), 45)
        assert_equal(mtest, np.ones(45, dtype=[(_, int) for _ in 'abcde']))
        #
        mdata.seek(0)
        assert_raises(ValueError, np.genfromtxt, mdata,
                      delimiter=",", names=True)

    def test_invalid_raise_with_usecols(self):
        # Test invalid_raise with usecols
        data = ["1, 1, 1, 1, 1"] * 50
        for i in range(5):
            data[10 * i] = "2, 2, 2, 2 2"
        data.insert(0, "a, b, c, d, e")
        mdata = TextIO("\n".join(data))

        kwargs = {"delimiter": ",", "dtype": None, "names": True,
                      "invalid_raise": False}

        def f():
            return np.genfromtxt(mdata, usecols=(0, 4), **kwargs)
        mtest = assert_warns(ConversionWarning, f)
        assert_equal(len(mtest), 45)
        assert_equal(mtest, np.ones(45, dtype=[(_, int) for _ in 'ae']))
        #
        mdata.seek(0)
        mtest = np.genfromtxt(mdata, usecols=(0, 1), **kwargs)
        assert_equal(len(mtest), 50)
        control = np.ones(50, dtype=[(_, int) for _ in 'ab'])
        control[[10 * _ for _ in range(5)]] = (2, 2)
        assert_equal(mtest, control)

    def test_inconsistent_dtype(self):
        # Test inconsistent dtype
        data = ["1, 1, 1, 1, -1.1"] * 50
        mdata = TextIO("\n".join(data))

        converters = {4: lambda x: f"({x.decode()})"}
        kwargs = {"delimiter": ",", "converters": converters,
                      "dtype": [(_, int) for _ in 'abcde'], "encoding": "bytes"}
        assert_raises(ValueError, np.genfromtxt, mdata, **kwargs)

    def test_default_field_format(self):
        # Test default format
        data = "0, 1, 2.3\n4, 5, 6.7"
        mtest = np.genfromtxt(TextIO(data),
                             delimiter=",", dtype=None, defaultfmt="f%02i")
        ctrl = np.array([(0, 1, 2.3), (4, 5, 6.7)],
                        dtype=[("f00", int), ("f01", int), ("f02", float)])
        assert_equal(mtest, ctrl)

    def test_single_dtype_wo_names(self):
        # Test single dtype w/o names
        data = "0, 1, 2.3\n4, 5, 6.7"
        mtest = np.genfromtxt(TextIO(data),
                             delimiter=",", dtype=float, defaultfmt="f%02i")
        ctrl = np.array([[0., 1., 2.3], [4., 5., 6.7]], dtype=float)
        assert_equal(mtest, ctrl)

    def test_single_dtype_w_explicit_names(self):
        # Test single dtype w explicit names
        data = "0, 1, 2.3\n4, 5, 6.7"
        mtest = np.genfromtxt(TextIO(data),
                             delimiter=",", dtype=float, names="a, b, c")
        ctrl = np.array([(0., 1., 2.3), (4., 5., 6.7)],
                        dtype=[(_, float) for _ in "abc"])
        assert_equal(mtest, ctrl)

    def test_single_dtype_w_implicit_names(self):
        # Test single dtype w implicit names
        data = "a, b, c\n0, 1, 2.3\n4, 5, 6.7"
        mtest = np.genfromtxt(TextIO(data),
                             delimiter=",", dtype=float, names=True)
        ctrl = np.array([(0., 1., 2.3), (4., 5., 6.7)],
                        dtype=[(_, float) for _ in "abc"])
        assert_equal(mtest, ctrl)

    def test_easy_structured_dtype(self):
        # Test easy structured dtype
        data = "0, 1, 2.3\n4, 5, 6.7"
        mtest = np.genfromtxt(TextIO(data), delimiter=",",
                             dtype=(int, float, float), defaultfmt="f_%02i")
        ctrl = np.array([(0, 1., 2.3), (4, 5., 6.7)],
                        dtype=[("f_00", int), ("f_01", float), ("f_02", float)])
        assert_equal(mtest, ctrl)

    def test_autostrip(self):
        # Test autostrip
        data = "01/01/2003  , 1.3,   abcde"
        kwargs = {"delimiter": ",", "dtype": None, "encoding": "bytes"}
        with warnings.catch_warnings(record=True) as w:
            warnings.filterwarnings('always', '', VisibleDeprecationWarning)
            mtest = np.genfromtxt(TextIO(data), **kwargs)
            assert_(w[0].category is VisibleDeprecationWarning)
        ctrl = np.array([('01/01/2003  ', 1.3, '   abcde')],
                        dtype=[('f0', '|S12'), ('f1', float), ('f2', '|S8')])
        assert_equal(mtest, ctrl)
        with warnings.catch_warnings(record=True) as w:
            warnings.filterwarnings('always', '', VisibleDeprecationWarning)
            mtest = np.genfromtxt(TextIO(data), autostrip=True, **kwargs)
            assert_(w[0].category is VisibleDeprecationWarning)
        ctrl = np.array([('01/01/2003', 1.3, 'abcde')],
                        dtype=[('f0', '|S10'), ('f1', float), ('f2', '|S5')])
        assert_equal(mtest, ctrl)

    def test_replace_space(self):
        # Test the 'replace_space' option
        txt = "A.A, B (B), C:C\n1, 2, 3.14"
        # Test default: replace ' ' by '_' and delete non-alphanum chars
        test = np.genfromtxt(TextIO(txt),
                             delimiter=",", names=True, dtype=None)
        ctrl_dtype = [("AA", int), ("B_B", int), ("CC", float)]
        ctrl = np.array((1, 2, 3.14), dtype=ctrl_dtype)
        assert_equal(test, ctrl)
        # Test: no replace, no delete
        test = np.genfromtxt(TextIO(txt),
                             delimiter=",", names=True, dtype=None,
                             replace_space='', deletechars='')
        ctrl_dtype = [("A.A", int), ("B (B)", int), ("C:C", float)]
        ctrl = np.array((1, 2, 3.14), dtype=ctrl_dtype)
        assert_equal(test, ctrl)
        # Test: no delete (spaces are replaced by _)
        test = np.genfromtxt(TextIO(txt),
                             delimiter=",", names=True, dtype=None,
                             deletechars='')
        ctrl_dtype = [("A.A", int), ("B_(B)", int), ("C:C", float)]
        ctrl = np.array((1, 2, 3.14), dtype=ctrl_dtype)
        assert_equal(test, ctrl)

    def test_replace_space_known_dtype(self):
        # Test the 'replace_space' (and related) options when dtype != None
        txt = "A.A, B (B), C:C\n1, 2, 3"
        # Test default: replace ' ' by '_' and delete non-alphanum chars
        test = np.genfromtxt(TextIO(txt),
                             delimiter=",", names=True, dtype=int)
        ctrl_dtype = [("AA", int), ("B_B", int), ("CC", int)]
        ctrl = np.array((1, 2, 3), dtype=ctrl_dtype)
        assert_equal(test, ctrl)
        # Test: no replace, no delete
        test = np.genfromtxt(TextIO(txt),
                             delimiter=",", names=True, dtype=int,
                             replace_space='', deletechars='')
        ctrl_dtype = [("A.A", int), ("B (B)", int), ("C:C", int)]
        ctrl = np.array((1, 2, 3), dtype=ctrl_dtype)
        assert_equal(test, ctrl)
        # Test: no delete (spaces are replaced by _)
        test = np.genfromtxt(TextIO(txt),
                             delimiter=",", names=True, dtype=int,
                             deletechars='')
        ctrl_dtype = [("A.A", int), ("B_(B)", int), ("C:C", int)]
        ctrl = np.array((1, 2, 3), dtype=ctrl_dtype)
        assert_equal(test, ctrl)

    def test_incomplete_names(self):
        # Test w/ incomplete names
        data = "A,,C\n0,1,2\n3,4,5"
        kwargs = {"delimiter": ",", "names": True}
        # w/ dtype=None
        ctrl = np.array([(0, 1, 2), (3, 4, 5)],
                        dtype=[(_, int) for _ in ('A', 'f0', 'C')])
        test = np.genfromtxt(TextIO(data), dtype=None, **kwargs)
        assert_equal(test, ctrl)
        # w/ default dtype
        ctrl = np.array([(0, 1, 2), (3, 4, 5)],
                        dtype=[(_, float) for _ in ('A', 'f0', 'C')])
        test = np.genfromtxt(TextIO(data), **kwargs)

    def test_names_auto_completion(self):
        # Make sure that names are properly completed
        data = "1 2 3\n 4 5 6"
        test = np.genfromtxt(TextIO(data),
                             dtype=(int, float, int), names="a")
        ctrl = np.array([(1, 2, 3), (4, 5, 6)],
                        dtype=[('a', int), ('f0', float), ('f1', int)])
        assert_equal(test, ctrl)

    def test_names_with_usecols_bug1636(self):
        # Make sure we pick up the right names w/ usecols
        data = "A,B,C,D,E\n0,1,2,3,4\n0,1,2,3,4\n0,1,2,3,4"
        ctrl_names = ("A", "C", "E")
        test = np.genfromtxt(TextIO(data),
                             dtype=(int, int, int), delimiter=",",
                             usecols=(0, 2, 4), names=True)
        assert_equal(test.dtype.names, ctrl_names)
        #
        test = np.genfromtxt(TextIO(data),
                             dtype=(int, int, int), delimiter=",",
                             usecols=("A", "C", "E"), names=True)
        assert_equal(test.dtype.names, ctrl_names)
        #
        test = np.genfromtxt(TextIO(data),
                             dtype=int, delimiter=",",
                             usecols=("A", "C", "E"), names=True)
        assert_equal(test.dtype.names, ctrl_names)

    def test_fixed_width_names(self):
        # Test fix-width w/ names
        data = "    A    B   C\n    0    1 2.3\n   45   67   9."
        kwargs = {"delimiter": (5, 5, 4), "names": True, "dtype": None}
        ctrl = np.array([(0, 1, 2.3), (45, 67, 9.)],
                        dtype=[('A', int), ('B', int), ('C', float)])
        test = np.genfromtxt(TextIO(data), **kwargs)
        assert_equal(test, ctrl)
        #
        kwargs = {"delimiter": 5, "names": True, "dtype": None}
        ctrl = np.array([(0, 1, 2.3), (45, 67, 9.)],
                        dtype=[('A', int), ('B', int), ('C', float)])
        test = np.genfromtxt(TextIO(data), **kwargs)
        assert_equal(test, ctrl)

    def test_filling_values(self):
        # Test missing values
        data = b"1, 2, 3\n1, , 5\n0, 6, \n"
        kwargs = {"delimiter": ",", "dtype": None, "filling_values": -999}
        ctrl = np.array([[1, 2, 3], [1, -999, 5], [0, 6, -999]], dtype=int)
        test = np.genfromtxt(TextIO(data), **kwargs)
        assert_equal(test, ctrl)

    def test_comments_is_none(self):
        # Github issue 329 (None was previously being converted to 'None').
        with warnings.catch_warnings(record=True) as w:
            warnings.filterwarnings('always', '', VisibleDeprecationWarning)
            test = np.genfromtxt(TextIO("test1,testNonetherestofthedata"),
                                 dtype=None, comments=None, delimiter=',',
                                 encoding="bytes")
            assert_(w[0].category is VisibleDeprecationWarning)
        assert_equal(test[1], b'testNonetherestofthedata')
        with warnings.catch_warnings(record=True) as w:
            warnings.filterwarnings('always', '', VisibleDeprecationWarning)
            test = np.genfromtxt(TextIO("test1, testNonetherestofthedata"),
                                 dtype=None, comments=None, delimiter=',',
                                 encoding="bytes")
            assert_(w[0].category is VisibleDeprecationWarning)
        assert_equal(test[1], b' testNonetherestofthedata')

    def test_latin1(self):
        latin1 = b'\xf6\xfc\xf6'
        norm = b"norm1,norm2,norm3\n"
        enc = b"test1,testNonethe" + latin1 + b",test3\n"
        s = norm + enc + norm
        with warnings.catch_warnings(record=True) as w:
            warnings.filterwarnings('always', '', VisibleDeprecationWarning)
            test = np.genfromtxt(TextIO(s),
                                 dtype=None, comments=None, delimiter=',',
                                 encoding="bytes")
            assert_(w[0].category is VisibleDeprecationWarning)
        assert_equal(test[1, 0], b"test1")
        assert_equal(test[1, 1], b"testNonethe" + latin1)
        assert_equal(test[1, 2], b"test3")
        test = np.genfromtxt(TextIO(s),
                             dtype=None, comments=None, delimiter=',',
                             encoding='latin1')
        assert_equal(test[1, 0], "test1")
        assert_equal(test[1, 1], "testNonethe" + latin1.decode('latin1'))
        assert_equal(test[1, 2], "test3")

        with warnings.catch_warnings(record=True) as w:
            warnings.filterwarnings('always', '', VisibleDeprecationWarning)
            test = np.genfromtxt(TextIO(b"0,testNonethe" + latin1),
                                 dtype=None, comments=None, delimiter=',',
                                 encoding="bytes")
            assert_(w[0].category is VisibleDeprecationWarning)
        assert_equal(test['f0'], 0)
        assert_equal(test['f1'], b"testNonethe" + latin1)

    def test_binary_decode_autodtype(self):
        utf16 = b'\xff\xfeh\x04 \x00i\x04 \x00j\x04'
        v = self.loadfunc(BytesIO(utf16), dtype=None, encoding='UTF-16')
        assert_array_equal(v, np.array(utf16.decode('UTF-16').split()))

    def test_utf8_byte_encoding(self):
        utf8 = b"\xcf\x96"
        norm = b"norm1,norm2,norm3\n"
        enc = b"test1,testNonethe" + utf8 + b",test3\n"
        s = norm + enc + norm
        with warnings.catch_warnings(record=True) as w:
            warnings.filterwarnings('always', '', VisibleDeprecationWarning)
            test = np.genfromtxt(TextIO(s),
                                 dtype=None, comments=None, delimiter=',',
                                 encoding="bytes")
            assert_(w[0].category is VisibleDeprecationWarning)
        ctl = np.array([
                 [b'norm1', b'norm2', b'norm3'],
                 [b'test1', b'testNonethe' + utf8, b'test3'],
                 [b'norm1', b'norm2', b'norm3']])
        assert_array_equal(test, ctl)

    def test_utf8_file(self):
        utf8 = b"\xcf\x96"
        with temppath() as path:
            with open(path, "wb") as f:
                f.write((b"test1,testNonethe" + utf8 + b",test3\n") * 2)
            test = np.genfromtxt(path, dtype=None, comments=None,
                                 delimiter=',', encoding="UTF-8")
            ctl = np.array([
                     ["test1", "testNonethe" + utf8.decode("UTF-8"), "test3"],
                     ["test1", "testNonethe" + utf8.decode("UTF-8"), "test3"]],
                     dtype=np.str_)
            assert_array_equal(test, ctl)

            # test a mixed dtype
            with open(path, "wb") as f:
                f.write(b"0,testNonethe" + utf8)
            test = np.genfromtxt(path, dtype=None, comments=None,
                                 delimiter=',', encoding="UTF-8")
            assert_equal(test['f0'], 0)
            assert_equal(test['f1'], "testNonethe" + utf8.decode("UTF-8"))

    def test_utf8_file_nodtype_unicode(self):
        # bytes encoding with non-latin1 -> unicode upcast
        utf8 = '\u03d6'
        latin1 = '\xf6\xfc\xf6'

        # skip test if cannot encode utf8 test string with preferred
        # encoding. The preferred encoding is assumed to be the default
        # encoding of open. Will need to change this for PyTest, maybe
        # using pytest.mark.xfail(raises=***).
        try:
            encoding = locale.getpreferredencoding()
            utf8.encode(encoding)
        except (UnicodeError, ImportError):
            pytest.skip('Skipping test_utf8_file_nodtype_unicode, '
                        'unable to encode utf8 in preferred encoding')

        with temppath() as path:
            with open(path, "wt") as f:
                f.write("norm1,norm2,norm3\n")
                f.write("norm1," + latin1 + ",norm3\n")
                f.write("test1,testNonethe" + utf8 + ",test3\n")
            with warnings.catch_warnings(record=True) as w:
                warnings.filterwarnings('always', '',
                                        VisibleDeprecationWarning)
                test = np.genfromtxt(path, dtype=None, comments=None,
                                     delimiter=',', encoding="bytes")
                # Check for warning when encoding not specified.
                assert_(w[0].category is VisibleDeprecationWarning)
            ctl = np.array([
                     ["norm1", "norm2", "norm3"],
                     ["norm1", latin1, "norm3"],
                     ["test1", "testNonethe" + utf8, "test3"]],
                     dtype=np.str_)
            assert_array_equal(test, ctl)

    @pytest.mark.filterwarnings("ignore:.*recfromtxt.*:DeprecationWarning")
    def test_recfromtxt(self):
        #
        data = TextIO('A,B\n0,1\n2,3')
        kwargs = {"delimiter": ",", "missing_values": "N/A", "names": True}
        test = recfromtxt(data, **kwargs)
        control = np.array([(0, 1), (2, 3)],
                           dtype=[('A', int), ('B', int)])
        assert_(isinstance(test, np.recarray))
        assert_equal(test, control)
        #
        data = TextIO('A,B\n0,1\n2,N/A')
        test = recfromtxt(data, dtype=None, usemask=True, **kwargs)
        control = ma.array([(0, 1), (2, -1)],
                           mask=[(False, False), (False, True)],
                           dtype=[('A', int), ('B', int)])
        assert_equal(test, control)
        assert_equal(test.mask, control.mask)
        assert_equal(test.A, [0, 2])

    @pytest.mark.filterwarnings("ignore:.*recfromcsv.*:DeprecationWarning")
    def test_recfromcsv(self):
        #
        data = TextIO('A,B\n0,1\n2,3')
        kwargs = {"missing_values": "N/A", "names": True, "case_sensitive": True,
                      "encoding": "bytes"}
        test = recfromcsv(data, dtype=None, **kwargs)
        control = np.array([(0, 1), (2, 3)],
                           dtype=[('A', int), ('B', int)])
        assert_(isinstance(test, np.recarray))
        assert_equal(test, control)
        #
        data = TextIO('A,B\n0,1\n2,N/A')
        test = recfromcsv(data, dtype=None, usemask=True, **kwargs)
        control = ma.array([(0, 1), (2, -1)],
                           mask=[(False, False), (False, True)],
                           dtype=[('A', int), ('B', int)])
        assert_equal(test, control)
        assert_equal(test.mask, control.mask)
        assert_equal(test.A, [0, 2])
        #
        data = TextIO('A,B\n0,1\n2,3')
        test = recfromcsv(data, missing_values='N/A',)
        control = np.array([(0, 1), (2, 3)],
                           dtype=[('a', int), ('b', int)])
        assert_(isinstance(test, np.recarray))
        assert_equal(test, control)
        #
        data = TextIO('A,B\n0,1\n2,3')
        dtype = [('a', int), ('b', float)]
        test = recfromcsv(data, missing_values='N/A', dtype=dtype)
        control = np.array([(0, 1), (2, 3)],
                           dtype=dtype)
        assert_(isinstance(test, np.recarray))
        assert_equal(test, control)

        # gh-10394
        data = TextIO('color\n"red"\n"blue"')
        test = recfromcsv(data, converters={0: lambda x: x.strip('\"')})
        control = np.array([('red',), ('blue',)], dtype=[('color', (str, 4))])
        assert_equal(test.dtype, control.dtype)
        assert_equal(test, control)

    def test_max_rows(self):
        # Test the `max_rows` keyword argument.
        data = '1 2\n3 4\n5 6\n7 8\n9 10\n'
        txt = TextIO(data)
        a1 = np.genfromtxt(txt, max_rows=3)
        a2 = np.genfromtxt(txt)
        assert_equal(a1, [[1, 2], [3, 4], [5, 6]])
        assert_equal(a2, [[7, 8], [9, 10]])

        # max_rows must be at least 1.
        assert_raises(ValueError, np.genfromtxt, TextIO(data), max_rows=0)

        # An input with several invalid rows.
        data = '1 1\n2 2\n0 \n3 3\n4 4\n5  \n6  \n7  \n'

        test = np.genfromtxt(TextIO(data), max_rows=2)
        control = np.array([[1., 1.], [2., 2.]])
        assert_equal(test, control)

        # Test keywords conflict
        assert_raises(ValueError, np.genfromtxt, TextIO(data), skip_footer=1,
                      max_rows=4)

        # Test with invalid value
        assert_raises(ValueError, np.genfromtxt, TextIO(data), max_rows=4)

        # Test with invalid not raise
        with suppress_warnings() as sup:
            sup.filter(ConversionWarning)

            test = np.genfromtxt(TextIO(data), max_rows=4, invalid_raise=False)
            control = np.array([[1., 1.], [2., 2.], [3., 3.], [4., 4.]])
            assert_equal(test, control)

            test = np.genfromtxt(TextIO(data), max_rows=5, invalid_raise=False)
            control = np.array([[1., 1.], [2., 2.], [3., 3.], [4., 4.]])
            assert_equal(test, control)

        # Structured array with field names.
        data = 'a b\n#c d\n1 1\n2 2\n#0 \n3 3\n4 4\n5  5\n'

        # Test with header, names and comments
        txt = TextIO(data)
        test = np.genfromtxt(txt, skip_header=1, max_rows=3, names=True)
        control = np.array([(1.0, 1.0), (2.0, 2.0), (3.0, 3.0)],
                      dtype=[('c', '<f8'), ('d', '<f8')])
        assert_equal(test, control)
        # To continue reading the same "file", don't use skip_header or
        # names, and use the previously determined dtype.
        test = np.genfromtxt(txt, max_rows=None, dtype=test.dtype)
        control = np.array([(4.0, 4.0), (5.0, 5.0)],
                      dtype=[('c', '<f8'), ('d', '<f8')])
        assert_equal(test, control)

    def test_gft_using_filename(self):
        # Test that we can load data from a filename as well as a file
        # object
        tgt = np.arange(6).reshape((2, 3))
        linesep = ('\n', '\r\n', '\r')

        for sep in linesep:
            data = '0 1 2' + sep + '3 4 5'
            with temppath() as name:
                with open(name, 'w') as f:
                    f.write(data)
                res = np.genfromtxt(name)
            assert_array_equal(res, tgt)

    def test_gft_from_gzip(self):
        # Test that we can load data from a gzipped file
        wanted = np.arange(6).reshape((2, 3))
        linesep = ('\n', '\r\n', '\r')

        for sep in linesep:
            data = '0 1 2' + sep + '3 4 5'
            s = BytesIO()
            with gzip.GzipFile(fileobj=s, mode='w') as g:
                g.write(asbytes(data))

            with temppath(suffix='.gz2') as name:
                with open(name, 'w') as f:
                    f.write(data)
                assert_array_equal(np.genfromtxt(name), wanted)

    def test_gft_using_generator(self):
        # gft doesn't work with unicode.
        def count():
            for i in range(10):
                yield asbytes("%d" % i)

        res = np.genfromtxt(count())
        assert_array_equal(res, np.arange(10))

    def test_auto_dtype_largeint(self):
        # Regression test for numpy/numpy#5635 whereby large integers could
        # cause OverflowErrors.

        # Test the automatic definition of the output dtype
        #
        # 2**66 = 73786976294838206464 => should convert to float
        # 2**34 = 17179869184 => should convert to int64
        # 2**10 = 1024 => should convert to int (int32 on 32-bit systems,
        #                 int64 on 64-bit systems)

        data = TextIO('73786976294838206464 17179869184 1024')

        test = np.genfromtxt(data, dtype=None)

        assert_equal(test.dtype.names, ['f0', 'f1', 'f2'])

        assert_(test.dtype['f0'] == float)
        assert_(test.dtype['f1'] == np.int64)
        assert_(test.dtype['f2'] == np.int_)

        assert_allclose(test['f0'], 73786976294838206464.)
        assert_equal(test['f1'], 17179869184)
        assert_equal(test['f2'], 1024)

    def test_unpack_float_data(self):
        txt = TextIO("1,2,3\n4,5,6\n7,8,9\n0.0,1.0,2.0")
        a, b, c = np.loadtxt(txt, delimiter=",", unpack=True)
        assert_array_equal(a, np.array([1.0, 4.0, 7.0, 0.0]))
        assert_array_equal(b, np.array([2.0, 5.0, 8.0, 1.0]))
        assert_array_equal(c, np.array([3.0, 6.0, 9.0, 2.0]))

    def test_unpack_structured(self):
        # Regression test for gh-4341
        # Unpacking should work on structured arrays
        txt = TextIO("M 21 72\nF 35 58")
        dt = {'names': ('a', 'b', 'c'), 'formats': ('S1', 'i4', 'f4')}
        a, b, c = np.genfromtxt(txt, dtype=dt, unpack=True)
        assert_equal(a.dtype, np.dtype('S1'))
        assert_equal(b.dtype, np.dtype('i4'))
        assert_equal(c.dtype, np.dtype('f4'))
        assert_array_equal(a, np.array([b'M', b'F']))
        assert_array_equal(b, np.array([21, 35]))
        assert_array_equal(c, np.array([72.,  58.]))

    def test_unpack_auto_dtype(self):
        # Regression test for gh-4341
        # Unpacking should work when dtype=None
        txt = TextIO("M 21 72.\nF 35 58.")
        expected = (np.array(["M", "F"]), np.array([21, 35]), np.array([72., 58.]))
        test = np.genfromtxt(txt, dtype=None, unpack=True, encoding="utf-8")
        for arr, result in zip(expected, test):
            assert_array_equal(arr, result)
            assert_equal(arr.dtype, result.dtype)

    def test_unpack_single_name(self):
        # Regression test for gh-4341
        # Unpacking should work when structured dtype has only one field
        txt = TextIO("21\n35")
        dt = {'names': ('a',), 'formats': ('i4',)}
        expected = np.array([21, 35], dtype=np.int32)
        test = np.genfromtxt(txt, dtype=dt, unpack=True)
        assert_array_equal(expected, test)
        assert_equal(expected.dtype, test.dtype)

    def test_squeeze_scalar(self):
        # Regression test for gh-4341
        # Unpacking a scalar should give zero-dim output,
        # even if dtype is structured
        txt = TextIO("1")
        dt = {'names': ('a',), 'formats': ('i4',)}
        expected = np.array((1,), dtype=np.int32)
        test = np.genfromtxt(txt, dtype=dt, unpack=True)
        assert_array_equal(expected, test)
        assert_equal((), test.shape)
        assert_equal(expected.dtype, test.dtype)

    @pytest.mark.parametrize("ndim", [0, 1, 2])
    def test_ndmin_keyword(self, ndim: int):
        # lets have the same behaviour of ndmin as loadtxt
        # as they should be the same for non-missing values
        txt = "42"

        a = np.loadtxt(StringIO(txt), ndmin=ndim)
        b = np.genfromtxt(StringIO(txt), ndmin=ndim)

        assert_array_equal(a, b)


class TestPathUsage:
    # Test that pathlib.Path can be used
    def test_loadtxt(self):
        with temppath(suffix='.txt') as path:
            path = Path(path)
            a = np.array([[1.1, 2], [3, 4]])
            np.savetxt(path, a)
            x = np.loadtxt(path)
            assert_array_equal(x, a)

    def test_save_load(self):
        # Test that pathlib.Path instances can be used with save.
        with temppath(suffix='.npy') as path:
            path = Path(path)
            a = np.array([[1, 2], [3, 4]], int)
            np.save(path, a)
            data = np.load(path)
            assert_array_equal(data, a)

    def test_save_load_memmap(self):
        # Test that pathlib.Path instances can be loaded mem-mapped.
        with temppath(suffix='.npy') as path:
            path = Path(path)
            a = np.array([[1, 2], [3, 4]], int)
            np.save(path, a)
            data = np.load(path, mmap_mode='r')
            assert_array_equal(data, a)
            # close the mem-mapped file
            del data
            if IS_PYPY:
                break_cycles()
                break_cycles()

    @pytest.mark.xfail(IS_WASM, reason="memmap doesn't work correctly")
    @pytest.mark.parametrize("filename_type", [Path, str])
    def test_save_load_memmap_readwrite(self, filename_type):
        with temppath(suffix='.npy') as path:
            path = filename_type(path)
            a = np.array([[1, 2], [3, 4]], int)
            np.save(path, a)
            b = np.load(path, mmap_mode='r+')
            a[0][0] = 5
            b[0][0] = 5
            del b  # closes the file
            if IS_PYPY:
                break_cycles()
                break_cycles()
            data = np.load(path)
            assert_array_equal(data, a)

    @pytest.mark.parametrize("filename_type", [Path, str])
    def test_savez_load(self, filename_type):
        with temppath(suffix='.npz') as path:
            path = filename_type(path)
            np.savez(path, lab='place holder')
            with np.load(path) as data:
                assert_array_equal(data['lab'], 'place holder')

    @pytest.mark.parametrize("filename_type", [Path, str])
    def test_savez_compressed_load(self, filename_type):
        with temppath(suffix='.npz') as path:
            path = filename_type(path)
            np.savez_compressed(path, lab='place holder')
            data = np.load(path)
            assert_array_equal(data['lab'], 'place holder')
            data.close()

    @pytest.mark.parametrize("filename_type", [Path, str])
    def test_genfromtxt(self, filename_type):
        with temppath(suffix='.txt') as path:
            path = filename_type(path)
            a = np.array([(1, 2), (3, 4)])
            np.savetxt(path, a)
            data = np.genfromtxt(path)
            assert_array_equal(a, data)

    @pytest.mark.parametrize("filename_type", [Path, str])
    @pytest.mark.filterwarnings("ignore:.*recfromtxt.*:DeprecationWarning")
    def test_recfromtxt(self, filename_type):
        with temppath(suffix='.txt') as path:
            path = filename_type(path)
            with open(path, 'w') as f:
                f.write('A,B\n0,1\n2,3')

            kwargs = {"delimiter": ",", "missing_values": "N/A", "names": True}
            test = recfromtxt(path, **kwargs)
            control = np.array([(0, 1), (2, 3)],
                               dtype=[('A', int), ('B', int)])
            assert_(isinstance(test, np.recarray))
            assert_equal(test, control)

    @pytest.mark.parametrize("filename_type", [Path, str])
    @pytest.mark.filterwarnings("ignore:.*recfromcsv.*:DeprecationWarning")
    def test_recfromcsv(self, filename_type):
        with temppath(suffix='.txt') as path:
            path = filename_type(path)
            with open(path, 'w') as f:
                f.write('A,B\n0,1\n2,3')

            kwargs = {
                "missing_values": "N/A", "names": True, "case_sensitive": True
            }
            test = recfromcsv(path, dtype=None, **kwargs)
            control = np.array([(0, 1), (2, 3)],
                               dtype=[('A', int), ('B', int)])
            assert_(isinstance(test, np.recarray))
            assert_equal(test, control)


def test_gzip_load():
    a = np.random.random((5, 5))

    s = BytesIO()
    f = gzip.GzipFile(fileobj=s, mode="w")

    np.save(f, a)
    f.close()
    s.seek(0)

    f = gzip.GzipFile(fileobj=s, mode="r")
    assert_array_equal(np.load(f), a)


# These next two classes encode the minimal API needed to save()/load() arrays.
# The `test_ducktyping` ensures they work correctly
class JustWriter:
    def __init__(self, base):
        self.base = base

    def write(self, s):
        return self.base.write(s)

    def flush(self):
        return self.base.flush()

class JustReader:
    def __init__(self, base):
        self.base = base

    def read(self, n):
        return self.base.read(n)

    def seek(self, off, whence=0):
        return self.base.seek(off, whence)


def test_ducktyping():
    a = np.random.random((5, 5))

    s = BytesIO()
    f = JustWriter(s)

    np.save(f, a)
    f.flush()
    s.seek(0)

    f = JustReader(s)
    assert_array_equal(np.load(f), a)


def test_gzip_loadtxt():
    # Thanks to another windows brokenness, we can't use
    # NamedTemporaryFile: a file created from this function cannot be
    # reopened by another open call. So we first put the gzipped string
    # of the test reference array, write it to a securely opened file,
    # which is then read from by the loadtxt function
    s = BytesIO()
    g = gzip.GzipFile(fileobj=s, mode='w')
    g.write(b'1 2 3\n')
    g.close()

    s.seek(0)
    with temppath(suffix='.gz') as name:
        with open(name, 'wb') as f:
            f.write(s.read())
        res = np.loadtxt(name)
    s.close()

    assert_array_equal(res, [1, 2, 3])


def test_gzip_loadtxt_from_string():
    s = BytesIO()
    f = gzip.GzipFile(fileobj=s, mode="w")
    f.write(b'1 2 3\n')
    f.close()
    s.seek(0)

    f = gzip.GzipFile(fileobj=s, mode="r")
    assert_array_equal(np.loadtxt(f), [1, 2, 3])


def test_npzfile_dict():
    s = BytesIO()
    x = np.zeros((3, 3))
    y = np.zeros((3, 3))

    np.savez(s, x=x, y=y)
    s.seek(0)

    z = np.load(s)

    assert_('x' in z)
    assert_('y' in z)
    assert_('x' in z.keys())
    assert_('y' in z.keys())

    for f, a in z.items():
        assert_(f in ['x', 'y'])
        assert_equal(a.shape, (3, 3))

    for a in z.values():
        assert_equal(a.shape, (3, 3))

    assert_(len(z.items()) == 2)

    for f in z:
        assert_(f in ['x', 'y'])

    assert_('x' in z.keys())
    assert (z.get('x') == z['x']).all()


@pytest.mark.skipif(not HAS_REFCOUNT, reason="Python lacks refcounts")
def test_load_refcount():
    # Check that objects returned by np.load are directly freed based on
    # their refcount, rather than needing the gc to collect them.

    f = BytesIO()
    np.savez(f, [1, 2, 3])
    f.seek(0)

    with assert_no_gc_cycles():
        np.load(f)

    f.seek(0)
    dt = [("a", 'u1', 2), ("b", 'u1', 2)]
    with assert_no_gc_cycles():
        x = np.loadtxt(TextIO("0 1 2 3"), dtype=dt)
        assert_equal(x, np.array([((0, 1), (2, 3))], dtype=dt))


def test_load_multiple_arrays_until_eof():
    f = BytesIO()
    np.save(f, 1)
    np.save(f, 2)
    f.seek(0)
    out1 = np.load(f)
    assert out1 == 1
    out2 = np.load(f)
    assert out2 == 2
    with pytest.raises(EOFError):
        np.load(f)


def test_savez_nopickle():
    obj_array = np.array([1, 'hello'], dtype=object)
    with temppath(suffix='.npz') as tmp:
        np.savez(tmp, obj_array)

    with temppath(suffix='.npz') as tmp:
        with pytest.raises(ValueError, match="Object arrays cannot be saved when.*"):
            np.savez(tmp, obj_array, allow_pickle=False)

    with temppath(suffix='.npz') as tmp:
        np.savez_compressed(tmp, obj_array)

    with temppath(suffix='.npz') as tmp:
        with pytest.raises(ValueError, match="Object arrays cannot be saved when.*"):
            np.savez_compressed(tmp, obj_array, allow_pickle=False)