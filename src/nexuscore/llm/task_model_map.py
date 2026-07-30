from __future__ import annotations

import logging
import os
from dataclasses import dataclass

from .llm_profiles import get_profile, profile_to_model_name

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TaskModelConfig:
    """Structured mapping from a task to LLM profile candidates."""

    primary: str
    secondary: list[str]
    fallback: str
    temperature: float | None = None


TASK_MODEL_CONFIGS: dict[str, TaskModelConfig] = {
    # ==================================================================
    # 3LLM集約構成（2026-07-23 テスト用ローカル変更・バックアップあり）
    #   生成 = GLM(glm_default/glm_strict)
    #   レビュー = Gemini(gemini_secondary)
    #   分析/分類 = MiniMax(minimax_default/minimax_analytical)
    #   ※ 生成とレビューを別LLMに（自己チェックの偏り回避）
    #   ※ OpenAI/Anthropicプロファイルは今回無効化（キー不活性のため）
    # ==================================================================
    # --- 生成系: GLM（書く・直す・テスト生成・デバッグ・自己修復）---
    # ※ secondary から gemini_secondary を意図的に除外（Gemini節約・2026-07-23）
    #   将来 GLM_strict 品質問題時に Gemini 二次化が必要なら明示的に追加すること
    "code_generate": TaskModelConfig(
        primary="glm_default",
        secondary=["minimax_default"],
        fallback="minimax_default",
        temperature=0.2,
    ),
    "code_refactor": TaskModelConfig(
        primary="glm_default",
        secondary=["minimax_default"],
        fallback="minimax_default",
    ),
    "code_explain": TaskModelConfig(
        primary="glm_default",
        secondary=["minimax_default"],
        fallback="minimax_default",
    ),
    "test_generate": TaskModelConfig(
        primary="glm_default",
        secondary=["minimax_default", "gemini_secondary"],
        fallback="minimax_default",
    ),
    "debug": TaskModelConfig(
        primary="glm_strict",
        secondary=["glm_default", "minimax_default"],
        fallback="glm_default",
    ),
    # --- レビュー系: Gemini（品質チェック・設計・要件・計画・ポリシー・ポストモーテム）---
    "code_review": TaskModelConfig(
        primary="gemini_secondary",
        secondary=["minimax_analytical", "glm_strict"],
        fallback="glm_strict",
    ),
    "architect": TaskModelConfig(
        primary="glm_strict",
        secondary=["minimax_analytical", "glm_strict"],
        fallback="glm_strict",
    ),
    "arch_design": TaskModelConfig(
        primary="glm_strict",
        secondary=["minimax_analytical", "glm_strict"],
        fallback="glm_strict",
    ),
    "plan_generate": TaskModelConfig(
        primary="gemini_secondary",
        secondary=["minimax_analytical", "glm_strict"],
        fallback="glm_strict",
    ),
    "requirement": TaskModelConfig(
        primary="gemini_secondary",
        secondary=["minimax_analytical", "glm_strict"],
        fallback="glm_strict",
    ),
    "requirement_elicit": TaskModelConfig(
        primary="glm_strict",
        secondary=["minimax_analytical", "glm_strict"],
        fallback="glm_strict",
    ),
    "policy_check": TaskModelConfig(
        primary="glm_strict",
        secondary=["minimax_analytical", "glm_strict"],
        fallback="glm_strict",
    ),
    "postmortem_analyze": TaskModelConfig(
        primary="glm_strict",
        secondary=["minimax_analytical", "glm_strict"],
        fallback="glm_strict",
    ),
    # --- 保守: 自己修復は生成系(Geminiレビュー対象を直すのでGLM生成)---
    "self_heal": TaskModelConfig(
        primary="glm_strict",
        secondary=["glm_default", "minimax_default"],
        fallback="glm_default",
    ),
    # --- 分析/分類系: MiniMax（ルーティング・知識整理・分析・コマース推論・一般チャット）---
    "routing_classify": TaskModelConfig(
        primary="minimax_default",
        secondary=["glm_default"],
        fallback="glm_default",
    ),
    "knowledge_curate": TaskModelConfig(
        primary="minimax_analytical",
        secondary=["glm_strict", "glm_default"],
        fallback="glm_default",
    ),
    "scraping_analyze": TaskModelConfig(
        primary="minimax_analytical",
        secondary=["glm_default"],
        fallback="glm_default",
    ),
    "pricing_strategy": TaskModelConfig(
        primary="minimax_analytical",
        secondary=["glm_strict", "glm_default"],
        fallback="glm_default",
    ),
    "catalog_enrich": TaskModelConfig(
        primary="minimax_default",
        secondary=["glm_default"],
        fallback="glm_default",
    ),
    "shipping_infer": TaskModelConfig(
        primary="minimax_default",
        secondary=["glm_default"],
        fallback="glm_default",
    ),
    "chat_general": TaskModelConfig(
        primary="minimax_default",
        secondary=["glm_default"],
        fallback="glm_default",
    ),
    "creative": TaskModelConfig(
        primary="minimax_default",
        secondary=["glm_default"],
        fallback="glm_default",
    ),
    "analytical": TaskModelConfig(
        primary="minimax_analytical",
        secondary=["glm_default"],
        fallback="glm_default",
    ),
    "secure": TaskModelConfig(
        primary="minimax_analytical",
        secondary=["glm_strict", "glm_default"],
        fallback="glm_default",
    ),
    "general": TaskModelConfig(
        primary="minimax_default",
        secondary=["glm_default"],
        fallback="glm_default",
    ),
    "vc_analysis": TaskModelConfig(
        primary="minimax_analytical",
        secondary=["glm_default"],
        fallback="glm_default",
    ),
    "npe_govern": TaskModelConfig(
        primary="minimax_analytical",
        secondary=["glm_strict", "glm_default"],
        fallback="glm_default",
    ),
}

# Legacy task names expect concrete configs as well.
_TASK_ALIAS_SOURCE = {
    "testing": "test_generate",
    "debugging": "debug",
    "review": "code_review",
    "policy": "policy_check",
    "planning": "plan_generate",
    "requirements": "requirement",
}
for alias, target in _TASK_ALIAS_SOURCE.items():
    if target in TASK_MODEL_CONFIGS:
        TASK_MODEL_CONFIGS[alias] = TASK_MODEL_CONFIGS[target]


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


# ---------------------------------------------------------------------------
# env 上書き: NEXUS_TASK_MODEL_CODING/REVIEW/GENERAL で各カテゴリの primary を切替
#   7-23監査④デッドキー是正。値は profile ID（glm_default/gemini_secondary 等）。
#   未設定時は既定（TASK_MODEL_CONFIGS の primary）を維持。
#   カテゴリは 2026-07-23 3LLM集約構成（生成=GLM / レビュー=Gemini / 分析分類=MiniMax）に準拠。
# ---------------------------------------------------------------------------
_TASK_CATEGORY: dict[str, str] = {
    # CODING系（生成: 書く・直す・テスト生成・デバッグ・自己修復）
    "code_generate": "coding",
    "code_refactor": "coding",
    "code_explain": "coding",
    "test_generate": "coding",
    "debug": "coding",
    "self_heal": "coding",
    # REVIEW系（レビュー: 品質チェック・設計・要件・計画・ポリシー・ポストモーテム）
    "code_review": "review",
    "architect": "review",
    "arch_design": "review",
    "plan_generate": "review",
    "requirement": "review",
    "requirement_elicit": "review",
    "policy_check": "review",
    "postmortem_analyze": "review",
    # GENERAL系（分析/分類ほか）は _TASK_CATEGORY 未登録タスクを "general" にフォールバック
}

# alias（testing/review/planning 等）は target と同カテゴリを継承
for _alias, _target in _TASK_ALIAS_SOURCE.items():
    if _target in _TASK_CATEGORY:
        _TASK_CATEGORY[_alias] = _TASK_CATEGORY[_target]

_CATEGORY_ENV: dict[str, str] = {
    "coding": "NEXUS_TASK_MODEL_CODING",
    "review": "NEXUS_TASK_MODEL_REVIEW",
    "general": "NEXUS_TASK_MODEL_GENERAL",
}


def _resolve_primary(task: str, default_profile: str) -> str:
    """Return the primary profile id, overridden by env when set.

    env の値は profile ID（glm_default/gemini_secondary 等）として扱う。
    未知の値（model name 形式や typo 等）の場合は既定にフォールバックし
    警告1回を出力（移行安全性: 既存 .env の古い値でクラッシュしない）。
    """
    category = _TASK_CATEGORY.get(task, "general")
    env_key = _CATEGORY_ENV[category]
    override = os.environ.get(env_key, "").strip()
    if not override:
        return default_profile
    if get_profile(override) is None:
        # env キーごと1回だけ警告（起動時に大量の重複ログを出さない）
        if env_key not in _WARNED_BAD_ENV:
            _WARNED_BAD_ENV.add(env_key)
            logger.warning(
                "%s=%r は未知の profile ID です（既定 %r を使用）。"
                "profile ID（glm_default/gemini_secondary/minimax_default 等）を指定してください。",
                env_key, override, default_profile,
            )
        return default_profile
    return override


_WARNED_BAD_ENV: set[str] = set()


def build_task_model_map_dict() -> dict[str, dict[str, object]]:
    """
    Build a dict matching the legacy TASK_MODEL_MAP_DEFAULT structure.
    """
    result: dict[str, dict[str, object]] = {}
    for task, cfg in TASK_MODEL_CONFIGS.items():
        primary_model = profile_to_model_name(_resolve_primary(task, cfg.primary))
        fallbacks = [profile_to_model_name(profile_id) for profile_id in cfg.secondary]
        fallback_model = profile_to_model_name(cfg.fallback)
        if fallback_model not in fallbacks:
            fallbacks.append(fallback_model)
        result_entry: dict[str, object] = {
            "primary": primary_model,
            "fallbacks": fallbacks,
        }
        if cfg.temperature is not None:
            result_entry["temperature"] = cfg.temperature
        result[task] = result_entry
    return result


__all__ = [
    "TaskModelConfig",
    "TASK_MODEL_CONFIGS",
    "LEGACY_TO_TASK",
    "build_task_model_map_dict",
]
