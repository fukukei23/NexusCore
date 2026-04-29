import json

import pytest

from nexuscore.analyzer.context_agent import ContextAgent


@pytest.fixture(autouse=True)
def disable_heavy_dependencies(monkeypatch):
    from nexuscore.analyzer import context_agent as context_module
    from nexuscore.config import policy_interface as policy_module

    class DummyPolicy:
        def launch_and_wait_for_input(self, timeout=180):
            return {
                "test_import_policy": "関数を直接埋め込み",
                "error_language": "日本語",
                "quality_requirements": ["docstring必須"],
                "security_policy": ["APIキー環境変数管理"],
            }

    class DummyAnalyzer:
        def __init__(self, project_root):
            self.project_root = project_root

        def detect_tech_stack(self):
            return {"lang": "python"}

        def scan_file_structure(self):
            return {"files": []}

        def parse_dependencies(self):
            return {"requirements": []}

        def detect_environment(self):
            return {"platform": "ws"}

    monkeypatch.setattr(policy_module, "PolicyInterface", DummyPolicy)
    monkeypatch.setattr(context_module, "PolicyInterface", DummyPolicy)
    monkeypatch.setattr(context_module, "ContextAnalyzer", DummyAnalyzer)


@pytest.fixture
def sandbox(tmp_path, monkeypatch):
    project = tmp_path / "proj"
    project.mkdir()
    (project / ".git").mkdir()
    (project / "requirements.txt").write_text("gradio\npytest\n", encoding="utf-8")
    (project / "src").mkdir()
    (project / "tests").mkdir()
    cache_file = project / ".nexus_context.json"
    if cache_file.exists():
        cache_file.unlink()
    monkeypatch.chdir(project)
    return project


def test_load_or_create_context_creates_cache(sandbox):
    agent = ContextAgent(project_root=str(sandbox))
    data = agent.get_context()
    assert data["dev_policy"]["test_import_policy"] == "関数を直接埋め込み"
    cache_path = sandbox / ".nexus_context.json"
    assert cache_path.exists()
    loaded = json.loads(cache_path.read_text(encoding="utf-8"))
    assert loaded["version"] == "2.1-stable"


def test_update_context_refreshes_timestamp(sandbox):
    agent = ContextAgent(project_root=str(sandbox))
    first_updated = agent.context_profile["last_updated"]
    agent.update_context()
    assert agent.context_profile["last_updated"] != first_updated


def test_get_error_prevention_rules_reflect_policy(monkeypatch, sandbox):
    agent = ContextAgent(project_root=str(sandbox))
    agent.context_profile["dev_policy"] = {
        "test_import_policy": "関数を直接埋め込み",
        "error_language": "日本語",
        "quality_requirements": ["docstring必須", "エラーハンドリング必須"],
        "security_policy": ["APIキー環境変数管理"],
    }
    rules = agent.get_error_prevention_rules()
    assert rules["use_japanese_errors"] is True
    assert rules["require_docstring"] is True
    assert rules["use_env_vars"] is True
