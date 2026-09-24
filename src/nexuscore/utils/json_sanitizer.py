from __future__ import annotations

import json
import re
from typing import Any

# コードフェンスを検出するためのコンパイル済み正規表現
_FENCE_RE = re.compile(r"^\s*```(?:json)?\s*|\s*```\s*$", re.DOTALL)


def _reject_constant(name: str) -> float:
    """json.loads の parse_constant 用: NaN/Infinity 等の非標準定数を拒否する（MLR mm#3対策）."""
    raise ValueError(f"non-standard constant is not allowed: {name}")


def _iter_json_blocks(s: str):
    """文字列リテラルを意識しつつ、釣り合う {...} / [...] ブロックを順に走査する.

    文字列内のブレースは数えず、エスケープされた引用符も正しく扱う。
    未閉鎖ブロック（途中切断）に到達したら走査を打ち切る。
    """
    i, n = 0, len(s)
    while i < n:
        ch = s[i]
        if ch not in "{[":
            i += 1
            continue
        open_ch = ch
        close_ch = "}" if ch == "{" else "]"
        depth = 0
        in_str = False
        esc = False
        j = i
        closed = False
        last_opener = -1
        while j < n:
            cur = s[j]
            if in_str:
                if esc:
                    esc = False
                elif cur == "\\":
                    esc = True
                elif cur == '"':
                    in_str = False
            elif cur == '"':
                in_str = True
            elif cur == open_ch:
                depth += 1
                if j > i:
                    last_opener = j
            elif cur == close_ch:
                depth -= 1
                if depth == 0:
                    yield s[i : j + 1]
                    i = j + 1
                    closed = True
                    break
            j += 1
        if not closed:
            # 未閉鎖（truncation）— 走査中に記録した最後の内側オープナーへ跳び、
            # ネストした有効ブロックの復元を試みる（gem#1 MLR指摘のO(N²)回避・
            # 病理入力「{が50000連続」で実測120秒超過→跳び先修正で即時終了を確認）。
            # last_opener が無い（=自分自身が最後）場合は1文字進める。
            # ※ last_opener は必ず > i（j > i 条件）のため進行保証・off-by-oneに注意
            #   （last_opener+1 にするとオープナー自体をスキップする事故・実測で発見）
            i = last_opener if last_opener != -1 else i + 1
            continue


def extract_json_payload(s: str) -> dict | list | str:
    """釣り合うJSONブロックを順にパースし、最初に成功したものを返す.

    strict=False で文字列内の制御文字（生改行等）を許容する。
    どのブロックもパースできなければ元の文字列を返す。
    """
    for block in _iter_json_blocks(s):
        try:
            return json.loads(block, strict=False, parse_constant=_reject_constant)
        except (json.JSONDecodeError, ValueError):
            continue
    return s


def sanitize_json_like(payload: Any) -> dict | list | Any:
    """
    LLMからの出力を安全にJSONオブジェクトに変換する。

    - dict/list はそのまま返却
    - str の場合:
        1) ```json / ``` フェンスを除去
        2) 釣り合うJSONブロックを順に抽出し json.loads（strict=False・制御文字許容）
           複数ブロックが散在する場合は有効な最初のブロックを採用
        3) 失敗時は元の文字列を返却
    - その他の型はそのまま返却
    """
    if isinstance(payload, (dict, list)):
        return payload
    if not isinstance(payload, str):
        return payload

    # 1. コードフェンスを除去
    s = _FENCE_RE.sub("", payload.strip())

    # 2-3. ブロック抽出+パース（失敗時は元文字列）
    return extract_json_payload(s)
