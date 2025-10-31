# ファイル: src/nexuscore/gradio_app/revision_tab.py

import gradio as gr
import os
import re
from openai import OpenAI
from dotenv import load_dotenv

# .envファイルからAPIキーを読み込み
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

SAMPLE_FILE = "./sandbox_output/sample.py"
TEST_FILE = "./sandbox_output/test_sample.py"
HISTORY_FILE = "./sandbox_output/patch_history.txt"


def read_file(file_path: str) -> str:
    if not os.path.exists(file_path):
        return ""
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()


def save_file(file_path: str, content: str):
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)


def save_patch_history(code: str, reason: str, prompt: str):
    os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)
    with open(HISTORY_FILE, "a", encoding="utf-8") as f:
        f.write("\n=== 新しい修正案 ===\n")
        f.write("[📝 修正理由]:\n" + reason + "\n")
        f.write("[📤 GPTプロンプト]:\n" + prompt + "\n")
        f.write("[💻 修正コード]:\n" + code + "\n")


def run_pytest() -> str:
    try:
        import subprocess
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
    except Exception as e:
        return f"❌ pytest 実行エラー: {str(e)}"


def generate_prompt(sample_path: str, test_path: str, summary: str, history: str, error_log: str, user_note: str) -> str:
    sample_code = read_file(sample_path)
    test_code = read_file(test_path)

    return f"""# Context
以下はPython関数（sample.py）と対応するテスト（test_sample.py）です。

# sample.py
{sample_code}

# test_sample.py
{test_code}

# ユーザーの目的
{user_note}

# バージョン要約（最新版）
{summary}

# 修正履歴（直近）
{history}

# テスト結果
{error_log}

# 指示
上記情報を踏まえて、ユーザーが意図した動作を達成できるように `sample.py` の修正コードを提案してください。

- コードのみを返してください
- 余計な説明文、Markdown記法、```python や ``` は不要です
- すべてのコードは sample.py に直接書き込める内容にしてください
- コメントを付けるのは歓迎です
- 既存コードの行番号や差分ではなく、完全な最新コードを提示してください
"""


def extract_code_and_reason(response: str) -> tuple[str, str]:
    """
    GPTレスポンスからコード部分と修正理由を抽出。
    """
    match = re.search(r"```python\n(.*?)```", response, re.DOTALL)
    code = match.group(1).strip() if match else response.strip()

    reason_match = re.search(r"(?:(?:修正理由|Reason)[：:]?)(.*)", response)
    reason = reason_match.group(1).strip() if reason_match else "（理由が抽出できませんでした）"

    return code, reason


def call_gpt(prompt: str) -> str:
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3
    )
    return response.choices[0].message.content.strip()


def tab_revision():
    """
    Gradioタブを返す：反復修正UI
    """
    with gr.Blocks() as tab:
        gr.Markdown("## 🔁 AIによる反復コード修正とpytest実行")

        code_input = gr.Code(label="📝 修正対象のPython関数コード", language="python")
        user_instruction = gr.Textbox(label="💡 ユーザーからの要望・補足", placeholder="例：引数nが負のときはFalseを返すようにしてください")
        test_failures = gr.Textbox(label="❌ テスト失敗ログ", placeholder="pytestの失敗出力を貼り付けてください", lines=5)

        generated_code = gr.Code(label="✅ GPTが生成した修正コード", language="python")
        explanation = gr.Textbox(label="📄 修正理由と要約", lines=3)
        test_result = gr.Textbox(label="🧪 pytest 実行結果", lines=10)

        revise_btn = gr.Button("🔁 修正案を生成")
        approve_btn = gr.Button("✅ 修正案を適用して上書き")

        def generate_revision(user_code: str, user_note: str, fail_log: str):
            save_file(SAMPLE_FILE, user_code)
            prompt = generate_prompt(SAMPLE_FILE, TEST_FILE, "現行バージョンはユーザー入力", "直近の1件のみ", fail_log, user_note)
            gpt_response = call_gpt(prompt)
            code, reason = extract_code_and_reason(gpt_response)
            return code, reason, prompt

        def apply_patch(code: str, reason: str, prompt: str):
            save_file(SAMPLE_FILE, code)
            save_patch_history(code, reason, prompt)
            return run_pytest()

        revise_btn.click(
            fn=generate_revision,
            inputs=[code_input, user_instruction, test_failures],
            outputs=[generated_code, explanation, user_instruction]
        )

        approve_btn.click(
            fn=apply_patch,
            inputs=[generated_code, explanation, user_instruction],
            outputs=test_result
        )

    return tab
