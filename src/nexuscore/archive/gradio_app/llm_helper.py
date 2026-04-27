"""
Gradio UI コンポーネント用 LLM 呼び出しヘルパー。
Orchestrator の LLMRouter を経由し、失敗時は MiniMax 直接 API にフォールバックする。

Issue #53: Orchestratorバイパスアクセスパスの排除
"""

import logging
import os

import requests

logger = logging.getLogger(__name__)

_agent = None


def _get_agent():
    """BaseAgent シングルトンを遅延初期化して返す。"""
    global _agent
    if _agent is None:
        try:
            from nexuscore.agents.base_agent import BaseAgent

            _agent = BaseAgent()
            logger.info("BaseAgent 初期化成功 — LLMRouter 経由でルーティングします")
        except Exception as e:
            logger.warning("BaseAgent 初期化失敗: %s", e)
    return _agent


def _fallback_minimax(messages: list[dict], temperature: float = 0.2) -> str:
    """MiniMax 直接 HTTP 呼び出し（後方互換フォールバック）。"""
    api_key = os.getenv("MINIMAX_API_KEY")
    api_base = os.getenv("MINIMAX_API_BASE", "https://api.minimax.chat/v1")
    model = os.getenv("MINIMAX_MODEL", "MiniMax-M2.7")
    if not api_key:
        raise RuntimeError("MINIMAX_API_KEY is not set. Provide it via env or .env file.")
    response = requests.post(
        f"{api_base}/chat/completions",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={"model": model, "messages": messages, "temperature": temperature},
        timeout=120,
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"].strip()


def call_llm(prompt: str, temperature: float = 0.2) -> str:
    """BaseAgent.execute_llm_task() 経由で LLM を呼び出す。失敗時は MiniMax 直接 API にフォールバック。"""
    agent = _get_agent()
    if agent:
        try:
            return agent.execute_llm_task(prompt=prompt)
        except Exception as e:
            logger.warning("BaseAgent 呼び出し失敗、フォールバック: %s", e)
    return _fallback_minimax([{"role": "user", "content": prompt}], temperature)


def call_llm_messages(messages: list[dict], temperature: float = 0.2) -> str:
    """メッセージリスト形式の LLM 呼び出し（app_ui.py 等の _call_minimax 互換）。"""
    prompt = messages[-1]["content"] if messages else ""
    agent = _get_agent()
    if agent:
        try:
            return agent.execute_llm_task(prompt=prompt)
        except Exception as e:
            logger.warning("BaseAgent 呼び出し失敗、フォールバック: %s", e)
    return _fallback_minimax(messages, temperature)
