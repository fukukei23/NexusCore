"""Task 20: 撃つ系tool（run_command）+ 禁止パターンdeny

plan雛形からの変更点（実装時判断・exec.py docstringにも記録）:
- round7修正条項: stdout/stderrは**末尾**5KBを保持（先頭ではない・エラー根本原因は
  末尾に出ることが多い）
- タイムアウトは生TimeoutExpiredでなくToolResult(status="timeout")で通知
  （読む系/書く系と同一のToolResult規約・LLMが状態を判断できる）
- tool_policy.yamlへrun_command（default: ask + deny_patterns）を追加
"""
from __future__ import annotations

from nexuscore.harness.tools import ToolResult
from nexuscore.harness.tools.exec import run_command


def test_run_command_captures_stdout() -> None:
    r = run_command("echo hello")
    assert isinstance(r, dict)
    assert "hello" in r["stdout"]
    assert r["rc"] == 0


def test_run_command_captures_stderr_and_rc() -> None:
    r = run_command("echo boom >&2; exit 3")
    assert "boom" in r["stderr"]
    assert r["rc"] == 3


def test_run_command_keeps_tail_not_head() -> None:
    """round7修正条項: 出力は末尾5KB保持（先頭切捨て）"""
    cmd = ("python3 -c \"print('HEAD_MARKER'); print('x' * 9000); "
           "print('TAIL_MARKER')\"")
    r = run_command(cmd)
    assert "TAIL_MARKER" in r["stdout"]  # 末尾は保持
    assert "HEAD_MARKER" not in r["stdout"]  # 先頭は切り捨て
    assert len(r["stdout"]) <= 5100


def test_run_command_timeout_returns_toolresult() -> None:
    """タイムアウトはToolResult通知（生例外でLLMを汚さない）"""
    r = run_command("sleep 5", timeout_seconds=1)
    assert isinstance(r, ToolResult) and r.status == "timeout"
    assert r.allowed_max == 1


def test_run_command_missing_binary_reports_error() -> None:
    r = run_command("definitely_not_a_command_xyz")
    assert r["rc"] != 0
    assert r["stderr"] != ""
