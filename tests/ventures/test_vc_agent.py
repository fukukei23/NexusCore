import json
from typing import Any

from nexuscore.ventures.vc_agent import VentureCapitalistAgent


class DummySearch:
    def __init__(self, responses: list[list[dict[str, Any]]]):
        self.responses = responses
        self.index = 0

    def search(self, queries: list[str]):
        resp = self.responses[self.index]
        self.index += 1
        return resp


class DummyLLM:
    def __init__(self, response: str):
        self.response = response
        self.prompts = []

    def invoke(self, prompt: str, **kwargs):
        self.prompts.append(prompt)
        return self.response


def test_build_prompt_contains_trends():
    llm = DummyLLM("{}")
    agent = VentureCapitalistAgent(llm_client=llm, tools={"Google Search": DummySearch([[]])})
    trends = [{"title": "Trend", "snippet": "Snippet"}]
    prompt = agent._build_prompt(trends)
    assert "Trend" in prompt
    assert "ventureName" in prompt


def test_parse_memo_validates_fields():
    llm = DummyLLM("{}")
    agent = VentureCapitalistAgent(llm_client=llm, tools={"Google Search": DummySearch([[]])})
    memo = {
        "ventureName": "X",
        "marketAnalysis": "A",
        "productThesis": "B",
        "strategicFit": "C",
        "resourceRequest": "D",
        "projectedROI": "E",
    }
    parsed = agent._parse_memo(json.dumps(memo))
    assert parsed["ventureName"] == "X"


def test_search_retry_and_summarize(monkeypatch):
    llm = DummyLLM("{}")
    DummySearch([Exception("fail"), [{"title": "t1", "snippet": "s1"}]])

    class RetrySearch:
        def __init__(self):
            self.calls = 0

        def search(self, queries):
            self.calls += 1
            if self.calls == 1:
                raise RuntimeError("fail")
            return [{"title": "t1", "snippet": "s1"}]

    agent = VentureCapitalistAgent(llm_client=llm, tools={"Google Search": RetrySearch()})
    results = agent._search_with_retry(["test"], retries=1, delay=0)
    assert results

    summary = agent._summarize_trends(results)
    assert summary[0]["title"] == "t1"


def test_scout_for_opportunities_handles_failure(monkeypatch):
    class FailLLM:
        def invoke(self, prompt, **kwargs):
            return "not-json"

    agent = VentureCapitalistAgent(
        llm_client=FailLLM(),
        tools={"Google Search": DummySearch([[{"title": "t", "snippet": "s"}]])},
    )
    memo = agent.scout_for_opportunities()
    assert memo is None
