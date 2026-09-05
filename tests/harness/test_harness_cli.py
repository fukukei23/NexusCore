"""Task 15: harness_cli.py（Phase 1 CLI）

- CLI経由でAgentHarnessが起動しJSON 1行を出力すること（spec §6）
- --provider mock でオフライン動作確認ができること
- abort_reason なしは exit 0・ありは exit 1
- state保存が --state-path に書き出されること（resume土台）
- policy不在でもクラッシュせず fail-closed で走ること

plan雛形からの変更点（実装時判断・harness_cli.py docstringにも記録）:
- 雛形の ``LLMRouter().get_llm_for_task()`` は RoutedLLM（complete_with_tools
  未実装・execute()のみ）を返しharness契約を満たさないため、``create_provider()``
  経由で ToolCallingMixin 済みプロバイダを直接生成する（``--model``・既定マップ）
- テスト注入のため ``main(argv, llm_factory)``・``--state-path`` を追加
"""
from __future__ import annotations

import contextlib
import io
import json
from pathlib import Path

import pytest

from nexuscore.cli import harness_cli
from nexuscore.harness.mock_provider import LocalToolCallDummyLLM
from nexuscore.harness.run_state import RunStateStore

POLICY_ALL_ALLOW = """
tools:
  read_file:  { default: allow }
  list_dir:   { default: allow }
  search_text: { default: allow }
"""


class _ContentLLM:
    """tool呼出なしで即contentを返す最小スタブ（exit 0経路用）"""

    def __init__(self, content: str = "done") -> None:
        self.content = content

    def complete_with_tools(self, messages, tools, **kwargs) -> dict:
        return {"content": self.content, "tool_calls": [], "usage": {}}


def _run_cli(tmp_path: Path, llm_factory=None, *extra: str) -> tuple[int, dict, str]:
    policy = tmp_path / "tool_policy.yaml"
    policy.write_text(POLICY_ALL_ALLOW)
    state = tmp_path / "state.json"
    argv = ["hello", "--provider", "mock", "--policy", str(policy),
            "--state-path", str(state), *extra]
    kwargs = {} if llm_factory is None else {"llm_factory": llm_factory}
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = harness_cli.main(argv, **kwargs)
    return code, json.loads(buf.getvalue()), buf.getvalue()


def test_cli_content_response_exit0(tmp_path: Path) -> None:
    """正常系: content応答なら exit 0・JSONにabort_reason=None"""
    code, out, raw = _run_cli(tmp_path, llm_factory=lambda p, m: _ContentLLM("done"))
    assert (code, out["abort_reason"], out["content"]) == (0, None, "done")
    assert raw.count("\n") >= 1  # JSON 1行出力


def test_cli_mock_always_tool_calls_exits_limits(tmp_path: Path) -> None:
    """異常系: mock dummyは常時tool_call→max_steps消費でabort・exit 1"""
    code, out, _raw = _run_cli(tmp_path)  # 既定llm_factory=build_llm("mock")
    assert code == 1
    assert out["abort_reason"] == "limits"


def test_cli_state_saved_to_state_path(tmp_path: Path) -> None:
    """境界: 実行後、--state-path にRunStateが保存されている（resume土台）"""
    _run_cli(tmp_path, llm_factory=lambda p, m: _ContentLLM())
    state, reason = RunStateStore(path=tmp_path / "state.json").load_or_quarantine()
    assert state is not None
    assert reason is None
    assert state.abort_reason is None


def test_cli_missing_policy_fail_closed_no_crash(tmp_path: Path) -> None:
    """異常系: policy不在でもGate fail-closedでクラッシュせず完走する"""
    state = tmp_path / "state.json"
    argv = ["hello", "--provider", "mock", "--policy",
            str(tmp_path / "missing.yaml"), "--state-path", str(state)]
    code = harness_cli.main(argv, llm_factory=lambda p, m: _ContentLLM())
    assert code == 0  # gateは全拒否するがループ自体は継続・content応答で正常終了


def test_cli_unsupported_provider_systemexit() -> None:
    """異常系: 未対応providerはSystemExit（BuildErrorを握りつぶさない）"""
    with pytest.raises(SystemExit):
        harness_cli.build_llm("nope", None)


def test_build_llm_mock_returns_dummy() -> None:
    """--provider mock はオフラインダミーを返す（実HTTP不発）"""
    assert isinstance(harness_cli.build_llm("mock", None), LocalToolCallDummyLLM)
