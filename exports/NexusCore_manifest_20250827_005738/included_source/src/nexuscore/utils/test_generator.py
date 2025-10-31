# 📁 test_generator.py
# 📂 保存場所: /src/utils/test_generator.py

from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def generate_unit_tests(code: str) -> str:
    prompt = f"""次のPythonコードに対して、pytest形式のユニットテストを生成してください。

# 対象コード
{code}

# 出力形式（必須）
```python
# test_sample.py
import pytest

# ユニットテスト内容
# ...
```"""

    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "あなたは優秀なPythonのテストエンジニアです。"},
            {"role": "user", "content": prompt}
        ],
        temperature=0.3,
    )

    return response.choices[0].message.content
