# src/gradio_app/interactive_generator.py
import gradio as gr
import os
import re
import difflib
import subprocess
from datetime import datetime
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

DEFAULT_OUTPUT_DIR = "../sandbox_output"
DEFAULT_FILENAME = "sample.py"
LOG_FILE = "../logs/save_log.txt"
os.makedirs(DEFAULT_OUTPUT_DIR, exist_ok=True)
os.makedirs("../logs", exist_ok=True)

# === GPT呼び出し ===
def call_gpt(prompt):
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )
    return response.choices[0].message.content.strip()

# === コードと理由の抽出 ===
def extract_code_and_reason(full_response):
    code_match = re.search(r"```(?:python)?\n(.*?)```", full_response, re.DOTALL)
    reason_match = re.split(r"```.*?```", full_response, maxsplit=1)
    code = code_match.group(1).strip() if code_match else ""
    reason = reason_match[1].strip() if len(reason_match) > 1 else ""
    return code, reason

# === ファイルパス抽出 ===
def extract_file_path_from_code(code: str, default_path: str = os.path.join(DEFAULT_OUTPUT_DIR, DEFAULT_FILENAME)) -> str:
    match = re.search(r"#\s*filepath\s*:\s*(.+\.py)", code)
    if match:
        return match.group(1).strip()
    return default_path

# === 差分取得 ===
def get_diff(old, new):
    diff = difflib.HtmlDiff().make_file(old.splitlines(), new.splitlines(), context=True)
    return diff

# === バージョン番号付与 ===
def get_versioned_path(path):
    base, ext = os.path.splitext(path)
    i = 2
    while os.path.exists(path):
        path = f"{base}_v{i}{ext}"
        i += 1
    return path

# === ファイル保存 ===
def save_code_with_backup_and_diff(code: str, user_path: str):
    try:
        save_path = extract_file_path_from_code(code, default_path=user_path)
        full_path = os.path.join("..", save_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)

        diff_html = ""
        if os.path.exists(full_path):
            with open(full_path, "r", encoding="utf-8") as f:
                old_code = f.read()
            diff_html = get_diff(old_code, code)
            backup_path = full_path + ".bak"
            with open(backup_path, "w", encoding="utf-8") as f:
                f.write(old_code)
            save_path = get_versioned_path(full_path)  # avoid overwrite

        with open(save_path, "w", encoding="utf-8") as f:
            f.write(code)

        with open(LOG_FILE, "a", encoding="utf-8") as log:
            log.write(f"{datetime.now()} - Saved: {save_path}\n")

        return f"✅ 保存成功: {save_path}", diff_html

    except Exception as e:
        return f"❌ 保存失敗: {str(e)}", ""

# === Gradio UI ===
with gr.Blocks() as app:
    gr.Markdown("### 🧐 自然文からAI補足付き 初期コード自動生成")

    initial_input = gr.Textbox(label="📝 やりたいこと（自然文）")
    output_path_input = gr.Textbox(label="📂 保存先（例: src/utils/my_func.py）", value="src/generated/sample.py")
    submit_btn = gr.Button("🔍 質問を開始")
    gpt_question = gr.Textbox(label="🤠 GPTの補足質問", lines=2)
    user_reply = gr.Textbox(label="✍️ 回答を記入")
    loop_again_btn = gr.Button("🔁 さらに質問してほしい")
    generate_code_btn = gr.Button("✅ これでコード生成してよい")
    code_output = gr.Code(label="📄 GPTによる初期コード", language="python")
    save_result = gr.Textbox(label="✅ 保存結果メッセージ", interactive=False)
    file_list = gr.Dropdown(label="🗂 保存済みファイル一覧", choices=[])
    open_in_vscode_btn = gr.Button("🖥 VSCodeで開く")
    diff_output = gr.HTML(label="📌 差分表示（HTML強調）")
    history = gr.State("")

    def ask_gpt_question(user_goal, prev_answers):
        prompt = f"""
以下はユーザーの目的です。
これに基づいて、実装前に補足確認すべき点を最大3点、質問形式で出力してください。
すでに以下の回答が得られています：
{prev_answers}

【ユーザー目的】
{user_goal}
"""
        return call_gpt(prompt)

    def update_history(history_text, question, answer):
        return history_text + f"【GPTの質問】\n{question}\n【ユーザーの回答】\n{answer}\n\n"

    def ask_more_questions(user_goal, current_answer, prev_q, hist):
        new_hist = update_history(hist, prev_q, current_answer)
        next_q = ask_gpt_question(user_goal, new_hist)
        return next_q, new_hist

    def generate_final_code(user_goal, hist, output_path):
        final_prompt = f"""
以下はユーザーの実施目的と、事前の質問・回答のやりとり履歴です。
この情報に基づき、docstring付きのPython関数を一つ作成してください。

【目的】
{user_goal}

【補足内容】
{hist}
"""
        response = call_gpt(final_prompt)
        code, _ = extract_code_and_reason(response)
        result, diff = save_code_with_backup_and_diff(code, output_path)
        return code, result, diff

    def list_saved_files():
        file_paths = []
        for root, _, files in os.walk("../src"):
            for f in files:
                if f.endswith(".py"):
                    rel_path = os.path.relpath(os.path.join(root, f), "../")
                    file_paths.append(rel_path)
        return sorted(file_paths)

    def open_file_in_vscode(file_path):
        try:
            subprocess.Popen(["code", os.path.join("..", file_path)])
            return f"🖥 VSCodeで開きました: {file_path}"
        except Exception as e:
            return f"❌ VSCode起動失敗: {str(e)}"

    submit_btn.click(fn=ask_gpt_question, inputs=[initial_input, history], outputs=[gpt_question])
    loop_again_btn.click(fn=ask_more_questions, inputs=[initial_input, user_reply, gpt_question, history], outputs=[gpt_question, history])
    generate_code_btn.click(fn=generate_final_code, inputs=[initial_input, history, output_path_input], outputs=[code_output, save_result, diff_output])
    generate_code_btn.click(fn=list_saved_files, inputs=[], outputs=[file_list])
    open_in_vscode_btn.click(fn=open_file_in_vscode, inputs=[file_list], outputs=[save_result])