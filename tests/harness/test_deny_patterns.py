"""Task 20: 禁止パターンdeny（ToolGate deny_patterns）

- deny_patterns一致コマンドはask承認対象にすらならず即DENY
- 非list型deny_patternsはfail-closed（deny-all）
- deny_patterns無しのtoolは従来どおりask/allowで判定
"""
from __future__ import annotations

from pathlib import Path

from nexuscore.harness.tool_gate import Mode, ToolGate

POLICY = """
tools:
  run_command: { default: ask, deny_patterns: ['rm -rf', 'sudo ', 'git push --force'] }
  echo_tool:   { default: allow }
"""


def _gate(tmp_path: Path) -> ToolGate:
    p = tmp_path / "tool_policy.yaml"
    p.write_text(POLICY)
    return ToolGate(policy_path=p)


def test_deny_patterns_blocked(tmp_path: Path) -> None:
    g = _gate(tmp_path)
    for bad in ["rm -rf /tmp/x", "sudo apt update", "git push --force origin main"]:
        d = g.evaluate(tool="run_command", tool_args={"cmd": bad}, ask_supported=True)
        assert d.mode == Mode.DENY, bad


def test_deny_pattern_precedes_ask(tmp_path: Path) -> None:
    """deny一致はask承認の有無と無関係にDENY"""
    g = _gate(tmp_path)
    d = g.evaluate(tool="run_command", tool_args={"cmd": "rm -rf /"},
                   ask_supported=True)
    assert d.mode == Mode.DENY


def test_non_matching_command_falls_to_ask(tmp_path: Path) -> None:
    g = _gate(tmp_path)
    d = g.evaluate(tool="run_command", tool_args={"cmd": "ls -la"},
                   ask_supported=True)
    assert d.mode == Mode.ASK


def test_broken_deny_patterns_fail_closed(tmp_path: Path) -> None:
    """非list型deny_patternsはdeny-all（deny_pathsと対称・fail-closed）"""
    p = tmp_path / "tool_policy.yaml"
    p.write_text("tools:\n  run_command: { default: ask, deny_patterns: 'rm -rf' }\n")
    g = ToolGate(policy_path=p)
    d = g.evaluate(tool="run_command", tool_args={"cmd": "ls"},
                   ask_supported=True)
    assert d.mode == Mode.DENY


def test_tool_without_deny_patterns_unaffected(tmp_path: Path) -> None:
    """deny_patterns無しtoolは従来どおり判定される"""
    g = _gate(tmp_path)
    d = g.evaluate(tool="echo_tool", tool_args={"text": "hello"},
                   ask_supported=False)
    assert d.mode == Mode.ALLOW
