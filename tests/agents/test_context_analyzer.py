from nexuscore.analyzer.context_analyzer import (
    ContextAnalyzer,
    _fallback_list,
    _fallback_value,
)


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


def test_fallback_list_uses_default_when_unset(monkeypatch):
    """環境変数未設定時はデフォルト値をパースして返す（後方互換）。"""
    monkeypatch.delenv("NEXUSCORE_CONTEXT_FALLBACK_FRAMEWORKS", raising=False)
    assert _fallback_list("NEXUSCORE_CONTEXT_FALLBACK_FRAMEWORKS", "gradio,openai") == [
        "gradio",
        "openai",
    ]


def test_fallback_list_reads_env_when_set(monkeypatch):
    """環境変数設定時はその値でフォールバックを上書きする。"""
    monkeypatch.setenv("NEXUSCORE_CONTEXT_FALLBACK_FRAMEWORKS", "flask, fastapi")
    assert _fallback_list("NEXUSCORE_CONTEXT_FALLBACK_FRAMEWORKS", "gradio,openai") == [
        "flask",
        "fastapi",
    ]


def test_fallback_list_strips_whitespace_and_empties(monkeypatch):
    """空要素・前後空白を除外する。"""
    monkeypatch.setenv("NEXUSCORE_CONTEXT_FALLBACK_FRAMEWORKS", " , a ,, b ,")
    assert _fallback_list("NEXUSCORE_CONTEXT_FALLBACK_FRAMEWORKS", "gradio") == ["a", "b"]


def test_fallback_value_uses_default_when_unset(monkeypatch):
    """環境変数未設定時はデフォルト値を返す（後方互換）。"""
    monkeypatch.delenv("NEXUSCORE_CONTEXT_FALLBACK_PYTHON_VERSION", raising=False)
    assert _fallback_value("NEXUSCORE_CONTEXT_FALLBACK_PYTHON_VERSION", "3.11+") == "3.11+"


def test_fallback_value_reads_env_when_set(monkeypatch):
    """環境変数設定時はその値でフォールバックを上書きする。"""
    monkeypatch.setenv("NEXUSCORE_CONTEXT_FALLBACK_PYTHON_VERSION", "3.12")
    assert _fallback_value("NEXUSCORE_CONTEXT_FALLBACK_PYTHON_VERSION", "3.11+") == "3.12"


def test_safe_parse_requirements_fallback_honors_env(tmp_path, monkeypatch):
    """requirements.txt が大きすぎる場合、環境変数のフォールバックが使われること。"""
    monkeypatch.setenv("NEXUSCORE_CONTEXT_FALLBACK_FRAMEWORKS", "flask,fastapi")
    req_file = tmp_path / "requirements.txt"
    req_file.write_text("gradio==3.0.0\n" * 100000, encoding="utf-8")
    analyzer = ContextAnalyzer(str(tmp_path))
    assert analyzer._safe_parse_requirements() == ["flask", "fastapi"]
