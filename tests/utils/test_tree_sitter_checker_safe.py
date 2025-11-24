import pytest

tsc = pytest.importorskip("nexuscore.utils.tree_sitter_checker")


def test_semantic_analyzer_availability(monkeypatch):
    monkeypatch.setattr(tsc, "TREE_SITTER_AVAILABLE", False, raising=False)
    analyzer = tsc.SemanticAnalyzer()
    ok, msg = analyzer.check_availability()
    assert ok is False
    assert "Missing" in msg


def test_setup_parsers_handles_failure(monkeypatch):
    monkeypatch.setattr(tsc, "TREE_SITTER_AVAILABLE", True, raising=False)
    monkeypatch.setattr(tsc, "get_language", lambda lang: "lang")

    def bad_get_parser(lang):
        raise RuntimeError("boom")

    monkeypatch.setattr(tsc, "get_parser", bad_get_parser)
    analyzer = tsc.SemanticAnalyzer()
    result = analyzer.setup_parsers(["python"])
    assert result is False
