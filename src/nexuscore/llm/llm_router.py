from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

_logger = logging.getLogger(__name__)

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
from nexuscore.llm.runtime import REQUEST_TIMEOUT

# Extracted modules
from nexuscore.llm._adapters import BUDGET_API, BudgetManager, log_transaction  # noqa: F401
from nexuscore.llm._model_detection import apply_detected_models, detect_available_models
from nexuscore.llm._routed_llm import RoutedLLM  # noqa: F401
from nexuscore.llm._router_utils import estimate_tokens


# -----------------------------------------------------------------------------
# LLMRouter 本体
# -----------------------------------------------------------------------------
class LLMRouter:
    """
    - プロンプトをタスクに分類
    - タスクに対応するモデルを決定
    - モデルに応じたLLMクライアントを初期化
    - 予算＆呼び出しログを一元管理
    - RoutedLLM を返す
    """

    CLASSIFIER_MODEL_DEFAULT = "openai:gpt-4o-mini"
    CLASSIFIER_MODEL: str = CLASSIFIER_MODEL_DEFAULT
    LONG_THRESHOLD = 8000

    def __init__(
        self,
        task_model_map: dict[str, str] | None = None,
        daily_limit_usd: float | None = None,
        log_dir: str = "logs",
    ):
        self.logger = logging.getLogger("LLMRouter")
        self.logger.setLevel(logging.INFO)
        self.env = os.environ
        self.last_mode: str = "init"

        # モデル振り分けテーブル
        self.task_model_map = task_model_map or TASK_MODEL_MAP_DEFAULT.copy()
        self.default_model = (self.task_model_map.get("general") or {}).get("primary")  # type: ignore[union-attr]
        self.task_temperature_overrides = {
            "code_generate": float(os.getenv("NEXUS_CODEGEN_TEMP", "0.1")),
        }

        # ログディレクトリ
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.call_log_path = str(self.log_dir / "llm_calls.jsonl")

        # BudgetManager 初期化
        limit_env = os.getenv("LLM_DAILY_LIMIT_USD")
        if daily_limit_usd is None:
            if limit_env:
                try:
                    daily_limit_usd = float(limit_env)
                except ValueError:
                    daily_limit_usd = 5.0
            else:
                daily_limit_usd = 5.0

        self.budget_manager = BudgetManager(
            daily_limit_usd=daily_limit_usd,
            log_dir=self.log_dir,
        )
        self.logger.info("[Budget] API variant detected: %s", BUDGET_API)

        # モデル検出とtask model mapの更新
        self._detect_and_update_models()

        # タスク分類用モデル
        classifier_model_name = (
            self.env.get("NEXUS_CLASSIFIER_MODEL")
            or (self.task_model_map.get("routing_classify") or {}).get("primary")  # type: ignore[union-attr]
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
        self.logger.info("TASK MODEL MAP = %s", self.task_model_map)
        self.logger.info("BudgetManager Daily Limit (USD) = %.4f", daily_limit_usd)

        # v2.1.1: FORCE_CHEAP_FOR_TASKS
        raw = self.env.get("FORCE_CHEAP_FOR_TASKS") or ""
        self.force_tasks = {t for t in (x.strip() for x in raw.split(",")) if t}
        self.cheap_model = self.env.get("CHEAP_LLM_MODEL")
        if self.force_tasks and self.cheap_model:
            self.logger.info("[Router] FORCE_CHEAP_FOR_TASKS enabled for: %s", self.force_tasks)
            self.logger.info("[Router] CHEAP model override target: %s", self.cheap_model)

    # -----------------------------------------------------------------
    # 内部: モデル検出（_model_detection.py へのデリゲート）
    # -----------------------------------------------------------------
    def _detect_and_update_models(self) -> None:
        detected = detect_available_models(self.logger)
        self._apply_detected_models(detected)

    def _apply_detected_models(self, detected: dict[str, list[str]]) -> None:
        apply_detected_models(detected, self.task_model_map, self.logger)

    # -----------------------------------------------------------------
    # 内部: タスク分類
    # -----------------------------------------------------------------
    def _classify_task_type(self, prompt: str) -> str:
        try:
            task = self._classifier.classify(prompt, self.task_model_map)
        except Exception as e:  # noqa: BLE001 — タスク分類失敗時のフォールバック
            self.logger.error("Task classification failed: %s. Falling back to 'general'.", e)
            task = "general"
        task = LEGACY_TO_TASK.get(task, task)
        if task not in self.task_model_map:
            task = "general"
        self.logger.info("Task classified as '%s'.", task)
        return task

    # -----------------------------------------------------------------
    # 内部: モデル名→LLMクライアント生成
    # -----------------------------------------------------------------
    def _make_client(self, model_name: str) -> BaseLLM:
        model_name = normalize_model(model_name)
        return create_provider(model_name)

    # -----------------------------------------------------------------
    # public: エントリポイント
    # -----------------------------------------------------------------
    def get_llm_for_task(self, prompt: str, task_type: str | None = None) -> RoutedLLM:
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
            return primary, fb  # type: ignore[return-value]

        if llm_mode == "cheap":
            cheap_map = {
                "routing_classify": "openai:gpt-5.1-instant",
                "catalog_enrich": "google:gemini-2.5-flash-latest",
                "chat_general": "openai:gpt-5.1-instant",
            }
            cheap_model = cheap_map.get(task_type)
            if cheap_model:
                model_name, fallbacks = cheap_model, []  # type: ignore[var-annotated]
            else:
                model_name, fallbacks = _resolve(task_type)
        else:
            model_name, fallbacks = _resolve(task_type)

        if task_type in self.force_tasks and self.cheap_model:
            self.logger.info(
                "[Router] FORCE_CHEAP_FOR_TASKS hit: %s -> %s", task_type, self.cheap_model
            )
            model_name = self.cheap_model

        candidates = [m for m in [model_name] + fallbacks if m]
        base_client = None
        last_err: Exception | None = None
        for candidate in candidates:
            try:
                base_client = self._make_client(candidate)
                model_name = candidate
                break
            except Exception as e:  # noqa: BLE001 — LLMクライアント初期化失敗時のフォールバック
                last_err = e
                self.logger.warning("Failed to init client for model='%s': %s", candidate, e)
        if base_client is None:
            raise RuntimeError(
                f"No available LLM client for task '{task_type}'. last_error={last_err}"
            )

        routed = RoutedLLM(
            inner_llm=base_client,
            router=self,
            task_type=task_type,
        )
        self.logger.info(
            "Selecting model '%s' (Provider: %s) for task '%s'",
            routed.model_name,
            model_family(routed.model_name),
            task_type,
        )
        return routed

    # -----------------------------------------------------------------
    # complete() API
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

            prompt_tokens = usage.get("prompt_tokens") or estimate_tokens(
                system_prompt + user_prompt
            )
            completion_tokens = usage.get("completion_tokens") or estimate_tokens(str(output_text))
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
        except Exception as e:  # noqa: BLE001 — complete API全体のフォールバック
            self.logger.error("LLMRouter.complete failed: %s", e, exc_info=True)
            return {
                "ok": False,
                "reason": str(e),
                "content": "",
                "usage": {"prompt_tokens": 0, "completion_tokens": 0},
                "task_type": task or "general",
                "mode": "error",
            }
