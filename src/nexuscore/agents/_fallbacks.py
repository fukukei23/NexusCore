from __future__ import annotations

import logging

try:
    from .base_agent import BaseAgent
except ImportError:
    class BaseAgent:  # type: ignore[no-redef]
        """Fallback when base_agent is not importable."""

        def __init__(self, *args, **kwargs):
            self.logger = logging.getLogger(self.__class__.__name__)

        def execute_llm_task(self, prompt: str, as_json: bool = False) -> str:
            return ""

        def _call_llm(self, prompt: str, system_prompt: str, as_json: bool = False) -> str:
            return self.execute_llm_task(prompt, as_json)
