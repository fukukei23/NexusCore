"""
Utility for LLM task classification prompts.
"""

from __future__ import annotations

import json
from typing import Any


def build_classify_prompt(prompt: str, allowed_task_types: dict[str, object]) -> tuple[str, str]:
    allowed = ",".join(allowed_task_types.keys())
    system_prompt = (
        "You are a task classifier. "
        "Return ONLY valid JSON: "
        '{"task_type":"<one of [' + allowed + ']>"}.\n'
        "If unsure, respond with general."
    )
    classify_prompt = (
        "Classify this developer request:\n" f"{prompt}\n\n" "Which task type best matches?"
    )
    return classify_prompt, system_prompt


class TaskClassifier:
    """Wrapper around an LLM client used for task classification."""

    def __init__(self, model_name: str, client: Any):
        self.model_name = model_name
        self.client = client

    def classify(self, prompt: str, task_model_map: dict[str, object]) -> str:
        classify_prompt, system_prompt = build_classify_prompt(prompt, task_model_map)
        raw = self.client.execute(
            classify_prompt,
            system_prompt=system_prompt,
            as_json=True,
            temperature=0.0,
        )
        data = json.loads(raw)
        return str(data.get("task_type", "general")).strip().lower()


__all__ = ["TaskClassifier", "build_classify_prompt"]
