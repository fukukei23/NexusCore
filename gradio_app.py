import gradio as gr
import os
import re

def save_to_sample_py(code_str):
    """sample.py に関数コードを保存する"""
    with open("sample.py", "w", encoding="utf-8") as f:
        f.write(code_str.strip())
    return "✅ sample.py に保存されました。"

def extract_function_name(code_str):
    """関数名を抽出（最初の def xxx(...) を探す）"""
    match = re.search(r'def\s+(\w+)\s*\(', code_str)
    return match.group(1) if match else None

def generate_test_code(code_str):
    """pytest 形式のテストコードを生成"""
    func_name = extract_function_name(code_str)
    if not func_name:
        return "⚠️ 関数が見つかりません。先に正しい Python 関数を入力してください。"

    test_code = f'''# test_sample.py
import pytest
from sample import {func_name}

def test_{func_name}():
    # ✅ ここは任意で編集してください（例：is_prime 用のテスト例）
    assert {func_name}(2) == True
    assert {func_name}(4) == False
    assert {func_name}(5) == True
    assert {func_name}(0) == False
    assert {func_name}(-1) == False
'''
    return test_code

def save_test_py(test_code):
    """生成されたテストコードを test_sample.py に保存"""
    with open("test_sample.py", "w", encoding="utf-8") as f:
        f.write(test_code.strip())
    return "✅ test_sample.py に保存されました。"

with gr.Blocks(title="Python関数→保存＋テスト生成") as demo:
    gr.Markdown("## 🧪 Python関数を入力 → sample.py に保存 → pytestコードを生成")

    code_input = gr.Code(label="✏️ Python関数を入力", language="python")

    with gr.Row():
        save_btn = gr.Button("💾 sample.py に保存")
        gen_test_btn = gr.Button("🧪 テストコード生成")
        save_test_btn = gr.Button("💾 test_sample.py に保存")

    save_output = gr.Textbox(label="保存メッセージ")
    test_output = gr.Code(label="✅ 自動生成されたユニットテスト", language="python")

    save_btn.click(fn=save_to_sample_py, inputs=code_input, outputs=save_output)
    gen_test_btn.click(fn=generate_test_code, inputs=code_input, outputs=test_output)
    save_test_btn.click(fn=save_test_py, inputs=test_output, outputs=save_output)

if __name__ == "__main__":
    demo.launch()
