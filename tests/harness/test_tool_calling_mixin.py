"""ToolCallingMixin × OpenAILLM 結合テスト（Task 6 / plan §Task 6）

plan雛形をベースに、plan修正条項・既存実装・Task 9の force_429 などを考慮して
「stub モードで fixed echo 応答が返ること」「返り値キー3種を含むこと」を検証する。

実 HTTP 経路は叩かない（real_calls=False の stub 分岐を踏む）。
"""
from __future__ import annotations

from nexuscore.harness.tool_calling_mixin import InternalToolCall
from nexuscore.llm.providers.openai_provider import OpenAILLM


def _make_openai_llm_stub() -> OpenAILLM:
    """real_calls=False を保証する OpenAILLM を生成（実 HTTP を絶対叩かない）

    pytest 実行環境で OPENAI_API_KEY が設定されていたり HTTP_CLIENT_FACTORY.available が真でも、
    生成後に real_calls を強制 False にすることで stub 分岐を踏ませる。
    """
    llm = OpenAILLM(model_name="gpt-5-mini")
    llm.real_calls = False  # 強制 stub
    return llm


def test_openai_complete_with_tools_returns_required_keys():
    """complete_with_tools が {content, tool_calls, usage} の3キーを持つ dict を返す"""
    llm = _make_openai_llm_stub()
    out = llm.complete_with_tools(
        messages=[{"role": "user", "content": "hi"}],
        tools=[
            {
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
        ],
    )
    assert isinstance(out, dict)
    assert "content" in out, f"missing 'content' in {out}"
    assert "tool_calls" in out, f"missing 'tool_calls' in {out}"
    assert "usage" in out, f"missing 'usage' in {out}"


def test_openai_complete_with_tools_stub_returns_tool_call_object():
    """stub モード（real_calls=False）で InternalToolCall 相当の tool_calls が返る

    OpenAI 形式の tool_calls 形式: `[{"id":..,"type":"function","function":{"name":..,"arguments":..}}]`
    """
    llm = _make_openai_llm_stub()
    out = llm.complete_with_tools(
        messages=[{"role": "user", "content": "hi"}],
        tools=[{"type": "function", "function": {"name": "echo"}}],
    )
    tcs = out["tool_calls"]
    assert isinstance(tcs, list), f"expected list, got {type(tcs)}"
    assert len(tcs) >= 1, f"expected at least one tool_call in stub mode, got {tcs}"
    tc = tcs[0]
    assert isinstance(tc, InternalToolCall), f"expected InternalToolCall, got {type(tc)}"
    assert tc.name == "echo", f"expected name='echo', got {tc.name!r}"
    assert isinstance(tc.args, dict), f"expected dict args, got {type(tc.args)}"
    assert tc.id, f"expected non-empty id, got {tc.id!r}"


def test_openai_mro_includes_tool_calling_mixin():
    """Mix-in 追加後の MRO が [OpenAILLM, ToolCallingMixin, BaseLLM, object] になっている"""
    llm = _make_openai_llm_stub()
    mro_names = [c.__name__ for c in type(llm).__mro__]
    assert "ToolCallingMixin" in mro_names, f"ToolCallingMixin not in MRO: {mro_names}"
    assert "BaseLLM" in mro_names, f"BaseLLM not in MRO: {mro_names}"
    # OpenAICompatLLM 等は無関係のはず
    assert mro_names.index("ToolCallingMixin") < mro_names.index("BaseLLM"), (
        f"ToolCallingMixin must come before BaseLLM in MRO: {mro_names}"
    )


def test_adapt_request_passes_model_and_tools():
    """_adapt_request_openai_to_native が model と messages と tools を含む dict を返す"""
    llm = _make_openai_llm_stub()
    body = llm._adapt_request_openai_to_native(
        messages=[{"role": "user", "content": "hi"}],
        tools=[{"type": "function", "function": {"name": "echo"}}],
    )
    assert body["model"] == llm.model_name
    assert body["messages"] == [{"role": "user", "content": "hi"}]
    assert body["tools"] == [{"type": "function", "function": {"name": "echo"}}]
