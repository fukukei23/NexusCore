from __future__ import annotations

import json
import re
from typing import Any

# コードフェンスを検出するためのコンパイル済み正規表現
_FENCE_RE = re.compile(r"^\s*```(?:json)?\s*|\s*```\s*$", re.DOTALL)


def sanitize_json_like(payload: Any) -> dict | list | Any:
    """
    LLMからの出力を安全にJSONオブジェクトに変換する。

    - dict/list はそのまま返却
    - str の場合:
        1) ```json / ``` フェンスを除去
        2) 文字列中の最長 {…} or […] を抽出し json.loads
        3) 失敗時は元の文字列を返却
    - その他の型はそのまま返却
    """
    if isinstance(payload, (dict, list)):
        return payload
    if not isinstance(payload, str):
        return payload

    # 1. コードフェンスを除去
    s = _FENCE_RE.sub("", payload.strip())

    # 2. 文字列中から最も外側にあるJSONオブジェクト/配列候補を特定
    brace, bracket = s.find("{"), s.find("[")
    starts = [p for p in (brace, bracket) if p != -1]
    if not starts:
        return payload  # JSON形式の開始記号が見つからない

    start = min(starts)
    end = max(s.rfind("}"), s.rfind("]"))
    if end <= start:
        return payload  # 有効な閉じ記号が見つからない

    candidate = s[start : end + 1]

    # 3. JSONとしてパースを試みる
    try:
        return json.loads(candidate)
    except Exception:
        return payload
