"""BaseLLM._stub_response の明示的 WARN ログテスト（silent failure 対策）。

real呼び出し無効時（APIキー無し等）に _stub_response がダミー応答を返す際、
WARN ログで「本物のLLMは動いていない」ことを実行時に判別可能にする。
"""

import logging

from nexuscore.llm.providers.base import BaseLLM


def test_stub_response_emits_warning(caplog):
    """_stub_response 呼出時、real無効を示す WARN が出る。"""
    base = BaseLLM("glm:glm-5.2")
    with caplog.at_level(logging.WARNING, logger="BaseLLM"):
        result = base._stub_response("glm")
    # 応答は返す（処理継続）
    assert isinstance(result, str)
    # WARN ログに real 無効の旨が含まれる
    assert "STUB" in caplog.text or "stub" in caplog.text
    assert "real calls disabled" in caplog.text
    # model 名がログに含まれる（どのLLMがstubか判別可能）
    assert "glm-5.2" in caplog.text
    assert base.last_call_mode == "stub"


def test_stub_response_warning_level_is_warning(caplog):
    """WARN ログのレベルが WARNING（ERROR でなく・処理は継続）。"""
    base = BaseLLM("minimax:MiniMax-M3")
    with caplog.at_level(logging.DEBUG, logger="BaseLLM"):
        base._stub_response("minimax")
    warning_records = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert len(warning_records) >= 1


def test_stub_fallback_response_not_changed_this_task(caplog):
    """_stub_fallback_response は今回 WARN 追加対象外（既存 log_error あり）。

    本タスクの範囲: real無効時(_stub_response) のみ。real失敗時(stub-fallback) は
    execute_real_or_fallback / 各provider で既に log_error(ERROR) が出るため据え置き。
    """
    base = BaseLLM("glm:glm-5.2")
    with caplog.at_level(logging.WARNING, logger="BaseLLM"):
        base._stub_fallback_response("glm")
    # 「real calls disabled」は _stub_response 専用メッセージ・fallback には出ない
    assert "real calls disabled" not in caplog.text
    assert base.last_call_mode == "stub-fallback"
