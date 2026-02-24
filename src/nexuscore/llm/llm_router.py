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

import json
import logging
import os
import time
from pathlib import Path
from typing import Any

from nexuscore.llm.helpers import (
    normalize_model,
)
from nexuscore.llm.provider_factory import create_provider
from nexuscore.llm.providers.base import BaseLLM
from nexuscore.llm.routing_policy import (
    LEGACY_TO_TASK,
    TASK_MODEL_MAP_DEFAULT,
    model_family,
)
from nexuscore.llm.runtime import HTTP_CLIENT_FACTORY, REQUEST_TIMEOUT

# ---- Budget / Logger import (v1/v2 後方互換) ------------------------------
# (v2.2.1 既存)
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
                    return self._b.preflight_check(
                        model_name=model_name, est_input_tokens=est_input_tokens
                    )
                except Exception:
                    return True, 0.0

            def track_cost(self, model_name: str, input_tokens: int, output_tokens: int) -> float:
                try:
                    # (v1 IF -> v2 IF 変換)
                    return self._b.record_usage(
                        model_name=model_name,
                        input_tokens=input_tokens,
                        output_tokens=output_tokens,
                    )
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
# Router から返す  “実行用LLMクライアント” のラッパ
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
        router: LLMRouter,
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
        self.inner._last_usage = None  # usage 格納庫をリセット
        # task別の温度上書き（code_generateなど）
        temp_override = self.router.task_temperature_overrides.get(self.task_type)
        if temp_override is not None and "temperature" not in kwargs:
            kwargs["temperature"] = temp_override
        output_text = self.inner.execute(prompt, system_prompt, **kwargs)
        self.router.last_mode = getattr(self.inner, "last_call_mode", "stub")

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
                out_tokens = self._estimate_tokens(output_text)  # out だけ推定

        if out_tokens == 0:  # _last_usage が無い (Gemini等) or 失敗
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
                "provider": model_family(self.model_name),  # ★ v2.3.5 provider追加
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

    CLASSIFIER_MODEL_DEFAULT = "openai:gpt-4o-mini"
    CLASSIFIER_MODEL: str = CLASSIFIER_MODEL_DEFAULT

    LONG_THRESHOLD = 8000  # 文字数しきい値などでモデルを切り替えたい場合に使う

    def __init__(
        self,
        task_model_map: dict[str, str] | None = None,
        daily_limit_usd: float | None = None,
        log_dir: str = "logs",
    ):
        self.logger = logging.getLogger("LLMRouter")
        self.logger.setLevel(logging.INFO)
        self.env = os.environ  # ★v2.1.1 維持
        self.last_mode: str = "init"

        # モデル振り分けテーブル
        self.task_model_map = task_model_map or TASK_MODEL_MAP_DEFAULT.copy()
        self.default_model = (self.task_model_map.get("general") or {}).get("primary")
        self.task_temperature_overrides = {
            "code_generate": float(os.getenv("NEXUS_CODEGEN_TEMP", "0.1")),
        }

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

        # モデル検出とtask model mapの更新（Smoke Test対応）
        self._detect_and_update_models()

        # "タスク分類用" モデル（デフォルト: openai:gpt-4o-mini）
        classifier_model_name = (
            self.env.get("NEXUS_CLASSIFIER_MODEL")
            or (self.task_model_map.get("routing_classify") or {}).get("primary")
            or self.CLASSIFIER_MODEL_DEFAULT
        )
        LLMRouter.CLASSIFIER_MODEL = classifier_model_name
        self.CLASSIFIER_MODEL = classifier_model_name
        from nexuscore.llm.task_classifier import TaskClassifier

        classifier_client = self._make_client(classifier_model_name)
        self._classifier = TaskClassifier(classifier_model_name, classifier_client)

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
        raw = self.env.get("FORCE_CHEAP_FOR_TASKS") or ""
        # 空要素を除去しつつトリム
        self.force_tasks = {t for t in (x.strip() for x in raw.split(",")) if t}
        self.cheap_model = self.env.get("CHEAP_LLM_MODEL")

        if self.force_tasks and self.cheap_model:
            self.logger.info("[Router] FORCE_CHEAP_FOR_TASKS enabled for: %s", self.force_tasks)
            self.logger.info("[Router] CHEAP model override target: %s", self.cheap_model)
        # --- ★★★★★ v2.1.1 統合コード (ここまで) ★★★★★ ---

    # -----------------------------------------------------------------
    # 内部: モデル検出（Smoke Test対応）
    # -----------------------------------------------------------------
    def _detect_and_update_models(self) -> None:
        """
        起動時に利用可能なモデルを検出し、task model mapを更新する。
        ネットワーク失敗時は既存設定にフォールバック（警告ログのみ）。
        """
        detected_models = {"openai": [], "gemini": []}

        # OpenAI モデル検出
        openai_key = os.getenv("OPENAI_API_KEY")
        if openai_key and HTTP_CLIENT_FACTORY.available:
            try:
                session = HTTP_CLIENT_FACTORY.create_session()
                if session:
                    url = "https://api.openai.com/v1/models"
                    headers = {"Authorization": f"Bearer {openai_key}"}
                    resp = session.get(url, headers=headers, timeout=10)
                    if resp.status_code == 200:
                        data = resp.json()
                        all_models = [m["id"] for m in data.get("data", [])]
                        # chat/completionsエンドポイントで使えるモデルのみを抽出
                        # codex系やcompletions専用モデルを除外
                        chat_compatible = [
                            m
                            for m in all_models
                            if not m.endswith("-codex") and not m.endswith("-instruct")
                        ]
                        detected_models["openai"] = chat_compatible
                        self.logger.info(
                            f"[Model Detection] OpenAI: Found {len(all_models)} total models, {len(chat_compatible)} chat-compatible models"
                        )
                        if chat_compatible:
                            self.logger.debug(
                                f"[Model Detection] OpenAI chat-compatible models (first 10): {chat_compatible[:10]}"
                            )
            except Exception as e:
                self.logger.warning(
                    f"[Model Detection] OpenAI models.list failed: {e}. Using static defaults."
                )

        # Gemini モデル検出（403回避のためURLエンコーディング使用）
        gemini_key = os.getenv("GEMINI_API_KEY")
        if gemini_key and HTTP_CLIENT_FACTORY.available:
            try:
                session = HTTP_CLIENT_FACTORY.create_session()
                if session:
                    url = "https://generativelanguage.googleapis.com/v1beta/models"
                    # paramsを使用してURLエンコーディングを適切に処理（403回避）
                    params = {"key": gemini_key}
                    resp = session.get(url, params=params, timeout=10)
                    if resp.status_code == 200:
                        data = resp.json()
                        models_list = data.get("models", [])
                        # generateContent対応モデルのみ抽出
                        for m in models_list:
                            name = m.get("name", "")
                            methods = m.get("supportedGenerationMethods", [])
                            if "generateContent" in methods and name.startswith("models/"):
                                # models/gemini-2.5-flash -> gemini-2.5-flash に変換
                                pure_name = name.replace("models/", "")
                                detected_models["gemini"].append(pure_name)
                        self.logger.info(
                            f"[Model Detection] Gemini: Found {len(detected_models['gemini'])} generateContent-compatible models"
                        )
                    elif resp.status_code == 403:
                        self.logger.warning(
                            "[Model Detection] Gemini API returned 403 (key/permission issue). Gemini will be disabled for this run."
                        )
                    else:
                        self.logger.warning(
                            f"[Model Detection] Gemini API returned status {resp.status_code}. Using static defaults."
                        )
            except Exception as e:
                self.logger.warning(
                    f"[Model Detection] Gemini models.list failed: {e}. Using static defaults."
                )

        # task model mapを検出結果に基づいて更新
        self._apply_detected_models(detected_models)

    def _apply_detected_models(self, detected: dict[str, list[str]]) -> None:
        """
        検出されたモデル一覧に基づいてtask model mapを更新する。
        実在しないモデル名を実在するモデルに置き換える。
        """
        openai_models = detected.get("openai", [])
        gemini_models = detected.get("gemini", [])

        # OpenAIモデルの優先順位（chat/completionsエンドポイントで使えるもののみ）
        # codex系は除外（v1/chat/completionsで使えないため、検出結果にも含まれない）
        openai_chat_candidates = [
            "gpt-5.2-chat-latest",
            "gpt-5.1-chat-latest",
            "gpt-5-chat-latest",
            "gpt-4o",
            "gpt-4-turbo",
            "gpt-3.5-turbo",
        ]
        # code_generate用：codex系は除外し、chat系のみを使用（Smoke Test要件）
        openai_codex_candidates = ["gpt-4o"]  # codex系は除外済み、chat系のみ
        openai_mini_candidates = ["gpt-5-mini", "gpt-5.1-mini", "gpt-4o-mini", "gpt-3.5-turbo"]

        def find_available_model(candidates: list[str], available_list: list[str]) -> str | None:
            """候補リストから実在する最初のモデルを返す"""
            for candidate in candidates:
                if candidate in available_list:
                    return candidate
            return None

        # general/requirement/planning: chat対応モデル
        chat_model = find_available_model(openai_chat_candidates, openai_models)
        if not chat_model:
            chat_model = "gpt-4o"  # フォールバック

        # code_generate/test_generate/debug: Smoke Testではchat系に固定（codex系が存在しない場合）
        # エンドポイント不一致を避けるため、chat/completionsで呼べるモデルのみ使用
        codex_model = find_available_model(openai_codex_candidates, openai_models)
        if not codex_model:
            # codex系が存在しない場合はchat系を使用（Smoke Test要件）
            codex_model = chat_model

        # routing_classify: miniモデル
        mini_model = find_available_model(openai_mini_candidates, openai_models) or "gpt-4o-mini"

        # Gemini: gemini-2.5-pro/flash が存在する場合
        gemini_model = None
        if gemini_models:
            for candidate in ["gemini-2.5-pro", "gemini-2.5-flash", "gemini-1.5-pro"]:
                if candidate in gemini_models:
                    gemini_model = f"google:{candidate}"
                    break

        # task model mapを更新（provider:model形式）
        updates = {}
        if chat_model:
            # general, requirement, planning, review, testing 系を更新（Smoke Test要件）
            chat_tasks = [
                "general",
                "requirement",
                "requirement_elicit",
                "plan_generate",
                "planning",
                "code_review",
                "review",
                "testing",
                "test",
            ]
            for task in chat_tasks:
                if task in self.task_model_map:
                    current = self.task_model_map[task]
                    if isinstance(current, dict):
                        # provider:model形式に変換
                        if not chat_model.startswith("openai:"):
                            chat_model_with_provider = f"openai:{chat_model}"
                        else:
                            chat_model_with_provider = chat_model
                        updates[task] = {**current, "primary": chat_model_with_provider}

        if codex_model:
            # code_generate, test_generate, debug を更新（Smoke Testではchat系に固定）
            for task in ["code_generate", "test_generate", "debug", "code_refactor"]:
                if task in self.task_model_map:
                    current = self.task_model_map[task]
                    if isinstance(current, dict):
                        if not codex_model.startswith("openai:"):
                            codex_model_with_provider = f"openai:{codex_model}"
                        else:
                            codex_model_with_provider = codex_model
                        updates[task] = {**current, "primary": codex_model_with_provider}
                        self.logger.debug(
                            f"[Model Detection] {task} will use {codex_model_with_provider} (chat-compatible for Smoke Test)"
                        )

        if mini_model:
            # routing_classify を更新
            if "routing_classify" in self.task_model_map:
                current = self.task_model_map["routing_classify"]
                if isinstance(current, dict):
                    if not mini_model.startswith("openai:"):
                        mini_model_with_provider = f"openai:{mini_model}"
                    else:
                        mini_model_with_provider = mini_model
                    updates["routing_classify"] = {**current, "primary": mini_model_with_provider}

        if gemini_model:
            # Gemini系タスクを更新
            for task in ["analytical", "plan_generate", "catalog_enrich", "scraping_analyze"]:
                if task in self.task_model_map:
                    current = self.task_model_map[task]
                    if isinstance(current, dict):
                        updates[task] = {**current, "primary": gemini_model}

        # 更新を適用
        for task, new_config in updates.items():
            self.task_model_map[task] = new_config
            self.logger.info(f"[Model Detection] Updated {task}: {new_config.get('primary')}")

        if updates:
            self.logger.info(
                f"[Model Detection] Updated {len(updates)} task model mappings based on detected models"
            )
        else:
            self.logger.info("[Model Detection] No model mappings updated (using static defaults)")

    # -----------------------------------------------------------------
    # 内部: タスク分類
    # -----------------------------------------------------------------
    def _classify_task_type(self, prompt: str) -> str:
        """
        プロンプトを task_model_map のキー(=タスク種別)に分類する。
        (v2.3.4: _classifier が Hotfix 3 適用済みの GeminiLLM を使う)
        """
        try:
            task = self._classifier.classify(prompt, self.task_model_map)
        except Exception as e:
            self.logger.error("Task classification failed: %s. Falling back to 'general'.", e)
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
        return create_provider(model_name)

    # -----------------------------------------------------------------
    # public: 呼び出し側(BaseAgent)が使うエントリポイント
    # -----------------------------------------------------------------
    def get_llm_for_task(self, prompt: str, task_type: str | None = None) -> RoutedLLM:
        """
        1. タスク分類
        2. (v2.1.1) 安価モデル強制対象かチェック
        3. タスク種別→モデル名を取得（強制なら上書き）
        4. モデル名から vendor LLM クライアントを初期化 (v2.3.5)
        5. それを RoutedLLM で包んで返す (v2.3.5)
        """
        task_type = task_type or self._classify_task_type(prompt)

        llm_mode = os.getenv("NEXUS_LLM_MODE", "production").strip().lower()

        def _resolve(task: str) -> tuple[str, list[str]]:
            entry = self.task_model_map.get(task) or self.task_model_map.get("general", {})
            if isinstance(entry, dict):
                primary = entry.get("primary")
                fb = entry.get("fallbacks", [])
            else:
                primary = entry
                fb = []
            return primary, fb

        if llm_mode == "cheap":
            cheap_map = {
                "routing_classify": "openai:gpt-5.1-instant",
                "catalog_enrich": "google:gemini-2.5-flash-latest",
                "chat_general": "openai:gpt-5.1-instant",
            }
            cheap_model = cheap_map.get(task_type)
            if cheap_model:
                model_name, fallbacks = cheap_model, []
            else:
                model_name, fallbacks = _resolve(task_type)
        else:
            model_name, fallbacks = _resolve(task_type)

        # --- ★★★★★ v2.1.1 統合コード (リファイン) ★★★★★ ---
        if task_type in self.force_tasks and self.cheap_model:
            self.logger.info(
                "[Router] FORCE_CHEAP_FOR_TASKS hit: %s -> %s", task_type, self.cheap_model
            )
            model_name = self.cheap_model
        # --- ★★★★★ v2.1.1 統合コード (ここまで) ★★★★★ ---

        candidates = [m for m in [model_name] + fallbacks if m]
        base_client = None
        last_err: Exception | None = None
        for candidate in candidates:
            try:
                base_client = self._make_client(candidate)
                model_name = candidate
                break
            except Exception as e:
                last_err = e
                self.logger.warning("Failed to init client for model='%s': %s", candidate, e)
        if base_client is None:
            raise RuntimeError(
                f"No available LLM client for task '{task_type}'. last_error={last_err}"
            )

        # RoutedLLM で包む (v2.3.5: ログ強化済みの RoutedLLM)
        routed = RoutedLLM(
            inner_llm=base_client,
            router=self,
            task_type=task_type,
        )
        self.logger.info(
            "Selecting model '%s' (Provider: %s) for task '%s'",
            routed.model_name,
            model_family(routed.model_name),  # ログにも provider を出す
            task_type,
        )
        return routed

    # -----------------------------------------------------------------
    # NPE 経由で使うための complete() API
    # -----------------------------------------------------------------
    def complete(
        self,
        *,
        model: str | None = None,
        system_prompt: str,
        user_prompt: str,
        task: str | None = None,
        as_json: bool = False,
        **kwargs,
    ) -> dict[str, Any]:
        """
        guarded_llm_call から呼ばれる統一エントリ。
        戻り値は {"ok": bool, "reason": str, "content": str, "usage": {...}} 形式。
        """
        try:
            routed = None
            if model:
                base_client = self._make_client(model)
                routed = RoutedLLM(inner_llm=base_client, router=self, task_type=task or "general")
            else:
                routed = self.get_llm_for_task(user_prompt, task_type=task)

            output_text = routed.execute(
                prompt=user_prompt,
                system_prompt=system_prompt,
                as_json=as_json,
                **kwargs,
            )

            inner = getattr(routed, "inner", routed)
            usage = getattr(inner, "_last_usage", None) or {}

            # 推定トークン（実測が無い場合のみ）
            def _estimate_tokens(text: str) -> int:
                if not text:
                    return 0
                return (len(text) + 2) // 3

            prompt_tokens = usage.get("prompt_tokens") or _estimate_tokens(
                system_prompt + user_prompt
            )
            completion_tokens = usage.get("completion_tokens") or _estimate_tokens(str(output_text))
            usage = {
                "prompt_tokens": int(prompt_tokens),
                "completion_tokens": int(completion_tokens),
            }

            return {
                "ok": True,
                "reason": "",
                "content": output_text,
                "usage": usage,
                "task_type": task or getattr(routed, "task_type", "general"),
                "mode": getattr(inner, "last_call_mode", getattr(routed, "last_call_mode", "stub")),
            }
        except Exception as e:
            self.logger.error("LLMRouter.complete failed: %s", e, exc_info=True)
            return {
                "ok": False,
                "reason": str(e),
                "content": "",
                "usage": {"prompt_tokens": 0, "completion_tokens": 0},
                "task_type": task or "general",
                "mode": "error",
            }


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
        sample_prompt_debug = "pytestの失敗ログを分析し、原因を特定して修正案を提示してください。"
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
        sample_prompt_json = "項目A:foo\n項目B:bar をJSONに"
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
        print(f"--- (Real calls use 3 retries on 429/5xx, timeout={REQUEST_TIMEOUT}s) ---")
