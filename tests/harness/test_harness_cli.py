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
    """正常系: content応答なら exit 0・JSON 1行・run戻り値キー網羅"""
    code, out, raw = _run_cli(tmp_path, llm_factory=lambda p, m: _ContentLLM("done"))
    assert (code, out["abort_reason"], out["content"]) == (0, None, "done")
    assert len(raw.strip().splitlines()) == 1  # JSON 1行出力（末尾改行のみ許容）
    assert set(out) >= {"content", "loop_steps", "tokens_used", "abort_reason"}


def test_cli_factory_exception_returns_cli_error_json(tmp_path: Path) -> None:
    """異常系: 予期せぬ例外はJSON(abort_reason=cli_error)+exit 1（MLR採用M10）"""
    def _boom(provider: str, model: str | None) -> object:
        raise ValueError("factory failed")
    code, out, raw = _run_cli(tmp_path, llm_factory=_boom)
    assert (code, out["abort_reason"], out["error"]) == (1, "cli_error",
                                                         "factory failed")
    assert len(raw.strip().splitlines()) == 1


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
    """異常系: policy不在でもGate fail-closedでクラッシュせず健全完走する"""
    state = tmp_path / "state.json"
    argv = ["hello", "--provider", "mock", "--policy",
            str(tmp_path / "missing.yaml"), "--state-path", str(state)]
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = harness_cli.main(argv, llm_factory=lambda p, m: _ContentLLM())
    out = json.loads(buf.getvalue())
    assert code == 0  # gateは全拒否するがループ自体は継続・content応答で正常終了
    assert out["abort_reason"] is None  # MLR採用M5: fail-closedでも健全完走を明示


def test_cli_ask_registry_includes_exec_tool() -> None:
    """Task 21: --ask時はrun_command（ask必須の撃つ系）もregistryへ登録する

    plan Task 21のE2E（pytest実行をask承認込みでCLI経由）に必要。
    policy既定（tool_policy.yaml）は run_command: { default: ask } のため
    AskSessionありの文脈でのみ登録する（ask無しではfail-closed維持）。
    """
    reg = harness_cli.build_registry(ask=True)
    assert set(reg) == {"read_file", "list_dir", "search_text",
                        "write_file", "edit_file", "run_command"}


def test_cli_default_registry_is_read_only() -> None:
    """Task 21: --ask無しのregistryは読む系のみ（exec/writeは登録しない）"""
    reg = harness_cli.build_registry(ask=False)
    assert set(reg) == {"read_file", "list_dir", "search_text"}


def test_cli_unsupported_provider_systemexit() -> None:
    """異常系: 未対応providerはSystemExit（BuildErrorを握りつぶさない）"""
    with pytest.raises(SystemExit):
        harness_cli.build_llm("nope", None)


def test_build_llm_mock_returns_dummy() -> None:
    """--provider mock はオフラインダミーを返す（実HTTP不発）"""
    assert isinstance(harness_cli.build_llm("mock", None), LocalToolCallDummyLLM)


def test_cli_injects_working_directory_context(tmp_path: Path) -> None:
    """G-1: CLIがcwdを作業コンテキストとしてsystemロールで注入する（run1迷走対策）"""
    import contextlib
    import io

    from nexuscore.cli import harness_cli

    captured: dict = {}

    class _ContentLLM:
        def complete_with_tools(self, messages, tools, **kw):
            captured["messages"] = messages
            return {"content": "done", "usage": {}}

    policy = tmp_path / "tool_policy.yaml"
    policy.write_text("provider_insecure_default: []\ntools:\n  read_file: {default: allow}\n")
    state = tmp_path / "state.json"
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        harness_cli.main(
            ["hello", "--provider", "mock", "--policy", str(policy),
             "--state-path", str(state)],
            llm_factory=lambda p, m: _ContentLLM())
    roles = [m["role"] for m in captured["messages"]]
    assert roles[0] == "system"
    import os
    assert "作業ディレクトリ" in captured["messages"][0]["content"]
    assert os.getcwd() in captured["messages"][0]["content"]


class _TokenLLM:
    """usage で固定トークンを報告する content 応答スタブ（上限結線の実効検証用）"""

    def __init__(self, tokens: int) -> None:
        self.tokens = tokens

    def complete_with_tools(self, messages, tools, **kwargs) -> dict:
        return {"content": "done", "tool_calls": [],
                "usage": {"total_tokens": self.tokens}}


def test_cli_max_tokens_option_aborts_run(tmp_path: Path) -> None:
    """fail条件ケース: --max-tokens が loop の Limits へ実際に届くこと

    10,000トークン消費する応答に対し --max-tokens 5000 を渡すと
    abort閾値(5000*0.9=4500)を超えて limits abort する。
    結線が欠けていれば既定500_000が使われ abort しない＝本テストがFAILする
    （2026-09-11〜18 のcron実測9run中8件が計測無効になった構造欠陥の回帰防止）。
    """
    code, out, _raw = _run_cli(tmp_path, lambda p, m: _TokenLLM(10_000),
                               "--max-tokens", "5000")
    assert (code, out["abort_reason"]) == (1, "limits")


def test_cli_max_tokens_default_does_not_abort(tmp_path: Path) -> None:
    """対照（正常系）: 同じ10,000トークン応答も既定上限(500_000)では完遂する"""
    code, out, _raw = _run_cli(tmp_path, lambda p, m: _TokenLLM(10_000))
    assert (code, out["abort_reason"]) == (0, None)


def test_cli_max_tokens_default_matches_limits_dataclass() -> None:
    """境界: --max-tokens 未指定時の既定は Limits.max_tokens と一致（二重管理防止）"""
    from nexuscore.harness.loop import Limits

    parser_default = harness_cli.build_arg_parser().get_default("max_tokens")
    assert parser_default == Limits().max_tokens


@pytest.mark.parametrize("bad", ["0", "-5"])
def test_cli_max_tokens_rejects_non_positive(tmp_path: Path, bad: str) -> None:
    """境界: --max-tokens に0以下を渡すと入口で弾く

    0や負値はloopが初回応答で即abortし全runが即死する（self-inspect境界検証で
    実測: --max-tokens 0 → loop_steps=0 / abort_reason=limits）。
    """
    with pytest.raises(SystemExit):
        _run_cli(tmp_path, lambda p, m: _ContentLLM(), "--max-tokens", bad)


def test_operational_max_tokens_matches_wrapper() -> None:
    """二重管理防止: CLI側の運用上限とラッパーのHARD_TOKEN_LIMITが同値であること"""
    import sys
    from pathlib import Path as _Path
    sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))
    from scripts.run_harness_task import HARD_TOKEN_LIMIT

    assert harness_cli.OPERATIONAL_MAX_TOKENS == HARD_TOKEN_LIMIT
