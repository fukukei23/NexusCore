import os
from pathlib import Path

from nexuscore.agents.context_analyzer import ContextAnalyzer


def test_safe_parse_requirements_large_file(tmp_path, monkeypatch, capsys):
    req = tmp_path / "requirements.txt"
    req.write_text("a\n" * 10, encoding="utf-8")
    monkeypatch.setattr(os.path, "getsize", lambda p: 10**8)  # force large
    analyzer = ContextAnalyzer(str(tmp_path))
    frameworks = analyzer._safe_parse_requirements()
    assert frameworks  # fallback list


def test_safe_detect_tools_handles_exception(monkeypatch):
    analyzer = ContextAnalyzer(str(Path.cwd()))

    def bad_exists(path):
        raise RuntimeError("boom")

    monkeypatch.setattr(os.path, "exists", bad_exists)
    tools = analyzer._safe_detect_tools()
    assert isinstance(tools, list)
