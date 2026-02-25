# modules/tester.py

import os
import subprocess

SANDBOX_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "sandbox_output"))
SAMPLE_FILE = os.path.join(SANDBOX_DIR, "sample.py")
TEST_FILE = os.path.join(SANDBOX_DIR, "test_sample.py")
RESULT_LOG = os.path.join(SANDBOX_DIR, "test_result.log")


# 保存＋pytest実行
def save_and_test_code(code: str) -> str:
    os.makedirs(SANDBOX_DIR, exist_ok=True)

    with open(SAMPLE_FILE, "w", encoding="utf-8") as f:
        f.write(code)

    if not os.path.exists(TEST_FILE):
        with open(TEST_FILE, "w", encoding="utf-8") as f:
            f.write(
                """import sample

def test_dummy():
    assert hasattr(sample, '__doc__')  # ダミー
"""
            )

    try:
        result = subprocess.run(
            ["pytest", TEST_FILE], capture_output=True, text=True
        )
        output = result.stdout + "\n" + result.stderr
        with open(RESULT_LOG, "w", encoding="utf-8") as f:
            f.write(output)
        return output
    except Exception as e:
        return f"⚠️ Test failed: {e}"
