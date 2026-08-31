"""LocalLLM用 tool_call ダミーラッパー（Task 9 / spec §3 V3）

LocalLLM は本番対象外のオフラインスタブ（spec §3 V3）のため
ToolCallingMixin を継承させず、テスト用に薄いラッパーで
complete_with_tools() の形だけ提供する。

plan雛形からの変更点（実装時判断）:
- 雛形は tool あり応答で ``content: None`` を返すが、ToolCallingMixin の
  戻り値契約は ``content: str`` のため ``""`` を返すよう修正
- 雛形の ``_inner`` が未使用でwrapが形骸化するため、``model_name`` /
  ``last_call_mode`` を内包オブジェクトへ委譲
"""
from __future__ import annotations

from nexuscore.harness.tool_calling_mixin import InternalToolCall
from nexuscore.llm.providers.local_provider import LocalLLM


class LocalToolCallDummyLLM:
    """LocalLLMを内包しcomplete_with_tools()の形だけ提供するテスト専用スタブ

    capability table には一切触れない（更新はloop経由のみ・plan 1959行）。
    """

    def __init__(self) -> None:
        self._inner = LocalLLM(model_name="dummy")

    @property
    def model_name(self) -> str:
        """内包するLocalLLMへ委譲（wrapを形骸化させない）"""
        return self._inner.model_name

    @property
    def last_call_mode(self) -> str:
        """常にstub（実HTTPを一切叩かない）"""
        return self._inner.last_call_mode

    def complete_with_tools(self, messages, tools, **kwargs):
        """直前のtool名から最小のダミーtool_call応答を返す（引数は呼び出し側で補完）"""
        self._inner.last_call_mode = "stub"
        if not tools:
            return {"content": "", "tool_calls": [], "usage": {}}
        name = tools[0]["function"]["name"]
        return {
            "content": "",
            "tool_calls": [InternalToolCall(name=name, args={}, id="dummy-1")],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
        }
