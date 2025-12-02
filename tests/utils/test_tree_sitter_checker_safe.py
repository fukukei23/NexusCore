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

    # get_language と get_parser は tree_sitter_language_pack からインポートされているため、
    # モジュール内で直接モックする必要がある
    # ただし、tree_sitter_language_pack がインストールされていない場合はスキップ
    try:
        import tree_sitter_language_pack
    except ImportError:
        pytest.skip("tree_sitter_language_pack not installed")

    def bad_get_language(lang):
        return "lang"

    def bad_get_parser(lang):
        raise RuntimeError("boom")

    monkeypatch.setattr(tree_sitter_language_pack, "get_language", bad_get_language)
    monkeypatch.setattr(tree_sitter_language_pack, "get_parser", bad_get_parser)

    analyzer = tsc.SemanticAnalyzer()
    result = analyzer.setup_parsers(["python"])
    assert result is False
