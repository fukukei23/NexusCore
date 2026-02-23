# modules/history_viewer.py

import json
import os


def load_history(directory="patch_history"):
    entries = []
    for file in sorted(os.listdir(directory), reverse=True):
        if file.endswith(".json"):
            with open(os.path.join(directory, file), encoding="utf-8") as f:
                data = json.load(f)
                entries.append(
                    {
                        "time": data["timestamp"],
                        "result": (
                            "✅ Success"
                            if "failed" not in data.get("test_log", "")
                            else "❌ Failed"
                        ),
                        "reason": data.get("reason", "")[:200] + "...",
                    }
                )
    return entries


def format_history_markdown(entries):
    md = "# 🧾 修正履歴一覧\n"
    for e in entries:
        md += f"### {e['time']} - {e['result']}\n- {e['reason']}\n\n"
    return md
