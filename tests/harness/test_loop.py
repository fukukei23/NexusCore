"""Task 14: loop.py（AgentHarness 最小ループ）

plan + round7修正条項3件 + 起票2件:
- loop↔breaker連携順序固定（LLM呼出前allow_request→429検出→OPEN遷移save→90% abort・80% warn・SIGINT）
- deny時tool_result形式（{"role":"tool","tool_call_id":...,"content":"denied: ..."}）
- exec呼出前budget確認（超過見込み=would_exceed_limit ToolResult・実行せず）
- 起票①probe結線: HALF_OPEN→CLOSED復帰が結合テストで実現できること（fail条件）
- 起票②deny_paths C案: policy値がregistry束縛で道具へ供給されること・LLM引数では上書き不可

plan雛形からの変更点（実装時判断・loop.py docstringにも記録）:
- 雛形の deny時 record_failure は削除（denyはpolicy判定であってprovider障害でない・
  spec §5はブレーカトリガを「429×3・タイムアウト連続」と規定）
- 雛形は1ステップで先頭tool_callのみ処理→全tool_calls処理に修正
  （OpenAI契約: 全tool_callに対応するtool resultを返す前に次request不可）
- token比較は直前応答のみ→累計に修正
"""
from __future__ import annotations

import ast
import logging
from pathlib import Path

import pytest

from nexuscore.harness.circuit_breaker import CircuitBreaker, State
from nexuscore.harness.loop import AgentHarness, Limits
from nexuscore.harness.mock_provider import LocalToolCallDummyLLM
from nexuscore.harness.run_state import RunStateStore, SaveResult
from nexuscore.harness.tool_gate import ToolGate
from nexuscore.harness.tools import list_dir

POLICY_ALL_ALLOW = """
tools:
  echo:       { default: allow }
  read_file:  { default: allow }
  list_dir:   { default: allow }
  search_text: { default: allow }
"""


class Exc429(Exception):
    """requests.HTTPError互換の429例外（response.status_codeを持つ）"""

    def __init__(self) -> None:
        super().__init__("429 too many requests")
        self.response = type("R", (), {"status_code": 429})()


def _content_resp(content: str, total_tokens: int = 0) -> dict:
    return {"content": content, "tool_calls": [], "usage": {"total_tokens": total_tokens}}


def _tool_resp(name: str, args: dict, call_id: str = "tc-1") -> dict:
    from nexuscore.harness.tool_calling_mixin import InternalToolCall

    return {
        "content": "",
        "tool_calls": [InternalToolCall(name=name, args=args, id=call_id)],
        "usage": {"total_tokens": 5},
    }


class ScriptedLLM:
    """complete_with_tools をスクリプト順に返すテスト用スタブ（呼出履歴を保持）"""

    def __init__(self, script: list) -> None:
        self.script = list(script)
        self.calls = 0
        self.seen_messages: list[list[dict]] = []

    def complete_with_tools(self, messages, tools, **kwargs) -> dict:
        self.calls += 1
        self.seen_messages.append([dict(m) for m in messages])
        item = self.script.pop(0)
        if isinstance(item, BaseException):
            raise item
        return item


def echo(text: str) -> str:
    """テスト用の単純道具（呼出回数を数えられるよう属性で共有）"""
    return f"echo:{text}"


def _make_policy(tmp_path: Path, body: str = POLICY_ALL_ALLOW) -> ToolGate:
    tmp_path.mkdir(parents=True, exist_ok=True)
    p = tmp_path / "tool_policy.yaml"
    p.write_text(body)
    return ToolGate(policy_path=p)


def _make_harness(tmp_path, llm, *, policy_body=POLICY_ALL_ALLOW, limits=None,
                  registry=None, breaker=None):
    gate = _make_policy(tmp_path / "cfg", policy_body)
    store = RunStateStore(path=tmp_path / "state.json")
    br = breaker or CircuitBreaker(provider="test")
    tools = registry if registry is not None else {"echo": echo, "list_dir": list_dir}
    return AgentHarness(llm=llm, gate=gate, tool_registry=tools,
                        state_store=store, breaker=br, limits=limits), br, store


# --- 最小ループ（plan Step 1） ---


def test_loop_terminates_with_no_tools(tmp_path):
    """1ターンでcontentのみ返すLLM→完了応答（plan雛形テスト）"""
    llm = ScriptedLLM([_content_resp("hi", total_tokens=10)])
    h, _, _ = _make_harness(tmp_path, llm)
    out = h.run("say hi")
    assert out["content"] == "hi"
    assert out["loop_steps"] >= 1
    assert out["abort_reason"] is None
    assert out["tokens_used"] == 10


def test_tool_call_executed_then_finish(tmp_path):
    """tool_call→実行→次ターンでcontent→完了・累計token"""
    llm = ScriptedLLM([_tool_resp("echo", {"text": "x"}), _content_resp("done", 7)])
    h, _, _ = _make_harness(tmp_path, llm)
    out = h.run("use echo")
    assert out["content"] == "done"
    assert out["abort_reason"] is None
    assert out["tokens_used"] == 5 + 7  # 累計（plan偏差: 直前応答のみ比較しない）


def test_all_tool_calls_processed_per_step(tmp_path):
    """1応答に複数tool_call→全て処理（OpenAI契約・plan偏差）"""
    from nexuscore.harness.tool_calling_mixin import InternalToolCall

    resp = {
        "content": "",
        "tool_calls": [
            InternalToolCall(name="echo", args={"text": "a"}, id="id-a"),
            InternalToolCall(name="echo", args={"text": "b"}, id="id-b"),
        ],
        "usage": {"total_tokens": 1},
    }
    llm = ScriptedLLM([resp, _content_resp("ok")])
    h, _, _ = _make_harness(tmp_path, llm)
    out = h.run("twice")
    tool_results = [m for m in llm.seen_messages[-1] if m.get("role") == "tool"]
    assert [m["tool_call_id"] for m in tool_results] == ["id-a", "id-b"]
    assert out["content"] == "ok"


def test_assistant_message_appended_before_tool_results(tmp_path):
    """tool結果の前にassistant(tool_calls付き)メッセージを連結（プロトコル整合）"""
    llm = ScriptedLLM([_tool_resp("echo", {"text": "x"}), _content_resp("done")])
    h, _, _ = _make_harness(tmp_path, llm)
    h.run("proto")
    second = llm.seen_messages[1]
    roles = [m["role"] for m in second]
    assert roles.index("assistant") < roles.index("tool")


# --- deny系（round7修正条項② + plan偏差: denyでブレーカに記録しない） ---


def test_denied_tool_returns_denied_result_and_not_executed(tmp_path):
    """policy deny→"denied: ..." 形式でtool result・道具は実行されない"""
    llm = ScriptedLLM([_tool_resp("echo", {"text": "x"}), _content_resp("ok")])
    body = POLICY_ALL_ALLOW.replace("echo:       { default: allow }",
                                    "echo:       { default: deny }")
    h, _, _ = _make_harness(tmp_path, llm, policy_body=body)
    out = h.run("nope")
    assert out["content"] == "ok"
    # 2回目のLLM呼出に渡されたmessagesにdeny結果がある
    tool_msgs = [m for m in llm.seen_messages[1] if m.get("role") == "tool"]
    assert len(tool_msgs) == 1
    assert tool_msgs[0]["content"].startswith("denied: ")


def test_deny_does_not_trip_breaker(tmp_path):
    """deny連続でもブレーカはCLOSED維持（plan偏差: record_failure削除の検証）"""
    resp = _tool_resp("echo", {"text": "x"})
    llm = ScriptedLLM([resp, resp, resp, resp, _content_resp("ok")])
    body = POLICY_ALL_ALLOW.replace("echo:       { default: allow }",
                                    "echo:       { default: deny }")
    h, br, _ = _make_harness(tmp_path, llm, policy_body=body)
    h.run("deny x4")
    assert br.state == State.CLOSED


def test_unknown_tool_name_is_error_not_crash(tmp_path):
    """policyでallowだがregistryに無いtool→クラッシュせずerror tool result

    registry・policy両方に無いtool名はgateがdenyする（fail-closed・別経路）。
    本テストは「policy/registry不整合」の経路を検証する。
    """
    llm = ScriptedLLM([_tool_resp("read_file", {"path": "/tmp/x"}), _content_resp("ok")])
    h, _, _ = _make_harness(tmp_path, llm, registry={"echo": echo})
    out = h.run("ghost")
    assert out["content"] == "ok"
    tool_msgs = [m for m in llm.seen_messages[1] if m.get("role") == "tool"]
    assert tool_msgs[0]["content"].startswith("error:")


# --- 起票①probe結線（fail条件: HALF_OPEN→CLOSED復帰の結合実現） ---


def test_probe_recovery_half_open_to_closed(tmp_path):
    """429でOPEN→cooldown経過→HALF_OPEN中のLLM成功がprobe成功として記録→CLOSED復帰"""
    br = CircuitBreaker(provider="test", threshold=1, cooldown_seconds=0.0,
                        probe_required=1)
    llm = ScriptedLLM([Exc429(), _content_resp("recovered")])
    h, br, _ = _make_harness(tmp_path, llm, breaker=br)
    with pytest.raises(Exc429):
        h.run("first")  # 失敗→OPEN（save→raise・round7(3)）
    # cooldown_seconds=0のため即時HALF_OPEN遷移する（_maybe_transitionは
    # elapsed>=cooldownで遷移・0秒ならOPEN確認の読み取り自体がHALF_OPEN化する）
    assert br.state in (State.OPEN, State.HALF_OPEN)
    out = h.run("second")  # allow_probe=True→成功→record_probe_success→CLOSED
    assert out["content"] == "recovered"
    assert br.state == State.CLOSED  # 起票fail条件: 復帰が1度は実現


def test_probe_failure_returns_to_open(tmp_path):
    """HALF_OPEN中のLLM失敗→probe失敗扱いでOPEN復帰"""
    br = CircuitBreaker(provider="test", threshold=1, cooldown_seconds=0.0,
                        probe_required=2)
    llm = ScriptedLLM([Exc429(), Exc429()])
    h, br, _ = _make_harness(tmp_path, llm, breaker=br)
    with pytest.raises(Exc429):
        h.run("first")
    with pytest.raises(Exc429):
        h.run("second")  # probe失敗→OPEN（cooldown=0のため読み取り時点でHALF_OPEN化）
    assert br.state != State.CLOSED  # 復帰していないことの検証


# --- loop↔breaker連携順序固定（round7修正条項①） ---


def test_429_records_failure_saves_open_state_and_reraises(tmp_path):
    """429→record_failure(is_429=True)→OPEN遷移→state.save→re-raiseの順序"""
    br = CircuitBreaker(provider="test", threshold=1)
    llm = ScriptedLLM([Exc429()])
    h, br, store = _make_harness(tmp_path, llm, breaker=br)
    with pytest.raises(Exc429):
        h.run("boom")
    assert br.state == State.OPEN
    state, reason = store.load_or_quarantine()
    assert reason is None
    assert state is not None and state.breaker_state == "OPEN"
    assert state.abort_reason == "breaker_open"


def test_breaker_open_before_llm_call_graceful_exit(tmp_path):
    """LLM呼出前にallow_request()==False→呼出せずgraceful exit（round7(1)）"""
    br = CircuitBreaker(provider="test", threshold=1)
    br.record_failure(is_429=True)  # threshold=1で即OPEN
    llm = ScriptedLLM([])  # 1回も呼ばれないはず
    h, br, store = _make_harness(tmp_path, llm, breaker=br)
    out = h.run("blocked")
    assert out["abort_reason"] == "breaker_open"
    assert llm.calls == 0


def test_non_429_error_also_records_failure(tmp_path):
    """非429例外→record_failure(is_429=False)・CLOSED中は窓カウントに含む"""
    br = CircuitBreaker(provider="test", threshold=1)
    llm = ScriptedLLM([RuntimeError("timeout-ish")])
    h, br, _ = _make_harness(tmp_path, llm, breaker=br)
    with pytest.raises(RuntimeError):
        h.run("boom")
    assert br.state == State.OPEN


# --- 4ハードリミット（warn80/abort90・round7修正条項④） ---


def test_max_steps_hard_abort_saves_state(tmp_path):
    """max_steps到達→abort limits・state保存"""
    resp = _tool_resp("echo", {"text": "x"})
    llm = ScriptedLLM([resp, resp, resp, resp, resp])
    limits = Limits(max_steps=2)
    h, _, store = _make_harness(tmp_path, llm, limits=limits)
    out = h.run("loop forever")
    assert out["abort_reason"] == "limits"
    assert llm.calls == 2
    state, _ = store.load_or_quarantine()
    assert state is not None and state.abort_reason == "limits"


def test_token_abort_at_90_percent(tmp_path):
    """累計tokenがmax_tokens×90%到達→abort limits"""
    llm = ScriptedLLM([_content_resp("a", total_tokens=95), _content_resp("b")])
    limits = Limits(max_tokens=100)
    h, _, _ = _make_harness(tmp_path, llm, limits=limits)
    out = h.run("tokens")
    assert out["abort_reason"] == "limits"
    assert out["tokens_used"] == 95


def test_warn_logged_at_80_percent_but_loop_continues(tmp_path, caplog):
    """80%到達で警告ログのみ・ループは継続（90%未満）"""
    # tool_call応答でトークンを消費し、その後content応答で完了させる
    # （contentのみ応答はその時点で完了扱いになるため・warn継続の検証には
    #  ループを続ける必要がある）
    llm = ScriptedLLM([_tool_resp("echo", {"text": "x"}), _content_resp("done")])
    # 1応答85tok・累計85%で80%警告・90%未満
    limits = Limits(max_tokens=100)
    llm.script[0]["usage"] = {"total_tokens": 85}
    h, _, _ = _make_harness(tmp_path, llm, limits=limits)
    with caplog.at_level(logging.WARNING, logger="nexuscore.harness.loop"):
        out = h.run("warn")
    assert out["content"] == "done"  # 90%未満なので継続
    assert any("80" in r.message for r in caplog.records)


def test_tool_budget_would_exceed_limit(tmp_path):
    """max_tool_calls超過見込み→実行せずwould_exceed_limitを返す（round7③）"""
    calls = {"n": 0}

    def counting_echo(text: str) -> str:
        calls["n"] += 1
        return f"echo:{text}"

    resp1 = _tool_resp("echo", {"text": "a"}, call_id="id-1")
    resp2 = _tool_resp("echo", {"text": "b"}, call_id="id-2")
    llm = ScriptedLLM([resp1, resp2, _content_resp("done")])
    limits = Limits(max_tool_calls=1)
    h, _, _ = _make_harness(tmp_path, llm, limits=limits,
                            registry={"echo": counting_echo})
    h.run("budget")
    assert calls["n"] == 1  # 2本目は実行されない
    tool_msgs = [m for m in llm.seen_messages[2] if m.get("role") == "tool"]
    assert tool_msgs[-1]["content"].find("would_exceed_limit") >= 0


# --- SIGINT / state保存失敗 ---


def test_sigint_saves_state_and_returns_gracefully(tmp_path):
    """KeyboardInterrupt→state.save→graceful return（round7(5)）"""
    class InterruptOn2nd(ScriptedLLM):
        def complete_with_tools(self, messages, tools, **kwargs):
            if self.calls == 1:
                return super().complete_with_tools(messages, tools, **kwargs)
            raise KeyboardInterrupt

    llm = InterruptOn2nd([_tool_resp("echo", {"text": "x"})])
    h, _, store = _make_harness(tmp_path, llm)
    out = h.run("interrupt me")
    assert out["abort_reason"] == "sigint"
    state, _ = store.load_or_quarantine()
    assert state is not None and state.abort_reason == "sigint"


def test_partial_failure_save_aborts(tmp_path):
    """save()がPartialFailure→resume契約不能のためabort（Task 12 round7連携）"""
    llm = ScriptedLLM([_content_resp("hi")])

    class FailingStore(RunStateStore):
        def save(self, state):
            return SaveResult.PARTIAL_FAILURE

    gate = _make_policy(tmp_path / "cfg")
    br = CircuitBreaker(provider="test")
    h = AgentHarness(llm=llm, gate=gate, tool_registry={"echo": echo},
                     state_store=FailingStore(path=tmp_path / "s.json"),
                     breaker=br)
    out = h.run("x")
    assert out["abort_reason"] == "state_save_failed"
    assert out["content"] is None


# --- 起票②deny_paths C案（registry束縛） ---


def test_deny_paths_bound_from_policy_registry(tmp_path):
    """policyのdeny_pathsがregistry束縛で道具へ供給される（C案・fail条件grep対象）"""
    workdir = tmp_path / "work"
    workdir.mkdir()
    (workdir / "a.txt").write_text("hello")
    (workdir / "secret.txt").write_text("hidden")
    body = POLICY_ALL_ALLOW.replace(
        "list_dir:   { default: allow }",
        "list_dir:   { default: allow, deny_paths: ['secret.txt'] }")
    llm = ScriptedLLM([_tool_resp("list_dir", {"path": str(workdir)}),
                       _content_resp("done")])
    h, _, _ = _make_harness(tmp_path, llm, policy_body=body)
    h.run("ls")
    tool_msgs = [m for m in llm.seen_messages[1] if m.get("role") == "tool"]
    # ast.literal_eval: 道具戻り値(list[dict]のrepr)の安全な復元・任意コード実行なし
    names = [e["name"] for e in ast.literal_eval(tool_msgs[0]["content"])]
    assert "a.txt" in names
    assert "secret.txt" not in names  # policy束縛で隠蔽される


def test_llm_cannot_override_bound_deny_paths(tmp_path):
    """LLMがdeny_paths=[]をargsに注入しても束縛値が勝つ（policy唯一の情報源）"""
    workdir = tmp_path / "work"
    workdir.mkdir()
    (workdir / "a.txt").write_text("hello")
    (workdir / "secret.txt").write_text("hidden")
    body = POLICY_ALL_ALLOW.replace(
        "list_dir:   { default: allow }",
        "list_dir:   { default: allow, deny_paths: ['secret.txt'] }")
    llm = ScriptedLLM([_tool_resp("list_dir",
                                  {"path": str(workdir), "deny_paths": []}),
                       _content_resp("done")])
    h, _, _ = _make_harness(tmp_path, llm, policy_body=body)
    h.run("injection")
    tool_msgs = [m for m in llm.seen_messages[1] if m.get("role") == "tool"]
    names = [e["name"] for e in ast.literal_eval(tool_msgs[0]["content"])]
    assert "secret.txt" not in names


def test_tool_defs_expose_registry_names(tmp_path):
    """_tool_defs: registryの全tool名がfunction定義として出る"""
    llm = ScriptedLLM([_content_resp("ok")])
    h, _, _ = _make_harness(tmp_path, llm)
    defs = h._tool_defs()
    names = {d["function"]["name"] for d in defs}
    assert {"echo", "list_dir"} <= names


def test_local_dummy_llm_smoke(tmp_path):
    """LocalToolCallDummyLLM併用スモーク（registry先頭toolを1回呼んで終了）"""
    llm = LocalToolCallDummyLLM()
    h, _, _ = _make_harness(tmp_path, llm)
    out = h.run("smoke")
    # ダミーは常にtools[0]のtool_callを返す→max_steps内で完了しない=limits abort
    assert out["abort_reason"] in (None, "limits")
