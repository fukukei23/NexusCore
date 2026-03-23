import pytest

tsc = pytest.importorskip("nexuscore.utils.tree_sitter_checker")


def test_report_generator_counts_symbols():
    res = {
        "a.py": tsc.AnalysisResult(
            success=True,
            language="python",
            source_stats={"line_count": 10},
            semantic_symbols={"functions": [{"name": "f"}], "classes": []},
            errors={"has_syntax_errors": False},
        )
    }
    summary = tsc.ReportGenerator.generate_summary(res)
    assert summary["overview"]["total_files"] == 1
    assert summary["symbols"]["functions"] == 1


def test_cli_main_parser_failure(monkeypatch, capsys, tmp_path):
    # force setup_parsers to fail
    class DummyAnalyzer(tsc.SemanticAnalyzer):
        def setup_parsers(self, languages=None):
            return False

    monkeypatch.setattr(tsc, "SemanticAnalyzer", DummyAnalyzer)
    monkeypatch.setattr(tsc, "Fore", type("F", (), {"RED": ""}))
    argv = ["prog", str(tmp_path)]
    monkeypatch.setattr(tsc.sys, "argv", argv)
    rc = tsc.main()
    assert rc == 1
