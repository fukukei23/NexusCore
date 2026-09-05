"""Task 18: ask確認フロー（CLI対話・タイムアウト=deny）spec §4

書く系道具（Task 17 write.py）の実行前に人間へ対話確認を求めるチャネル。
タイムアウト=deny（タイムアウト制御はループ側責務・ToolGateはask_supported=False
をdenyに倒すのみ）。

plan雛形からの変更点（実装時判断）:
- 雛形の未使用 import signal / threading を削除（select方式に不要）
- テスト可能性のため reader 関数を注入可能にした（雛形テストの
  monkeypatch(builtins.input)方式はselect()のstdin監視と非互換のため）
- store はask履歴のべき等記録用に受け取るが、結線はTask 19以降（plan §122の
  checkpoint+べき等記録はPhase 2全体スコープ）
"""
from __future__ import annotations

import select
import sys
from collections.abc import Callable
from enum import StrEnum

from nexuscore.harness.run_state import RunStateStore


class AskResult(StrEnum):
    APPROVED = "approved"
    DENIED_TIMEOUT = "denied_timeout"
    DENIED_USER = "denied_user"


def _readline_with_timeout(prompt: str, timeout: float) -> str | None:
    """select(2)でstdin監視（round7修正G#1 critical: threading.Timerは
    メインスレッドのstdinブロックを割り込めないため不可・Linux/WSL前提）"""
    print(prompt, end="", flush=True)
    ready, _, _ = select.select([sys.stdin], [], [], timeout)
    if not ready:
        print("\n[timeout]")
        return None
    return sys.stdin.readline()


class AskSession:
    """1回の道具呼び出しごとに対話確認を取る（束ね承認不可・ToolGateと対）"""

    def __init__(self, *, store: RunStateStore, timeout_seconds: float = 120.0,
                 reader: Callable[[str], str | None] | None = None) -> None:
        self.store = store  # ask履歴べき等記録用（Task 19以降で結線）
        self.timeout = timeout_seconds
        self._reader = reader or _readline_with_timeout

    def prompt(self, *, tool: str, args: dict) -> AskResult:
        msg = f"[ASK] tool={tool} args={args} → approve? (y/N, timeout {self.timeout}s): "
        ans = self._reader(msg)
        if ans is None:
            return AskResult.DENIED_TIMEOUT
        return AskResult.APPROVED if ans.strip().lower() == "y" else AskResult.DENIED_USER


def _ask_supported() -> bool:
    """TTY対話時のみask可・CI/pipe起動はask不可（=denyに倒る・安全側・round7採用）"""
    return sys.stdin.isatty()
