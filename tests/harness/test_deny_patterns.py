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


# --- MLR採用分: ループ統合テスト（Gate→loop→execの結合・2026-09-06） ---

def test_loop_denies_deny_pattern_before_execution(tmp_path: Path) -> None:
    """MLR採用: harnessループ経由でもdeny_patternsは実行前に遮断される"""
    from nexuscore.harness.circuit_breaker import CircuitBreaker
    from nexuscore.harness.loop import AgentHarness
    from nexuscore.harness.mock_provider import LocalToolCallDummyLLM  # noqa: F401
    from nexuscore.harness.run_state import RunStateStore
    from nexuscore.harness.tool_calling_mixin import InternalToolCall
    from nexuscore.harness.tools.exec import run_command

    policy = tmp_path / "tool_policy.yaml"
    policy.write_text("tools:\n  run_command: { default: allow, "
                      "deny_patterns: ['cat>rophic'] }\n")
    llm_executed: list[dict] = []

    def _spy_run(cmd: str) -> dict:
        llm_executed.append({"cmd": cmd})
        return run_command(cmd)

    class _ScriptedLLM:
        calls = 0

        def complete_with_tools(self, messages, tools, **kwargs):
            self.calls += 1
            if self.calls == 1:
                return {"content": "", "tool_calls": [InternalToolCall(
                    name="run_command", args={"cmd": "echo cat>rophic"}, id="tc-1")],
                    "usage": {}}
            return {"content": "done", "tool_calls": [], "usage": {}}

    gate = ToolGate(policy_path=policy)
    store = RunStateStore(path=tmp_path / "state.json")
    h = AgentHarness(llm=_ScriptedLLM(), gate=gate,
                     tool_registry={"run_command": _spy_run},
                     state_store=store, breaker=CircuitBreaker(provider="t"))
    out = h.run("run it")
    assert out["abort_reason"] is None
    assert llm_executed == []  # denyされたため道具は実行されない
