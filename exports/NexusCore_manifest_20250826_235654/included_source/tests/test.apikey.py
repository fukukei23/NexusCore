from dotenv import load_dotenv, find_dotenv
import os
from openai import OpenAI

# .env を探して読み込む（カレントディレクトリ基準）
dotenv_path = find_dotenv()
print("dotenv file:", dotenv_path)
load_dotenv(dotenv_path, override=True)

api_key = os.getenv("OPENAI_API_KEY")
project_id = os.getenv("OPENAI_PROJECT")

print("API_KEY:", api_key[:5] + "...", "len:", len(api_key) if api_key else None)
print("PROJECT:", project_id)

# OpenAIクライアント生成
client = OpenAI(api_key=api_key, project=project_id)

# モデル一覧取得
models = client.models.list()
print("モデル数:", len(models.data))
