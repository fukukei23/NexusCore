# C:\Users\USER\tools\OpenCodeInterpreter\src\utils\test_utils.py

import subprocess
import sys
import os
import locale # OSの言語設定を取得するためのライブラリをインポート

def run_tests(project_path: str) -> tuple[bool, str]:
    """
    指定されたプロジェクトパスでpytestを実行し、成功したかどうかと、
    その出力結果を返します。
    """
    try:
        python_executable = sys.executable
        
        # --- ★★★★★ ここが最重要修正点 ★★★★★ ---
        # OSが使用しているデフォルトの文字コード（方言）を自動で取得します。
        # これにより、Windows, Mac, Linuxなど、どの環境でも柔軟に対応できます。
        preferred_encoding = locale.getpreferredencoding(False)
        print(f"🔧 使用する文字コード: {preferred_encoding}")

        result = subprocess.run(
            [python_executable, "-m", "pytest"],
            cwd=project_path,
            capture_output=True,
            text=True,
            encoding=preferred_encoding, # 自動取得した文字コードを使用
            errors='replace',            # 万が一変換できない文字があっても、?に置き換えて処理を続行する
            check=False
        )
        
        # UnicodeDecodeErrorで結果がNoneになる可能性を考慮し、安全に結合します。
        stdout = result.stdout if result.stdout is not None else ""
        stderr = result.stderr if result.stderr is not None else ""
        output = stdout + "\n" + stderr
        
        return result.returncode == 0, output

    except FileNotFoundError:
        return False, "pytestコマンドが見つかりませんでした。仮想環境が有効で、pytestがインストールされているか確認してください。"
    except Exception as e:
        return False, f"テスト実行中に予期せぬエラーが発生しました: {e}"

