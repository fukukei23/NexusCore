# OpenCodeInterpreter 拡張：反復AI修正ループ・バージョン管理付きGradioアプリ

import json
import os
import re
import subprocess
from datetime import datetime
from typing import TYPE_CHECKING, Optional

import gradio as gr
from dotenv import load_dotenv

if TYPE_CHECKING:
    from openai import OpenAI
else:
    try:
        from openai import OpenAI
    except Exception:  # pragma: no cover - when openai is missing
        OpenAI = None  # type: ignore[assignment,misc]

# === 設定と初期化 ===
load_dotenv()
_client: Optional["OpenAI"] = None


def get_client() -> "OpenAI":
    """Lazy-load OpenAI client to avoid import時のAPIキー不足で落ちるのを防ぐ。"""
    global _client
    if _client is not None:
        return _client
    if OpenAI is None:
        raise RuntimeError("openai SDK is not installed. Please install `openai`.")
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set. Provide it via env or .env file.")
    _client = OpenAI(api_key=api_key)
    return _client


# === パス設定 ===
SANDBOX_DIR = "../sandbox_output"
SAMPLE_FILE = os.path.join(SANDBOX_DIR, "sample.py")
TEST_FILE = os.path.join(SANDBOX_DIR, "test_sample.py")
RESULT_LOG = os.path.join(SANDBOX_DIR, "test_result.log")
HISTORY_DIR = "patch_history"
os.makedirs(HISTORY_DIR, exist_ok=True)


# === ファイル保存 ===
def save_file(path, content):
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def read_file(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


# === テスト実行 ===
def run_pytest():
    try:
        result = subprocess.run(["pytest", TEST_FILE], capture_output=True, text=True)
        output = result.stdout + "\n" + result.stderr
        save_file(RESULT_LOG, output)
        return output
    except Exception as e:
        return f"⚠️ pytest execution failed: {e}"


# === GPTプロンプト生成 ===
def generate_prompt(
    main_file, related_files, version_summary, history_summary, failed_tests, user_instruction
):
    return f"""
【前提】
- 対象ファイル: {main_file}
- 関連ファイル・依存関係: {related_files}
- 現在のバージョン: {version_summary}
- 修正履歴: {history_summary}
- 直近のテスト失敗内容: {failed_tests}
- ユーザーからの追加指示: {user_instruction}

【タスク】
1. 上記情報をもとに、{main_file}の修正版を提案してください。
2. 修正内容の要約と、なぜその修正が必要かを簡潔に説明してください。
3. 依存ファイルや関連箇所に問題があれば、修正案に含めてください。
4. テストが通らない場合は、失敗理由・考えられる原因・追加で見直すべき点を解説してください。
5. 修正案は必ず「コードブロック」で出力し、説明文と分けてください。

【出力フォーマット例】
---
【修正版コード】
ここに修正版コード

【修正理由・要約】
- 主な修正点:
- 修正が必要な理由:
- 依存関係の見直し点:
- テスト失敗時の考察:
---
"""


# === GPT呼び出しとコード抽出 ===
def extract_code_and_reason(full_response):
    code_match = re.search(r"```(?:python)?\n(.*?)```", full_response, re.DOTALL)
    reason_match = re.split(r"```.*?```", full_response, maxsplit=1, flags=re.DOTALL)
    code = code_match.group(1).strip() if code_match else ""
    reason = reason_match[1].strip() if len(reason_match) > 1 else ""
    return code, reason


def call_gpt(prompt):
    client = get_client()
    response = client.chat.completions.create(
        model="gpt-4", messages=[{"role": "user", "content": prompt}], temperature=0
    )
    return response.choices[0].message.content.strip()


# === 履歴保存 ===
def save_patch_history(code, reason, prompt):
    now = datetime.now().strftime("%Y%m%d_%H%M%S")
    data = {
        "timestamp": now,
        "code": code,
        "reason": reason,
        "prompt": prompt,
        "test_log": read_file(RESULT_LOG) if os.path.exists(RESULT_LOG) else "",
    }
    save_file(
        os.path.join(HISTORY_DIR, f"patch_{now}.json"),
        json.dumps(data, indent=2, ensure_ascii=False),
    )


# === Gradio UI ===
with gr.Blocks() as demo:
    gr.Markdown("## 🛠 安全・納得・AIアシスト型修正フロー")

    code_input = gr.Code(label="📝 修正対象コード", language="python")
    user_instruction = gr.Textbox(label="🧠 ユーザーからの追加指示")
    test_failures = gr.Textbox(label="❌ 直近のテスト失敗ログ", lines=5)

    generated_code = gr.Code(label="✅ 修正版コード", language="python")
    explanation = gr.Textbox(label="📄 修正理由・要約")
    test_result = gr.Textbox(label="🧪 pytest実行結果", lines=10)

    approve_btn = gr.Button("✅ 承認して上書き")
    revise_btn = gr.Button("🔁 AI修正案を再生成")

    def generate_revision(user_code, user_note, fail_log):
        version_summary = "現行バージョンはユーザー入力の内容"
        history = "履歴は直近の1回のみ"
        prompt = generate_prompt(
            "sample.py", "test_sample.py", version_summary, history, fail_log, user_note
        )
        gpt_response = call_gpt(prompt)
        code, reason = extract_code_and_reason(gpt_response)
        return code, reason, prompt

    def apply_patch(generated_code, reason, prompt):
        save_file(SAMPLE_FILE, generated_code)
        save_patch_history(generated_code, reason, prompt)
        result = run_pytest()
        return result

    revise_btn.click(
        fn=generate_revision,
        inputs=[code_input, user_instruction, test_failures],
        outputs=[generated_code, explanation, user_instruction],
    )
    approve_btn.click(
        fn=apply_patch,
        inputs=[generated_code, explanation, user_instruction],
        outputs=[test_result],
    )

if __name__ == "__main__":
    demo.launch()


def launch_revision_ui():
    with gr.Row():
        # ここに反復AI修正ループの UI を構成
        gr.Markdown("### 🔁 反復AI修正ループ & バージョン管理")
        # 元の Blocks の中身をここにコピーしてください（demo = gr.Blocks() の中身だけ）
