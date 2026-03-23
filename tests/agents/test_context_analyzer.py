from nexuscore.agents.context_analyzer import ContextAnalyzer


def test_safe_parse_requirements(tmp_path):
    req = tmp_path / "requirements.txt"
    req.write_text("gradio==4.0.0\npytest>=7.0\n# comment\n", encoding="utf-8")
    analyzer = ContextAnalyzer(str(tmp_path))
    packages = analyzer._safe_parse_requirements()
    assert "gradio" in packages
    assert "pytest" in packages


def test_safe_detect_tools(tmp_path):
    (tmp_path / "pytest.ini").write_text("", encoding="utf-8")
    (tmp_path / ".flake8").write_text("", encoding="utf-8")
    analyzer = ContextAnalyzer(str(tmp_path))
    tools = analyzer._safe_detect_tools()
    assert "pytest" in tools
    assert "flake8" in tools


def test_scan_file_structure_counts_files(tmp_path):
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "main.py").write_text("print('hi')", encoding="utf-8")
    analyzer = ContextAnalyzer(str(tmp_path))
    structure = analyzer.scan_file_structure()
    assert structure["total_files"] >= 1
    assert "root" in structure["modules"] or "src" in " ".join(structure["modules"])
