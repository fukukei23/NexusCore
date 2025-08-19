# ==============================================================================
# フォルダ: src/nexuscore/llm/
# ファイル名: llm_router.py
# メモ: 【APIキー検索機能強化版】
#      - secrets.pyから 'GEMINI_API_KEY' という固定名でキーを探すのではなく、
#        'GEMINI_API_KEY' で始まる最初のキーを自動で検索して利用するように修正。
#      - これにより、複数のエージェント用キーが存在する環境でも柔軟に動作する。
# ==============================================================================
import logging
import sys
import os
from abc import ABC, abstractmethod

# --- パス設定と安全なインポート ---
current_dir = os.path.dirname(os.path.abspath(__file__))
src_path = os.path.dirname(os.path.dirname(current_dir))
if src_path not in sys.path:
    sys.path.insert(0, src_path)

try:
    from nexuscore.config.secrets import Secrets
    import google.generativeai as genai
    from openai import OpenAI
except ImportError as e:
    print(f"エラー: 必要なモジュールをインポートできませんでした: {e}")
    sys.exit(1)

# --- ★★★★★ ここからが最重要修正点 (1/2) ★★★★★ ---
def find_api_key(prefix: str) -> str | None:
    """
    Secretsクラス内をスキャンし、指定されたプレフィックスで始まる最初のAPIキーを見つける。
    """
    for key, value in vars(Secrets).items():
        if key.startswith(prefix) and not key.startswith('__'):
            logging.info(f"APIキー '{key}' を使用します。")
            return value
    return None
# --- ★★★★★ ここまで ★★★★★ ---

class BaseLLM(ABC):
    def __init__(self, model_name: str):
        self.model_name = model_name
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.info(f"LLM client initialized for model: {self.model_name}")

    @abstractmethod
    def execute(self, prompt: str, system_prompt: str, **kwargs) -> str:
        pass

class GeminiLLM(BaseLLM):
    def __init__(self, model_name: str):
        super().__init__(model_name)
        # --- ★★★★★ ここからが最重要修正点 (2/2) ★★★★★ ---
        api_key = find_api_key('GEMINI_API_KEY') # 固定名ではなく、検索関数を呼び出す
        # --- ★★★★★ ここまで ★★★★★ ---
        if not api_key: raise ValueError("Gemini APIキーがsecrets.pyにありません。")
        try:
            genai.configure(api_key=api_key)
            self.client = genai.GenerativeModel(self.model_name)
        except Exception as e:
            self.logger.error(f"Geminiクライアントの初期化に失敗しました: {e}")
            raise

    def execute(self, prompt: str, system_prompt: str, **kwargs) -> str:
        as_json = kwargs.get("as_json", False)
        temperature = kwargs.get("temperature", 0.5)
        generation_config = genai.types.GenerationConfig(
            temperature=temperature,
            response_mime_type="application/json" if as_json else "text/plain"
        )
        full_prompt = f"{system_prompt}\n\n---\n\n{prompt}"
        response = self.client.generate_content(full_prompt, generation_config=generation_config)
        return response.text.strip()

class OpenAILLM(BaseLLM):
    def __init__(self, model_name: str):
        super().__init__(model_name)
        api_key = find_api_key('OPENAI_API_KEY') # こちらも同様に修正
        if not api_key: raise ValueError("OpenAI APIキーがsecrets.pyにありません。")
        self.client = OpenAI(api_key=api_key)

    def execute(self, prompt: str, system_prompt: str, **kwargs) -> str:
        as_json = kwargs.get("as_json", False)
        temperature = kwargs.get("temperature", 0.5)
        messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": prompt}]
        response_format = {"type": "json_object"} if as_json else {"type": "text"}
        response = self.client.chat.completions.create(
            model=self.model_name, messages=messages, temperature=temperature, response_format=response_format
        )
        return response.choices[0].message.content.strip()

class LocalLLM(BaseLLM):
    def __init__(self, model_name: str):
        super().__init__(model_name)
        self.logger.info(f"Local LLM would be loaded for model: {self.model_name}")

    def execute(self, prompt: str, system_prompt: str, **kwargs) -> str:
        self.logger.info("Executing task on Local LLM.")
        return f"Mock response from local model for: {prompt[:50]}..."

class LLMRouter:
    ROUTER_MODEL_NAME = "gemini-1.5-flash-latest" 
    ROUTING_SYSTEM_PROMPT = """
    あなたは、様々なAIモデルの特性を熟知した、AIタスクのディスパッチャーです。
    ユーザーからのタスク説明を分析し、そのタスクに最も適したLLMの「タイプ」を、
    以下の選択肢から一つだけ選んでください。
    - creative: 新しいアイデア、文章、コードの生成など、創造性が求められるタスク。
    - analytical: コードの分析、デバッグ、レビュー、要約など、論理的分析能力が求められるタスク。
    - secure: 顧客の機密情報や、セキュリティが重視されるコードを扱うタスク。
    - general: 上記のいずれにも分類されない、一般的なタスク。
    """

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        try:
            self.router_llm = GeminiLLM(model_name=self.ROUTER_MODEL_NAME)
            self.logger.info(f"LLM Router initialized with model: {self.ROUTER_MODEL_NAME}")
        except Exception as e:
            self.logger.critical(f"ルーターLLMの初期化に失敗しました。ルーターは機能しません。: {e}")
            self.router_llm = None

    def _classify_task(self, task_description: str) -> str:
        if not self.router_llm:
            self.logger.warning("ルーターLLMが利用できないため、'general'にフォールバックします。")
            return "general"
        
        try:
            response = self.router_llm.execute(task_description, self.ROUTING_SYSTEM_PROMPT, temperature=0.0)
            task_type = response.strip().lower()
            if task_type not in ["creative", "analytical", "secure", "general"]:
                self.logger.warning(f"未知のタスクタイプ '{task_type}' が返されました。'general'にフォールバックします。")
                return "general"
            return task_type
        except Exception as e:
            self.logger.error(f"タスク分類中にエラーが発生しました: {e}")
            return "general"

    def get_llm_for_task(self, task_description: str) -> BaseLLM:
        task_type = self._classify_task(task_description)
        self.logger.info(f"タスク '{task_description[:30]}...' は '{task_type}' タイプに分類されました。")

        if task_type == "creative":
            self.logger.info("Selecting high-performance model (gpt-4o) for creative task.")
            return OpenAILLM(model_name="gpt-4o")
        elif task_type == "analytical":
            self.logger.info("Selecting balanced model (gemini-1.5-pro-latest) for analytical task.")
            return GeminiLLM(model_name="gemini-1.5-pro-latest")
        elif task_type == "secure":
            self.logger.info("Selecting secure model (local-llm) for secure task.")
            return LocalLLM(model_name="llama3-local-8b")
        else: # general
            self.logger.info("Selecting cost-effective model (gemini-1.5-flash-latest) for general task.")
            return GeminiLLM(model_name="gemini-1.5-flash-latest")
