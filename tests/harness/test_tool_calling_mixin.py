"""ToolCallingMixin × OpenAILLM 結合テスト（Task 6 / plan §Task 6）

plan雛形をベースに、plan修正条項・既存実装・Task 9の force_429 などを考慮して
「stub モードで fixed echo 応答が返ること」「返り値キー3種を含むこと」を検証する。

実 HTTP 経路は叩かない（real_calls=False の stub 分岐を踏む）。
"""
from __future__ import annotations

import pytest

from nexuscore.harness.tool_calling_mixin import InternalToolCall
from nexuscore.llm.providers.anthropic_provider import (
    AnthropicLLM,  # noqa: F401 — factory closure で参照
)
from nexuscore.llm.providers.gemini_provider import GeminiLLM
from nexuscore.llm.providers.openai_compat import OpenAICompatLLM
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


# --- セキュリティレビュー対応（push後 feedback 2件）のガード検証 ---


def test_adapt_response_handles_empty_choices():
    """不正応答: choices が空でも KeyError を出さず空の tool_calls を返す（finding 2 対応）"""
    llm = _make_openai_llm_stub()
    out = llm._adapt_response_native_to_internal({"choices": [], "usage": {"total_tokens": 0}})
    assert out == {"content": "", "tool_calls": [], "usage": {"total_tokens": 0}}


def test_adapt_response_handles_missing_message():
    """不正応答: message が不在でも AttributeError を出さない"""
    llm = _make_openai_llm_stub()
    out = llm._adapt_response_native_to_internal({"choices": [{}]})
    assert out["tool_calls"] == []
    assert out["content"] is None


def test_adapt_response_skips_tool_call_without_function_name():
    """不正応答: tool_call に function.name が無いものはスキップ"""
    llm = _make_openai_llm_stub()
    raw = {
        "choices": [
            {
                "message": {
                    "tool_calls": [
                        {"id": "bad", "type": "function", "function": {}},  # name 不在
                        {
                            "id": "ok",
                            "type": "function",
                            "function": {"name": "echo", "arguments": "{}"},
                        },
                    ]
                }
            }
        ]
    }
    out = llm._adapt_response_native_to_internal(raw)
    assert len(out["tool_calls"]) == 1
    assert out["tool_calls"][0].name == "echo"


def test_call_http_tool_stub_path_unchanged():
    """stub モード（real_calls=False）はセキュリティ指摘後も同じ固定 echo 応答を返す"""
    llm = _make_openai_llm_stub()
    out = llm._call_http_tool({"model": "x"})
    assert out["choices"][0]["message"]["tool_calls"][0]["function"]["name"] == "echo"
    assert "usage" in out


# --- Task 7: 残り3クラス Mix-in 検証 ---


def _force_stub(llm):
    """どのproviderでもreal_calls=Falseに強制してstub分岐を踏ませる"""
    llm.real_calls = False
    return llm


@pytest.mark.parametrize(
    "factory",
    [
        lambda: _force_stub(OpenAICompatLLM(model_name="test-model")),
        lambda: _force_stub(AnthropicLLM(model_name="test-model")),
        lambda: _force_stub(GeminiLLM(model_name="test-model")),
    ],
    ids=["OpenAICompat", "Anthropic", "Gemini"],
)
def test_other_providers_complete_with_tools_stub(factory):
    """残り3プロバイダーも stub モードで complete_with_tools が動作する"""
    llm = factory()
    out = llm.complete_with_tools(
        messages=[{"role": "user", "content": "x"}],
        tools=[
            {
                "type": "function",
                "function": {
                    "name": "echo",
                    "parameters": {"type": "object", "properties": {}, "required": []},
                },
            }
        ],
    )
    assert "tool_calls" in out, f"missing tool_calls in {out}"
    assert "content" in out, f"missing content in {out}"
    assert "usage" in out, f"missing usage in {out}"
    assert isinstance(out["tool_calls"], list)
    assert len(out["tool_calls"]) >= 1, f"expected at least one tool_call in stub: {out['tool_calls']}"
    tc = out["tool_calls"][0]
    assert isinstance(tc, InternalToolCall)
    assert tc.name == "echo"


@pytest.mark.parametrize(
    "factory",
    [
        lambda: _force_stub(OpenAICompatLLM(model_name="test-model")),
        lambda: _force_stub(AnthropicLLM(model_name="test-model")),  # noqa: F841
        lambda: _force_stub(GeminiLLM(model_name="test-model")),
    ],
    ids=["OpenAICompat", "Anthropic", "Gemini"],
)
def test_other_providers_mro_includes_mixin(factory):
    """残り3プロバイダーの MRO に ToolCallingMixin が含まれる"""
    llm = factory()
    mro_names = [c.__name__ for c in type(llm).__mro__]
    assert "ToolCallingMixin" in mro_names, f"ToolCallingMixin not in MRO: {mro_names}"
    assert mro_names.index("ToolCallingMixin") < mro_names.index("BaseLLM"), mro_names


# --- tool-calling 経路の stub fallback 契約（2026-09-05・mypy 12件の実バグ側） ---


def _prepare_real_call_attrs(llm):
    """real 経路を踏ませるために provider 別の必須属性を揃える

    NOTE: GeminiLLM は `__init__` で `self.base_url` / `self.api_key` を設定しないため
    （`_call_http_tool` が `self.base_url` を参照するのに定義が無い＝real 経路は未完成）、
    テスト側で注入して他 provider と同じ条件に揃える。この実装欠陥自体は本テストの対象外で、
    別途バックログへ起票済み（2026-09-05 実測）。
    """
    llm.real_calls = True
    llm.api_key = "dummy-key"
    if not hasattr(llm, "base_url"):
        llm.base_url = "https://example.invalid"
    return llm


@pytest.mark.parametrize(
    "factory",
    [
        lambda: OpenAILLM(model_name="gpt-5-mini"),
        lambda: OpenAICompatLLM(model_name="test-model"),
        lambda: AnthropicLLM(model_name="test-model"),
        lambda: GeminiLLM(model_name="test-model"),
    ],
    ids=["OpenAI", "OpenAICompat", "Anthropic", "Gemini"],
)
def test_tool_call_stub_fallback_returns_dict(monkeypatch, factory):
    """real call 失敗 + ALLOW_STUB_FALLBACK 時、_call_http_tool は dict を返す

    旧実装は `_stub_fallback_response` が as_json の値に関わらず常に str を返していたため、
    dict 契約の tool-calling 経路では `_adapt_response_native_to_internal` が
    `AttributeError: 'str' object has no attribute 'get'` でクラッシュしていた
    （2026-09-05 実測）。fallback は「失敗時に代替応答を返す」のが目的なので、
    tool-calling 経路では provider native 形式の dict を返さなければならない。
    """
    monkeypatch.setenv("NEXUSCORE_ALLOW_STUB_FALLBACK", "1")
    llm = factory()
    _prepare_real_call_attrs(llm)

    class _FailingSession:
        def post(self, *args, **kwargs):
            raise RuntimeError("simulated network failure")

    llm.session = _FailingSession()

    raw = llm._call_http_tool({"model": llm.model_name, "messages": [], "tools": []})
    assert isinstance(raw, dict), f"fallback must return provider-native dict, got {type(raw)}: {raw!r}"

    # dict を受け取ったアダプタが壊れずに内部形式へ変換できること
    out = llm._adapt_response_native_to_internal(raw)
    assert isinstance(out, dict)
    for key in ("content", "tool_calls", "usage"):
        assert key in out, f"missing {key!r} in adapted fallback response: {out}"


@pytest.mark.parametrize(
    "factory",
    [
        lambda: OpenAILLM(model_name="gpt-5-mini"),
        lambda: OpenAICompatLLM(model_name="test-model"),
        lambda: AnthropicLLM(model_name="test-model"),
        lambda: GeminiLLM(model_name="test-model"),
    ],
    ids=["OpenAI", "OpenAICompat", "Anthropic", "Gemini"],
)
def test_tool_call_raises_when_fallback_disabled(monkeypatch, factory):
    """ALLOW_STUB_FALLBACK 無効（既定）なら黙って代替せず例外を上げる（C5 silent-fallback 対策の維持）"""
    monkeypatch.delenv("NEXUSCORE_ALLOW_STUB_FALLBACK", raising=False)
    llm = factory()
    _prepare_real_call_attrs(llm)

    class _FailingSession:
        def post(self, *args, **kwargs):
            raise RuntimeError("simulated network failure")

    llm.session = _FailingSession()

    with pytest.raises(RuntimeError):
        llm._call_http_tool({"model": llm.model_name, "messages": [], "tools": []})


@pytest.mark.parametrize(
    "factory",
    [
        lambda: OpenAILLM(model_name="gpt-5-mini"),
        lambda: OpenAICompatLLM(model_name="test-model"),
        lambda: AnthropicLLM(model_name="test-model"),
        lambda: GeminiLLM(model_name="test-model"),
    ],
    ids=["OpenAI", "OpenAICompat", "Anthropic", "Gemini"],
)
def test_tool_call_raises_clear_error_when_session_missing(factory):
    """session 未初期化のまま real 呼び出しすると、None 属性エラーでなく明示的な RuntimeError になる"""
    llm = factory()
    _prepare_real_call_attrs(llm)
    llm.session = None

    with pytest.raises(RuntimeError, match="session"):
        llm._call_http_tool({"model": llm.model_name, "messages": [], "tools": []})
