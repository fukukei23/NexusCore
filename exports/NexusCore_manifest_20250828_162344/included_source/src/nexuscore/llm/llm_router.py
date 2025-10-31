# ==============================================================================
# NexusCore LLM Router
# Folder: src/nexuscore/llm/
# File  : llm_router.py
# Ver   : 4.0 (2025-08-12) - Finalized version with robust .env loading
# ==============================================================================

from __future__ import annotations

import os
import sys
import re
import json
import time
import hashlib
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Tuple, Set
from datetime import datetime
from threading import Lock

# --- .env 自動読み込み（プロジェクトルート推定） -------------------------------
try:
    from dotenv import load_dotenv
    # llm_router.py -> llm -> nexuscore -> src -> (Project Root)
    _ROOT = Path(__file__).resolve().parents[3]
    _ENV_PATH = _ROOT / ".env"
    if _ENV_PATH.exists():
        load_dotenv(dotenv_path=str(_ENV_PATH), override=True)
except Exception:
    # 起動を妨げないよう、ライブラリが無い場合などはpassする
    pass

# ---- path 保険 ----------------------------------------------------------------
_CUR = os.path.dirname(os.path.abspath(__file__))
_SRC = os.path.dirname(os.path.dirname(_CUR))
if _SRC not in sys.path:
    sys.path.insert(0, str(_SRC))

# ---- SDK Imports --------------------------------------------------------------
try:
    from openai import OpenAI
    import openai
except Exception:
    OpenAI = None
try:
    import anthropic
except Exception:
    anthropic = None
try:

    import google.generativeai as genai
except Exception:
    genai = None
try:
    from nexuscore.config.secrets import Secrets
except Exception:
    Secrets = None


# ==============================================================================
# Utils
# ==============================================================================
_WS = re.compile(r"[ \t]+")
_NL = re.compile(r"\r\n|\r")

def canonicalize(text: str) -> str:
    if not text:
        return ""
    t = _NL.sub("\n", text.strip())
    t = _WS.sub(" ", t)
    return t

def read_shared_preamble() -> str:
    p = os.getenv("NEXUS_SHARED_PREAMBLE_FILE")
    if not p:
        return ""
    try:
        return Path(p).read_text(encoding="utf-8")
    except Exception:
        return ""


# ==============================================================================
# Usage and Cost Logging
# ==============================================================================
_USAGE_LOCK = Lock()
_USAGE_DIR = Path(os.getenv("NEXUS_USAGE_DIR", "./data/usage")).resolve()

def _write_usage(rec: dict):
    with _USAGE_LOCK:
        _USAGE_DIR.mkdir(parents=True, exist_ok=True)
        ym = datetime.utcnow().strftime("%Y%m")
        usage_file = _USAGE_DIR / f"usage_{ym}.jsonl"
        with usage_file.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

_MODEL_CONFIG_DEFAULT = {
    "no_temp_models": ["gpt-5", "gpt-5-mini", "gpt-4o-mini"],
    "models": {
        "openai:gpt-4o": {"in": 2.50, "out": 10.00},
        "openai:gpt-4o-mini": {"in": 0.15, "out": 0.60},
        "moonshot:kimi-k2-turbo-preview": {"in": 0.60, "out": 2.40},
        "moonshot:kimi-k2-0711-preview": {"in": 1.00, "out": 4.00},
        "deepseek:deepseek-reasoner": {"in": 0.55, "out": 2.19},
        "deepseek:deepseek-chat": {"in": 0.14, "out": 0.28},
    }
}
KIMI_TURBO_PROMO = os.getenv("KIMI_TURBO_PROMO50", "1") == "1"

def _get_config() -> dict:
    raw = (os.getenv("NEXUS_COST_TABLE_JSON") or "").strip()
    if not raw:
        return _MODEL_CONFIG_DEFAULT
    try:
        data = json.loads(raw) if not os.path.exists(raw) else json.loads(Path(raw).read_text("utf-8"))
        if "models" in data:
            return {"models": data.get("models", {}), "no_temp_models": data.get("no_temp_models", [])}
        return {"models": data, "no_temp_models": _MODEL_CONFIG_DEFAULT["no_temp_models"]}
    except Exception:
        return _MODEL_CONFIG_DEFAULT

_CACHED_CONFIG = _get_config()

def _price_lookup(provider: str, model: str) -> dict:
    key = f"{provider}:{model}"
    table = _CACHED_CONFIG.get("models", {})
    p = table.get(key)
    if provider == "moonshot" and model == "kimi-k2-turbo-preview" and p and KIMI_TURBO_PROMO:
        return {"in": p["in"] / 2.0, "out": p["out"] / 2.0}
    return p or {"in": 0.0, "out": 0.0}

def _estimate_cost_usd(provider: str, model: str, in_tokens: int | None, out_tokens: int | None) -> Tuple[float|None, float|None]:
    price = _price_lookup(provider, model)
    cost_in = (in_tokens / 1_000_000.0 * price["in"]) if in_tokens is not None else None
    cost_out = (out_tokens / 1_000_000.0 * price["out"]) if out_tokens is not None else None
    return cost_in, cost_out


# ==============================================================================
# Model Normalization
# ==============================================================================
MODEL_ALIAS: Dict[str, str] = {
    "claude-3.5-sonnet": "claude-3-5-sonnet-latest", "claude-3-opus": "claude-3-opus-20240229",
    "gpt4o": "gpt-4o", "kimi-latest": "kimi-k2-turbo-preview",
}
def normalize_model(name: str) -> str:
    return MODEL_ALIAS.get(name, name)

def model_family(model_name: str) -> str:
    m = (model_name or "").lower()
    if m.startswith(("gpt-", "openai-")): return "openai"
    if m.startswith("gemini-"): return "gemini"
    if m.startswith("claude"): return "anthropic"
    if m.startswith("deepseek"): return "deepseek"
    if m.startswith(("kimi", "moonshot")): return "moonshot"
    return "unknown"


# ==============================================================================
# API Key Finder
# ==============================================================================
def _find_api_key(prefix: str) -> str | None:
    if exact := os.getenv(prefix): return exact
    for k in sorted([k for k in os.environ if k.startswith(prefix)]):
        if v := os.getenv(k): return v
    if Secrets:
        try:
            for k in sorted([k for k in dir(Secrets) if k.startswith(prefix)]):
                if v := getattr(Secrets, k, None): return v if isinstance(v, str) else None
        except Exception: pass
    return None


# ==============================================================================
# Abstract Base LLM
# ==============================================================================
class BaseLLM(ABC):
    def __init__(self, model_name: str):
        self.model_name = model_name
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.info(f"LLM client initialized for model: {self.model_name}")

    @abstractmethod
    def execute(self, prompt: str, system_prompt: str, **kwargs) -> str:
        ...


# ==============================================================================
# OpenAI-Compatible Clients
# ==============================================================================
class OpenAICompat(BaseLLM):
    NO_TEMP_MODELS = set(_CACHED_CONFIG.get("no_temp_models", []))

    def __init__(self, model_name: str, api_key: str, base_url: str | None = None, **kwargs):
        super().__init__(model_name)
        if OpenAI is None: raise RuntimeError("openai package not found. pip install openai")
        self.client = OpenAI(api_key=api_key, base_url=base_url, **kwargs)

    def _chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        as_json = {"response_format": {"type": "json_object"}} if kwargs.pop("as_json", False) else {}
        temp = {"temperature": kwargs.pop("temperature")} if "temperature" in kwargs and not any(self.model_name.startswith(p) for p in self.NO_TEMP_MODELS) else {}
        prov = model_family(self.model_name) or "unknown"
        try:
            r = self.client.chat.completions.create(model=self.model_name, messages=messages, **as_json, **temp, **kwargs)
        except openai.InternalServerError as e:
            if prov == "deepseek" and self.model_name == "deepseek-reasoner":
                self.logger.warning("deepseek-reasoner failed with 500, falling back to deepseek-chat.")
                self.model_name = "deepseek-chat"
                r = self.client.chat.completions.create(model=self.model_name, messages=messages, **as_json, **temp, **kwargs)
            else: raise e
        
        usage = r.usage
        in_toks, out_toks = (usage.prompt_tokens if usage else None), (usage.completion_tokens if usage else None)
        cost_in, cost_out = _estimate_cost_usd(prov, self.model_name, in_toks, out_toks)
        _write_usage({
            "ts": int(time.time()), "provider": prov, "model": self.model_name,
            "input_tokens": in_toks, "output_tokens": out_toks,
            "cost_in_usd": cost_in, "cost_out_usd": cost_out,
            "total_usd": (cost_in or 0.0) + (cost_out or 0.0),
        })
        return r.choices[0].message.content or ""


class OpenAILLM(OpenAICompat):
    def __init__(self, model_name: str):
        api_key = _find_api_key("OPENAI_API_KEY")
        if not api_key: raise ValueError("OPENAI_API_KEY is not set.")
        kwargs = {}
        if api_key.startswith("sk-proj-"):
            if not (project := os.getenv("OPENAI_PROJECT")):
                raise ValueError("OPENAI_PROJECT is required for project-based keys.")
            kwargs["project"] = project
        if org := os.getenv("OPENAI_ORG"): kwargs["organization"] = org
        super().__init__(model_name, api_key=api_key, **kwargs)

    def execute(self, prompt: str, system_prompt: str, **kwargs) -> str:
        return self._chat([{"role": "system", "content": system_prompt}, {"role": "user", "content": prompt}], **kwargs)


class DeepSeekLLM(OpenAICompat):
    def __init__(self, model_name: str):
        api_key = _find_api_key("DEEPSEEK_API_KEY")
        if not api_key: raise ValueError("DEEPSEEK_API_KEY is not set.")
        super().__init__(model_name, api_key=api_key, base_url="https://api.deepseek.com")

    def execute(self, prompt: str, system_prompt: str, **kwargs) -> str:
        return self._chat([{"role": "system", "content": system_prompt}, {"role": "user", "content": prompt}], **kwargs)


class MoonshotLLM(OpenAICompat):
    def __init__(self, model_name: str):
        api_key = _find_api_key("KIMI_API_KEY") or _find_api_key("MOONSHOT_API_KEY")
        if not api_key: raise ValueError("KIMI_API_KEY or MOONSHOT_API_KEY is not set.")
        super().__init__(model_name, api_key=api_key, base_url="https://api.moonshot.ai/v1")

    def execute(self, prompt: str, system_prompt: str, **kwargs) -> str:
        sys_full = f"{LLMRouter.SHARED_PREAMBLE}\n\n{system_prompt}".strip()
        return self._chat([{"role": "system", "content": sys_full}, {"role": "user", "content": prompt}], **kwargs)


# ==============================================================================
# Other Major Clients
# ==============================================================================
class AnthropicLLM(BaseLLM):
    def __init__(self, model_name: str):
        super().__init__(model_name)
        if not anthropic: raise RuntimeError("anthropic package not found. pip install anthropic")
        api_key = _find_api_key("ANTHROPIC_API_KEY")
        if not api_key: raise ValueError("ANTHROPIC_API_KEY is not set.")
        self.client = anthropic.Anthropic(api_key=api_key)

    def execute(self, prompt: str, system_prompt: str, **kwargs) -> str:
        sys_full = f"{LLMRouter.SHARED_PREAMBLE}\n\n{system_prompt}".strip()
        r = self.client.messages.create(model=self.model_name, system=sys_full, messages=[{"role": "user", "content": prompt}], **kwargs)
        return r.content[0].text if r.content and r.content[0].type == "text" else ""


class GeminiLLM(BaseLLM):
    def __init__(self, model_name: str):
        super().__init__(model_name)
        if not genai: raise RuntimeError("google-generativeai package not found. pip install google-generativeai")
        api_key = _find_api_key("GEMINI_API_KEY")
        if not api_key: raise ValueError("GEMINI_API_KEY is not set.")
        genai.configure(api_key=api_key)
        self.client = genai.GenerativeModel(self.model_name)

    def execute(self, prompt: str, system_prompt: str, **kwargs) -> str:
        config = genai.types.GenerationConfig(
            temperature=kwargs.get("temperature", 0.3),
            response_mime_type="application/json" if kwargs.get("as_json") else "text/plain",
        )
        full_prompt = f"{system_prompt}\n\n---\n\n{prompt}"
        return self.client.generate_content(full_prompt, generation_config=config).text


class LocalLLM(BaseLLM):
    def execute(self, prompt: str, system_prompt: str, **kwargs) -> str:
        self.logger.warning(f"Local mock used for model='{self.model_name}'")
        return "{}" if kwargs.get("as_json") else f"[LOCAL MOCK FOR {self.model_name}]"


# ==============================================================================
# Default Task Assignment
# ==============================================================================
TASK_MODEL_MAP_DEFAULT = {
    "requirements": "gpt-5-mini", "planning": "gpt-5-mini", "coding": "gpt-5",
    "testing": "gpt-5-mini", "debugging": "gpt-5", "review": "gpt-4o-mini",
    "policy": "gpt-5-mini", "general": "gemini-1.5-flash-latest",
}
LEGACY_TO_TASK = {"creative": "coding", "analytical": "planning", "secure": "policy", "general": "general"}


# ==============================================================================
# LLM Router Core
# ==============================================================================
class LLMRouter:
    CLASSIFIER_MODEL = os.getenv("NEXUS_CLASSIFIER_MODEL", "gemini-1.5-flash-latest")
    SHARED_PREAMBLE = canonicalize(read_shared_preamble())
    LONG_THRESHOLD = int(os.getenv("NEXUS_LONG_PROMPT_THRESHOLD", "6000"))
    VALID_CLASSIFIERS = (OpenAILLM, GeminiLLM, AnthropicLLM, MoonshotLLM, DeepSeekLLM)

    def __init__(self):
        logging.basicConfig(level=os.getenv("NEXUS_LOG_LEVEL", "INFO").upper(), format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.info(f"ENV sanity: " + ", ".join([f"{k}={'set' if os.getenv(k) else 'unset'}" for k in ["OPENAI_API_KEY", "DEEPSEEK_API_KEY", "KIMI_API_KEY", "GEMINI_API_KEY"]]))

        self.default_model = os.getenv("NEXUS_DEFAULT_MODEL", "gemini-1.5-flash-latest")
        self.task_model_map = {t: normalize_model(os.getenv(f"NEXUS_TASK_MODEL_{t.upper()}", m)) for t, m in TASK_MODEL_MAP_DEFAULT.items()}
        self.logger.info(f"TASK MODEL MAP = {self.task_model_map}")
        self._classifier = self._make_client(self.CLASSIFIER_MODEL)

    def get_llm_for_task(self, prompt: str) -> BaseLLM:
        task_type = self._classify_task_type(prompt)
        model_name = self.task_model_map.get(task_type, self.default_model)
        if model_family(model_name) == "moonshot":
            model_name = self._select_kimi(prompt)
        self.logger.info(f"Selecting model '{model_name}' for task '{task_type}'")
        return self._make_client(model_name)

    def _classify_task_type(self, prompt: str) -> str:
        if not isinstance(self._classifier, self.VALID_CLASSIFIERS):
            self.logger.warning(f"Classifier client is not a valid remote LLM ({type(self._classifier).__name__}). Falling back to 'general'.")
            return "general"
        allowed = ",".join(TASK_MODEL_MAP_DEFAULT.keys())
        system = f"You are a task classifier. Return ONLY JSON: {{\"task_type\":\"<one of [{allowed}]>\"}}."
        try:
            raw = self._classifier.execute(f"Classify this prompt:\n{prompt}", system_prompt=system, as_json=True, temperature=0.0)
            data = json.loads(raw)
            task = str(data.get("task_type", "general")).strip().lower()
            task = LEGACY_TO_TASK.get(task, task)
            if task not in self.task_model_map: task = "general"
        except Exception as e:
            self.logger.error(f"Task classification failed: {e}. Falling back to 'general'.")
            task = "general"
        self.logger.info(f"Task classified as '{task}'.")
        return task

    def _select_kimi(self, prompt: str) -> str:
        chosen = "kimi-k2-0711-preview" if len(prompt) >= self.LONG_THRESHOLD else "kimi-k2-turbo-preview"
        self.logger.info(f"Kimi auto-switch: prompt_len={len(prompt)} -> {chosen}")
        return chosen

    def _make_client(self, model_name: str) -> BaseLLM:
        model_name = normalize_model(model_name)
        fam = model_family(model_name)
        try:
            if fam == "openai": return OpenAILLM(model_name)
            if fam == "gemini": return GeminiLLM(model_name)
            if fam == "anthropic": return AnthropicLLM(model_name)
            if fam == "deepseek": return DeepSeekLLM(model_name)
            if fam == "moonshot": return MoonshotLLM(model_name)
            self.logger.warning(f"Unknown model '{model_name}'. Falling back to default '{self.default_model}'.")
            return self._make_client(self.default_model) if model_name != self.default_model else LocalLLM(model_name)
        except ValueError as ve:
            self.logger.error(f"Config error for '{model_name}': {ve}")
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error creating client for '{model_name}': {e}", exc_info=True)
            return LocalLLM(model_name)

# ==============================================================================
# Smoke Test (for direct execution)
# ==============================================================================
if __name__ == "__main__":
    logging.basicConfig(level="INFO", format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
    print("--- LLMRouter Smoke Test ---")
    try:
        router = LLMRouter()
        print("\nTASK MAP:", json.dumps(router.task_model_map, indent=2))
        sample_prompt = "pytestの失敗ログを分析し、原因を特定して修正案を提示してください。"
        print(f"\nSample Prompt: \"{sample_prompt[:50]}...\"")
        llm_client = router.get_llm_for_task(sample_prompt)
        print(f"\n--> Selected Client: {type(llm_client).__name__}, Model: {llm_client.model_name}")
        if not isinstance(llm_client, LocalLLM):
            print("--> Client generation successful (API call will not be made).")
    except ValueError as e:
        print(f"\n--> Client generation failed as expected due to missing API key: {e}")
    except Exception as e:
        print(f"\n--> An unexpected error occurred during smoke test: {e}")
    print("\n--- Smoke Test Finished ---")