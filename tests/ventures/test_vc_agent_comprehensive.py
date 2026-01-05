"""
Comprehensive tests for nexuscore.ventures.vc_agent module.

This test suite achieves 2.0x+ test coverage by thoroughly testing:
- Initialization and configuration
- Search retry logic with exponential backoff
- Trend summarization with deduplication
- Prompt building with schema validation
- JSON parsing with multiple formats
- End-to-end scouting workflow
- Self-cloning with permission control
- Error handling and edge cases
- Logging and telemetry
"""
import json
import logging
import time
import uuid
from typing import Any, Dict, List
from unittest.mock import MagicMock, Mock, patch

import pytest

from nexuscore.ventures.vc_agent import (
    INVESTMENT_MEMO_KEYS,
    InvestmentMemo,
    LLMClient,
    SearchTool,
    VentureCapitalistAgent,
)


# =============================================================================
# Mock Classes and Fixtures
# =============================================================================


class MockSearchTool:
    """Mock search tool for testing."""

    def __init__(self, responses: List[List[Dict[str, Any]]] = None, raise_error: bool = False):
        self.responses = responses or [[]]
        self.index = 0
        self.raise_error = raise_error
        self.call_count = 0
        self.queries_received: List[List[str]] = []

    def search(self, queries: List[str]) -> List[Dict[str, Any]]:
        self.call_count += 1
        self.queries_received.append(queries)

        if self.raise_error:
            raise RuntimeError("Search API failure")

        if self.index >= len(self.responses):
            return []

        resp = self.responses[self.index]
        self.index += 1
        return resp


class MockLLMClient:
    """Mock LLM client for testing."""

    def __init__(self, response: str = "", raise_error: bool = False):
        self.response = response
        self.raise_error = raise_error
        self.prompts: List[str] = []
        self.kwargs_history: List[Dict[str, Any]] = []

    def invoke(self, prompt: str, **kwargs) -> str:
        self.prompts.append(prompt)
        self.kwargs_history.append(kwargs)

        if self.raise_error:
            raise RuntimeError("LLM API failure")

        return self.response


@pytest.fixture
def valid_memo_json() -> str:
    """Valid investment memo JSON."""
    return json.dumps({
        "ventureName": "AI Health Monitor",
        "marketAnalysis": "Growing healthcare AI market with $10B TAM.",
        "productThesis": "Real-time health monitoring using wearable AI.",
        "strategicFit": "Aligns with our AI-first investment strategy.",
        "resourceRequest": "$2M seed funding, 3 engineers, 18 months.",
        "projectedROI": "3-year 10-15x return on investment.",
    })


@pytest.fixture
def partial_memo_json() -> str:
    """Memo JSON missing required fields."""
    return json.dumps({
        "ventureName": "Incomplete Venture",
        "marketAnalysis": "Some analysis",
    })


@pytest.fixture
def search_results() -> List[Dict[str, Any]]:
    """Sample search results."""
    return [
        {
            "title": "AI Healthcare Trends 2025",
            "snippet": "Healthcare AI is expected to reach $10B by 2025...",
            "url": "https://example.com/1"
        },
        {
            "title": "Top AI Startups",
            "snippet": "These AI startups are leading the innovation...",
            "url": "https://example.com/2"
        },
        {
            "title": "YC Request for Startups",
            "snippet": "Y Combinator is looking for AI healthcare solutions...",
            "url": "https://example.com/3"
        },
    ]


# =============================================================================
# Test: Initialization
# =============================================================================


class TestVCAgentInitialization:
    """Test VentureCapitalistAgent initialization."""

    def test_init_success_with_google_search(self):
        """Test successful initialization with Google Search tool."""
        llm = MockLLMClient()
        search = MockSearchTool()

        agent = VentureCapitalistAgent(
            llm_client=llm,
            tools={"Google Search": search}
        )

        assert agent.llm_client is llm
        assert agent.market_scanner is search
        assert isinstance(agent.run_id, str)
        assert len(agent.run_id) == 36  # UUID length

    def test_init_raises_value_error_when_google_search_missing(self):
        """Test initialization fails when Google Search tool is missing."""
        llm = MockLLMClient()

        with pytest.raises(ValueError, match="Google Search tool is required"):
            VentureCapitalistAgent(llm_client=llm, tools={})

        with pytest.raises(ValueError, match="Google Search tool is required"):
            VentureCapitalistAgent(llm_client=llm, tools={"Other Tool": MockSearchTool()})

    def test_init_generates_unique_run_ids(self):
        """Test that each agent gets a unique run_id."""
        llm = MockLLMClient()
        search = MockSearchTool()

        agent1 = VentureCapitalistAgent(llm_client=llm, tools={"Google Search": search})
        agent2 = VentureCapitalistAgent(llm_client=llm, tools={"Google Search": search})

        assert agent1.run_id != agent2.run_id


# =============================================================================
# Test: Search with Retry
# =============================================================================


class TestSearchWithRetry:
    """Test _search_with_retry method."""

    def test_search_success_on_first_attempt(self, search_results):
        """Test search succeeds on first attempt."""
        llm = MockLLMClient()
        search = MockSearchTool(responses=[search_results])
        agent = VentureCapitalistAgent(llm_client=llm, tools={"Google Search": search})

        result = agent._search_with_retry(["test query"])

        assert result == search_results
        assert search.call_count == 1

    def test_search_retry_on_failure_then_success(self, search_results):
        """Test search retries on failure then succeeds."""
        llm = MockLLMClient()

        # First call fails, second succeeds
        class RetrySearch:
            def __init__(self):
                self.call_count = 0

            def search(self, queries):
                self.call_count += 1
                if self.call_count == 1:
                    raise RuntimeError("Temporary failure")
                return search_results

        retry_search = RetrySearch()
        agent = VentureCapitalistAgent(llm_client=llm, tools={"Google Search": retry_search})

        result = agent._search_with_retry(["test"], retries=2, delay=0.01)

        assert result == search_results
        assert retry_search.call_count == 2

    def test_search_exhausts_all_retries_then_raises(self):
        """Test search raises error after all retries exhausted."""
        llm = MockLLMClient()
        search = MockSearchTool(raise_error=True)
        agent = VentureCapitalistAgent(llm_client=llm, tools={"Google Search": search})

        with pytest.raises(RuntimeError, match="Search failed after retries"):
            agent._search_with_retry(["test"], retries=2, delay=0.01)

        assert search.call_count == 3  # Initial + 2 retries

    def test_search_returns_empty_list_when_result_is_none(self):
        """Test search returns empty list when scanner returns None."""
        llm = MockLLMClient()

        class NoneSearch:
            def search(self, queries):
                return None

        agent = VentureCapitalistAgent(llm_client=llm, tools={"Google Search": NoneSearch()})

        result = agent._search_with_retry(["test"])

        assert result == []

    @patch('time.sleep')
    def test_search_exponential_backoff(self, mock_sleep):
        """Test exponential backoff delay between retries."""
        llm = MockLLMClient()

        class AlwaysFailSearch:
            def search(self, queries):
                raise RuntimeError("Always fails")

        agent = VentureCapitalistAgent(llm_client=llm, tools={"Google Search": AlwaysFailSearch()})

        with pytest.raises(RuntimeError):
            agent._search_with_retry(["test"], retries=2, delay=0.5)

        # Check exponential backoff: delay * (2^0), delay * (2^1), delay * (2^2)
        # With retries=2, there are 3 total attempts (initial + 2 retries) = 3 sleep calls
        assert mock_sleep.call_count == 3
        mock_sleep.assert_any_call(0.5)  # First retry: 0.5 * 2^0
        mock_sleep.assert_any_call(1.0)  # Second retry: 0.5 * 2^1
        mock_sleep.assert_any_call(2.0)  # Third retry: 0.5 * 2^2


# =============================================================================
# Test: Summarize Trends
# =============================================================================


class TestSummarizeTrends:
    """Test _summarize_trends method."""

    def test_summarize_basic_deduplication(self):
        """Test trend summarization with basic deduplication."""
        llm = MockLLMClient()
        search = MockSearchTool()
        agent = VentureCapitalistAgent(llm_client=llm, tools={"Google Search": search})

        items = [
            {"title": "Trend 1", "snippet": "Snippet 1", "url": "https://ex.com/1"},
            {"title": "Trend 1", "snippet": "Snippet 2", "url": "https://ex.com/2"},  # Duplicate
            {"title": "Trend 2", "snippet": "Snippet 3", "url": "https://ex.com/3"},
        ]

        result = agent._summarize_trends(items)

        assert len(result) == 2
        assert result[0]["title"] == "Trend 1"
        assert result[1]["title"] == "Trend 2"

    def test_summarize_respects_top_k_limit(self):
        """Test that only top_k items are returned."""
        llm = MockLLMClient()
        search = MockSearchTool()
        agent = VentureCapitalistAgent(llm_client=llm, tools={"Google Search": search})

        items = [{"title": f"Trend {i}", "snippet": f"Snippet {i}", "url": f"url{i}"}
                 for i in range(20)]

        result = agent._summarize_trends(items, top_k=5)

        assert len(result) == 5

    def test_summarize_truncates_long_titles(self):
        """Test that titles longer than 160 chars are truncated."""
        llm = MockLLMClient()
        search = MockSearchTool()
        agent = VentureCapitalistAgent(llm_client=llm, tools={"Google Search": search})

        long_title = "A" * 200
        items = [{"title": long_title, "snippet": "Short", "url": "url"}]

        result = agent._summarize_trends(items)

        assert len(result[0]["title"]) == 160

    def test_summarize_truncates_long_snippets(self):
        """Test that snippets longer than 300 chars are truncated."""
        llm = MockLLMClient()
        search = MockSearchTool()
        agent = VentureCapitalistAgent(llm_client=llm, tools={"Google Search": search})

        long_snippet = "B" * 400
        items = [{"title": "Title", "snippet": long_snippet, "url": "url"}]

        result = agent._summarize_trends(items)

        assert len(result[0]["snippet"]) == 300

    def test_summarize_handles_empty_list(self):
        """Test summarizing empty list returns empty result."""
        llm = MockLLMClient()
        search = MockSearchTool()
        agent = VentureCapitalistAgent(llm_client=llm, tools={"Google Search": search})

        result = agent._summarize_trends([])

        assert result == []

    def test_summarize_skips_items_with_empty_title(self):
        """Test items with None or empty title are skipped."""
        llm = MockLLMClient()
        search = MockSearchTool()
        agent = VentureCapitalistAgent(llm_client=llm, tools={"Google Search": search})

        items = [
            {"title": None, "snippet": "Snippet 1"},
            {"title": "", "snippet": "Snippet 2"},
            {"title": "Valid", "snippet": "Snippet 3"},
        ]

        result = agent._summarize_trends(items)

        assert len(result) == 1
        assert result[0]["title"] == "Valid"

    def test_summarize_handles_missing_fields(self):
        """Test items with missing snippet or url use defaults."""
        llm = MockLLMClient()
        search = MockSearchTool()
        agent = VentureCapitalistAgent(llm_client=llm, tools={"Google Search": search})

        items = [{"title": "Title Only"}]

        result = agent._summarize_trends(items)

        assert result[0]["snippet"] == ""
        assert result[0]["url"] == ""


# =============================================================================
# Test: Build Prompt
# =============================================================================


class TestBuildPrompt:
    """Test _build_prompt method."""

    def test_build_prompt_contains_all_required_fields(self):
        """Test that prompt contains all memo fields."""
        llm = MockLLMClient()
        search = MockSearchTool()
        agent = VentureCapitalistAgent(llm_client=llm, tools={"Google Search": search})

        trends = [{"title": "Test", "snippet": "Snippet"}]
        prompt = agent._build_prompt(trends)

        for key in INVESTMENT_MEMO_KEYS:
            assert key in prompt

    def test_build_prompt_includes_trends_data(self):
        """Test that trends data is embedded in prompt."""
        llm = MockLLMClient()
        search = MockSearchTool()
        agent = VentureCapitalistAgent(llm_client=llm, tools={"Google Search": search})

        trends = [{"title": "Unique Title 123", "snippet": "Unique Snippet 456"}]
        prompt = agent._build_prompt(trends)

        assert "Unique Title 123" in prompt
        assert "Unique Snippet 456" in prompt

    def test_build_prompt_includes_constraints(self):
        """Test that prompt includes all constraints."""
        llm = MockLLMClient()
        search = MockSearchTool()
        agent = VentureCapitalistAgent(llm_client=llm, tools={"Google Search": search})

        prompt = agent._build_prompt([])

        assert "English" in prompt
        assert "120 words" in prompt
        assert "No URLs" in prompt
        assert "Projected ROI" in prompt
        assert "3-year" in prompt


# =============================================================================
# Test: Parse Memo
# =============================================================================


class TestParseMemo:
    """Test _parse_memo method."""

    def test_parse_valid_json(self, valid_memo_json):
        """Test parsing valid memo JSON."""
        llm = MockLLMClient()
        search = MockSearchTool()
        agent = VentureCapitalistAgent(llm_client=llm, tools={"Google Search": search})

        memo = agent._parse_memo(valid_memo_json)

        assert memo["ventureName"] == "AI Health Monitor"
        assert memo["marketAnalysis"] == "Growing healthcare AI market with $10B TAM."
        assert len(memo) == 6

    def test_parse_json_with_surrounding_text(self, valid_memo_json):
        """Test parsing JSON embedded in text."""
        llm = MockLLMClient()
        search = MockSearchTool()
        agent = VentureCapitalistAgent(llm_client=llm, tools={"Google Search": search})

        text_with_json = f"Here is the memo:\n{valid_memo_json}\n\nEnd of memo."

        memo = agent._parse_memo(text_with_json)

        assert memo["ventureName"] == "AI Health Monitor"

    def test_parse_raises_error_on_invalid_json(self):
        """Test parsing invalid JSON raises ValueError."""
        llm = MockLLMClient()
        search = MockSearchTool()
        agent = VentureCapitalistAgent(llm_client=llm, tools={"Google Search": search})

        with pytest.raises(ValueError, match="did not return a JSON object"):
            agent._parse_memo("not json at all")

    def test_parse_raises_error_on_missing_keys(self, partial_memo_json):
        """Test parsing memo with missing keys raises ValueError."""
        llm = MockLLMClient()
        search = MockSearchTool()
        agent = VentureCapitalistAgent(llm_client=llm, tools={"Google Search": search})

        with pytest.raises(ValueError, match="Missing keys"):
            agent._parse_memo(partial_memo_json)

    def test_parse_strips_whitespace_from_fields(self):
        """Test that field values are stripped of whitespace."""
        llm = MockLLMClient()
        search = MockSearchTool()
        agent = VentureCapitalistAgent(llm_client=llm, tools={"Google Search": search})

        memo_with_spaces = json.dumps({
            "ventureName": "  Spacey Name  ",
            "marketAnalysis": "\n\nAnalysis\n\n",
            "productThesis": "\tThesis\t",
            "strategicFit": "  Fit  ",
            "resourceRequest": " Request ",
            "projectedROI": "  ROI  ",
        })

        memo = agent._parse_memo(memo_with_spaces)

        assert memo["ventureName"] == "Spacey Name"
        assert memo["marketAnalysis"] == "Analysis"

    def test_parse_converts_all_values_to_strings(self):
        """Test that all memo values are converted to strings."""
        llm = MockLLMClient()
        search = MockSearchTool()
        agent = VentureCapitalistAgent(llm_client=llm, tools={"Google Search": search})

        memo_with_numbers = json.dumps({
            "ventureName": 12345,
            "marketAnalysis": "Analysis",
            "productThesis": True,
            "strategicFit": ["item1", "item2"],
            "resourceRequest": None,
            "projectedROI": 3.14,
        })

        memo = agent._parse_memo(memo_with_numbers)

        assert isinstance(memo["ventureName"], str)
        assert isinstance(memo["productThesis"], str)
        assert isinstance(memo["projectedROI"], str)


# =============================================================================
# Test: Scout for Opportunities
# =============================================================================


class TestScoutForOpportunities:
    """Test scout_for_opportunities method."""

    def test_scout_success_end_to_end(self, search_results, valid_memo_json):
        """Test successful end-to-end scouting workflow."""
        llm = MockLLMClient(response=valid_memo_json)
        search = MockSearchTool(responses=[search_results])
        agent = VentureCapitalistAgent(llm_client=llm, tools={"Google Search": search})

        memo = agent.scout_for_opportunities()

        assert memo is not None
        assert memo["ventureName"] == "AI Health Monitor"
        assert search.call_count == 1
        assert len(llm.prompts) == 1

    def test_scout_returns_none_on_llm_failure(self, search_results):
        """Test scout returns None when LLM fails."""
        llm = MockLLMClient(raise_error=True)
        search = MockSearchTool(responses=[search_results])
        agent = VentureCapitalistAgent(llm_client=llm, tools={"Google Search": search})

        memo = agent.scout_for_opportunities()

        assert memo is None

    def test_scout_returns_none_on_invalid_memo(self, search_results):
        """Test scout returns None when LLM returns invalid memo."""
        llm = MockLLMClient(response="invalid json")
        search = MockSearchTool(responses=[search_results])
        agent = VentureCapitalistAgent(llm_client=llm, tools={"Google Search": search})

        memo = agent.scout_for_opportunities()

        assert memo is None

    def test_scout_passes_correct_llm_params(self, search_results, valid_memo_json):
        """Test scout passes temperature and max_tokens to LLM."""
        llm = MockLLMClient(response=valid_memo_json)
        search = MockSearchTool(responses=[search_results])
        agent = VentureCapitalistAgent(llm_client=llm, tools={"Google Search": search})

        agent.scout_for_opportunities()

        assert len(llm.kwargs_history) == 1
        assert llm.kwargs_history[0]["temperature"] == 0.2
        assert llm.kwargs_history[0]["max_tokens"] == 800

    def test_scout_uses_correct_search_queries(self, search_results, valid_memo_json):
        """Test scout uses expected search queries."""
        llm = MockLLMClient(response=valid_memo_json)
        search = MockSearchTool(responses=[search_results])
        agent = VentureCapitalistAgent(llm_client=llm, tools={"Google Search": search})

        agent.scout_for_opportunities()

        assert len(search.queries_received) == 1
        queries = search.queries_received[0]
        assert "healthcare" in queries[0].lower()
        assert "github" in queries[1].lower()
        assert "y combinator" in queries[2].lower()

    def test_scout_limits_trends_to_top_8(self, valid_memo_json):
        """Test scout limits trends to top 8 items."""
        llm = MockLLMClient(response=valid_memo_json)
        many_results = [{"title": f"T{i}", "snippet": f"S{i}", "url": f"U{i}"} for i in range(20)]
        search = MockSearchTool(responses=[many_results])
        agent = VentureCapitalistAgent(llm_client=llm, tools={"Google Search": search})

        agent.scout_for_opportunities()

        # Check that prompt includes max 8 trends
        prompt = llm.prompts[0]
        trend_count = prompt.count('"title":')
        assert trend_count <= 8


# =============================================================================
# Test: Trigger Self-Clone
# =============================================================================


class TestTriggerSelfClone:
    """Test trigger_self_clone method."""

    def test_self_clone_success_with_approval(self):
        """Test self-clone succeeds with human approval."""
        llm = MockLLMClient()
        search = MockSearchTool()
        agent = VentureCapitalistAgent(llm_client=llm, tools={"Google Search": search})

        policy = {"approved_by_human": True}

        # Should not raise
        agent.trigger_self_clone("AI Startup", policy)

    def test_self_clone_raises_permission_error_without_approval(self):
        """Test self-clone raises PermissionError without approval."""
        llm = MockLLMClient()
        search = MockSearchTool()
        agent = VentureCapitalistAgent(llm_client=llm, tools={"Google Search": search})

        policy = {"approved_by_human": False}

        with pytest.raises(PermissionError, match="human approval"):
            agent.trigger_self_clone("AI Startup", policy)

    def test_self_clone_raises_permission_error_when_key_missing(self):
        """Test self-clone raises PermissionError when approval key missing."""
        llm = MockLLMClient()
        search = MockSearchTool()
        agent = VentureCapitalistAgent(llm_client=llm, tools={"Google Search": search})

        policy = {}

        with pytest.raises(PermissionError, match="human approval"):
            agent.trigger_self_clone("AI Startup", policy)

    def test_self_clone_generates_sandbox_id(self):
        """Test self-clone generates sandbox ID from venture name."""
        llm = MockLLMClient()
        search = MockSearchTool()
        agent = VentureCapitalistAgent(llm_client=llm, tools={"Google Search": search})

        policy = {"approved_by_human": True}

        # Capture logging to verify sandbox_id format
        with patch('nexuscore.ventures.vc_agent.logger') as mock_logger:
            agent.trigger_self_clone("Test Venture Name", policy)

            assert mock_logger.info.called
            call_args = mock_logger.info.call_args[0][0]
            assert "sandbox_id" in call_args
            assert "test-venture-name" in call_args["sandbox_id"]


# =============================================================================
# Test: Logging and Telemetry
# =============================================================================


class TestLoggingAndTelemetry:
    """Test logging behavior."""

    def test_search_logs_success_with_latency(self, search_results):
        """Test search logs success with latency metrics."""
        llm = MockLLMClient()
        search = MockSearchTool(responses=[search_results])
        agent = VentureCapitalistAgent(llm_client=llm, tools={"Google Search": search})

        with patch('nexuscore.ventures.vc_agent.logger') as mock_logger:
            agent._search_with_retry(["test"])

            assert mock_logger.info.called
            log_data = mock_logger.info.call_args[0][0]
            assert log_data["event"] == "search_ok"
            assert "latency_ms" in log_data

    def test_search_logs_failure_on_retry(self):
        """Test search logs warning on retry attempts."""
        llm = MockLLMClient()

        class FailThenSucceed:
            def __init__(self):
                self.count = 0

            def search(self, queries):
                self.count += 1
                if self.count == 1:
                    raise RuntimeError("First fail")
                return []

        agent = VentureCapitalistAgent(llm_client=llm, tools={"Google Search": FailThenSucceed()})

        with patch('nexuscore.ventures.vc_agent.logger') as mock_logger:
            agent._search_with_retry(["test"], retries=1, delay=0.01)

            assert mock_logger.warning.called

    def test_scout_logs_start_and_success(self, search_results, valid_memo_json):
        """Test scout logs start and success events."""
        llm = MockLLMClient(response=valid_memo_json)
        search = MockSearchTool(responses=[search_results])
        agent = VentureCapitalistAgent(llm_client=llm, tools={"Google Search": search})

        with patch('nexuscore.ventures.vc_agent.logger') as mock_logger:
            agent.scout_for_opportunities()

            # Check for start and success logs
            calls = [call[0][0] for call in mock_logger.info.call_args_list]
            events = [c.get("event") for c in calls if isinstance(c, dict)]

            assert "vc_scan_start" in events
            assert "vc_memo_ok" in events

    def test_scout_logs_error_on_failure(self, search_results):
        """Test scout logs error event on failure."""
        llm = MockLLMClient(response="invalid")
        search = MockSearchTool(responses=[search_results])
        agent = VentureCapitalistAgent(llm_client=llm, tools={"Google Search": search})

        with patch('nexuscore.ventures.vc_agent.logger') as mock_logger:
            agent.scout_for_opportunities()

            assert mock_logger.error.called
            log_data = mock_logger.error.call_args[0][0]
            assert log_data["event"] == "vc_memo_fail"


# =============================================================================
# Test: Edge Cases and Integration
# =============================================================================


class TestEdgeCasesAndIntegration:
    """Test edge cases and integration scenarios."""

    def test_agent_handles_empty_search_results(self, valid_memo_json):
        """Test agent handles empty search results gracefully."""
        llm = MockLLMClient(response=valid_memo_json)
        search = MockSearchTool(responses=[[]])
        agent = VentureCapitalistAgent(llm_client=llm, tools={"Google Search": search})

        memo = agent.scout_for_opportunities()

        assert memo is not None  # Should still generate memo with empty trends

    def test_agent_handles_unicode_in_trends(self):
        """Test agent handles Unicode characters in trends."""
        llm = MockLLMClient(response=json.dumps({
            "ventureName": "日本AI",
            "marketAnalysis": "市場分析",
            "productThesis": "製品thesis",
            "strategicFit": "戦略fit",
            "resourceRequest": "リソース",
            "projectedROI": "ROI予測",
        }))
        trends = [{"title": "日本のAIトレンド", "snippet": "概要"}]
        search = MockSearchTool(responses=[trends])
        agent = VentureCapitalistAgent(llm_client=llm, tools={"Google Search": search})

        memo = agent.scout_for_opportunities()

        assert memo is not None
        assert "日本AI" in memo["ventureName"]

    def test_agent_run_id_is_valid_uuid(self):
        """Test agent run_id is a valid UUID."""
        llm = MockLLMClient()
        search = MockSearchTool()
        agent = VentureCapitalistAgent(llm_client=llm, tools={"Google Search": search})

        # Should not raise
        uuid.UUID(agent.run_id)

    def test_memo_keys_constant_matches_typeddict(self):
        """Test INVESTMENT_MEMO_KEYS matches InvestmentMemo TypedDict."""
        expected_keys = {"ventureName", "marketAnalysis", "productThesis",
                        "strategicFit", "resourceRequest", "projectedROI"}

        assert INVESTMENT_MEMO_KEYS == expected_keys

    def test_protocol_classes_define_expected_methods(self):
        """Test Protocol classes define expected methods."""
        # SearchTool protocol
        assert hasattr(SearchTool, 'search')

        # LLMClient protocol
        assert hasattr(LLMClient, 'invoke')
