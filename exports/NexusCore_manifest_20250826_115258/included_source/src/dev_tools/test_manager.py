# test_manager.py
import os
import sys
from dotenv import load_dotenv

# 環境変数読み込み
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")

# モジュールパスを追加（src配下を明示）
BASE_DIR = os.path.dirname(os.path.dirname(__file__))  # src/
sys.path.append(BASE_DIR)
sys.path.append(os.path.join(BASE_DIR, "modules"))

# モジュールインポート（例）
try:
    from whisper_handler import transcribe_audio
    from code_generator import generate_code_from_text
    from tester import save_and_test_code
    from diff_viewer import generate_diff
except ImportError as e:
    print(f"❌ モジュールの読み込みに失敗しました: {e}")
    sys.exit(1)

# テスト関数
def run_all_tests(audio_path=None, transcript_text=None):
    if not api_key:
        print("❌ .envにOPENAI_API_KEYが定義されていません。")
        return

    print("✅ OpenCodeInterpreter テスト開始\n")

    if audio_path:
        print(f"🎤 音声ファイル文字起こし: {audio_path}")
        transcript = transcribe_audio(audio_path)
    elif transcript_text:
        print(f"📝 指定されたテキストからコード生成：{transcript_text}")
        transcript = transcript_text
    else:
        print("⚠️ 音声ファイルまたはテキストを指定してください。")
        return

    print("\n🧠 GPTコード生成中...")
    code = generate_code_from_text(transcript)
    print("\n" + code)

    print("\n🧪 テスト実行中...")
    result = save_and_test_code(code)
    print("\n" + result)

    print("\n🔍 差分表示...")
    diff = generate_diff("", code)
    print(diff)

    print("\n✅ テスト完了")

# 実行例（任意の音声 or テキストで切り替え）
if __name__ == "__main__":
    # audio_path = os.path.join(BASE_DIR, "sandbox_output", "sample_audio.wav")
    audio_path = None  # 音声ファイルがない場合は None
    transcript_text = "偶数か奇数かを判定するPython関数を作成して"

    run_all_tests(audio_path, transcript_text)
