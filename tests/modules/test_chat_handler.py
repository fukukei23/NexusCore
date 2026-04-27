"""Tests for nexuscore.archive.modules.chat_handler — MiniMax HTTP backend"""

import pytest
from unittest.mock import patch

from nexuscore.archive.modules.chat_handler import handle_chat


@patch("nexuscore.archive.modules.chat_handler._call_minimax", return_value="こんにちは！")
def test_handle_chat_normal(mock_call):
    """[正常系] レスポンスと更新済み履歴が返る"""
    history = []
    result_msg, new_history = handle_chat("やあ", history)

    assert result_msg == "こんにちは！"
    assert new_history == [
        {"role": "user", "content": "やあ"},
        {"role": "assistant", "content": "こんにちは！"},
    ]
    # handle_chat is mutate-in-place: history already has both entries when _call_minimax returns
    assert mock_call.call_count == 1


@patch("nexuscore.archive.modules.chat_handler._call_minimax", return_value="元気です")
def test_handle_chat_with_existing_history(mock_call):
    """[正常系] 既存履歴を保持したまま追加"""
    history = [
        {"role": "user", "content": "前回の質問"},
        {"role": "assistant", "content": "前回の回答"},
    ]
    result_msg, new_history = handle_chat("元気？", history)

    assert result_msg == "元気です"
    assert len(new_history) == 4
    assert new_history[0] == {"role": "user", "content": "前回の質問"}
    assert new_history[2] == {"role": "user", "content": "元気？"}
    assert new_history[3] == {"role": "assistant", "content": "元気です"}

    called_arg = mock_call.call_args[0][0]
    assert len(called_arg) == 4  # 2 existing + 1 user + 1 assistant (mutated in-place)


@patch("nexuscore.archive.modules.chat_handler._call_minimax", side_effect=RuntimeError("API down"))
def test_handle_chat_error(mock_call):
    """[異常系] エラー時にエラーメッセージが返り、userのみ履歴に追加"""
    history = []
    result_msg, new_history = handle_chat("エラー起こして", history)

    assert "❌ エラー:" in result_msg
    assert "API down" in result_msg
    assert new_history == [{"role": "user", "content": "エラー起こして"}]


@patch("nexuscore.archive.modules.chat_handler._call_minimax", return_value="空ですね")
def test_handle_chat_empty_message(mock_call):
    """[境界] 空メッセージでも処理される"""
    history = []
    result_msg, new_history = handle_chat("", history)

    assert result_msg == "空ですね"
    assert new_history[0] == {"role": "user", "content": ""}
    assert new_history[1] == {"role": "assistant", "content": "空ですね"}


@patch("nexuscore.archive.modules.chat_handler._call_minimax")
def test_handle_chat_sequential_calls(mock_call):
    """[正常系] 複数回連続で履歴が累積される"""
    mock_call.side_effect = ["回答1", "回答2", "回答3"]

    history = []
    msg1, history = handle_chat("質問1", history)
    assert msg1 == "回答1"
    assert len(history) == 2

    msg2, history = handle_chat("質問2", history)
    assert msg2 == "回答2"
    assert len(history) == 4

    msg3, history = handle_chat("質問3", history)
    assert msg3 == "回答3"
    assert len(history) == 6

    roles = [h["role"] for h in history]
    assert roles == ["user", "assistant", "user", "assistant", "user", "assistant"]
    contents = [h["content"] for h in history]
    assert contents == ["質問1", "回答1", "質問2", "回答2", "質問3", "回答3"]


@patch("nexuscore.archive.modules.chat_handler._call_minimax")
def test_handle_chat_error_recovery(mock_call):
    """[正常系] エラー後も次の呼び出しで成功できる"""
    history = []

    mock_call.side_effect = ConnectionError("timeout")
    msg1, history = handle_chat("失敗する", history)
    assert "❌ エラー:" in msg1
    assert len(history) == 1

    mock_call.side_effect = None
    mock_call.return_value = "復旧しました"
    msg2, history = handle_chat("リトライ", history)
    assert msg2 == "復旧しました"
    assert len(history) == 3


@patch("nexuscore.archive.modules.chat_handler._call_minimax", return_value="Response")
def test_handle_chat_special_characters(mock_call):
    """[境界] 特殊文字を含むメッセージ"""
    special = "Hello! こんにちは! @#$%^&*()"
    result_msg, new_history = handle_chat(special, [])

    assert result_msg == "Response"
    assert new_history[0]["content"] == special


@patch("nexuscore.archive.modules.chat_handler._call_minimax", return_value="Long response ok")
def test_handle_chat_long_message(mock_call):
    """[境界] 長いメッセージ"""
    long_msg = "A" * 1000
    result_msg, new_history = handle_chat(long_msg, [])

    assert result_msg == "Long response ok"
    assert new_history[0]["content"] == long_msg


@patch("nexuscore.archive.modules.chat_handler._call_minimax", side_effect=TimeoutError("timeout"))
def test_handle_chat_timeout(mock_call):
    """[異常系] タイムアウト時にエラーメッセージが返る"""
    result_msg, new_history = handle_chat("Test", [])

    assert "❌ エラー:" in result_msg
    assert len(new_history) == 1


@patch("nexuscore.archive.modules.chat_handler._call_minimax")
def test_handle_chat_history_ordering(mock_call):
    """[正常系] 履歴の順序が保持される"""
    mock_call.side_effect = ["A", "B", "C"]

    history = []
    for msg in ["1", "2", "3"]:
        _, history = handle_chat(msg, history)

    contents = [h["content"] for h in history]
    assert contents == ["1", "A", "2", "B", "3", "C"]


@patch("nexuscore.archive.modules.chat_handler._call_minimax")
def test_handle_chat_error_recovery_sequence(mock_call):
    """[正常系] エラー→成功→エラー→成功のパターン"""
    mock_call.side_effect = [
        Exception("Error 1"),
        "Success 1",
        Exception("Error 2"),
        "Success 2",
    ]

    history = []
    r1, history = handle_chat("M1", history)
    assert "❌ エラー:" in r1

    r2, history = handle_chat("M2", history)
    assert r2 == "Success 1"

    r3, history = handle_chat("M3", history)
    assert "❌ エラー:" in r3

    r4, history = handle_chat("M4", history)
    assert r4 == "Success 2"
