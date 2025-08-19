# src/modules/chat_handler.py

from openai import OpenAI
from dotenv import load_dotenv
import os

# .envからAPIキーを読み込む
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# チャット履歴を元にGPT応答を取得
def handle_chat(message: str, history: list) -> tuple[str, list]:
    try:
        history.append({"role": "user", "content": message})
        response = client.chat.completions.create(
            model="gpt-4",
            messages=history
        )
        assistant_msg = response.choices[0].message.content
        history.append({"role": "assistant", "content": assistant_msg})
        return assistant_msg, history
    except Exception as e:
        return f"❌ エラー: {e}", history