# src/gradio_app/app_ui.py

import gradio as gr
import os
import subprocess
from openai import OpenAI
from dotenv import load_dotenv
import re

# .env から OPENAI_API_KEY を読み込み
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ファイル保存先
SAMPLE_FILE = "./sandbox_output/sample.py"
TEST_FILE = "./sandbox_output/test_sample.py"

def save_sample_code(code: str):
    os.makedirs(os.path.dirname(SAMPLE_FILE), exist_ok=True)
    with open(SAMPLE_FILE, "w", encoding="utf-8") as f:
        f.write(code)

def extract_code(full_response: str) -> str:
    match = re.search(r"```python\n(.*?)```", full_response, re.DOTALL)
    if match:
        return match.group(1).strip()
    code = full_response
    code = re.sub(r'^(Sure.*?pytest-style unit test.*?`is_prime\(n\)`:?\s*\n)?', '', code, flags=re.MULTILINE | re.IGNORECASE)
    code = re.sub(r'(\n?This test.*$|\n?Please note.*$)', '', code, flags=re.DOTALL)
    return code.strip()

def generate_unit_test(code: str) -> str:
    prompt = f"""
以下のPython関数に対するpytestスタイルのユニットテストを生成してください。

{code}

テストコードのみを返してください。test_sample.pyというファイルに直接書き込めるような、完全に有効なPythonコードのみが必要です。
前置きや結びの言葉、説明文は一切含めないでください。
**生成するすべてのコードを単一の「```python」と「```」ブロックで必ず囲んでください。**
**`sample.py`から`is_prime`関数をインポートする行を含めてください。**
"""
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )
    return extract_code(response.choices[0].message.content.strip())

def save_test_code(code: str):
    os.makedirs(os.path.dirname(TEST_FILE), exist_ok=True)
    with open(TEST_FILE, "w", encoding="utf-8") as f:
        f.write(code)

def run_pytest() -> str:
    try:
        result = subprocess.run(
            ["pytest", TEST_FILE],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=os.path.dirname(os.path.abspath(__file__))
        )
        output = result.stdout
        if result.stderr:
            output += "\n" + result.stderr
        return output
    except FileNotFoundError:
        return "⚠️ エラー: pytestが見つかりません。\n`pip install pytest` を実行してください。"
    except Exception as e:
        return f"⚠️ pytest実行中に予期せぬエラーが発生しました: {e}"

def process_code(code: str):
    if not code.strip():
        return "", "💡 Python関数を入力してください。"
    save_sample_code(code)
    try:
        test_code = generate_unit_test(code)
        save_test_code(test_code)
        test_result = run_pytest()
        return test_code, test_result
    except Exception as e:
        return "", f"❌ エラー: {e}\nAPIキー、ネットワーク、または生成コードに問題がある可能性があります。"

# GradioタブUIを構築
def launch_app_ui():
    with gr.Column():
        gr.Markdown("## ✅ Python関数入力 → ユニットテスト生成 → 自動実行")
        gr.Markdown("ChatGPTがpytest形式のテストコードを生成し、自動実行します。")

        code_input = gr.Code(
            label="📝 Python関数を入力", 
            language="python", 
            lines=10, 
            value="""def is_prime(n):
    if n < 2:
        return False
    for i in range(2, int(n**0.5) + 1):
        if n % i == 0:
            return False
    return True"""
        )
        generate_button = gr.Button("🔁 テスト生成＆実行")

        test_output = gr.Code(label="✅ 生成されたユニットテスト", language="python", lines=10, interactive=False)
        result_output = gr.Textbox(label="🧪 pytest実行結果", lines=15, interactive=False)

        generate_button.click(
            fn=process_code,
            inputs=code_input,
            outputs=[test_output, result_output]
        )
