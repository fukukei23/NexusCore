from openai import OpenAI
import os

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def suggest_fix(error_log, original_code):
    prompt = f"""
以下のPythonコードにはバグがあります。

コード:
{original_code}

エラー:
{error_log}

修正コードを提案してください（関数単位で）。
"""
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content.strip()
