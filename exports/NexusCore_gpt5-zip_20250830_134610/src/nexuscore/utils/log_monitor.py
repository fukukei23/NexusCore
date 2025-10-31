import threading
import time
import os
from auto_cycle_manager import auto_repair_cycle

LOG_FILE = "run.log"
WATCH_DIR = "watch_folder"
already_seen = set()

def log_watcher():
    print("🔍 エラーログ監視中...")
    while True:
        for filename in os.listdir(WATCH_DIR):
            if filename.endswith(".py") and filename not in already_seen:
                filepath = os.path.join(WATCH_DIR, filename)
                with open(filepath, "r", encoding="utf-8") as f:
                    code = f.read()
                print(f"📄 新ファイル検知: {filename}")
                fixed_code, output = auto_repair_cycle(code)
                with open(filepath.replace(".py", "_fixed.py"), "w", encoding="utf-8") as f:
                    f.write(fixed_code)
                already_seen.add(filename)
        time.sleep(10)

threading.Thread(target=log_watcher, daemon=True).start()

