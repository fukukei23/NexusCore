# nexuscore/ventures/vc_agent.py
from __future__ import annotations

import json
import logging
import time
import uuid
from typing import Any, Protocol, TypedDict

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class SearchTool(Protocol):
    def search(self, queries: list[str]) -> list[dict[str, Any]]: ...


class LLMClient(Protocol):
    def invoke(self, prompt: str, **kwargs) -> str: ...


class InvestmentMemo(TypedDict):
    ventureName: str
    marketAnalysis: str
    productThesis: str
    strategicFit: str
    resourceRequest: str
    projectedROI: str


INVESTMENT_MEMO_KEYS = {
    "ventureName",
    "marketAnalysis",
    "productThesis",
    "strategicFit",
    "resourceRequest",
    "projectedROI",
}


class VentureCapitalistAgent:
    def __init__(self, llm_client: LLMClient, tools: dict[str, Any]):
        self.llm_client = llm_client
        self.market_scanner: SearchTool = tools.get("Google Search")  # type: ignore[assignment]
        if self.market_scanner is None:
            raise ValueError("Google Search tool is required")
        self.run_id = str(uuid.uuid4())

    def _search_with_retry(self, queries: list[str], retries: int = 2, delay: float = 0.8):
        last_err = None
        for attempt in range(retries + 1):
            try:
                t0 = time.time()
                res = self.market_scanner.search(queries=queries)
                logger.info(
                    {
                        "event": "search_ok",
                        "run_id": self.run_id,
                        "attempt": attempt,
                        "latency_ms": int((time.time() - t0) * 1000),
                    }
                )
                return res or []
            except Exception as e:
                last_err = e
                logger.warning(
                    {
                        "event": "search_fail",
                        "run_id": self.run_id,
                        "attempt": attempt,
                        "error": str(e),
                    }
                )
                time.sleep(delay * (2**attempt))
        raise RuntimeError(f"Search failed after retries: {last_err}")

    def _summarize_trends(
        self, items: list[dict[str, Any]], top_k: int = 10
    ) -> list[dict[str, Any]]:
        uniq = []
        seen = set()
        for it in items:
            t = (it.get("title") or "")[:160]
            if t and t not in seen:
                uniq.append(
                    {
                        "title": t,
                        "snippet": (it.get("snippet") or "")[:300],
                        "url": it.get("url", ""),
                    }
                )
                seen.add(t)
            if len(uniq) >= top_k:
                break
        return uniq

    def _build_prompt(self, trends: list[dict[str, Any]]) -> str:
        schema = {
            "type": "object",
            "required": list(INVESTMENT_MEMO_KEYS),
            "properties": {k: {"type": "string"} for k in INVESTMENT_MEMO_KEYS},
        }
        return f"""
You are a venture capitalist AI generating a single high-potential AI venture idea.
Output MUST be valid JSON only. No prose.

Context (trend snippets, sanitized):
{json.dumps(trends, ensure_ascii=False, indent=2)}

Constraints:
- Language: English.
- Keep each field under 120 words.
- No URLs, emails, or PII in the output.
- Be concrete, avoid buzzwords.
- Projected ROI: include timeframe (e.g., "3-year 8-12x").

JSON Schema (informal):
{json.dumps(schema, indent=2)}

Fields:
- ventureName
- marketAnalysis
- productThesis
- strategicFit
- resourceRequest
- projectedROI
""".strip()

    def _parse_memo(self, text: str) -> InvestmentMemo:
        def try_parse(s: str) -> dict[str, Any] | None:
            try:
                return json.loads(s)
            except Exception:
                return None

        data = try_parse(text)
        if data is None:
            start, end = text.find("{"), text.rfind("}")
            if start != -1 and end != -1 and end > start:
                data = try_parse(text[start : end + 1])
        if not isinstance(data, dict):
            raise ValueError("LLM did not return a JSON object")
        missing = INVESTMENT_MEMO_KEYS - set(data.keys())
        if missing:
            raise ValueError(f"Missing keys in memo: {missing}")
        return {k: str(data.get(k, "")).strip() for k in INVESTMENT_MEMO_KEYS}  # type: ignore

    def scout_for_opportunities(self) -> InvestmentMemo | None:
        logger.info({"event": "vc_scan_start", "run_id": self.run_id})
        queries = [
            "new ai applications healthcare trends 2025",
            "open source ai projects github trending",
            "y combinator request for startups 2025",
        ]
        trends_raw = self._search_with_retry(queries)
        trends = self._summarize_trends(trends_raw, top_k=8)
        prompt = self._build_prompt(trends)

        try:
            response = self.llm_client.invoke(prompt, temperature=0.2, max_tokens=800)
            memo = self._parse_memo(response)
            logger.info({"event": "vc_memo_ok", "run_id": self.run_id})
            print("--- Investment Memo ---")
            print(json.dumps(memo, indent=2, ensure_ascii=False))
            print("-----------------------")
            return memo
        except Exception as e:
            logger.error({"event": "vc_memo_fail", "run_id": self.run_id, "error": str(e)})
            print(f"VC Agent: Failed to formulate a valid investment memo. Error: {e}")
            return None

    def trigger_self_clone(self, venture_name: str, initial_policy: dict[str, Any]):
        if not initial_policy.get("approved_by_human"):
            raise PermissionError("Self-clone requires human approval (approved_by_human=True).")
        sandbox_id = f"{venture_name.lower().replace(' ', '-')}-{self.run_id[:8]}"
        logger.info(
            {
                "event": "vc_self_clone",
                "run_id": self.run_id,
                "venture": venture_name,
                "sandbox_id": sandbox_id,
            }
        )
        print(f"VC Agent: Proposal for '{venture_name}' approved.")
        print("Initiating self-replication protocol...")
        # TODO: 実際のクローン処理をここに実装
        print(f"New sandboxed environment '{sandbox_id}' created.")
        print("A new CEO Agent has been instantiated with its first mission.")
        print(f"Congratulations on the birth of a new company: {venture_name}!")
