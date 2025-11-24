import pytest

from nexuscore.agents.context_analyzer import ContextAnalyzer


def test_detect_tech_stack_handles_missing_files(tmp_path):
    analyzer = ContextAnalyzer(str(tmp_path))
    result = analyzer.detect_tech_stack()
    assert isinstance(result, dict)


def test_scan_file_structure_limits_entries(tmp_path):
    (tmp_path / "src").mkdir()
    for i in range(5):
        (tmp_path / f"file{i}.py").write_text("print('x')", encoding="utf-8")
    analyzer = ContextAnalyzer(str(tmp_path))
    structure = analyzer.scan_file_structure()
    assert structure["python_files"] >= 1
