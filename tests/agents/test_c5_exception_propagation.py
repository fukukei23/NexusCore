"""C5: execute_llm_task の例外伝播検証（spec E+α改 T5/T6/T7）。

T5: フラグOFF(本番)で LLM失敗時・{}/「」でなく例外伝播(α)
T6: フラグON(テスト保護)で従来{}/「」フォールバック維持
T7: real成功時は従来通り result を返す(回帰)

※429/恒久失敗の retry 境界(T6 spec FR4)は provider 層(openai_compat.py:131 429 raise・
base.py convert_http_error_to_nexus_error)+ 既存 retry_on で保証される。
"""
from unittest.mock import MagicMock, patch

import pytest


def _import_base_agent():
    from nexuscore.agents.base_agent import BaseAgent

    return BaseAgent


def _make_agent(exc=None, result="ok"):
    """LLM が exc を投げる(または result を返す)エージェントを構築。"""
    mock_llm = MagicMock()
    if exc is not None:
        mock_llm.execute.side_effect = exc
    else:
        mock_llm.execute.return_value = result
        mock_llm.last_call_mode = "real"
    mock_router = MagicMock()
    mock_router.get_llm_for_task.return_value = mock_llm
    with patch("nexuscore.agents.base_agent.LLMRouter", None):
        BaseAgent = _import_base_agent()
        agent = BaseAgent()
    agent.llm_router = mock_router
    return agent


def test_t5_execute_llm_task_raises_without_flag(monkeypatch):
    """T5: フラグOFF(本番)で LLM失敗時・{}/「」でなく例外伝播(α)。"""
    monkeypatch.delenv("NEXUSCORE_ALLOW_STUB_FALLBACK", raising=False)
    agent = _make_agent(exc=RuntimeError("exec failed"))
    with patch("nexuscore.agents.base_agent.HAS_RETRY", False):
        with pytest.raises(RuntimeError, match="exec failed"):
            agent.execute_llm_task("test", as_json=True)


def test_t6_fallback_with_flag(monkeypatch):
    """T6: フラグON(テスト保護)で従来{}/「」フォールバック維持(C5後方互換)。"""
    monkeypatch.setenv("NEXUSCORE_ALLOW_STUB_FALLBACK", "1")
    agent = _make_agent(exc=RuntimeError("exec failed"))
    with patch("nexuscore.agents.base_agent.HAS_RETRY", False):
        result = agent.execute_llm_task("test", as_json=True)
        assert result == "{}"


def test_t7_real_success_returns_result(monkeypatch):
    """T7: real成功時は従来通り result を返す(回帰・フラグOFFでも成功は妨げない)。"""
    monkeypatch.delenv("NEXUSCORE_ALLOW_STUB_FALLBACK", raising=False)
    agent = _make_agent(result="real response")
    with patch("nexuscore.agents.base_agent.HAS_RETRY", False):
        result = agent.execute_llm_task("test")
        assert result == "real response"
