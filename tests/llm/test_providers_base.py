import logging

from nexuscore.llm.providers.base import BaseLLM


class DummyLLM(BaseLLM):
    def execute(self, prompt: str, system_prompt: str, **kwargs) -> str:
        return ""


def test_record_usage_casts_to_int():
    llm = DummyLLM("openai:gpt-5")
    llm.record_usage(prompt_tokens="12", completion_tokens=3.7)
    assert llm._last_usage == {"prompt_tokens": 12, "completion_tokens": 3}


def test_log_error_emits_message(caplog):
    llm = DummyLLM("local")
    caplog.set_level(logging.ERROR, logger="DummyLLM")
    exc = RuntimeError("boom")
    llm.log_error("during-call", exc, "response body")
    assert any("during-call" in record.message for record in caplog.records)
    assert any("response_snippet" in record.message for record in caplog.records)
