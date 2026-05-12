"""
Manual smoke test for LLMRouter.

Usage:
    python -m pytest tests/llm/test_llm_router_smoke.py -v --run-integration
    python -m nexuscore.llm.llm_router  (legacy entrypoint — redirects here)
"""

import json
import logging

import pytest

from nexuscore.llm.llm_router import LLMRouter
from nexuscore.llm.runtime import REQUEST_TIMEOUT

_logger = logging.getLogger(__name__)

pytestmark = pytest.mark.skipif(
    "not config.getoption('--run-integration')",
    reason="Smoke test requires --run-integration flag",
)


def test_smoke_debug(router: LLMRouter) -> None:
    sample_prompt_debug = "pytestの失敗ログを分析し、原因を特定して修正案を提示してください。"
    _logger.info("Sample Prompt (Debug): %s...", sample_prompt_debug[:80])
    llm_client_debug = router.get_llm_for_task(sample_prompt_debug)
    _logger.info("--> Selected Client: %s", type(llm_client_debug.inner).__name__)
    _logger.info("    Model: %s", llm_client_debug.model_name)
    _logger.info("    Task Type: %s", llm_client_debug.task_type)

    resp_debug = llm_client_debug.execute(
        prompt=sample_prompt_debug,
        system_prompt="You are a world-class debugging assistant.",
        as_json=False,
    )
    _logger.info("LLM Response:\n%s...", resp_debug[:200])
    assert len(resp_debug) > 0


def test_smoke_json(router: LLMRouter) -> None:
    sample_prompt_json = "項目A:foo\n項目B:bar をJSONに"
    _logger.info("Sample Prompt (JSON): %s...", sample_prompt_json[:80])
    llm_client_json = router.get_llm_for_task(sample_prompt_json)
    _logger.info("--> Selected Client: %s", type(llm_client_json.inner).__name__)
    _logger.info("    Model: %s", llm_client_json.model_name)

    resp_json = llm_client_json.execute(
        prompt=sample_prompt_json,
        system_prompt="You output JSON only.",
        as_json=True,
    )
    _logger.info("LLM Response (JSON):\n%s...", resp_json[:200])
    assert len(resp_json) > 0


@pytest.fixture(scope="module")
def router():
    _logger.info("--- LLMRouter Smoke Test (v2.4.0-split) ---")
    r = LLMRouter()
    _logger.info("TASK MAP: %s", json.dumps(r.task_model_map, indent=2, ensure_ascii=False))
    yield r
    _logger.info("--- SmokeTest Finished ---")
    _logger.info("--- (Logs: %s) ---", r.call_log_path)
    _logger.info("--- (Timeout: %ss) ---", REQUEST_TIMEOUT)
