import os

from dotenv import find_dotenv, load_dotenv
from openai import OpenAI

# .env を探して読み込む（カレントディレクトリ基準）
dotenv_path = find_dotenv()
print("dotenv file:", dotenv_path)
load_dotenv(dotenv_path, override=True)

api_key = os.getenv("OPENAI_API_KEY")
project_id = os.getenv("OPENAI_PROJECT")

key_status = "set" if api_key else "unset"
key_length = len(api_key) if api_key else 0
print("API_KEY:", key_status, "length:", key_length)
print("PROJECT:", project_id)

if not api_key:
    print("Skipping: OPENAI_API_KEY is not set")
else:
    # OpenAIクライアント生成
    client = OpenAI(api_key=api_key, project=project_id)

    # モデル一覧取得
    models = client.models.list()
    print("モデル数:", len(models.data))
