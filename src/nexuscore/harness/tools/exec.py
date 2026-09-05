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

3機MLR採用分（2026-09-06・24指摘から採用5・review_log参照）:
- encoding="utf-8"+errors="replace"明示（バイナリ出力でUnicodeDecodeError不発・
  Gemini#1+OR#3）
- stdin=subprocess.DEVNULL（対話型コマンドがaskチャネルのstdinを奪わない・OR#6）
- timeout_secondsの型検証+クランプ（LLMが文字列/負数/巨大値を渡しても安全・
  Gemini#4）
- OSError（PermissionError等）もToolResult(status="exec_error")通知
  （生例外でLLMを汚さない・Gemini#1+OR#3）
- ToolResultへdetailフィールド追加（例外文言搬送用）

既知制限（docstring明記）:
- shellメタ文字経由のdeny_patterns回避（base64|sh・変数展開等）は原理的に閉じ
  ない。ask承認時に人間へ**コマンド全文**が表示されるのが最終防線（MiniMax#2・
  Gemini#3）
- env/cwd引数は非対応（将来追加時はdeny_patterns評価対象に含めること・MiniMax#3）
- 対話型コマンドはstdin=DEVNULLで即EOF（ハングしない・OR#6）
"""
from __future__ import annotations

import subprocess

from nexuscore.harness.tools import ToolResult

TIMEOUT_SECONDS = 60
MAX_TIMEOUT_SECONDS = 600
KEEP_BYTES = 5000  # stdout/stderrそれぞれの保持上限（末尾・文字数）


def _keep_tail(text: str, keep: int = KEEP_BYTES) -> str:
    """末尾keep文字を保持する（round7修正条項・先頭は切り捨て）"""
    if len(text) <= keep:
        return text
    return text[-keep:]


def _sanitize_timeout(value: object) -> int:
    """LLM指定timeoutをintへ正規化し[1, 600]へクランプ（不正値は既定値）"""
    try:
        seconds = int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return TIMEOUT_SECONDS
    return max(1, min(seconds, MAX_TIMEOUT_SECONDS))


def run_command(cmd: str, timeout_seconds: int = TIMEOUT_SECONDS) -> dict | ToolResult:
    """LLM指定コマンドを実行しstdout/stderr末尾5KB・rcを返す（deny_patterns+ask必須）"""
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True,
                           encoding="utf-8", errors="replace",
                           stdin=subprocess.DEVNULL,
                           timeout=_sanitize_timeout(timeout_seconds))
    except subprocess.TimeoutExpired:
        return ToolResult(status="timeout", allowed_max=MAX_TIMEOUT_SECONDS)
    except OSError as exc:
        return ToolResult(status="exec_error", detail=str(exc))
    return {"stdout": _keep_tail(r.stdout), "stderr": _keep_tail(r.stderr),
            "rc": r.returncode}
