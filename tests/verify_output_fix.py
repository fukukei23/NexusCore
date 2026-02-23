#!/usr/bin/env python3
"""
verify_output_fix.py

WSL環境での出力取得問題の検証スクリプト。
ログファイルに結果を書き込むことで、Cursorのrun_terminal_cmdでも結果を確認できる。
"""

import os
import subprocess
import sys
from datetime import datetime


def main():
    log_file = "verify_output_fix.log"

    with open(log_file, "w", encoding="utf-8") as f:
        f.write(f"=== 検証開始: {datetime.now().isoformat()} ===\n")
        f.flush()

        # テスト1: 基本的なコマンド
        f.write("\n[テスト1] echo コマンド\n")
        f.flush()
        try:
            result = subprocess.run(
                ["echo", "Hello from WSL"], capture_output=True, text=True, timeout=5
            )
            f.write(f"  終了コード: {result.returncode}\n")
            f.write(f"  出力: {result.stdout}\n")
            f.write(f"  エラー: {result.stderr}\n")
        except Exception as e:
            f.write(f"  エラー: {e}\n")
        f.flush()

        # テスト2: Pythonスクリプトの実行
        f.write("\n[テスト2] Pythonスクリプト\n")
        f.flush()
        try:
            result = subprocess.run(
                [
                    sys.executable,
                    "-c",
                    "print('Python test output'); import sys; sys.stdout.flush()",
                ],
                capture_output=True,
                text=True,
                timeout=5,
                env={**os.environ, "PYTHONUNBUFFERED": "1"},
            )
            f.write(f"  終了コード: {result.returncode}\n")
            f.write(f"  出力: {result.stdout}\n")
            f.write(f"  エラー: {result.stderr}\n")
        except Exception as e:
            f.write(f"  エラー: {e}\n")
        f.flush()

        # テスト3: run_test_with_immediate_output.py の動作確認
        f.write("\n[テスト3] run_test_with_immediate_output.py の動作確認\n")
        f.flush()
        script_path = "run_test_with_immediate_output.py"
        if os.path.exists(script_path):
            f.write(f"  ✓ スクリプトが存在します: {script_path}\n")
            try:
                result = subprocess.run(
                    [sys.executable, script_path, "--help"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                f.write(f"  終了コード: {result.returncode}\n")
                if result.stdout:
                    f.write("  出力（最初の5行）:\n")
                    for line in result.stdout.split("\n")[:5]:
                        f.write(f"    {line}\n")
            except Exception as e:
                f.write(f"  エラー: {e}\n")
        else:
            f.write(f"  ✗ スクリプトが見つかりません: {script_path}\n")
        f.flush()

        # テスト4: シェルスクリプトの動作確認
        f.write("\n[テスト4] tools/run_with_output.sh の動作確認\n")
        f.flush()
        script_path = "tools/run_with_output.sh"
        if os.path.exists(script_path):
            f.write(f"  ✓ スクリプトが存在します: {script_path}\n")
            if os.access(script_path, os.X_OK):
                f.write("  ✓ 実行権限があります\n")
            else:
                f.write("  ✗ 実行権限がありません\n")
        else:
            f.write(f"  ✗ スクリプトが見つかりません: {script_path}\n")
        f.flush()

        f.write(f"\n=== 検証完了: {datetime.now().isoformat()} ===\n")
        f.flush()

    # ログファイルの内容を標準出力にも表示（可能な場合）
    try:
        with open(log_file, encoding="utf-8") as f:
            content = f.read()
            # 標準出力に出力を試みる（WSL環境では表示されない可能性がある）
            print(content, flush=True)
    except Exception:
        pass

    print(f"\n✅ 検証結果をログファイルに保存しました: {log_file}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
