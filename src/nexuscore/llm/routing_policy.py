"""
Routing policy utilities and task-model mappings for LLMRouter.
"""

from __future__ import annotations

from typing import Any

from nexuscore.llm.task_model_map import LEGACY_TO_TASK, build_task_model_map_dict

TASK_MODEL_MAP_DEFAULT: dict[str, dict[str, Any]] = build_task_model_map_dict()

_KNOWN_VENDORS = {
    "openai",
    "anthropic",
    "google",
    "deepseek",
    "glm",
    "minimax",
    "moonshot",
    "local",
}


def model_family(name: str) -> str:
    """Return provider family string based on a model identifier."""
    n = name.lower()
    if n in _KNOWN_VENDORS:
        return n
    if ":" in n:
        vendor, model = n.split(":", 1)
        if vendor in _KNOWN_VENDORS:
            return vendor
        n = model
    if n.startswith(("gpt-", "o1-", "o3-", "o4-")):
        return "openai"
    if n.startswith("claude"):
        return "anthropic"
    if n.startswith("gemini"):
        return "google"
    if n.startswith("deepseek"):
        return "deepseek"
    if n.startswith(("glm-", "chatglm")):
        return "glm"
    if n.startswith("minimax"):
        return "minimax"
    if n.startswith("moonshot"):
        return "moonshot"
    return "glm"


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
