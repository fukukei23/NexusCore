# =============================================================================
# FILE:        src/nexuscore/llm/llm_router.py
# REGISTRY:    nexuscore.llm.llm_router.LLMRouter
# DATE:        2025年11月7日
# 日本時間:    00:30
# VERSION:     2.3.5-robust (v2.3.4 + robustness patch)
#
# 概要:
# - v2.3.4 の全機能（Gemini堅牢化, NPEv1/v2アダプタ, 実コール,
#   実トークン計測, JSONガード, Azure互換, ログ互換性）を完全に維持。
# - v2.3.4 に残存していた「BASE URLのMarkdown誤植」バグを修正。
# - 任意提案（仕上げの軽微提案）をすべて統合。
#   1. (堅牢化) 429/5xx系エラー時に3回/指数バックオフで
#      自動リトライする requests.Session を導入。
#   2. (堅牢化) requests のタイムアウトを
#      NEXUS_REQUEST_TIMEOUT_SEC (既定120秒) で環境変数化。
#   3. (可視化) llm_calls.jsonl に "provider" フィールドを追加。
# =============================================================================

from __future__ import annotations
# ---- .env ロード (v2.2.5) ---------------------------------------------------
from pathlib import Path
import os, logging
try:
    from dotenv import load_dotenv, find_dotenv
    _here = Path(__file__).resolve()
    # ① 明示指定（最優先）
    _env_from_env = os.getenv("NEXUSCORE_ENV_FILE")
    _candidates = []
    if _env_from_env:
        _candidates.append(Path(_env_from_env))
    # ② 既知パス候補
    _candidates += [
        _here.parents[3] / ".env",  # <repo-root>/.env
        _here.parents[2] / ".env",  # src/.env
        _here.parents[1] / ".env",  # src/nexuscore/.env
    ]
    _loaded = None
    for _p in _candidates:
        try:
            if _p and Path(_p).is_file():
                load_dotenv(dotenv_path=_p, override=False)
                os.environ["NEXUSCORE_ENV_LOADED"] = str(Path(_p).resolve())
                _loaded = _p
                break
        except Exception:
            pass
    # ③ 自動探索（最後の砦）
    if not _loaded:
        _auto = find_dotenv(usecwd=True)
        if _auto:
            load_dotenv(_auto, override=False)
            os.environ["NEXUSCORE_ENV_LOADED"] = _auto
except ImportError:
    logging.getLogger("LLMRouter").warning(
        "[ENV] python-dotenv 未導入のため .env 自動ロードは無効です"
    )
# ---- .env ロード (ここまで) -----------------------------------------------

# import os (↑でインポート済み)
import time
# import logging (↑でインポート済み)
# from pathlib import Path (↑でインポート済み)
from typing import Dict, Optional, Tuple

# ---- ★ v2.3.5 堅牢化パッチ (requests + Retry) ------------------------------
try:
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
    REQUESTS_AVAILABLE = True

    def create_retry_session() -> requests.Session:
        """
        429/5xx系エラー時に指数バックオフで3回リトライするセッションを作成
        """
        session = requests.Session()
        retry_strategy = Retry(
            total=3,  # 合計3回リトライ
            backoff_factor=1,  # 1s, 2s, 4s... のように待機
            status_forcelist=[429, 500, 502, 503, 504], # リトライ対象ステータス
            allowed_methods=frozenset({"POST"}) # POSTもリトライ対象に
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        return session

except ImportError:
    REQUESTS_AVAILABLE = False
    requests = None # type: ignore
    HTTPAdapter = None # type: ignore
    Retry = None # type: ignore
    logging.getLogger("LLMRouter").warning(
        "[Init] 'requests' or 'urllib3' library not found. OpenAI/DeepSeek/Kimi will run in STUB mode."
    )
    def create_retry_session(): # スタブ
        return None
# -----------------------------------------------------------------------------

if REQUESTS_AVAILABLE:
    RequestsHTTPError = requests.exceptions.HTTPError
else:
    class RequestsHTTPError(Exception):
        """requests が無い環境向けのダミーHTTPエラー"""
        pass

# ---- Budget / Logger import (v1/v2 後方互換) ------------------------------
# (v2.2.1 既存)
import json
# import logging (↑でインポート済み)
# from pathlib import Path # (↑でインポート済み)
try:
    # v1系: クラス BudgetManager（check_budget / track_cost）
    from nexuscore.npe.budget import BudgetManager as _BudgetManagerV1  # type: ignore
    BUDGET_API = "v1"
    class BudgetManager(_BudgetManagerV1):
        pass
except Exception:
    # v1が無い → v2（関数API）を探す
    try:
        from nexuscore.npe import budget as _budget_v2  # type: ignore
        BUDGET_API = "v2"
        class BudgetManager:  # v1互換の薄ラッパ
            def __init__(self, daily_limit_usd: float | None = None, log_dir=None):
                self._b = _budget_v2
            def check_budget(self, model_name: str, est_input_tokens: int) -> tuple[bool, float]:
                try:
                    # (v1 IF -> v2 IF 変換)
                    return self._b.preflight_check(model_name=model_name, est_input_tokens=est_input_tokens)
                except Exception:
                    return True, 0.0
            def track_cost(self, model_name: str, input_tokens: int, output_tokens: int) -> float:
                try:
                    # (v1 IF -> v2 IF 変換)
                    return self._b.record_usage(model_name=model_name, input_tokens=input_tokens, output_tokens=output_tokens)
                except Exception:
                    return 0.0
    except Exception:
        # どちらも無い → No-Op で警告
        BUDGET_API = "none"
        class BudgetManager:
            def __init__(self, daily_limit_usd: float | None = None, log_dir=None):
                logging.getLogger("LLMRouter").warning(
                    "[Budget] No BudgetManager found (v1/v2). Running with NO budget guard!"
                )
            def check_budget(self, model_name: str, est_input_tokens: int) -> tuple[bool, float]:
                return True, 0.0
            def track_cost(self, model_name: str, input_tokens: int, output_tokens: int) -> float:
                return 0.0
# ロガー: v1/v2 で両対応
try:
    from nexuscore.npe.logger import log_transaction  # v1
except Exception:
    try:
        from nexuscore.npe import logger as _logger_v2  # v2
        log_transaction = _logger_v2.log_transaction
    except Exception:
        def log_transaction(payload: dict, log_file: str):
            try:
                # (v2.2.1 既存のフォールバック)
                Path(log_file).parent.mkdir(parents=True, exist_ok=True)
                with open(log_file, "a", encoding="utf-8") as f:
                    f.write(json.dumps(payload, ensure_ascii=False) + "\n")
            except Exception:
                pass  # ログ失敗は致命にしない
# ---- (アダプタ・ブロックここまで) ----------------------------------------


# -----------------------------------------------------------------------------
# モデル割り当てポリシー（最新版）
# -----------------------------------------------------------------------------
TASK_MODEL_MAP_DEFAULT: Dict[str, str] = {
    "requirements": "gemini-2.5-flash",
    "planning":     "gemini-2.5-flash",
    "coding":       "gpt-5",
    "testing":      "gpt-5-mini",
    "debugging":    "gpt-5",
    "review":       "gemini-2.5-pro",
    "policy":       "gemini-2.5-pro",
    "general":      "gemini-2.5-flash",
}

# 旧名称→新タスク種別のマッピング(後方互換)
LEGACY_TO_TASK = {
    "qa": "testing",
    "test": "testing",
    "tdd": "testing",
    "unit_test": "testing",
    "analysis": "debugging",
    "debug": "debugging",
    "fix": "debugging",
    "review_code": "review",
    "compliance": "policy",
    "governance": "policy",
    "plan": "planning",
    "spec": "requirements",
}


# -----------------------------------------------------------------------------
# モデルファミリー判定＆標準化
# -----------------------------------------------------------------------------
def normalize_model(name: str) -> str:
    # 例: 大文字/サフィックスのゆらぎを吸収
    if not name:
        return "local-mock"
    name = name.strip()
    # よくあるゆらぎ: -latest / :latest / -turbo など
    replacements = {
        "gemini-2.5-flash-latest": "gemini-2.5-flash",
        "gemini-2.5-pro-latest": "gemini-2.5-pro",
        "kimi-k2-0711-preview": "kimi-k2-0711-preview",
        "kimi-k2-turbo-preview": "kimi-k2-turbo-preview",
    }
    return replacements.get(name, name)


def model_family(name: str) -> str:
    """
    どのベンダー系かをざっくり返す。
    Routerがクライアントを生成する時に使う。
    """
    n = name.lower()
    if n.startswith("gpt-") or n.startswith("o") or n.startswith("openai-"):
        return "openai"
    if n.startswith("gemini"):
        return "gemini"
    if n.startswith("deepseek"):
        return "deepseek"
    if n.startswith("kimi"):
        return "kimi"
    return "local"

# -----------------------------------------------------------------------------
# ★ パッチ 2) JSON 整形ガード (v2.3.3)
# -----------------------------------------------------------------------------
def _strip_jsonish(text: str) -> str:
    """
    OpenAI互換モデルが返しがちな余分なマークダウンや前置きを除去する
    """
    if not text: return text
    t = text.strip()
    # ```json ... ``` や ``` ... ``` を除去
    if t.startswith("```"):
        t = t.strip("`")
        # 先頭にjsonという言葉が紛れても丸める
        if t.lower().startswith("json"):
            t = t[4:].strip() # "json" (4文字) を除去
    # 先頭の余計な前置き（e.g., “Here is JSON:”）をごく軽く除去
    if "{" in t:
        t = t[t.index("{"):]
    # 末尾の余計なゴミを除去
    if "}" in t:
        t = t[:t.rindex("}")+1]
    return t

# -----------------------------------------------------------------------------
# 各LLMクライアント定義（v2.3.5: Bugfix + Retry 適用）
# -----------------------------------------------------------------------------
class BaseLLM:
    def __init__(self, model_name: str):
        self.model_name = normalize_model(model_name)
        self.logger = logging.getLogger(self.__class__.__name__)
        # ★ パッチ 1) トークン実測値格納用 (v2.3.3)
        self._last_usage: Optional[Dict[str, int]] = None
        # ★ v2.3.5: 直近の呼び出しモードを記録 (real / stub / stub-fallback)
        self.last_call_mode: str = "stub"
        # ★ v2.3.5 リトライ用セッション (requests系のみ)
        self.session: Optional[requests.Session] = None

    def execute(self, prompt: str, system_prompt: str, **kwargs) -> str:
        raise NotImplementedError("Subclasses must implement execute()")


class OpenAILLM(BaseLLM):
    """
    gpt-5 / gpt-5-mini 等のOpenAI系モデル想定
    (v2.3.5: BASE URL 誤植修正 + Retry)
    """
    def __init__(self, model_name: str):
        super().__init__(model_name)
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY is not set.")

        # ★ パッチ 3) Azure 互換スイッチ (v2.3.3)
        # ★ Bugfix (v2.3.5) BASE URL 誤植修正（Markdown表記を素のURLに）
        self.base_url = (os.getenv("OPENAI_BASE_URL") or "https://api.openai.com").rstrip("/")
        self.azure = os.getenv("OPENAI_AZURE", "0") == "1"
        self.azure_deployment = os.getenv("OPENAI_AZURE_DEPLOYMENT")  # 例: gpt-5
        self.azure_api_version = os.getenv("OPENAI_AZURE_API_VERSION", "2024-08-01-preview")

        # 実コール or スタブを環境変数で切替 (v2.3.3)
        self.real_calls = (os.getenv("NEXUS_REAL_CALLS", "0") == "1") and REQUESTS_AVAILABLE
        if self.real_calls:
            # ★ v2.3.5 リトライセッション作成
            self.session = create_retry_session()
            self.logger.info("OpenAILLM initialized in REAL-CALL mode (Azure: %s, Retry: On).", self.azure)
        else:
            self.logger.info("OpenAILLM initialized in STUB mode.")

    def execute(self, prompt: str, system_prompt: str, **kwargs) -> str:
        temperature = kwargs.get("temperature", 0.2)
        as_json = kwargs.get("as_json", False)

        if self.real_calls and self.session:
            # --- 実APIコール (v2.3.5) ---
            try:
                # ★ パッチ 3) Azure URL分岐
                if self.azure:
                    if not self.azure_deployment:
                        raise ValueError("OPENAI_AZURE=1 requires OPENAI_AZURE_DEPLOYMENT to be set.")
                    url = f"{self.base_url}/openai/deployments/{self.azure_deployment}/chat/completions?api-version={self.azure_api_version}"
                    headers = {"api-key": self.api_key, "Content-Type": "application/json"}
                else:
                    url = f"{self.base_url}/v1/chat/completions"
                    headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt},
                ]
                # gpt-5 / o* 系は temperature=1 固定 & max_completion_tokens を使用する
                is_gpt5_or_o = self.model_name.startswith("gpt-5") or self.model_name.startswith("o")

                payload = {
                    "model": self.model_name,
                    "messages": messages,
                }

                # gpt-5 / o* 以外のモデルには従来通り temperature を送る
                if not is_gpt5_or_o:
                    try:
                        payload["temperature"] = float(temperature)
                    except (TypeError, ValueError):
                        # temperature が変な値でも無視してデフォルトに任せる
                        pass

                max_out = os.getenv("NEXUS_DEFAULT_MAX_OUT_TOKENS")
                if max_out:
                    try:
                        max_val = int(max_out)
                    except ValueError:
                        max_val = None

                    if max_val is not None:
                        # gpt-5 / o* 系は「推論トークン＋表出テキスト」を内部で
                        # いい感じに配分する前提のモデルなので、
                        # ここで一律に max_* で絞ると
                        # finish_reason=length & text="" になりがち。
                        #
                        # そのため、デフォルトでは gpt-5 / o* では
                        # 明示的な上限は送らず、既定値に任せる。
                        if not (
                            self.model_name.startswith("gpt-5")
                            or self.model_name.startswith("o")
                        ):
                            # 旧世代モデルなどについては従来どおり
                            # max_tokens を明示指定する。
                            payload["max_tokens"] = max_val
                        # ※ gpt-5 / o* にも明示的な上限を付けたい場合は、
                        #    上の if を外して、用途に合わせて
                        #    payload["max_completion_tokens"] = max_val
                        #    にするなどして調整する想定。

                if as_json:
                    payload["response_format"] = {"type": "json_object"}

                # ★ v2.3.5 Timeout 環境変数 + self.session.post
                timeout = float(os.getenv("NEXUS_REQUEST_TIMEOUT_SEC", "120"))
                resp = self.session.post(url, headers=headers, json=payload, timeout=timeout)
                resp.raise_for_status() # 4xx/5xx は (リトライ後も) 例外

                data = resp.json()
                text = ""
                for ch in (data.get("choices") or []):
                    msg = (ch.get("message") or {})
                    if msg.get("content"):
                        text += str(msg["content"])

                # ★ パッチ 1) 実使用トークン (v2.3.3)
                usage = data.get("usage") or {}
                self._last_usage = {
                    "prompt_tokens": usage.get("prompt_tokens"),
                    "completion_tokens": usage.get("completion_tokens"),
                }

                if not text:
                    raise RuntimeError(f"OpenAI returned no text (FinishReason: {data.get('choices', [{}])[0].get('finish_reason')}).")
                
                # ★ パッチ 2) JSON 整形 (v2.3.3)
                self.last_call_mode = "real"
                return _strip_jsonish(text) if as_json else text

            except RequestsHTTPError as e:
                body = ""
                try:
                    if getattr(e, "response", None) is not None:
                        body = e.response.text
                except Exception:
                    pass
                self.logger.error(
                    "OpenAILLM REAL-CALL HTTP error (after retries): %s\nResponse body: %s",
                    e,
                    body[:2000],
                )
                self.last_call_mode = "stub-fallback"
                fake = {
                    "model": self.model_name,
                    "mode": "openai-stub-fallback",
                    "preview": "Real call failed. Fallback to stub."
                }
                return json.dumps(fake, ensure_ascii=False) if as_json else fake["preview"]
            except Exception as e:
                self.logger.error(f"OpenAILLM REAL-CALL failed (after retries): {e}")
                self.last_call_mode = "stub-fallback"
                # フォールバックスタブ
                fake = {
                    "model": self.model_name,
                    "mode": "openai-stub-fallback",
                    "preview": "Real call failed. Fallback to stub."
                }
                return json.dumps(fake, ensure_ascii=False) if as_json else fake["preview"]

        # スタブ応答
        self.last_call_mode = "stub"
        fake = {
            "model": self.model_name,
            "mode": "openai-stub",
            "as_json": as_json,
            "preview": "This is a stubbed OpenAI model response."
        }
        return json.dumps(fake, ensure_ascii=False) if as_json else fake["preview"]


class GeminiLLM(BaseLLM):
    """
    gemini-2.5-flash / gemini-2.5-pro 等のGoogle/Geminiモデル想定
    (v2.3.4: Hotfix 3 適用済)
    (注: SDKが独自のリトライ処理を持つため、v2.3.5のrequests.Retryは対象外)
    """
    def __init__(self, model_name: str):
        super().__init__(model_name)
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY is not set.")
        # 実コール or スタブを環境変数で切替 (v2.3.2)
        self.real_calls = os.getenv("NEXUS_REAL_CALLS", "0") == "1"
        if self.real_calls:
            # ライブラリが無くてもスタブモードなら動くよう、ここでimport
            try:
                import google.generativeai as genai
                genai.configure(api_key=api_key)
                self.client = "ok" # 初期化OKのフラグとして利用
                self.logger.info("GeminiLLM initialized in REAL-CALL mode.")
            except ImportError:
                self.logger.error("GeminiLLM REAL-CALL mode failed: 'google-generativeai' not installed.")
                self.client = None
                self.real_calls = False # 強制的にスタブモードに戻す
        else:
            self.client = None  # スタブ
            self.logger.info("GeminiLLM initialized in STUB mode.")


    # --- ★★★★★ v2.3.2 堅牢化 execute() (ここから) ★★★★★ ---
    # (v2.3.4: Hotfix 3 適用済)
    def execute(self, prompt: str, system_prompt: str, **kwargs) -> str:
        temperature = kwargs.get("temperature", 0.3)
        as_json = kwargs.get("as_json", False)

        if self.real_calls and self.client:
            # 実APIコール
            try:
                import google.generativeai as genai
                model = genai.GenerativeModel(
                    self.model_name,
                    system_instruction=system_prompt
                )
            except Exception as e:
                self.logger.error(f"Gemini init failed (system): {e}")
                self.last_call_mode = "stub-fallback"
                fake = {"model": self.model_name, "mode": "gemini-stub-fallback",
                        "preview": "Init failed. Fallback to stub."}
                return json.dumps(fake, ensure_ascii=False) if as_json else fake["preview"]

            gen_cfg = {"temperature": float(temperature)}
            max_out = os.getenv("NEXUS_DEFAULT_MAX_OUT_TOKENS")
            if max_out:
                try:
                    gen_cfg["max_output_tokens"] = int(max_out)
                except ValueError:
                    pass
            if as_json:
                gen_cfg["response_mime_type"] = "application/json"
            else:
                gen_cfg["response_mime_type"] = "text/plain"

            try:
                # ★ v2.3.5注: SDKが内部でリトライ（gRPC）を行う
                resp = model.generate_content(
                    prompt,
                    generation_config=gen_cfg
                )

                # --- 安全な取り出しロジック ---
                text = ""
                for cand in getattr(resp, "candidates", []) or []:
                    parts = getattr(getattr(cand, "content", None), "parts", []) or []
                    for p in parts:
                        if hasattr(p, "text") and p.text:
                            text += p.text
                if not text:
                    try:
                        text = getattr(resp, "text", "") or ""
                    except Exception:
                        text = ""

                if not text:
                    fr = None
                    try:
                        fr = getattr(getattr(resp, "candidates", [None])[0], "finish_reason", None)
                    except Exception:
                        pass
                    self.logger.warning(f"Gemini returned no text (finish_reason={fr}). Fallback to stub.")
                    self.last_call_mode = "stub-fallback"
                    fake = {
                        "model": self.model_name,
                        "mode": "gemini-stub-fallback",
                        "preview": "No text returned (possibly blocked)."
                    }
                    return json.dumps(fake, ensure_ascii=False) if as_json else fake["preview"]

                # ★ パッチ 1) Geminiは usage 取得が安定しないため推定フォールバック
                
                # ★ Hotfix 3) Gemini SDK でも as_json 時に _strip_jsonish 適用
                self.last_call_mode = "real"
                return _strip_jsonish(text) if as_json else text

            except Exception as e:
                self.logger.error(f"GeminiLLM REAL-CALL failed: {e}")
                self.last_call_mode = "stub-fallback"
                fake = {
                    "model": self.model_name,
                    "mode": "gemini-stub-fallback",
                    "preview": "Real call failed. Fallback to stub."
                }
                return json.dumps(fake, ensure_ascii=False) if as_json else fake["preview"]

        # スタブ応答
        self.last_call_mode = "stub"
        fake = {
            "model": self.model_name,
            "mode": "gemini-stub",
            "as_json": as_json,
            "preview": "This is a stubbed Gemini model response."
        }
        return json.dumps(fake, ensure_ascii=False) if as_json else fake["preview"]
    # --- ★★★★★ v2.3.2 堅牢化 execute() (ここまで) ★★★★★ ---


class MoonshotLLM(BaseLLM):
    """
    kimi-* 系 (Moonshot / Kimi)
    (v2.3.5: BASE URL 誤植修正 + Retry)
    """
    def __init__(self, model_name: str):
        super().__init__(model_name)
        self.api_key = os.getenv("KIMI_API_KEY")
        if not self.api_key:
            raise ValueError("KIMI_API_KEY is not set.")
        
        # ★ Bugfix (v2.3.5) BASE URL 誤植修正（Markdown表記を素のURLに）
        self.base_url = (os.getenv("KIMI_BASE_URL") or "https://api.moonshot.cn").rstrip("/")
        
        self.real_calls = (os.getenv("NEXUS_REAL_CALLS", "0") == "1") and REQUESTS_AVAILABLE
        if self.real_calls:
            # ★ v2.3.5 リトライセッション作成
            self.session = create_retry_session()
            self.logger.info("MoonshotLLM initialized in REAL-CALL mode (Retry: On).")
        else:
            self.logger.info("MoonshotLLM initialized in STUB mode.")

    def execute(self, prompt: str, system_prompt: str, **kwargs) -> str:
        temperature = kwargs.get("temperature", 0.3) # Kimi は 0.3 がデフォルト
        as_json = kwargs.get("as_json", False)

        if self.real_calls and self.session:
            # --- 実APIコール (v2.3.5) ---
            try:
                url = f"{self.base_url}/v1/chat/completions"
                headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt},
                ]
                payload = {
                    "model": self.model_name,
                    "messages": messages,
                    "temperature": float(temperature),
                }
                max_out = os.getenv("NEXUS_DEFAULT_MAX_OUT_TOKENS")
                if max_out:
                    payload["max_tokens"] = int(max_out)
                
                if as_json:
                    payload["response_format"] = {"type": "json_object"}

                # ★ v2.3.5 Timeout 環境変数 + self.session.post
                timeout = float(os.getenv("NEXUS_REQUEST_TIMEOUT_SEC", "120"))
                resp = self.session.post(url, headers=headers, json=payload, timeout=timeout)
                resp.raise_for_status()

                data = resp.json()
                text = ""
                for ch in (data.get("choices") or []):
                    msg = (ch.get("message") or {})
                    if msg.get("content"):
                        text += str(msg["content"])

                # ★ パッチ 1) 実使用トークン (v2.3.3)
                usage = data.get("usage") or {}
                self._last_usage = {
                    "prompt_tokens": usage.get("prompt_tokens"),
                    "completion_tokens": usage.get("completion_tokens"),
                }

                if not text:
                    raise RuntimeError(f"Kimi/Moonshot returned no text (FinishReason: {data.get('choices', [{}])[0].get('finish_reason')}).")

                # ★ パッチ 2) JSON 整形 (v2.3.3)
                self.last_call_mode = "real"
                return _strip_jsonish(text) if as_json else text

            except Exception as e:
                self.logger.error(f"MoonshotLLM REAL-CALL failed (after retries): {e}")
                self.last_call_mode = "stub-fallback"
                fake = {
                    "model": self.model_name,
                    "mode": "kimi-stub-fallback",
                    "preview": "Real call failed. Fallback to stub."
                }
                return json.dumps(fake, ensure_ascii=False) if as_json else fake["preview"]

        # スタブ応答
        self.last_call_mode = "stub"
        fake = {
            "model": self.model_name,
            "mode": "kimi-stub",
            "as_json": as_json,
            "preview": "This is a stubbed Kimi model response."
        }
        return json.dumps(fake, ensure_ascii=False) if as_json else fake["preview"]


class DeepSeekLLM(BaseLLM):
    """
    deepseek-* 系
    (v2.3.5: BASE URL 誤植修正 + Retry)
    """
    def __init__(self, model_name: str):
        super().__init__(model_name)
        self.api_key = os.getenv("DEEPSEEK_API_KEY")
        if not self.api_key:
            raise ValueError("DEEPSEEK_API_KEY is not set.")
        
        # ★ Bugfix (v2.3.5) BASE URL 誤植修正（Markdown表記を素のURLに）
        self.base_url = (os.getenv("DEEPSEEK_BASE_URL") or "https://api.deepseek.com").rstrip("/")

        self.real_calls = (os.getenv("NEXUS_REAL_CALLS", "0") == "1") and REQUESTS_AVAILABLE
        if self.real_calls:
            # ★ v2.3.5 リトライセッション作成
            self.session = create_retry_session()
            self.logger.info("DeepSeekLLM initialized in REAL-CALL mode (Retry: On).")
        else:
            self.logger.info("DeepSeekLLM initialized in STUB mode.")

    def execute(self, prompt: str, system_prompt: str, **kwargs) -> str:
        temperature = kwargs.get("temperature", 0.2)
        as_json = kwargs.get("as_json", False)

        if self.real_calls and self.session:
            # --- 実APIコール (v2.3.5) ---
            try:
                url = f"{self.base_url}/v1/chat/completions"
                headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt},
                ]
                payload = {
                    "model": self.model_name,
                    "messages": messages,
                    "temperature": float(temperature),
                }
                max_out = os.getenv("NEXUS_DEFAULT_MAX_OUT_TOKENS")
                if max_out:
                    payload["max_tokens"] = int(max_out)

                if as_json:
                    payload["response_format"] = {"type": "json_object"}

                # ★ v2.3.5 Timeout 環境変数 + self.session.post
                timeout = float(os.getenv("NEXUS_REQUEST_TIMEOUT_SEC", "120"))
                resp = self.session.post(url, headers=headers, json=payload, timeout=timeout)
                resp.raise_for_status()

                data = resp.json()
                text = ""
                for ch in (data.get("choices") or []):
                    msg = (ch.get("message") or {})
                    if msg.get("content"):
                        text += str(msg["content"])

                # ★ パッチ 1) 実使用トークン (v2.3.3)
                usage = data.get("usage") or {}
                self._last_usage = {
                    "prompt_tokens": usage.get("prompt_tokens"),
                    "completion_tokens": usage.get("completion_tokens"),
                }

                if not text:
                    raise RuntimeError(f"DeepSeek returned no text (FinishReason: {data.get('choices', [{}])[0].get('finish_reason')}).")

                # ★ パッチ 2) JSON 整形 (v2.3.3)
                self.last_call_mode = "real"
                return _strip_jsonish(text) if as_json else text

            except Exception as e:
                self.logger.error(f"DeepSeekLLM REAL-CALL failed (after retries): {e}")
                self.last_call_mode = "stub-fallback"
                fake = {
                    "model": self.model_name,
                    "mode": "deepseek-stub-fallback",
                    "preview": "Real call failed. Fallback to stub."
                }
                return json.dumps(fake, ensure_ascii=False) if as_json else fake["preview"]

        # スタブ応答
        self.last_call_mode = "stub"
        fake = {
            "model": self.model_name,
            "mode": "deepseek-stub",
            "as_json": as_json,
            "preview": "This is a stubbed DeepSeek model response."
        }
        return json.dumps(fake, ensure_ascii=False) if as_json else fake["preview"]

# 後方互換のためのエイリアス
DeepseekLLM = DeepSeekLLM


class LocalLLM(BaseLLM):
    """
    オフライン/テスト用の安全なダミーモデル。
    本当にお金を使いたくないときの最終フォールバック。
    (v2.3.2 から変更なし)
    """
    def execute(self, prompt: str, system_prompt: str, **kwargs) -> str:
        as_json = kwargs.get("as_json", False)
        preview = (
            "LOCAL FALLBACK: この応答はスタブです。"
            "（本番APIコールは行われていません）"
        )
        self.last_call_mode = "stub"
        if as_json:
            return json.dumps(
                {
                    "model": self.model_name,
                    "mode": "local-fallback",
                    "preview": preview,
                },
                ensure_ascii=False,
            )
        return preview


# -----------------------------------------------------------------------------
# Router から返す “実行用LLMクライアント” のラッパ
# (v2.3.5: ★ Provider ログ 適用)
# -----------------------------------------------------------------------------
class RoutedLLM(BaseLLM):
    """
    LLMRouter.get_llm_for_task() が返す実体。
    もともとの vendor LLM クライアント(self.inner)を包んで、
    execute() 時に BudgetManager と log_transaction を噛ませる。
    (NPE v1/v2/none をアダプタが自動解決)
    """

    def __init__(
        self,
        inner_llm: BaseLLM,
        router: "LLMRouter",
        task_type: str,
    ):
        # super() は inner_llm の model_name を引き継ぐ
        super().__init__(inner_llm.model_name)
        self.inner = inner_llm
        self.router = router
        self.task_type = task_type
        self.logger = logging.getLogger("RoutedLLM")
        # ★ パッチ 1) inner の _last_usage を引き継ぐ (v2.3.3)

    def _estimate_tokens(self, text: str) -> int:
        """
        超ざっくりトークン見積もり (len/3 切り上げ)
        (v2.3.2 から変更なし)
        """
        if not text:
            return 0
        approx = (len(text) + 2) // 3
        return approx

    def execute(self, prompt: str, system_prompt: str, **kwargs) -> str:
        """
        1. 事前に予算をチェック
        2. inner_llm.execute() を呼ぶ (v2.3.5: Retry/Timeout 実装)
        3. (★パッチ1) 実トークン/推定トークンを決定
        4. コストを記録 (v1 IF)
        5. (★v2.3.5) 呼び出しログ(provider, 互換キー併記)をJSONLに追記
        """
        started_at = time.time()

        # --- 1) 予算チェック (NPE v1.x IF) ---
        in_tokens = self._estimate_tokens(prompt + "\n" + system_prompt)
        can_run, est_cost = self.router.budget_manager.check_budget(
            model_name=self.model_name,
            est_input_tokens=in_tokens,
        )
        if not can_run:
            raise RuntimeError(
                f"[LLMRouter] Budget limit exceeded for model={self.model_name}. "
                f"estimated_cost_usd={est_cost}"
            )

        # --- 2) 実際のLLM呼び出し (実コール or スタブ) ------------------
        self.inner._last_usage = None # usage 格納庫をリセット
        output_text = self.inner.execute(prompt, system_prompt, **kwargs)

        # --- 3) 実コスト記録 (NPE v1.x IF) ---
        # ★ パッチ 1) 実トークン優先 (v2.3.3)
        out_tokens = 0
        if getattr(self.inner, "_last_usage", None):
            u = self.inner._last_usage
            in_tokens_real = u.get("prompt_tokens")
            if in_tokens_real:
                in_tokens = int(in_tokens_real)
            
            out_tokens_real = u.get("completion_tokens")
            if out_tokens_real:
                out_tokens = int(out_tokens_real)
            else:
                out_tokens = self._estimate_tokens(output_text) # out だけ推定
        
        if out_tokens == 0: # _last_usage が無い (Gemini等) or 失敗
            out_tokens = self._estimate_tokens(output_text)

        actual_cost = self.router.budget_manager.track_cost(
            model_name=self.model_name,
            input_tokens=in_tokens,
            output_tokens=out_tokens,
        )

        duration_s = time.time() - started_at

        # --- 4) 呼び出しログ(JSONL) ----------------------------------
        # ★ v2.3.5 ログ強化 (provider + 互換キー)
        log_transaction(
            {
                "ts": time.time(),
                "task_type": self.task_type,
                "model": self.model_name,
                "provider": model_family(self.model_name), # ★ v2.3.5 provider追加
                # 実際の結果 (real / stub / stub-fallback)
                "mode": getattr(self.inner, "last_call_mode", "stub"),
                # 新キー（実測優先）
                "input_tokens": in_tokens,
                "output_tokens": out_tokens,
                # 旧キー（下位互換） (v2.3.4)
                "input_tokens_est": in_tokens,
                "output_tokens_est": out_tokens,
                "cost_est_usd": actual_cost,
                "duration_sec": duration_s,
                "prompt_preview": prompt[:200],
            },
            log_file=self.router.call_log_path,
        )

        return output_text


# -----------------------------------------------------------------------------
# LLMRouter 本体
# (v2.3.2 / v2.3.3 から変更なし)
# -----------------------------------------------------------------------------
class LLMRouter:
    """
    - プロンプトを「どのタスクか」に分類
    - タスクに対応するモデルを決定 (v2.1.1: コスト強制上書き機能つき)
    - モデルに応じた LLM クライアントを初期化 (v2.3.5: Bugfix/Retry適用済)
    - 予算＆呼び出しログを一元管理 (v2.2.5: NPE v1/v2 自動対応)
    - 呼び出し側(BaseAgentなど)には RoutedLLM を返す
    """

    LONG_THRESHOLD = 8000  # 文字数しきい値などでモデルを切り替えたい場合に使う

    def __init__(
        self,
        task_model_map: Optional[Dict[str, str]] = None,
        daily_limit_usd: Optional[float] = None,
        log_dir: str = "logs",
    ):
        self.logger = logging.getLogger("LLMRouter")
        self.logger.setLevel(logging.INFO)
        self.env = os.environ  # ★v2.1.1 維持

        # モデル振り分けテーブル
        self.task_model_map = task_model_map or TASK_MODEL_MAP_DEFAULT.copy()

        # ログディレクトリ・ログファイルパス
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.call_log_path = str(self.log_dir / "llm_calls.jsonl")

        # BudgetManager 初期化 (NPE v1.x IF)
        limit_env = os.getenv("LLM_DAILY_LIMIT_USD")
        if daily_limit_usd is None:
            if limit_env:
                try:
                    daily_limit_usd = float(limit_env)
                except ValueError:
                    daily_limit_usd = 5.0
            else:
                daily_limit_usd = 5.0  # デフォルト上限 (USD想定)

        # (アダプタ・レイヤーがv1/v2/noneを自動で解決)
        self.budget_manager = BudgetManager(
            daily_limit_usd=daily_limit_usd,
            log_dir=self.log_dir,  # BudgetManagerのusage記録もこの下に置く
        )
        self.logger.info("[Budget] API variant detected: %s", BUDGET_API)

        # "タスク分類用" の軽量モデル。基本はGemini FlashでOK。
        classifier_model_name = self.task_model_map.get("general", "gemini-2.5-flash")
        try:
            self._classifier = self._make_client(classifier_model_name)
        except Exception as e:
            self.logger.warning(
                f"Classifier init failed for model='{classifier_model_name}': {e}. "
                "Falling back to LocalLLM."
            )
            self._classifier = LocalLLM("local-mock")

        # 起動ログ
        self.logger.info(
            "ENV sanity: OPENAI_API_KEY=%s, DEEPSEEK_API_KEY=%s, KIMI_API_KEY=%s, GEMINI_API_KEY=%s, ENV_FILE=%s",
            "set" if os.getenv("OPENAI_API_KEY") else "unset",
            "set" if os.getenv("DEEPSEEK_API_KEY") else "unset",
            "set" if os.getenv("KIMI_API_KEY") else "unset",
            "set" if os.getenv("GEMINI_API_KEY") else "unset",
            os.getenv("NEXUSCORE_ENV_LOADED", "(auto-detect failed)"),
        )
        self.logger.info(
            "TASK MODEL MAP = %s",
            self.task_model_map,
        )
        self.logger.info(
            "BudgetManager Daily Limit (USD) = %.4f",
            daily_limit_usd,
        )

        # --- ★★★★★ v2.1.1 統合コード (リファイン) ★★★★★ ---
        # (v2.3.2でも完全維持)
        raw = (self.env.get("FORCE_CHEAP_FOR_TASKS") or "")
        # 空要素を除去しつつトリム
        self.force_tasks = {t for t in (x.strip() for x in raw.split(",")) if t}
        self.cheap_model = self.env.get("CHEAP_LLM_MODEL")

        if self.force_tasks and self.cheap_model:
            self.logger.info(
                "[Router] FORCE_CHEAP_FOR_TASKS enabled for: %s",
                self.force_tasks
            )
            self.logger.info(
                "[Router] CHEAP model override target: %s",
                self.cheap_model
            )
        # --- ★★★★★ v2.1.1 統合コード (ここまで) ★★★★★ ---

    # -----------------------------------------------------------------
    # 内部: タスク分類
    # -----------------------------------------------------------------
    def _classify_task_type(self, prompt: str) -> str:
        """
        プロンプトを task_model_map のキー(=タスク種別)に分類する。
        (v2.3.4: _classifier が Hotfix 3 適用済みの GeminiLLM を使う)
        """
        allowed_task_types = ",".join(self.task_model_map.keys())
        system_prompt = (
            "You are a task classifier. "
            "Return ONLY valid JSON: "
            '{"task_type":"<one of [' + allowed_task_types + ']>"}.\n'
            "If unsure, respond with general."
        )
        classify_prompt = (
            "Classify this developer request:\n"
            f"{prompt}\n\n"
            "Which task type best matches?"
        )

        try:
            # _classifier (GeminiLLM.execute) が直接呼ばれる
            raw = self._classifier.execute(
                classify_prompt,
                system_prompt=system_prompt,
                as_json=True,
                temperature=0.0,
            )
            # ★ Hotfix 3 により、この raw は _strip_jsonish 済み
            data = json.loads(raw)
            task = str(data.get("task_type", "general")).strip().lower()
        except Exception as e:
            self.logger.error(
                "Task classification failed: %s. Falling back to 'general'.", e
            )
            task = "general"

        # 後方互換の別名(legacy)を吸収
        task = LEGACY_TO_TASK.get(task, task)

        # 万が一未知のタスク種別なら general
        if task not in self.task_model_map:
            task = "general"

        self.logger.info("Task classified as '%s'.", task)
        return task

    # -----------------------------------------------------------------
    # 内部: モデル名→LLMクライアント生成
    # -----------------------------------------------------------------
    def _make_client(self, model_name: str) -> BaseLLM:
        """
        モデル名(文字列)から、該当する LLM クラス(OpenAILLM, GeminiLLM...)を生成する。
        (v2.3.5: 各クラスが Bugfix/Retry 適用済み)
        """
        model_name = normalize_model(model_name)
        fam = model_family(model_name)

        if fam == "openai":
            return OpenAILLM(model_name)
        if fam == "gemini":
            return GeminiLLM(model_name)
        if fam == "kimi":
            return MoonshotLLM(model_name)
        if fam == "deepseek":
            return DeepSeekLLM(model_name)
        return LocalLLM(model_name)

    # -----------------------------------------------------------------
    # public: 呼び出し側(BaseAgent)が使うエントリポイント
    # -----------------------------------------------------------------
    def get_llm_for_task(self, prompt: str) -> RoutedLLM:
        """
        1. タスク分類
        2. (v2.1.1) 安価モデル強制対象かチェック
        3. タスク種別→モデル名を取得（強制なら上書き）
        4. モデル名から vendor LLM クライアントを初期化 (v2.3.5)
        5. それを RoutedLLM で包んで返す (v2.3.5)
        """
        task_type = self._classify_task_type(prompt)

        model_name = self.task_model_map.get(task_type, self.task_model_map["general"])

        # --- ★★★★★ v2.1.1 統合コード (リファイン) ★★★★★ ---
        if task_type in self.force_tasks and self.cheap_model:
            self.logger.info(
                "[Router] FORCE_CHEAP_FOR_TASKS hit: %s -> %s",
                task_type, self.cheap_model
            )
            model_name = self.cheap_model
        # --- ★★★★★ v2.1.1 統合コード (ここまで) ★★★★★ ---

        try:
            base_client = self._make_client(model_name)
        except Exception as e:
            self.logger.warning(
                "Failed to init client for model='%s': %s. Falling back to LocalLLM.",
                model_name,
                e,
            )
            base_client = LocalLLM("local-mock")

        # RoutedLLM で包む (v2.3.5: ログ強化済みの RoutedLLM)
        routed = RoutedLLM(
            inner_llm=base_client,
            router=self,
            task_type=task_type,
        )
        self.logger.info(
            "Selecting model '%s' (Provider: %s) for task '%s'",
            routed.model_name,
            model_family(routed.model_name), # ログにも provider を出す
            task_type,
        )
        return routed


# -----------------------------------------------------------------------------
# 手動テスト用: python -m nexuscore.llm.llm_router で簡易起動して確認できる
# (v2.3.5: 堅牢化パッチ適用後の動作確認)
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    print("--- LLMRouter Smoke Test (v2.3.5-robust) ---")
    
    router = None 
    try:
        # [AI提案] テスト時に環境変数をセットして実コールを試せます
        # $env:NEXUS_REAL_CALLS="1"
        # $env:NEXUS_DEFAULT_MAX_OUT_TOKENS="256"
        # $env:NEXUSCORE_ENV_FILE="C:\Users\USER\tools\NexusCore\.env"
        # $env:NEXUS_REQUEST_TIMEOUT_SEC="60" # タイムアウトテスト
        #
        # $env:OPENAI_API_KEY="sk-..." 
        # $env:DEEPSEEK_API_KEY="sk-..."
        # $env:KIMI_API_KEY="sk-..."
        # $env:GEMINI_API_KEY="AIzaSy..."

        router = LLMRouter()
        print("\nTASK MAP:", json.dumps(router.task_model_map, indent=2, ensure_ascii=False))

        # --- Test 1: Debugging (default: gpt-5) ---
        sample_prompt_debug = (
            "pytestの失敗ログを分析し、原因を特定して修正案を提示してください。"
        )
        print(f"\nSample Prompt (Debug): {sample_prompt_debug[:80]}...")
        llm_client_debug = router.get_llm_for_task(sample_prompt_debug)
        print(f"--> Selected Client: {type(llm_client_debug.inner).__name__}")
        print(f"    Model: {llm_client_debug.model_name}")
        print(f"    Task Type (router classified): {llm_client_debug.task_type}")

        resp_debug = llm_client_debug.execute(
            prompt=sample_prompt_debug,
            system_prompt="You are a world-class debugging assistant.",
            as_json=False,
        )
        print("\nLLM Response (Stub or Real):\n", resp_debug[:200], "...")

        # --- Test 2: JSON (default: gpt-5) ---
        sample_prompt_json = (
            "項目A:foo\n項目B:bar をJSONに"
        )
        print(f"\nSample Prompt (JSON): {sample_prompt_json[:80]}...")
        llm_client_json = router.get_llm_for_task(sample_prompt_json) 
        print(f"--> Selected Client: {type(llm_client_json.inner).__name__}")
        print(f"    Model: {llm_client_json.model_name}")
        print(f"    Task Type (router classified): {llm_client_json.task_type}")
        
        resp_json = llm_client_json.execute(
            prompt=sample_prompt_json,
            system_prompt="You output JSON only.",
            as_json=True,
        )
        print("\nLLM Response (Stub or Real, JSON):\n", resp_json[:200], "...")


    except Exception as e:
        print(f"\n[SmokeTest] Unexpected error: {e}")

    print("\n--- SmokeTest Finished ---")
    if router:
        print(f"--- (To see logs, check: {router.call_log_path}) ---")
        print(f"--- (Real calls use 3 retries on 429/5xx, timeout={os.getenv('NEXUS_REQUEST_TIMEOUT_SEC', '120')}s) ---")

