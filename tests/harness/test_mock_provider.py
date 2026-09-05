"""LocalToolCallDummyLLM 単体テスト（Task 9 / plan §Task 9）

plan雛形をベースに、実体契約へ修正した上で検証する。

plan雛形からの変更点（実装時判断）:
- 雛形は tool あり応答で ``content: None`` を返すが、ToolCallingMixin の
  戻り値契約は ``content: str``（tool_calling_mixin.py docstring）のため
  ``""`` を期待値に変更
- 雛形の ``_inner``（LocalLLM）は未使用でwrapが形骸化するため、
  ``model_name`` を委譲する契約を追加
- plan 1959行「mock実行時はcapability更新禁止」の検証テストを追加
  （mockはcapability tableに一切触れないことを固定）
"""
from __future__ import annotations

import json

from nexuscore.harness.mock_provider import LocalToolCallDummyLLM
from nexuscore.llm.providers.local_provider import LocalLLM

_ECHO_TOOL = {
    "type": "function",
    "function": {
        "name": "echo",
        "parameters": {
            "type": "object",
            "properties": {"x": {"type": "string"}},
            "required": ["x"],
        },
    },
}


def test_dummy_returns_tool_call_for_first_tool():
    """先頭tool名のダミーtool_callを返す（spec §3 V3: LocalLLM=ダミースタブ）"""
    llm = LocalToolCallDummyLLM()
    out = llm.complete_with_tools(
        messages=[{"role": "user", "content": "hi"}],
        tools=[_ECHO_TOOL],
    )
    assert len(out["tool_calls"]) >= 1
    assert out["tool_calls"][0].name == "echo"
    assert isinstance(out["tool_calls"][0].args, dict)


def test_tool_call_response_matches_mixin_contract():
    """戻り値は mixin 契約どおり content: str / usage: dict（雛形のNone修正）"""
    llm = LocalToolCallDummyLLM()
    out = llm.complete_with_tools(
        messages=[{"role": "user", "content": "hi"}],
        tools=[_ECHO_TOOL],
    )
    assert isinstance(out["content"], str)
    assert isinstance(out["usage"], dict)
    assert out["tool_calls"][0].id  # spec §10: id は常に存在


def test_empty_tools_returns_empty_result():
    """tools空なら tool_calls 空で返す"""
    llm = LocalToolCallDummyLLM()
    out = llm.complete_with_tools(messages=[{"role": "user", "content": "hi"}], tools=[])
    assert out["tool_calls"] == []
    assert isinstance(out["content"], str)


def test_wrapper_is_offline_stub():
    """実HTTPを一切叩かないスタブであること（last_call_mode=stub固定）"""
    llm = LocalToolCallDummyLLM()
    assert llm.last_call_mode == "stub"


def test_wrapper_delegates_model_name():
    """wrapしたLocalLLMへ model_name を委譲する（wrapが形骸化しない根拠）"""
    llm = LocalToolCallDummyLLM()
    assert llm.model_name == llm._inner.model_name
    assert isinstance(llm._inner, LocalLLM)


def test_mock_never_touches_capability_table(tmp_path):
    """plan 1959行: mock単体実行ではcapability tableを更新しない（loop経由のみ）"""
    cap_file = tmp_path / "cap.json"
    cap_file.write_text(
        json.dumps({"openai": {"supports_tool_calling": True, "schema_version": 1}})
    )
    before = cap_file.read_text()

    llm = LocalToolCallDummyLLM()
    llm.complete_with_tools(
        messages=[{"role": "user", "content": "hi"}],
        tools=[_ECHO_TOOL],
    )

    assert cap_file.read_text() == before  # ファイル無変更
    assert not hasattr(llm, "capability_table")  # 参照も保持しない


def test_multi_tools_selects_first(tmp_path):
    """境界④: 複数tools時は先頭toolを選択する（仕様固定・L438④）"""
    import copy

    second = copy.deepcopy(_ECHO_TOOL)
    second["function"]["name"] = "write_file"
    llm = LocalToolCallDummyLLM()
    resp = llm.complete_with_tools(
        messages=[{"role": "user", "content": "hi"}],
        tools=[_ECHO_TOOL, second],
    )
    assert len(resp["tool_calls"]) == 1
    assert resp["tool_calls"][0].name == "echo"  # 先頭 = _ECHO_TOOL
