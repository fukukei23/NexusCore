# live_lint_checker.py

import time
import threading
import subprocess

def run_lint(filepath: str) -> str:
    result = subprocess.run(["pylint", filepath], capture_output=True, text=True)
    return result.stdout

def live_lint_checker(filepath: str, callback):
    def loop():
        last_code = None
        while True:
            try:
                with open(filepath) as f:
                    code = f.read()
                if code != last_code:
                    result = run_lint(filepath)
                    callback(result)
                    last_code = code
            except Exception as e:
                callback(f"[ERROR] {e}")
            time.sleep(0.5)

    threading.Thread(target=loop, daemon=True).start()
