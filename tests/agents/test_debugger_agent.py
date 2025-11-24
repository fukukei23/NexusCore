import pytest

from nexuscore.agents.debugger_agent import DebuggerAgent


@pytest.fixture(autouse=True)
def disable_llm_router(monkeypatch):
    from nexuscore.agents import base_agent

    monkeypatch.setattr(base_agent, "LLMRouter", None)


def test_debug_and_patch_requires_files():
    agent = DebuggerAgent()
    result = agent.debug_and_patch("err", {}, "/tmp")
    assert result["error"] == "No files provided for debugging."


def test_debug_and_patch_includes_solution(monkeypatch):
    agent = DebuggerAgent()
    files = {"src/foo.py": "print('hello')"}

    solution = {"error_signature": "ValueError", "cause": "bad call", "solution_pattern": {"type": "patch"}}
    monkeypatch.setattr(agent, "_find_solution_from_kb", lambda log: solution)

    def fake_generate(error_log, source_path, source_code, instruction):
        fake_generate.instruction = instruction
        return source_code.replace("hello", "world")

    fake_generate.instruction = None
    agent._generate_fixed_code = fake_generate
    agent._create_diff = lambda src, fixed, path, proj: f"diff:{path}"

    result = agent.debug_and_patch("ValueError", files, "/tmp")

    assert result["patch"] == "diff:src/foo.py"
    assert "solution_pattern" in result["solution_used"]
    assert fake_generate.instruction.startswith("A known solution was found")
