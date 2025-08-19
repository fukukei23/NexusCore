import os
import tempfile
import subprocess
import shutil
import difflib

from utils.test_generator import generate_unit_tests
from utils.repair_module import gpt_repair_code

# 非ASCIIコメントを除去する関数
def remove_non_ascii_comments(code: str) -> str:
    lines = code.splitlines()
    cleaned = []
    for line in lines:
        if "#" in line:
            code_part, comment = line.split("#", 1)
            comment = ''.join(c for c in comment if ord(c) < 128)
            cleaned.append(f"{code_part}# {comment}".rstrip())
        else:
            cleaned.append(line)
    return "\n".join(cleaned)

# 有意な変更かを判定（厳格ではなく緩やかな差分検出）
def is_meaningful_change(before: str, after: str) -> bool:
    ratio = difflib.SequenceMatcher(None, before.strip(), after.strip()).ratio()
    return ratio < 0.98

# 修正＋ユニットテスト実行
def run_test_and_repair(user_code: str, max_retries: int = 3):
    current_code = remove_non_ascii_comments(user_code)
    test_code = generate_unit_tests(current_code)
    
    os.makedirs("sandbox_output", exist_ok=True)
    
    for attempt in range(max_retries):
        print(f"\n🔁 修正サイクル {attempt + 1}")
        
        # 書き出し
        with tempfile.TemporaryDirectory() as tempdir:
            code_path = os.path.join(tempdir, "target_code.py")
            test_path = os.path.join(tempdir, "test_main.py")

            with open(code_path, "w", encoding="utf-8") as f:
                f.write(current_code)

            with open(test_path, "w", encoding="utf-8") as f:
                f.write(test_code)

            try:
                result = subprocess.run(
                    ["pytest", test_path, "-q", "--tb=short"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                    cwd=tempdir
                )
                print(result.stdout)
                print(result.stderr)

                if result.returncode == 0:
                    print("✅ テスト成功")
                    shutil.copy(code_path, "sandbox_output/final_code.py")
                    shutil.copy(test_path, "sandbox_output/test_main.py")
                    return current_code, test_code, True, result.stdout + result.stderr

            except subprocess.TimeoutExpired:
                print("⏰ テストタイムアウト")

        # 修正処理
        fixed = gpt_repair_code(current_code, test_code)
        if not is_meaningful_change(current_code, fixed):
            print("⚠️ 意味的な変化なし：強制継続")
        current_code = fixed

    print("❌ テスト失敗（最大試行回数）")
    return current_code, test_code, False, "最大試行回数を超えました"
