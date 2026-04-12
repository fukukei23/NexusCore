# ==============================================================================
# フォルダ: src/agents
# ファイル名: base_agent.py
# メモ: すべてのエージェントが自身のクラス名を冠した専用ロガーを持つように
#      アーキテクチャをアップグレード。
#      NexusCore uses GLM (Zhipu AI) and MiniMax as the sole LLM providers.
# ==============================================================================
import json
import logging
import os

import requests


class BaseAgent:
    def __init__(self, api_key: str, model: str):
        # 自分自身のクラス名をロガー名として、専用のロガーインスタンスを取得
        self.logger = logging.getLogger(self.__class__.__name__)

        self.model = model
        self.api_key = api_key
        self.provider = None
        self.base_url = None

        if "glm" in model.lower() or "chatglm" in model.lower():
            self.provider = "glm"
            self.base_url = os.getenv("GLM_API_BASE", "https://open.bigmodel.cn/api/paas/v4").rstrip("/")
            self.logger.info(f"GLM client initialized for model: {self.model}")

        elif "minimax" in model.lower():
            self.provider = "minimax"
            self.base_url = os.getenv("MINIMAX_API_BASE", "https://api.minimax.chat/v1").rstrip("/")
            self.logger.info(f"MiniMax client initialized for model: {self.model}")

        elif "dummy" in model.lower():
            self.provider = "dummy"
            self.logger.info("BaseAgent initialized in DUMMY mode for testing. No API client will be used.")

        else:
            raise ValueError(f"Unsupported or unknown model specified: {self.model}. Must contain 'glm', 'minimax', or 'dummy'.")

    def _call_llm(self, prompt: str, system_prompt: str, temperature: float = 0.1, as_json: bool = False) -> str:
        """
        プロバイダーに応じて適切なLLM呼び出しメソッドを振り分ける。
        """
        self.logger.debug(f"Calling LLM. Provider: {self.provider}, JSON mode: {as_json}")
        if self.provider in ("glm", "minimax"):
            return self._call_openai_compatible(prompt, system_prompt, temperature, as_json)
        elif self.provider == "dummy":
            self.logger.warning("LLM call attempted in DUMMY mode. Returning empty string.")
            return json.dumps({"response": "dummy response"}) if as_json else "dummy response"
        else:
            self.logger.error(f"LLM provider '{self.provider}' is not implemented.")
            raise NotImplementedError(f"LLM provider '{self.provider}' is not implemented.")

    def _call_openai_compatible(self, prompt: str, system_prompt: str, temperature: float, as_json: bool) -> str:
        """GLM/MiniMax共通のOpenAI互換API呼び出し"""
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ]
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
        }
        if as_json:
            payload["response_format"] = {"type": "json_object"}

        resp = requests.post(url, headers=headers, json=payload, timeout=120)
        resp.raise_for_status()

        data = resp.json()
        text = ""
        for ch in data.get("choices") or []:
            msg = ch.get("message") or {}
            if msg.get("content"):
                text += str(msg["content"])
        return text.strip()
