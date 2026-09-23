"""深修復テスト（2026-09-24・n≥10検証実測対策）.

MiniMax plan_generate の壊れ方3種への対応:
  (a) 有効JSON+余分テキスト（Extra data）→ 既存対応
  (b) 複数JSONブロックが本文中に散在 → 「最初の{〜最後の}」一括抽出では壊れる
  (c) 文字列内に生改行等の制御文字 → strictなjson.loadsでは壊れる
"""

from nexuscore.utils.json_sanitizer import sanitize_json_like


def test_two_json_blocks_with_prose_returns_first_valid():
    """複数JSONブロック+本文: 有効な最初のブロックを復元する（(b)対策）."""
    text = (
        "前文です。\n"
        '{"result": "first"}\n'
        "解説を挟みます { } 。\n"
        '{"result": "second"}\n'
        "末尾の文章。"
    )
    assert sanitize_json_like(text) == {"result": "first"}


def test_control_character_inside_string_is_tolerated():
    """文字列内の生改行（制御文字）を許容して復元する（(c)対策・strict=False）."""
    text = '{"note": "1行目\n2行目"}'
    assert sanitize_json_like(text) == {"note": "1行目\n2行目"}


def test_valid_json_unchanged():
    assert sanitize_json_like('{"a": 1}') == {"a": 1}


def test_fence_and_trailing_text_unchanged():
    text = '```json\n{"a": 1}\n```\n以上です。'
    assert sanitize_json_like(text) == {"a": 1}


def test_no_json_returns_original():
    assert sanitize_json_like("JSONは含まれません") == "JSONは含まれません"


def test_truncated_block_recovers_inner_balanced_block():
    """未閉鎖ブロック（途中切断）でもクラッシュせず、釣り合う内側ブロックを復元する.

    2026-09-24 契約変更: 未閉鎖の開始位置は読み飛ばし後続を探す方式にしたため、
    内側の釣り合うブロックが復元される。不正な構造は下流の計画検証
    （planner_agent._is_plan_valid 等）で弾かれるため復元優先が安全。
    """
    text = '{"a": {"b": 1} 途中で切断'
    assert sanitize_json_like(text) == {"b": 1}


def test_truncated_block_without_any_valid_json_returns_original():
    """有効なブロックが一切無い切断テキストはクラッシュせず元文字列を返す."""
    text = '{"a": [1, 2 途中で切断'
    assert sanitize_json_like(text) == text


def test_first_block_invalid_falls_through_to_second():
    """1ブロック目が壊れていても2ブロック目の有効JSONを復元する."""
    text = '{"broken": [1, 2\n{"ok": true}'
    assert sanitize_json_like(text) == {"ok": True}


def test_escaped_quote_inside_string_does_not_break_scanner():
    """文字列内のエスケープ引用符（\\"）でスキャンが文字列を抜けない（Phase1欠落#6）."""
    text = 'pre {"a": "he said \\"hi\\" } ok"} post'
    assert sanitize_json_like(text) == {"a": 'he said "hi" } ok'}


def test_brace_inside_string_does_not_break_scanner():
    """文字列内のブレースで深さ計算が崩れない（Phase1欠落#7）."""
    text = 'x {"a": "}"} y'
    assert sanitize_json_like(text) == {"a": "}"}
