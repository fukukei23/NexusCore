from __future__ import annotations

import json
import logging
import uuid
from typing import Any

_logger = logging.getLogger(__name__)

try:
    from ..utils.json_sanitizer import sanitize_json_like
except ImportError:
    def sanitize_json_like(payload: Any) -> Any:  # type: ignore[misc]
        return payload

from ._fallbacks import BaseAgent


class RequirementAgent(BaseAgent):
    def __init__(self, language: str = "ja"):
        super().__init__()
        self.language = language
        self.final_requirements: dict[str, Any] | None = None
        self._initial_requirement: str = ""

    def _get_initial_state(self) -> dict[str, Any]:
        return {"session_id": str(uuid.uuid4()), "history": [], "state": "INIT"}

    def generate_final_spec(self, history: list[dict]) -> dict[str, Any]:
        last_user_msg = next(
            (h["content"] for h in reversed(history) if h["role"] == "user"), "No user input."
        )
        return {"summary": "Final Specification", "details": last_user_msg}

    def set_initial_requirement(self, requirement: str) -> None:
        self._initial_requirement = requirement

    def analyze_requirement(self, requirement: str) -> dict[str, Any]:
        requirement = requirement.strip() or self._initial_requirement or "No requirement provided."
        prompt = f"""
You are a requirements analyst. Convert the user's request into a concise JSON specification.

# User Requirement
{requirement}

# Output JSON schema
{{
  "summary": "<overall goal>",
  "features": ["<feature1>", "<feature2>"],
  "constraints": ["<constraint>", "..."],
  "acceptance_criteria": ["<criteria>", "..."]
}}

Ensure the response is strictly valid JSON with filled arrays (no empty strings).
"""
        response = self.execute_llm_task(prompt, as_json=True)
        try:
            data = sanitize_json_like(json.loads(response))
        except Exception:
            data = {
                "summary": requirement[:80],
                "features": ["Auto-generated draft feature list"],
                "constraints": [],
                "acceptance_criteria": [],
            }
        self.final_requirements = data  # type: ignore[assignment]
        return data  # type: ignore[return-value]
