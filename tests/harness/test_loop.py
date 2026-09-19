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
import requests

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


class Exc429(requests.exceptions.RequestException):
    """requests.HTTPError互換の429例外（RequestException継承・status_codeを持つ）"""

    def __init__(self) -> None:
        super().__init__("429 too many requests")
        self.response = type("R", (), {"status_code": 429})()
        self.status_code = 429


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
    assert llm.calls == 2  # 直列実行の契約（probe判定は単一ループ前提・MLR採用）


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


def test_non_429_provider_error_also_records_failure(tmp_path):
    """provider系非429例外（Timeout等）→record_failure(is_429=False)で窓カウント"""
    br = CircuitBreaker(provider="test", threshold=1)
    llm = ScriptedLLM([requests.exceptions.Timeout("timeout-ish")])
    h, br, _ = _make_harness(tmp_path, llm, breaker=br)
    with pytest.raises(requests.exceptions.Timeout):
        h.run("boom")
    assert br.state == State.OPEN


def test_non_provider_error_not_recorded_to_breaker(tmp_path):
    """プログラミングエラー→ブレーカ記録せずre-raise・CLOSED維持（MLR採用）"""
    br = CircuitBreaker(provider="test", threshold=1)
    llm = ScriptedLLM([RuntimeError("programming error-ish")])
    h, br, _ = _make_harness(tmp_path, llm, breaker=br)
    with pytest.raises(RuntimeError):
        h.run("boom")
    assert br.state == State.CLOSED  # provider障害でないためOPEN化しない


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
    tool_msgs = [m for m in llm.seen_messages[-1] if m.get("role") == "tool"]
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


# --- Task 19: ask結線（Mode.ASK→AskSession.prompt） ---

POLICY_ASK_EDIT = POLICY_ALL_ALLOW.replace(
    "list_dir:   { default: allow }",
    "list_dir:   { default: allow }\n  edit_file:  { default: ask }")


def _make_edit_tool():
    def edit_file(path: str, old: str, new: str) -> str:
        return f"edited {path}"
    return edit_file


def _ask_harness(tmp_path, llm, reader):
    """ask_session注入済みharness（edit_file=ask policy）"""
    from nexuscore.harness.ask import AskSession
    gate = _make_policy(tmp_path / "cfg", POLICY_ASK_EDIT)
    store = RunStateStore(path=tmp_path / "state.json")
    ask_session = AskSession(store=store, reader=reader)
    tools = {"edit_file": _make_edit_tool(), "list_dir": list_dir}
    return AgentHarness(llm=llm, gate=gate, tool_registry=tools,
                        state_store=store,
                        breaker=CircuitBreaker(provider="test"),
                        ask_session=ask_session)


def test_ask_approved_executes_tool(tmp_path):
    """ask承認→道具実行される"""
    llm = ScriptedLLM([_tool_resp("edit_file", {"path": "a.txt", "old": "A", "new": "B"}),
                       _content_resp("done")])
    h = _ask_harness(tmp_path, llm, lambda _p: "y\n")
    out = h.run("edit it")
    assert out["abort_reason"] is None
    tool_msgs = [m for m in llm.seen_messages[1] if m.get("role") == "tool"]
    assert tool_msgs[0]["content"] == "edited a.txt"  # 実行されている


def test_ask_denied_by_user_does_not_execute(tmp_path):
    """ask拒否→道具は実行されずLLMへdenied通知"""
    llm = ScriptedLLM([_tool_resp("edit_file", {"path": "a.txt", "old": "A", "new": "B"}),
                       _content_resp("ok")])
    h = _ask_harness(tmp_path, llm, lambda _p: "n\n")
    out = h.run("edit it")
    assert out["abort_reason"] is None
    tool_msgs = [m for m in llm.seen_messages[1] if m.get("role") == "tool"]
    assert "denied" in tool_msgs[0]["content"]
    assert "edited" not in tool_msgs[0]["content"]


def test_ask_timeout_denies(tmp_path):
    """askタイムアウト（reader=None）→deny"""
    llm = ScriptedLLM([_tool_resp("edit_file", {"path": "a.txt", "old": "A", "new": "B"}),
                       _content_resp("ok")])
    h = _ask_harness(tmp_path, llm, lambda _p: None)
    h.run("edit it")
    tool_msgs = [m for m in llm.seen_messages[1] if m.get("role") == "tool"]
    assert "denied" in tool_msgs[0]["content"]


def test_no_ask_session_ask_policy_denies(tmp_path):
    """ask_session未注入ならask policyはDENY（現行挙動維持・fail-closed）"""
    llm = ScriptedLLM([_tool_resp("edit_file", {"path": "a.txt", "old": "A", "new": "B"}),
                       _content_resp("ok")])
    h, _, _ = _make_harness(tmp_path, llm, policy_body=POLICY_ASK_EDIT,
                            registry={"edit_file": _make_edit_tool(),
                                      "list_dir": list_dir})
    h.run("edit it")
    tool_msgs = [m for m in llm.seen_messages[1] if m.get("role") == "tool"]
    assert "denied" in tool_msgs[0]["content"]


# --- Task 19: tool_defスキーマ自動生成（空properties問題の解消） ---

def test_tool_defs_generate_signature_schema(tmp_path):
    """_tool_defs: シグネチャからparametersを自動生成する（空properties問題解消）"""
    def edit_file(path: str, old: str, new: str) -> str:
        """ファイル内のold→newを置換する"""
        return "ok"

    llm = ScriptedLLM([_content_resp("ok")])
    h, _, _ = _make_harness(tmp_path, llm, registry={"edit_file": edit_file})
    defs = {d["function"]["name"]: d["function"] for d in h._tool_defs()}
    params = defs["edit_file"]["parameters"]
    assert set(params["properties"]) == {"path", "old", "new"}
    assert params["required"] == ["path", "old", "new"]
    assert "old→newを置換" in defs["edit_file"]["description"]


def test_tool_defs_exclude_denied_paths_param(tmp_path):
    """_tool_defs: policy束縛対象のdeny_pathsはLLMに公開しない"""
    llm = ScriptedLLM([_content_resp("ok")])
    h, _, _ = _make_harness(tmp_path, llm)  # list_dirはdeny_paths束縛対象
    defs = {d["function"]["name"]: d["function"] for d in h._tool_defs()}
    assert "deny_paths" not in defs["list_dir"]["parameters"]["properties"]


def _AlwaysAllowBreaker():  # noqa: N802 (fixture的ファクトリ)
    """G-1テスト用: 本物のCircuitBreaker（CLOSED固定・loop契約を完全遵守）"""
    from nexuscore.harness.circuit_breaker import CircuitBreaker
    return CircuitBreaker(provider="test")


def _mk_harness(tmp_path: Path, captured: dict) -> AgentHarness:  # noqa: F821
    from nexuscore.harness.loop import AgentHarness

    class CapLLM:
        def complete_with_tools(self, messages, tools, **kw):
            captured["messages"] = messages
            return {"content": "done", "usage": {}}

    store = RunStateStore(path=tmp_path / "state.json")
    return AgentHarness(llm=CapLLM(), gate=None, tool_registry={}, state_store=store,
                        breaker=_AlwaysAllowBreaker(), ask_session=None)


def test_run_with_system_prompt_injects_system_message(tmp_path: Path) -> None:
    """G-1: system_prompt渡しで先頭にsystemロールが挿入される（実行コンテキスト注入）"""
    captured: dict = {}
    h = _mk_harness(tmp_path, captured)
    h.run("タスク", system_prompt="作業ディレクトリ: /repo")
    assert captured["messages"][0]["role"] == "system"
    assert "/repo" in captured["messages"][0]["content"]
    assert captured["messages"][1]["content"] == "タスク"


def test_run_without_system_prompt_keeps_user_first(tmp_path: Path) -> None:
    """後方互換: system_prompt無しは従来どおりuserメッセージが先頭"""
    captured: dict = {}
    h = _mk_harness(tmp_path, captured)
    h.run("タスク")
    assert captured["messages"][0]["role"] == "user"


# --- msgs履歴の圧縮（2026-09-19・二次増加対策） ---


def _big_echo(text: str) -> str:
    """大きなtool_resultを返す道具（履歴圧縮の効果測定用）"""
    return "R" * 4000


def test_old_tool_results_are_compacted(tmp_path):
    """fail条件ケース: 直近N件を超えた古いtool_resultの本文が畳まれること

    msgsを畳まないと送信量がステップ数の二次で増える（実測 k≈1,206
    tokens/steps^2・打ち切られていない2runで係数のばらつき1.10倍）。
    25step完走に753,750トークン必要になり現行上限200,000では到達不能。
    """
    script = [_tool_resp("echo", {"text": f"x{i}"}, call_id=f"tc-{i}")
              for i in range(6)]
    script.append(_content_resp("done", 1))
    llm = ScriptedLLM(script)
    h, _, _ = _make_harness(tmp_path, llm, registry={"echo": _big_echo},
                            limits=Limits(max_steps=10, keep_recent_tool_results=2))
    out = h.run("repeat")
    assert out["abort_reason"] is None

    final = llm.seen_messages[-1]
    tool_msgs = [m for m in final if m.get("role") == "tool"]
    assert len(tool_msgs) == 6, "tool_result のメッセージ自体は消さない（契約維持）"

    full = [m for m in tool_msgs if len(m["content"]) > 1000]
    omitted = [m for m in tool_msgs if m["content"].startswith("[omitted")]
    assert len(full) == 2, f"本文を残すのは直近2件のみ（実際: {len(full)}）"
    assert len(omitted) == 4, f"それ以前は畳む（実際: {len(omitted)}）"


def test_compacted_result_keeps_tool_identity(tmp_path):
    """畳んだ後も「何をして何が返ったか」が残ること

    本文を丸ごと捨てるとLLMが同じ道具を再実行し、かえってステップが増える。
    tool名・引数・元の長さを1行で残して「もう実行した」と分かるようにする。
    """
    script = [_tool_resp("echo", {"text": f"x{i}"}, call_id=f"tc-{i}")
              for i in range(3)]
    script.append(_content_resp("done", 1))
    llm = ScriptedLLM(script)
    h, _, _ = _make_harness(tmp_path, llm, registry={"echo": _big_echo},
                            limits=Limits(max_steps=10, keep_recent_tool_results=1))
    h.run("repeat")

    final = llm.seen_messages[-1]
    omitted = [m for m in final
               if m.get("role") == "tool" and m["content"].startswith("[omitted")]
    assert omitted, "畳まれたメッセージが存在すること"
    body = omitted[0]["content"]
    assert "echo" in body, f"tool名が残ること: {body}"
    assert "4000" in body, f"元の長さが残ること: {body}"


def test_tool_call_ids_preserved_after_compaction(tmp_path):
    """境界: 畳んでも tool_call_id の対応が壊れないこと

    OpenAI契約ではassistantのtool_callsと後続toolメッセージのidが
    1対1で対応している必要がある。壊れるとプロバイダが400を返す。
    """
    script = [_tool_resp("echo", {"text": f"x{i}"}, call_id=f"tc-{i}")
              for i in range(4)]
    script.append(_content_resp("done", 1))
    llm = ScriptedLLM(script)
    h, _, _ = _make_harness(tmp_path, llm, registry={"echo": _big_echo},
                            limits=Limits(max_steps=10, keep_recent_tool_results=1))
    h.run("repeat")

    final = llm.seen_messages[-1]
    assistant_ids = [tc["id"] for m in final if m.get("role") == "assistant"
                     for tc in (m.get("tool_calls") or [])]
    tool_ids = [m["tool_call_id"] for m in final if m.get("role") == "tool"]
    assert assistant_ids == tool_ids, "id対応が保たれること"
    assert len(set(tool_ids)) == len(tool_ids), "id重複が無いこと"


def test_compaction_growth_is_linear_not_quadratic(tmp_path):
    """効果検証: 圧縮ありなら送信量がステップ数に線形（二次でない）

    無効化(keep=999)との対比で、累計送信量の増加次数が変わることを示す。
    """
    def _run(keep: int) -> int:
        script = [_tool_resp("echo", {"text": f"x{i}"}, call_id=f"tc-{i}")
                  for i in range(12)]
        script.append(_content_resp("done", 1))
        llm = ScriptedLLM(script)
        h, _, _ = _make_harness(tmp_path / f"k{keep}", llm,
                                registry={"echo": _big_echo},
                                limits=Limits(max_steps=20,
                                              keep_recent_tool_results=keep))
        h.run("repeat")
        return sum(sum(len(str(m)) for m in msgs) for msgs in llm.seen_messages)

    compacted = _run(2)
    unbounded = _run(999)
    assert compacted < unbounded / 2, (
        f"圧縮で累計送信量が半分以下になること（圧縮{compacted:,} vs "
        f"無圧縮{unbounded:,}）")


def test_keep_recent_default_preserves_behaviour(tmp_path):
    """後方互換: keep_recent_tool_results の既定では短いrunの挙動が変わらない"""
    llm = ScriptedLLM([_tool_resp("echo", {"text": "x"}), _content_resp("done", 7)])
    h, _, _ = _make_harness(tmp_path, llm)
    out = h.run("use echo")
    assert out["content"] == "done"
    assert out["tokens_used"] == 5 + 7
    final = llm.seen_messages[-1]
    tool_msgs = [m for m in final if m.get("role") == "tool"]
    assert tool_msgs and not tool_msgs[0]["content"].startswith("[omitted")


def test_max_steps_is_reachable_within_token_limit():
    """spec内的不整合の再発防止: max_steps がトークン上限内で到達可能であること

    2026-09-19実測の欠陥: spec §5 は「ステップ25回」と「トークン500k」を同時に
    定めていたが、履歴圧縮が無いと25stepに753,750トークン必要で両立しなかった
    （k≈1,206 tokens/steps^2）。圧縮導入で1stepあたりが一定になったため、
    「1step平均 × max_steps < abort閾値」で機械的に整合を検査する。

    1step平均の基準値: mock実測 24,112文字/step ÷ 3.5文字/token ≒ 6,890 tokens
    （tool_result 8,000文字・keep=3 の保守的条件）。
    """
    lim = Limits()
    EST_TOKENS_PER_STEP = 6_890  # 上記実測由来の保守値
    abort_at = lim.max_tokens * lim.abort_at_fraction
    need = EST_TOKENS_PER_STEP * lim.max_steps
    assert need < abort_at, (
        f"max_steps={lim.max_steps} には約{need:,}トークン必要だが "
        f"abort閾値は{abort_at:,.0f}（max_tokens={lim.max_tokens:,}）。"
        "max_stepsを下げるか上限を上げるか、履歴圧縮を強めること")


def test_compaction_is_idempotent(tmp_path):
    """境界: 既に畳んだメッセージを再度畳んでも壊れない（毎ステップ呼ばれるため）"""
    llm = ScriptedLLM([_content_resp("done", 1)])
    h, _, _ = _make_harness(tmp_path, llm, limits=Limits(keep_recent_tool_results=0))
    msgs = [
        {"role": "assistant", "content": "",
         "tool_calls": [{"id": "a1", "type": "function",
                         "function": {"name": "echo", "arguments": '{"text":"x"}'}}]},
        {"role": "tool", "tool_call_id": "a1", "content": "R" * 500},
    ]
    h._compact_history(msgs)
    once = msgs[1]["content"]
    h._compact_history(msgs)
    assert msgs[1]["content"] == once, "2回目の呼び出しで内容が変わらないこと"
    assert "500 chars" in once, f"初回で元の長さが記録されること: {once}"


def test_compaction_applies_to_resumed_messages(tmp_path):
    """未検証領域1: resume経路（run(messages=...)）でも圧縮が効くこと

    specでresumeはPhase 1必須機能。渡された履歴が既に長い場合、圧縮が
    効かないとresume直後の1回目の送信でトークンを浪費する。
    """
    prior: list[dict] = [{"role": "user", "content": "task"}]
    for i in range(5):
        prior.append({"role": "assistant", "content": "",
                      "tool_calls": [{"id": f"p{i}", "type": "function",
                                      "function": {"name": "echo",
                                                   "arguments": '{"text":"x"}'}}]})
        prior.append({"role": "tool", "tool_call_id": f"p{i}", "content": "R" * 3000})

    llm = ScriptedLLM([_content_resp("done", 1)])
    h, _, _ = _make_harness(tmp_path, llm,
                            limits=Limits(keep_recent_tool_results=2))
    h.run("ignored", messages=prior)

    sent = llm.seen_messages[0]
    omitted = [m for m in sent
               if m.get("role") == "tool" and m["content"].startswith("[omitted")]
    full = [m for m in sent
            if m.get("role") == "tool" and len(m["content"]) > 1000]
    assert len(omitted) == 3, f"渡された履歴のうち古い3件が畳まれること（{len(omitted)}）"
    assert len(full) == 2, f"直近2件は本文が残ること（{len(full)}）"


def test_compaction_handles_missing_tool_call_id(tmp_path):
    """未検証領域2: tool_call_id が引けない場合も落ちず "?" で畳むこと

    assistant側にtool_callsが無い／idが欠けたtoolメッセージは通常発生しないが、
    resumeで外部から渡された履歴やプロバイダ差で起こりうる。ここで例外が出ると
    ループ全体が落ちる（圧縮は毎ステップ呼ばれるため影響が大きい）。
    """
    llm = ScriptedLLM([_content_resp("done", 1)])
    h, _, _ = _make_harness(tmp_path, llm, limits=Limits(keep_recent_tool_results=0))
    msgs: list[dict] = [
        {"role": "tool", "tool_call_id": "unknown-id", "content": "A" * 300},
        {"role": "tool", "content": "B" * 300},  # tool_call_id そのものが無い
    ]
    h._compact_history(msgs)
    assert msgs[0]["content"] == "[omitted: ?() → 300 chars]"
    assert msgs[1]["content"] == "[omitted: ?() → 300 chars]"


def test_compaction_truncates_huge_arguments(tmp_path):
    """境界: 引数自体が巨大な場合は120字で切る（畳んだのに1行が長大になるのを防ぐ）"""
    llm = ScriptedLLM([_content_resp("done", 1)])
    h, _, _ = _make_harness(tmp_path, llm, limits=Limits(keep_recent_tool_results=0))
    big_args = '{"text":"' + "Z" * 500 + '"}'
    msgs: list[dict] = [
        {"role": "assistant", "content": "",
         "tool_calls": [{"id": "h1", "type": "function",
                         "function": {"name": "echo", "arguments": big_args}}]},
        {"role": "tool", "tool_call_id": "h1", "content": "R" * 300},
    ]
    h._compact_history(msgs)
    body = msgs[1]["content"]
    assert body.endswith("→ 300 chars]")
    assert "…" in body, f"引数が切り詰められること: {body[:80]}"
    assert len(body) < 200, f"1行が長大化しないこと（実際 {len(body)}）"


def test_compaction_never_touches_system_or_user(tmp_path):
    """境界: system / user メッセージは畳まない（タスク本文の消失防止）"""
    llm = ScriptedLLM([_content_resp("done", 1)])
    h, _, _ = _make_harness(tmp_path, llm, limits=Limits(keep_recent_tool_results=0))
    msgs: list[dict] = [
        {"role": "system", "content": "S" * 5000},
        {"role": "user", "content": "U" * 5000},
        {"role": "tool", "tool_call_id": "x", "content": "T" * 5000},
    ]
    h._compact_history(msgs)
    assert len(msgs[0]["content"]) == 5000, "systemは不変"
    assert len(msgs[1]["content"]) == 5000, "userは不変"
    assert msgs[2]["content"].startswith("[omitted"), "toolのみ畳む"
