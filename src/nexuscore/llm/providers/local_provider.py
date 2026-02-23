from __future__ import annotations

import json

from .base import BaseLLM


class LocalLLM(BaseLLM):
    """
    オフライン/テスト用の安全なダミーモデル。
    本当にお金を使いたくないときの最終フォールバック。
    (v2.3.2 から変更なし)
    """

    def execute(self, prompt: str, system_prompt: str, **kwargs) -> str:
        as_json = kwargs.get("as_json", False)
        preview = "LOCAL FALLBACK: この応答はスタブです。" "（本番APIコールは行われていません）"
        self.last_call_mode = "stub"
        if as_json:
            return json.dumps(
                {
                    "model": self.model_name,
                    "mode": "local-fallback",
                    "preview": preview,
                    "content": {
                        "summary": "Stubbed local response",
                        "plan": [
                            {
                                "step": "analyze_requirement",
                                "owner": "PlannerAgent",
                                "status": "pending",
                            },
                            {
                                "step": "implement_core_logic",
                                "owner": "CoderAgent",
                                "status": "blocked_stub",
                            },
                            {
                                "step": "write_tests",
                                "owner": "TesterAgent",
                                "status": "blocked_stub",
                            },
                        ],
                    },
                },
                ensure_ascii=False,
            )
        return preview


__all__ = ["LocalLLM"]
