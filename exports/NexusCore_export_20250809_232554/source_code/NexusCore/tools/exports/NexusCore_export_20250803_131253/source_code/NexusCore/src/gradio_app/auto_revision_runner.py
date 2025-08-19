# auto_revision_runner.py
import os
import sys
import time
import json
from datetime import datetime
from revision_loop import generate_prompt, extract_code_and_reason, call_gpt, run_pytest, save_file, read_file, save_patch_history

SANDBOX_DIR = "../sandbox_output"
SAMPLE_FILE = os.path.join(SANDBOX_DIR, "sample.py")
TEST_FILE = os.path.join(SANDBOX_DIR, "test_sample.py")

MAX_RETRIES = 5

def auto_loop(user_instruction=""):
    retry_count = 0

    while retry_count < MAX_RETRIES:
        print(f"\n🔁 [Attempt {retry_count + 1}/{MAX_RETRIES}] Generating revision...")

        version_summary = f"自動反復試行 {retry_count + 1} 回目"
        history = f"試行回数: {retry_count}"
        failed_tests = read_file(os.path.join(SANDBOX_DIR, "test_result.log")) if os.path.exists(os.path.join(SANDBOX_DIR, "test_result.log")) else ""

        prompt = generate_prompt("sample.py", "test_sample.py", version_summary, history, failed_tests, user_instruction)
        gpt_response = call_gpt(prompt)
        code, reason = extract_code_and_reason(gpt_response)

        save_file(SAMPLE_FILE, code)
        save_patch_history(code, reason, prompt)

        result = run_pytest()
        print("🧪 テスト結果:\n", result)

        if "failed" not in result.lower():
            print(f"\n✅ テストに成功しました（{retry_count+1} 回目）")
            break
        else:
            print("❌ テスト失敗、再修正を試みます…")

        retry_count += 1

    if retry_count == MAX_RETRIES:
        print(f"\n⚠️ 最大試行回数 {MAX_RETRIES} に達しました。テスト未合格。")

if __name__ == "__main__":
    # 任意で命令文を指定可能（なければ空文字）
    user_instruction = "assert文を満たすよう修正してください"
    auto_loop(user_instruction)
