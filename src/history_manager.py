# ファイル名: history_manager.py
import json
import os
from datetime import datetime
from typing import Any


class HistoryManager:
    def __init__(self, history_dir="history", prefix="history_"):
        self.history_dir = history_dir
        self.prefix = prefix
        os.makedirs(history_dir, exist_ok=True)
        self.history_path = self._generate_new_path()
        self.state_history: list[dict[str, Any]] = []
        self.current_index: int = -1

    def _generate_new_path(self):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return os.path.join(self.history_dir, f"{self.prefix}{timestamp}.json")

    def add_state(self, state: dict[str, Any]):
        # 未来の履歴を切り捨ててから追加
        self.state_history = self.state_history[: self.current_index + 1]
        self.state_history.append(state)
        self.current_index += 1
        self.save_history()

    def rollback(self):
        if self.current_index > 0:
            self.current_index -= 1
            self.save_history()
            return self.state_history[self.current_index]
        else:
            print("Already at oldest state")
            return self.state_history[0] if self.state_history else None

    def get_current_state(self):
        if self.current_index >= 0:
            return self.state_history[self.current_index]
        return None

    def save_history(self):
        with open(self.history_path, "w", encoding="utf-8") as f:
            json.dump(
                {"history": self.state_history, "current_index": self.current_index},
                f,
                ensure_ascii=False,
                indent=2,
            )
