# ==============================================================================
# フォルダ: src/agents
# ファイル名: base_agent.py
# メモ: すべてのエージェントが自身のクラス名を冠した専用ロガーを持つように
#      アーキテクチャをアップグレード。
# ==============================================================================
import json
import logging # ロギングをインポート
from openai import OpenAI
import google.generativeai as genai

class BaseAgent:
    def __init__(self, api_key: str, model: str):
        # --- ★★★★★ ここからが最重要修正点 ★★★★★ ---
        # 自分自身のクラス名をロガー名として、専用のロガーインスタンスを取得
        self.logger = logging.getLogger(self.__class__.__name__)
        # --- ★★★★★ ここまで ★★★★★ ---

        self.model = model
        self.client = None
        self.provider = None

        if "gpt" in model.lower():
            if not api_key or api_key == "dummy_key":
                raise ValueError("GPTモデルを使用するには、有効なOpenAI APIキーが必要です。")
            self.client = OpenAI(api_key=api_key)
            self.provider = "openai"
            self.logger.info(f"OpenAI client initialized for model: {self.model}")

        elif "gemini" in model.lower():
            if not api_key or api_key == "dummy_key":
                raise ValueError("Geminiモデルを使用するには、有効なGoogle APIキーが必要です。")
            genai.configure(api_key=api_key)
            self.client = genai.GenerativeModel(model)
            self.provider = "google"
            self.logger.info(f"Google Gemini client initialized for model: {self.model}")

        elif "dummy" in model.lower():
            self.provider = "dummy"
            self.logger.info("BaseAgent initialized in DUMMY mode for testing. No API client will be used.")
        
        else:
            raise ValueError(f"Unsupported or unknown model specified: {self.model}. Must contain 'gpt', 'gemini', or 'dummy'.")

    def _call_llm(self, prompt: str, system_prompt: str, temperature: float = 0.1, as_json: bool = False) -> str:
        """
        プロバイダーに応じて適切なLLM呼び出しメソッドを振り分ける。
        """
        self.logger.debug(f"Calling LLM. Provider: {self.provider}, JSON mode: {as_json}")
        if self.provider == "openai":
            return self._call_openai(prompt, system_prompt, temperature, as_json)
        elif self.provider == "google":
            return self._call_gemini(prompt, system_prompt, temperature, as_json)
        elif self.provider == "dummy":
            self.logger.warning("LLM call attempted in DUMMY mode. Returning empty string.")
            return json.dumps({"response": "dummy response"}) if as_json else "dummy response"
        else:
            self.logger.error(f"LLM provider '{self.provider}' is not implemented.")
            raise NotImplementedError(f"LLM provider '{self.provider}' is not implemented.")

    def _call_openai(self, prompt: str, system_prompt: str, temperature: float, as_json: bool) -> str:
        # (実装は変更なし)
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]
        response_format = {"type": "json_object"} if as_json else {"type": "text"}
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            response_format=response_format
        )
        return response.choices[0].message.content.strip()

    def _call_gemini(self, prompt: str, system_prompt: str, temperature: float, as_json: bool) -> str:
        # (実装は変更なし)
        generation_config = genai.types.GenerationConfig(
            temperature=temperature,
            response_mime_type="application/json" if as_json else "text/plain"
        )
        full_prompt = f"{system_prompt}\\n\\n---\\n\\n{prompt}"
        
        response = self.client.generate_content(
            full_prompt,
            generation_config=generation_config
        )
        return response.text.strip()
