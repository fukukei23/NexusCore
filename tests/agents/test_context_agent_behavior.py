import json
from pathlib import Path

import pytest

from nexuscore.analyzer import context_agent as context_agent_module
from nexuscore.analyzer.context_agent import ContextAgent


@pytest.fixture(autouse=True)
def stub_policy_interface(monkeypatch):
    class DummyInterface:
        def launch_and_wait_for_input(self, timeout=180):
            return {"policy": "ui"}

    monkeypatch.setattr(context_agent_module, "PolicyInterface", lambda: DummyInterface())


def test_load_cached_context(tmp_path, monkeypatch):
    cache = tmp_path / ".nexus_context.json"
    cache.write_text(json.dumps({"cached": True}), encoding="utf-8")

    class DummyAnalyzer:
        def __init__(self, root):
            pass

        def detect_tech_stack(self):
            return {}

        def scan_file_structure(self):
            return {}

        def parse_dependencies(self):
            return {}

        def detect_environment(self):
            return {}

    monkeypatch.setattr(context_agent_module, "ContextAnalyzer", DummyAnalyzer)
    monkeypatch.setattr(ContextAgent, "request_human_dev_policy", lambda self: {"policy": "human"})
    monkeypatch.setattr(ContextAgent, "_create_enhanced_context", lambda self: {})

    agent = ContextAgent(project_root=str(tmp_path))
    assert agent.context_profile == {"cached": True}


def test_create_new_context_with_enhanced(tmp_path, monkeypatch):
    class DummyAnalyzer:
        def __init__(self, root):
            self.root = root

        def detect_tech_stack(self):
            return {"stack": ["python"]}

        def scan_file_structure(self):
            return {"files": []}

        def parse_dependencies(self):
            return {"deps": []}

        def detect_environment(self):
            return {"env": "test"}

    monkeypatch.setattr(context_agent_module, "ContextAnalyzer", DummyAnalyzer)
    monkeypatch.setattr(ContextAgent, "request_human_dev_policy", lambda self: {"policy": "manual"})

    (tmp_path / "requirements.txt").write_text("gradio\npytest", encoding="utf-8")
    (tmp_path / "src").mkdir()
    (tmp_path / "tests").mkdir()
    agent = ContextAgent(project_root=str(tmp_path))

    profile = agent.context_profile
    assert profile["dev_policy"] == {"policy": "manual"}
    assert "tech_stack_detailed" in profile
    assert Path(agent.context_cache_file).exists()
