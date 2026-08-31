"""全LLM形式のtool calling差分を吸収するMixin（spec §3・4クラスにMix-in）

Task 5 skeleton（plan §Task 5）: 差分フック3種は NotImplementedError を維持し、
Task 6/7 で provider 別に上書きされる前提のスケルトン。

spec 参照: docs/superpowers/specs/2026-08-30-nexuscore-agent-harness-design.md §3
"""
from __future__ import annotations

import json
import logging
import re
import uuid
from typing import Any

log = logging.getLogger(__name__)


class InternalToolCall:
    """tool call の内部表現（spec §3 フォーク2）

    provider 差を吸収する中立フォーマット。
    - id: spec §10 に従い sanitize した provider 側 id を優先、無ければ UUID v4 を採番
    - name: tool name
    - args: tool arguments（dict 形・パース失敗時は `{"_raw": <生>}`）
    """

    __slots__ = ("name", "args", "id")

    def __init__(self, name: str, args: dict, id: str) -> None:
        self.name = name
        self.args = args
        self.id = id

    def to_openai(self) -> dict:
        """OpenAI 形式への書出し（spec §3 固定ルール）: arguments は JSON 文字列"""
        return {
            "id": self.id,
            "type": "function",
            "function": {
                "name": self.name,
                "arguments": json.dumps(self.args, ensure_ascii=False),
            },
        }

    @classmethod
    def from_openai(cls, tc: dict) -> InternalToolCall:
        """OpenAI provider の tool_call dict から生成。arguments は文字列→dict パースを試みる"""
        raw_args = tc["function"]["arguments"]
        if isinstance(raw_args, str):
            try:
                args = json.loads(raw_args)
            except json.JSONDecodeError:
                args = {"_raw": raw_args}
        else:
            args = raw_args
        return cls(name=tc["function"]["name"], args=args, id=_sanitize_id(tc.get("id")))

    @classmethod
    def from_anthropic(cls, tc: dict) -> InternalToolCall:
        """Anthropic: `{"name":..., "input":...}` 形式"""
        return cls(name=tc["name"], args=tc.get("input", {}), id=_sanitize_id(tc.get("id")))

    @classmethod
    def from_gemini(cls, fc: dict) -> InternalToolCall:
        """Gemini: `{"name":..., "args":{...}}` 形式。id 不在/不正時は UUID v4 を採番"""
        sanitized = _sanitize_id(fc.get("id"))
        if not sanitized:
            sanitized = str(uuid.uuid4())
        return cls(
            name=fc["name"],
            args=fc.get("args", {}),
            id=sanitized,
        )


def _sanitize_id(raw: str | None) -> str:
    """spec §10: `^[a-zA-Z0-9_-]{1,64}$` に整形。空文字/不正文字除去後の結果も空なら空文字を返す（呼び出し側で UUID 採番を判断）

    Args:
        raw: provider から来た tool_call id。None/空文字の場合もある
    Returns:
        整形後の id（空文字の可能性あり・呼び出し側で UUID フォールバック判断）
    """
    s = (raw or "").strip()
    s = re.sub(r"[^a-zA-Z0-9_-]", "", s)[:64]
    return s


class ToolCallingMixin:
    """provider 基底の ``__init__`` 完了後に ``super().__init__()`` で呼ばれる Mixin

    OpenAI 形式の messages/tools を受け取り、`{content, tool_calls, usage}` を返す
    `complete_with_tools` の公開 API を持つ。provider 固有の差分は下の3フックで吸収する:

    - ``_adapt_request_openai_to_native``: OpenAI → provider native 形式への request 変換
    - ``_call_http_tool``: provider 側の HTTP 経路呼び出し（stub 切替もここを抜ける）
    - ``_adapt_response_native_to_internal``: provider native → 中立 InternalToolCall への response 変換

    これら3種は provider クラスで上書きされる前提（Task 6/7）。
    """

    def complete_with_tools(
        self, messages: list[dict], tools: list[dict], **kwargs: Any
    ) -> dict:
        """OpenAI 形式 messages/tools を受け取り、内部形式の tool_calls を含む応答 dict を返す

        Args:
            messages: OpenAI 形式の messages（`[{"role":..., "content":...}]`）
            tools: OpenAI 形式の tool 定義（`[{"type":"function","function":{...}}]`）
            **kwargs: provider 固有の追加パラメータ
        Returns:
            `{"content": str, "tool_calls": list[InternalToolCall], "usage": dict}` 形式 dict
        """
        body = self._adapt_request_openai_to_native(messages, tools, **kwargs)
        raw = self._call_http_tool(body)
        return self._adapt_response_native_to_internal(raw)

    # --- 差分フック（spec §3・Task 6/7 で provider 別に上書き） ---

    def _adapt_request_openai_to_native(
        self, messages: list[dict], tools: list[dict], **kwargs: Any
    ) -> Any:
        """OpenAI → provider native request 形式への変換（provider 別 override）"""
        raise NotImplementedError(
            "ToolCallingMixin._adapt_request_openai_to_native must be overridden "
            "by provider subclass (Task 6/7)"
        )

    def _adapt_response_native_to_internal(self, raw: Any) -> dict:
        """provider native response → 中立 dict 形式への変換（provider 別 override）

        戻り値: `{"content": str, "tool_calls": list[InternalToolCall], "usage": dict}`
        """
        raise NotImplementedError(
            "ToolCallingMixin._adapt_response_native_to_internal must be overridden "
            "by provider subclass (Task 6/7)"
        )

    def _call_http_tool(self, body: Any) -> Any:
        """provider の既存 HTTP 経路呼び出し（HTTP_CLIENT_FACTORY・stub 切替をそのまま利用）

        Task 6/7 で provider 別 override。
        """
        raise NotImplementedError(
            "ToolCallingMixin._call_http_tool must be overridden "
            "by provider subclass (Task 6/7)"
        )
