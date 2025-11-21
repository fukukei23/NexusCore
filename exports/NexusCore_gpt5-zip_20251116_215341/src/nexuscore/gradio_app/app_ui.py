# -*- coding: utf-8 -*-
"""
Gradio v4/5 対応：
- UI 構築とイベント結線は必ず Blocks 文脈内で行う
- launch_app_ui() は build_ui() で Blocks を受け取り queue().launch() する
"""

import os
import re
import subprocess
from pathlib import Path

import gradio as gr
from dotenv import load_dotenv
from openai import OpenAI

# ====== 設定・クライアント =====================================================

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

ROOT = Path(__file__).resolve().parents[2]  # リポジトリルート（src/ の2つ上）
SANDBOX_DIR = ROOT / "sandbox_output"
SAMPLE_FILE = SANDBOX_DIR / "sample.py"
TEST_FILE = SANDBOX_DIR / "test_sample.py"

# ====== 生成ロジック ============================================================

def save_sample_code(code: str) -> None:
    SANDBOX_DIR.mkdir(parents=True, exist_ok=True)
    SAMPLE_FILE.write_text(code, encoding="utf-8")


def extract_code(full_response: str) -> str:
    """```python ... ``` ブロックからコードのみ抽出（無ければ全文を返す）"""
    m = re.search(r"```python\n(.*?)```", full_response, re.DOTALL)
    return m.group(1).strip() if m else full_response.strip()


def generate_unit_test(code: str) -> str:
    """
    与えられた Python 関数に対する pytest スタイルのテストコードを生成
    """
    prompt = f"""
以下のPython関数に対するpytestスタイルのユニットテストを生成してください。

{code}

テストコードのみを返してください。test_sample.py というファイルに直接書き込めるような、
完全に有効なPythonコードのみが必要です。前置きや結びの言葉、説明文は一切不要です。
**生成するすべてのコードを単一の「```python」と「```」ブロックで必ず囲んでください。**
**`sample.py` から `is_prime` 関数をインポートする行を含めてください。**
""".strip()

    rsp = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
    )
    return extract_code(rsp.choices[0].message.content.strip())


def save_test_code(code: str) -> None:
    SANDBOX_DIR.mkdir(parents=True, exist_ok=True)
    TEST_FILE.write_text(code, encoding="utf-8")


def run_pytest() -> str:
    """
    生成した test_sample.py を pytest で実行して結果を返す
    """
    try:
        result = subprocess.run(
            ["pytest", str(TEST_FILE)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=str(ROOT),  # ルートで実行（相対 import を安定させる）
        )
        out = result.stdout or ""
        if result.stderr:
            out += ("\n" if out else "") + result.stderr
        return out
    except FileNotFoundError:
        return "⚠️ pytest が見つかりません。`pip install pytest` を実行してください。"
    except Exception as e:
        return f"❌ pytest 実行エラー: {e}"


def process_code(code: str):
    """
    Gradio から呼ばれるハンドラ
    入力: code → 出力: (生成テストコード, 実行結果)
    """
    if not code.strip():
        return "", "💡 Python関数を入力してください。"

    try:
        save_sample_code(code)
        test_code = generate_unit_test(code)
        save_test_code(test_code)
        test_result = run_pytest()
        return test_code, test_result
    except Exception as e:
        return "", f"❌ エラー: {e}"

# ====== UI 構築（Blocks 内でコンポーネントとイベントを定義） =====================

def build_ui() -> gr.Blocks:
    with gr.Blocks(theme=gr.themes.Soft(), fill_height=True) as demo:
        gr.Markdown("## ✅ Python関数 → ユニットテスト自動生成＆実行")
        gr.Markdown("ChatGPT が pytest 形式のテストコードを生成し、自動で実行します。")

        with gr.Row():
            with gr.Column():
                code_input = gr.Code(
                    label="📝 Python関数を入力",
                    language="python",
                    lines=12,
                    value="""def is_prime(n):
    if n < 2:
        return False
    for i in range(2, int(n**0.5) + 1):
        if n % i == 0:
            return False
    return True
""",
                )
                generate_button = gr.Button("🔁 テスト生成＆実行", variant="primary")

            with gr.Column():
                test_output = gr.Code(
                    label="✅ 生成されたユニットテスト",
                    language="python",
                    lines=12,
                    interactive=False,
                )
                result_output = gr.Textbox(
                    label="🧪 pytest 実行結果",
                    lines=18,
                    interactive=False,
                )

        # イベント結線（※ 必ず Blocks 文脈内）
        generate_button.click(
            fn=process_code,
            inputs=[code_input],
            outputs=[test_output, result_output],
            queue=True,
        )

    return demo


def launch_app_ui(
    server_name: str = "127.0.0.1",
    server_port: int = 7860,
    inbrowser: bool = False,
    share: bool = False,
) -> None:
    demo = build_ui()
    demo.queue().launch(
        server_name=server_name,
        server_port=server_port,
        inbrowser=inbrowser,
        share=share,
        show_error=True,
    )


if __name__ == "__main__":
    launch_app_ui()
