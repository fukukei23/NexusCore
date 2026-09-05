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

from nexuscore.harness import ask as ask_module
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


# --- 3機MLR採用分のテスト（2026-09-06） ---

def test_default_reader_non_tty_denies() -> None:
    """MLR採用: 対話チャネル不在（pytestは非TTY）で即None＝deny（fail-closed）

    Gemini#1 criticalの regression guard も兼ねる（既定readerは
    timeout束縛済み1引数ラッパ・直接呼出でTypeErrorしない）。
    """
    out = ask_module._readline_with_timeout("prompt: ", 1.0)
    assert out is None  # 非TTY環境（pytest）では入力待せず即deny


def test_ask_session_default_reader_calls_without_typeerror(tmp_path: Path) -> None:
    """MLR採用（Gemini#1 critical）: reader未指定でもpromptが動く

    旧実装は _readline_with_timeout(prompt, timeout) を1引数で呼び
    本番経路で必ずTypeErrorだった。非TTY環境ではNoneが返るため
    DENIED_TIMEOUT に倒れることまで検証する。
    """
    s = AskSession(store=RunStateStore(path=tmp_path / "s.json"))
    assert s.prompt(tool="write_file", args={"path": "a"}) == AskResult.DENIED_TIMEOUT
