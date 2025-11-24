"""
Routing policy utilities and task-model mappings for LLMRouter.
"""

from __future__ import annotations

from typing import Any, Dict, Tuple

TASK_MODEL_MAP_DEFAULT: Dict[str, Dict[str, Any]] = {
    # ===== 開発フロー（コード/テスト）=====
    "code_generate": {
        "primary": "openai:gpt-5.1",
        "fallbacks": [
            "google:gemini-2.5-pro-latest",
            "deepseek-coder",
            "anthropic:claude-3.5-sonnet",
        ],
    },
    "code_refactor": {
        "primary": "openai:gpt-5.1",
        "fallbacks": [
            "openai:gpt-5.1-instant",
            "anthropic:claude-3.5-sonnet",
        ],
    },
    "code_review": {
        "primary": "openai:gpt-5.1-thinking",
        "fallbacks": [
            "anthropic:claude-3.5-sonnet",
            "google:gemini-2.5-pro-latest",
        ],
    },
    "test_generate": {
        "primary": "openai:gpt-5.1",
        "fallbacks": [
            "anthropic:claude-3.5-sonnet",
            "google:gemini-2.5-pro-latest",
        ],
    },
    "self_heal": {
        "primary": "openai:gpt-5.1-thinking",
        "fallbacks": [
            "anthropic:claude-3.5-sonnet",
            "openai:gpt-5.1",
        ],
    },
    # ===== 要件・計画・アーキ =====
    "requirement_elicit": {
        "primary": "google:gemini-2.5-pro-latest",
        "fallbacks": [
            "openai:gpt-5.1-thinking",
            "anthropic:claude-3.5-sonnet",
        ],
    },
    "plan_generate": {
        "primary": "google:gemini-2.5-pro-latest",
        "fallbacks": [
            "openai:gpt-5.1-thinking",
            "anthropic:claude-3.5-sonnet",
        ],
    },
    "arch_design": {
        "primary": "google:gemini-2.5-pro-latest",
        "fallbacks": [
            "openai:gpt-5.1-thinking",
            "anthropic:claude-3.5-sonnet",
        ],
    },
    # ===== BUYMA / スクレイピング =====
    "scraping_analyze": {
        "primary": "openai:gpt-5.1-thinking",
        "fallbacks": [
            "google:gemini-2.5-pro-latest",
            "anthropic:claude-3.5-sonnet",
        ],
    },
    "pricing_strategy": {
        "primary": "google:gemini-2.5-pro-latest",
        "fallbacks": [
            "openai:gpt-5.1-thinking",
            "anthropic:claude-3.5-sonnet",
        ],
    },
    "catalog_enrich": {
        "primary": "google:gemini-2.5-flash-latest",
        "fallbacks": [
            "openai:gpt-5.1-instant",
        ],
    },
    "shipping_infer": {
        "primary": "google:gemini-2.5-pro-latest",
        "fallbacks": [
            "openai:gpt-5.1",
            "anthropic:claude-3.5-sonnet",
        ],
    },
    # ===== ガバナンス / ポリシー / NPE =====
    "routing_classify": {
        "primary": "openai:gpt-5.1-instant",
        "fallbacks": [
            "google:gemini-2.5-flash-latest",
        ],
    },
    "policy_check": {
        "primary": "anthropic:claude-3.5-sonnet",
        "fallbacks": [
            "openai:gpt-5.1-thinking",
            "google:gemini-2.5-pro-latest",
        ],
    },
    "postmortem_analyze": {
        "primary": "openai:gpt-5.1-thinking",
        "fallbacks": [
            "anthropic:claude-3.5-sonnet",
            "google:gemini-2.5-pro-latest",
        ],
    },
    "knowledge_curate": {
        "primary": "google:gemini-2.5-pro-latest",
        "fallbacks": [
            "anthropic:claude-3.5-sonnet",
            "openai:gpt-5.1-thinking",
        ],
    },
    # ===== 汎用 / VC / NPE =====
    "chat_general": {
        "primary": "openai:gpt-5.1-instant",
        "fallbacks": [
            "google:gemini-2.5-flash-latest",
            "anthropic:claude-3.5-sonnet",
        ],
    },
    # ==== Test / latest spec alignment (updated) ====
    "creative": {
        "primary": "openai:gpt-5.1",
        "fallbacks": [
            "openai:gpt-5.1-instant",
            "google:gemini-2.5-pro-latest",
        ],
    },
    "analytical": {
        "primary": "google:gemini-2.5-pro-latest",
        "fallbacks": [
            "google:gemini-2.5-pro-latest",
            "openai:gpt-5.1-thinking",
        ],
    },
    "secure": {
        "primary": "anthropic:claude-3.5-sonnet",
        "fallbacks": [
            "openai:gpt-5.1-thinking",
            "google:gemini-2.5-pro-latest",
        ],
    },
    "general": {
        "primary": "google:gemini-2.5-flash-latest",
        "fallbacks": [
            "openai:gpt-5.1-instant",
        ],
    },
    "vc_analysis": {
        "primary": "anthropic:claude-3.5-sonnet",
        "fallbacks": [
            "openai:gpt-5.1-thinking",
            "google:gemini-2.5-pro-latest",
        ],
    },
    "npe_govern": {
        "primary": "openai:gpt-5.1-thinking",
        "fallbacks": [
            "anthropic:claude-3.5-sonnet",
            "google:gemini-2.5-pro-latest",
        ],
    },
}

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


def model_family(name: str) -> str:
    """Return provider family string based on a model identifier."""
    n = name.lower()
    if n in {"openai", "google", "anthropic", "deepseek", "kimi", "gemini", "local"}:
        return {"google": "gemini"}.get(n, n)
    if ":" in n:
        vendor, model = n.split(":", 1)
        if vendor in {"openai", "google", "anthropic", "deepseek", "kimi", "local"}:
            return {"google": "gemini"}.get(vendor, vendor)
        n = model
    if n.startswith(("gpt-", "o", "openai-")):
        return "openai"
    if n.startswith("gemini"):
        return "gemini"
    if n.startswith("deepseek"):
        return "deepseek"
    if n.startswith("kimi"):
        return "kimi"
    if n.startswith(("claude", "anthropic")):
        return "anthropic"
    if n.startswith(("llama", "local")):
        return "local"
    return "local"


def split_provider(model_name: str) -> tuple[str, str]:
    """Split 'vendor:model' into a tuple; fallback to inferred vendor."""
    if ":" in model_name:
        vendor, model = model_name.split(":", 1)
        return vendor.lower().strip(), model.strip()
    return model_family(model_name), model_name


__all__ = [
    "TASK_MODEL_MAP_DEFAULT",
    "LEGACY_TO_TASK",
    "model_family",
    "split_provider",
]
