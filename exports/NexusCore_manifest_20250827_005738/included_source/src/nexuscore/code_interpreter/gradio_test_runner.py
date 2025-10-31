import os
import subprocess

def save_test_and_run(test_code: str, filename: str = "test_sample.py", work_dir: str = "."):
    """
    `test_code`を指定されたディレクトリに保存し、その後pytestで自動実行します。

    Parameters:
    - test_code (str): 保存するテストコード（pytest形式）
    - filename (str): 保存するファイル名（デフォルト: test_sample.py）
    - work_dir (str): 保存・実行するディレクトリパス（デフォルト: カレント）

    Returns:
    - dict: {'file': ファイルパス, 'result': pytest実行結果, 'exit_code': 終了コード}
    """
    filepath = os.path.join(work_dir, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(test_code)

    print(f"✅ テストコードを {filepath} に保存しました。")

    try:
        result = subprocess.run(
            ["pytest", filename],
            cwd=work_dir,
            capture_output=True,
            text=True
        )
        print("🧪 pytest 実行結果:")
        print(result.stdout)
        if result.stderr:
            print("⚠️ stderr:")
            print(result.stderr)

        return {
            "file": filepath,
            "result": result.stdout,
            "exit_code": result.returncode
        }

    except Exception as e:
        print(f"❌ エラー: {e}")
        return {
            "file": filepath,
            "result": str(e),
            "exit_code": -1
        }
