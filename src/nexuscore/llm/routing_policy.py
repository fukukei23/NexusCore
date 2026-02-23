"""
Routing policy utilities and task-model mappings for LLMRouter.
"""

from __future__ import annotations

from typing import Any

from nexuscore.llm.task_model_map import LEGACY_TO_TASK, build_task_model_map_dict

TASK_MODEL_MAP_DEFAULT: dict[str, dict[str, Any]] = build_task_model_map_dict()


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
