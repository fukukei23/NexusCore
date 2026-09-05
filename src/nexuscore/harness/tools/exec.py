"""Task 20: 撃つ系（run_command）— Phase 3

⚠️ セキュリティ設計（plan本文のsecurity-guidance指摘の反映）:
本道具は「LLMが選んだコマンドを意図的に実行する」ため shell=True が必須。
安全性は subprocess 自体でなく
1. ToolGateの deny_patterns（禁止コマンド部分一致・即DENY）
2. default: ask（人間承認・AskSession経由）
3. タイムアウト+出力上限
の3層で担保する。policy未登録=ゲート全拒否（fail-closed・write系と同一）。

plan雛形からの変更点（実装時判断）:
- round7修正条項: stdout/stderrは**末尾**5KB保持（エラー根本原因は末尾に出る
  ことが多い・plan雛形の先頭切り[:5000]を上書き）
- タイムアウトは生TimeoutExpiredでなくToolResult(status="timeout")通知
  （読む系/書く系と同一規約・LLMが状態判断できる）
"""
from __future__ import annotations

import subprocess

from nexuscore.harness.tools import ToolResult

TIMEOUT_SECONDS = 60
KEEP_BYTES = 5000  # stdout/stderrそれぞれの保持上限（末尾）


def _keep_tail(text: str, keep: int = KEEP_BYTES) -> str:
    """末尾keep文字を保持する（round7修正条項・先頭は切り捨て）"""
    if len(text) <= keep:
        return text
    return text[-keep:]


def run_command(cmd: str, timeout_seconds: int = TIMEOUT_SECONDS) -> dict | ToolResult:
    """LLM指定コマンドを実行しstdout/stderr末尾5KB・rcを返す（deny_patterns+ask必須）"""
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True,
                           timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        return ToolResult(status="timeout", allowed_max=timeout_seconds)
    return {"stdout": _keep_tail(r.stdout), "stderr": _keep_tail(r.stderr),
            "rc": r.returncode}
