"""Task 18: ask確認フロー（CLI対話・タイムアウト=deny）

- y承認→APPROVED・その他入力→DENIED_USER・応答なし→DENIED_TIMEOUT
- policy拡張: write_file/edit_file は default: ask + deny_paths
- ask_supported=False（CI/pipe）ではask要求はDENYに倒れる（fail-closed）

plan雛形からの変更点（実装時判断・ask.py docstringにも記録）:
- 雛形の monkeypatch(builtins.input) 方式は select() ベースのタイムアウト実装と
  非互換のため、reader関数の注入でテスト可能にした
- 雛形の未使用 import signal を削除
"""
from __future__ import annotations

from pathlib import Path

from nexuscore.harness.ask import AskResult, AskSession, _ask_supported
from nexuscore.harness.run_state import RunStateStore
from nexuscore.harness.tool_gate import Mode, ToolGate

ASK_POLICY = """
tools:
  read_file:  { default: allow }
  write_file: { default: ask, deny_paths: ['**/.env', '**/secrets/**'] }
  edit_file:  { default: ask, deny_paths: ['**/.env', '**/secrets/**'] }
"""


def _make_session(reader, tmp_path: Path) -> AskSession:
    return AskSession(store=RunStateStore(path=tmp_path / "s.json"),
                      timeout_seconds=120.0, reader=reader)


def test_ask_approve(tmp_path: Path) -> None:
    s = _make_session(lambda _p: "y\n", tmp_path)
    assert s.prompt(tool="write_file", args={"path": "a"}) == AskResult.APPROVED


def test_ask_approve_case_insensitive(tmp_path: Path) -> None:
    s = _make_session(lambda _p: "  Y \n", tmp_path)
    assert s.prompt(tool="write_file", args={"path": "a"}) == AskResult.APPROVED


def test_ask_reject(tmp_path: Path) -> None:
    s = _make_session(lambda _p: "n\n", tmp_path)
    assert s.prompt(tool="write_file", args={"path": "a"}) == AskResult.DENIED_USER


def test_ask_empty_answer_denies(tmp_path: Path) -> None:
    s = _make_session(lambda _p: "\n", tmp_path)
    assert s.prompt(tool="write_file", args={"path": "a"}) == AskResult.DENIED_USER


def test_ask_timeout_denies(tmp_path: Path) -> None:
    """round7: 応答なし（select非ready=None）はDENIED_TIMEOUT"""
    s = _make_session(lambda _p: None, tmp_path)
    assert s.prompt(tool="write_file", args={"path": "a"}) == AskResult.DENIED_TIMEOUT


def test_ask_supported_is_bool() -> None:
    assert isinstance(_ask_supported(), bool)


def test_gate_ask_mode_requires_channel(tmp_path: Path) -> None:
    """policy拡張: ask設定はチャネル有無でALLOW/ASK/DENYが決まる"""
    p = tmp_path / "tool_policy.yaml"
    p.write_text(ASK_POLICY)
    gate = ToolGate(policy_path=p)
    d = gate.evaluate(tool="write_file", tool_args={"path": "a.txt"},
                      ask_supported=False)
    assert d.mode == Mode.DENY  # チャネル無し=deny（fail-closed）
    d2 = gate.evaluate(tool="write_file", tool_args={"path": "a.txt"},
                       ask_supported=True)
    assert d2.mode == Mode.ASK
    d3 = gate.evaluate(tool="read_file", tool_args={"path": "a.txt"},
                       ask_supported=False)
    assert d3.mode == Mode.ALLOW


def test_gate_ask_policy_deny_paths_still_denied(tmp_path: Path) -> None:
    """ask設定でもdeny_paths一致はaskに上がらず即DENY"""
    p = tmp_path / "tool_policy.yaml"
    p.write_text(ASK_POLICY)
    gate = ToolGate(policy_path=p)
    d = gate.evaluate(tool="write_file",
                      tool_args={"path": "/home/x/proj/.env"},
                      ask_supported=True)
    assert d.mode == Mode.DENY
    assert "deny pattern" in d.reason
