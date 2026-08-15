"""C5: retry 境界の完全検証（spec E+α改 T6/T7・FR4）。

T6: execute_llm_task で 429 発生時 ModelRateLimitError に変換され retry_on が機能する
T7: execute_llm_task で恒久失敗（5xx 等）時、retry されず即例外伝播

既存 test_c5_exception_propagation.py は patch(HAS_RETRY, False) で retry 経路を
回避していた。本ファイルは HAS_RETRY=True の実経路（retry_with_context wrapper）
を通して境界を機械検証する。
"""

from unittest.mock import MagicMock, patch

import pytest
import requests

from nexuscore.core.errors import ModelRateLimitError, UnexpectedSystemError


def _make_agent(exc=None, result=None):
    """LLM が常に exc を投げる（または result を返す）エージェントを構築。"""
    mock_llm = MagicMock()
    if exc is not None:
        mock_llm.execute.side_effect = exc
    else:
        # result はシーケンス可（side_effect 的に消費）。文字列単体は毎回同じ値。
        mock_llm.execute.side_effect = result
        mock_llm.execute.return_value = None
    mock_router = MagicMock()
    mock_router.get_llm_for_task.return_value = mock_llm
    with patch("nexuscore.agents.base_agent.LLMRouter", None):
        from nexuscore.agents.base_agent import BaseAgent

        agent = BaseAgent()
    agent.llm_router = mock_router
    return agent, mock_llm


@pytest.fixture(autouse=True)
def _no_sleep(monkeypatch):
    """retry backoff の実スリープを無効化（テスト高速化）。"""
    monkeypatch.setattr("nexuscore.core.retry_utils.time.sleep", lambda s: None)


class TestT6RateLimitRetry:
    """T6: 429 → ModelRateLimitError 変換 + retry_on 機能（FR4）。"""

    def test_429_converted_to_rate_limit_error_and_retried(self, monkeypatch):
        """T6: 429 HTTPError が ModelRateLimitError に変換され、max_retries=2 で計3回試行される。"""
        monkeypatch.delenv("NEXUSCORE_ALLOW_STUB_FALLBACK", raising=False)
        agent, mock_llm = _make_agent(exc=requests.HTTPError("429 Client Error: Too Many Requests"))

        with pytest.raises(ModelRateLimitError, match="Rate limit error"):
            agent.execute_llm_task("test", as_json=True)

        # max_retries=2 → 初回+再試行2回 = 3 attempt
        assert mock_llm.execute.call_count == 3

    def test_429_retry_recovers_on_success(self, monkeypatch):
        """T6: 1回目だけ429、2回目で成功 → retry が復帰して result を返す（stubでない実応答）。"""
        monkeypatch.delenv("NEXUSCORE_ALLOW_STUB_FALLBACK", raising=False)
        # side_effect シーケンス: 1回目 429 → 2回目 成功
        agent, mock_llm = _make_agent(
            result=[requests.HTTPError("429 Too Many Requests"), "real response"]
        )

        result = agent.execute_llm_task("test")

        assert result == "real response"
        assert mock_llm.execute.call_count == 2


class TestT7PermanentFailure:
    """T7: 恒久失敗（5xx 等）は retry されず即例外伝播（FR4）。"""

    def test_5xx_not_retried_immediate_raise(self, monkeypatch):
        """T7: 5xx 系メッセージは unexpected 分類 → 1回のみ試行で即 raise。"""
        monkeypatch.delenv("NEXUSCORE_ALLOW_STUB_FALLBACK", raising=False)
        agent, mock_llm = _make_agent(exc=RuntimeError("500 Internal Server Error"))

        with pytest.raises(UnexpectedSystemError, match="500 Internal Server Error"):
            agent.execute_llm_task("test", as_json=True)

        # retry されない = 1 attempt のみ
        assert mock_llm.execute.call_count == 1

    def test_permanent_failure_type_not_in_retry_on(self, monkeypatch):
        """T7: 伝播する例外は UnexpectedSystemError（retry_on 対象外）で伝播する。"""
        monkeypatch.delenv("NEXUSCORE_ALLOW_STUB_FALLBACK", raising=False)
        agent, mock_llm = _make_agent(exc=RuntimeError("permission denied"))

        with pytest.raises(UnexpectedSystemError):
            agent.execute_llm_task("test", as_json=True)

        assert mock_llm.execute.call_count == 1
