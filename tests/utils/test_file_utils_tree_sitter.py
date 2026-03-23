from nexuscore.utils import file_utils, tree_sitter_checker


def test_create_project_structure_builds_files(tmp_path):
    files = [
        {"name": "src/module", "type": "folder"},
        {"name": "src/module/main.py", "type": "file", "content": "print('ok')"},
        {"name": "README.md", "type": "file", "content": "# doc"},
    ]

    file_utils.create_project_structure(str(tmp_path), files)

    assert (tmp_path / "src" / "module").is_dir()
    assert (tmp_path / "src" / "module" / "main.py").read_text(encoding="utf-8") == "print('ok')"
    assert (tmp_path / "README.md").exists()


def test_file_list_display_handles_list():
    class Dummy:
        def __init__(self, name):
            self.name = name

    result = file_utils.file_list_display([Dummy("a.txt"), Dummy("b.txt")])
    assert "a.txt" in result and "b.txt" in result
    assert file_utils.file_list_display([]) == "（ファイル未選択）"


def test_tree_sitter_unavailable(monkeypatch):
    monkeypatch.setattr(tree_sitter_checker, "TREE_SITTER_AVAILABLE", False)
    analyzer = tree_sitter_checker.SemanticAnalyzer()
    available, message = analyzer.check_availability()
    assert available is False
    assert "Missing" in message


def test_analyze_source_code_without_parser():
    analyzer = tree_sitter_checker.SemanticAnalyzer()
    analyzer.parsers = {}  # no parsers setup
    result = analyzer.analyze_source_code("print('hi')", language="python")
    assert result.success is False
    assert "Parser not available" in result.to_json()
